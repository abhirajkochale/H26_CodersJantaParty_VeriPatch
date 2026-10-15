import concurrent.futures
import copy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from . import ai
from .execution import verify, compare, digitalocean
from .inspection import inspect
from .patches import validate_edits, diff_edits, apply_edits
from .safety import repository_url
from .store import Store

store = Store(os.getenv('VERIPATCH_STATE','.veripatch'))
pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

def now(): return datetime.now(timezone.utc).isoformat()

def git(args, cwd=None):
    p = subprocess.run(['git','-c','core.hooksPath=/dev/null',*args],cwd=cwd,capture_output=True,text=True,timeout=120,
                       env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_NOSYSTEM':'1'})
    if p.returncode: raise RuntimeError(p.stderr[-4000:])
    return p.stdout.strip()

def step(run, stage):
    run['stage']=stage; run['updated_at']=now(); run['events'].append(dict(at=now(),stage=stage)); store.save(run)

def execute_analysis(run, release):
    try:
        folder=store.directory(run['id']); repo=folder/'baseline-repo'
        step(run,'Cloning public repository')
        git(['clone','--quiet','--no-recurse-submodules',run['url'],str(repo)])
        if run.get('requested_commit'): git(['checkout','--detach',run['requested_commit']],repo)
        run['commit']=git(['rev-parse','HEAD'],repo)
        step(run,'Inspecting repository and dependencies')
        inspection=inspect(repo)
        run.update({k:v for k,v in inspection.items() if k!='files'})
        step(run,'Executing '+run['provider']+' baseline')
        try:
            protected = tests_manifest(repo)
            run['baseline']=verify(repo,run['provider'],run['url'],run['commit'],[])
            if tests_manifest(repo) != protected:
                run['baseline']['success'] = False
                raise RuntimeError('Baseline tests changed during execution; result rejected')
        except Exception as e:
            run['baseline']={'error':str(e),'provider':run['provider']}; run['errors'].append('Baseline: '+str(e))
        # Execution failures are separate evidence, never silently attached to every source observation.
        for i,c in enumerate(run['baseline'].get('commands',[])):
            if c['exit_code']:
                fid='X-'+str(i)
                run['findings'].append(dict(id=fid,rule='execution-failure',title=c['name']+' failed',dependency=None,severity='high',
                    evidence_status='execution_verified',repair_status='unresolved',detail='Actual command exited '+str(c['exit_code']),
                    evidence=[dict(id='E-'+fid,kind='execution_verified',command=c['argv'],cwd=c['cwd'],provider=run['provider'],
                                   line=None,path=None,snippet=(c['stderr'] or c['stdout'])[-2500:])]))
        inspection['findings']=run['findings']
        step(run,'Qwen is analyzing bounded evidence batches')
        # Each batch is independent; one model failure does not discard other analyses.
        for start in range(0,max(1,len(run['findings'])),4):
            batch={**inspection,'findings':run['findings'][start:start+4]}
            try:
                result=ai.analyze(batch,run.get('baseline',{}))[0]
                run['ai'].append(result)
                for proposed in result['response']['recommendations']:
                    proposal=dict(proposed,id='P-'+uuid.uuid4().hex[:10],status='proposed',evidence_status='ai_hypothesis')
                    try:
                        supplied_paths = {item['path'] for item in result.get('source_context', [])}
                        if any(edit['path'] not in supplied_paths for edit in proposal['edits']):
                            raise ValueError('Patch references a file outside supplied relevant source context')
                        proposal['diff']=diff_edits(repo,proposal['edits'])
                    except Exception as e: proposal.update(status='invalid',error=str(e),diff='')
                    run['proposals'].append(proposal)
                    if proposal['status']=='proposed':
                        for f in run['findings']:
                            if f['id'] in proposal['issue_ids']: f['repair_status']='proposed'
            except Exception as e:
                run['ai'].append(dict(status='failed',model=ai.MODEL,error=str(e),issue_ids=[f['id'] for f in batch['findings']]))
                run['errors'].append('Qwen: '+str(e))
            step(run,f"Qwen batches completed: {len(run['ai'])}")
        run['status']='completed_with_errors' if run['errors'] else 'completed'
        step(run,'Analysis complete · review proposals')
    except Exception as e:
        run['status']='failed'; run['errors'].append(str(e)); step(run,'Analysis failed')
    finally: release()

def recover_interrupted():
    for old in store.list():
        if old['status'] == 'running':
            old['status'] = 'interrupted'
            old['stage'] = 'Coordinator stopped before operation completed'
            old['errors'].append('Interrupted operation; inspect retained artifacts and start a new analysis or retry a proposal.')
            store.save(old)

def start(url,provider,commit=None):
    url=repository_url(url)
    if commit and not __import__('re').fullmatch('[0-9a-f]{40}',commit): raise ValueError('Invalid commit')
    if provider not in {'LOCAL','DIGITALOCEAN'}: raise ValueError('Invalid provider')
    release=store.reserve()
    try:
        recover_interrupted()
        run=dict(id=uuid.uuid4().hex,url=url,provider=provider,created_at=now(),updated_at=now(),status='running',stage='Queued',
                 requested_commit=commit,events=[],findings=[],dependencies=[],ai=[],proposals=[],errors=[],limitations=['AI recommendations require human review. No claim of exhaustive bug discovery.'])
        store.save(run); pool.submit(execute_analysis,run,release)
        return run
    except Exception: release(); raise

def tests_manifest(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(root).rglob('*.py')
            if ('test' in p.parts or 'tests' in p.parts or p.name.startswith('test_') or p.name=='conftest.py') and not p.is_symlink()}

def execute_apply(run, proposal,release):
    try:
        folder=store.directory(run['id']); source=folder/'baseline-repo'
        patched=folder/('patched-'+uuid.uuid4().hex[:8])
        step(run,'Creating separate patch working copy')
        git(['clone','--quiet','--no-hardlinks',str(source),str(patched)])
        git(['checkout','--detach',run['commit']],patched)
        protected=tests_manifest(patched)
        apply_edits(patched,proposal['edits'])
        if protected != tests_manifest(patched): raise RuntimeError('Protected tests changed')
        proposal['status']='applied'
        for f in run['findings']:
            f['repair_status'] = 'proposed' if any(f['id'] in p['issue_ids'] and p['status']!='invalid' for p in run['proposals']) else 'unresolved'
            f.pop('verification_support', None)
        for f in run['findings']:
            if f['id'] in proposal['issue_ids']: f['repair_status']='applied'
        run['applied_proposal_id']=proposal['id']
        run['applied_edits']=proposal['edits']
        step(run,'Executing '+run['provider']+' patched verification')
        run['verification']=verify(patched,run['provider'],run['url'],run['commit'],proposal['edits'])
        if protected != tests_manifest(patched): raise RuntimeError('Tests modified during execution; verification rejected')
        run['comparison']=compare(run.get('baseline',{}),run['verification'])
        run['reinspection']={k:v for k,v in inspect(patched).items() if k!='files'}
        remaining={(f['rule'],e.get('path')) for f in run['reinspection']['findings'] for e in f['evidence']}
        for f in run['findings']:
            if f['id'] in proposal['issue_ids']:
                supported=all((f['rule'],e.get('path')) not in remaining for e in f['evidence']) and f['evidence_status']=='source_observed'
                f['repair_status']='checks_passed' if run['comparison']['checks_passed'] and supported else ('needs_review' if run['comparison']['checks_passed'] else 'failed')
                f['verification_support']={'profile_passed':run['comparison']['checks_passed'],'static_observation_absent':supported,'execution_commands':[c['name'] for c in run['verification']['commands']]}
        proposal['status']='checks_passed' if run['comparison']['checks_passed'] else 'failed'
        run.setdefault('verification_attempts', []).append(copy.deepcopy(dict(proposal_id=proposal['id'],at=now(),edits=proposal['edits'],verification=run['verification'],comparison=run['comparison'])))
        run['status']='completed'; step(run,'Verification complete · inspect results')
    except Exception as e:
        proposal['status']='failed'; proposal['error']=str(e)
        for f in run['findings']:
            if f['id'] in proposal['issue_ids']: f['repair_status']='failed'
        run.setdefault('verification_attempts', []).append(dict(proposal_id=proposal['id'],at=now(),error=str(e)))
        run['status']='completed_with_errors'; run['errors'].append('Patch verification: '+str(e)); step(run,'Patch verification failed')
    finally: release()

def start_apply(id,proposal_id):
    release=store.reserve()
    try:
        recover_interrupted()
        run=store.get(id)
        if run['status']=='running': raise ValueError('Run is busy')
        proposal=next((p for p in run['proposals'] if p['id']==proposal_id),None)
        if not proposal or proposal['status']=='invalid': raise ValueError('No valid proposal')
        validate_edits(store.directory(id)/'baseline-repo',proposal['edits'])
        run['status']='running'
        for field in ['verification','comparison','reinspection','applied_proposal_id','applied_edits']: run.pop(field,None)
        store.save(run); pool.submit(execute_apply,run,proposal,release)
        return run
    except Exception: release(); raise

def execute_plan(run, release):
    """A bounded synthesis pass connects executed failures and declaration conflicts."""
    try:
        step(run, 'Qwen is planning an integrated baseline repair')
        repo = store.directory(run['id'])/'baseline-repo'
        inspection = inspect(repo)
        selected = [f for f in run['findings'] if f['evidence_status']=='execution_verified' or f['rule'] in {'dependency-conflict','legacy-test-runner'}]
        if not selected: raise ValueError('No execution/dependency findings available for an integrated plan')
        if len(selected)>8: raise ValueError('Too many interacting findings for a bounded synthesis; review smaller proposals first')
        inspection['findings'] = selected
        result = ai.analyze(inspection,run.get('baseline',{}),batch_size=len(selected)+1)[0]
        run['ai'].append(result)
        supplied_paths = {item['path'] for item in result.get('source_context',[])}
        for proposed in result['response']['recommendations']:
            proposal = dict(proposed,id='P-'+uuid.uuid4().hex[:10],status='proposed',evidence_status='ai_hypothesis',integrated=True)
            try:
                if any(edit['path'] not in supplied_paths for edit in proposal['edits']): raise ValueError('Patch is outside supplied relevant source context')
                proposal['diff'] = diff_edits(repo,proposal['edits'])
            except Exception as e: proposal.update(status='invalid',error=str(e),diff='')
            run['proposals'].append(proposal)
            if proposal['status']=='proposed':
                for f in run['findings']:
                    if f['id'] in proposal['issue_ids']: f['repair_status']='proposed'
        run['status']='completed_with_errors' if run['errors'] else 'completed'
        step(run, 'Integrated planning complete · review the diff')
    except Exception as e:
        run['ai'].append(dict(status='failed',model=ai.MODEL,error=str(e),phase='integrated-plan'))
        run['errors'].append('Integrated Qwen planning: '+str(e));run['status']='completed_with_errors'
        step(run,'Integrated planning failed')
    finally: release()

def start_plan(id):
    release=store.reserve()
    try:
        recover_interrupted()
        run=store.get(id)
        if not run.get('commit'): raise ValueError('Repository baseline is not available')
        run['status']='running';store.save(run);pool.submit(execute_plan,run,release)
        return run
    except Exception: release();raise

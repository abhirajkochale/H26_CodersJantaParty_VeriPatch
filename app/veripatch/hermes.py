"""Official Hermes subprocess integration; application owns all tool authority."""
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time
import uuid
import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from .ai import Proposal
from .inspection import inspect
from .patches import preflight, diff_edits

ROOT=Path(__file__).resolve().parents[2]
MODEL='veripatch-qwen3.5:4b-64k'

def readiness():
    proof=ROOT/'docs/evidence/hermes-compatibility.json'
    result={'model':MODEL,'installed':(ROOT/'.hermes-runtime/source/run_agent.py').exists(),'compatible':False}
    try:
        p=json.loads(proof.read_text());result['compatible']=p['compatibility_proven'];result['version']=p['hermes']['derived_version']
        tags=httpx.get('http://127.0.0.1:11434/api/tags',timeout=3).json()['models']
        result['model_installed']=any(m['name']==MODEL for m in tags)
    except Exception as e: result['error']=str(e)
    return result

def execution_summary(result):
    return {**{k:v for k,v in result.items() if k!='commands'},'commands':[
        {**{k:v for k,v in c.items() if k not in {'stdout','stderr'}},'stdout':c.get('stdout','')[-3500:] if c.get('exit_code') else c.get('stdout','')[-400:],'stderr':c.get('stderr','')[-3500:] if c.get('exit_code') else c.get('stderr','')[-400:]} for c in result.get('commands',[])]}

class Tools:
    def __init__(self,run,root,service,phase):
        self.run,self.root,self.service,self.phase=run,Path(root),service,phase
        self.files=inspect(self.root)['files'];self.read={};self.proposed=False
    def call(self,name,args):
        r=self.run;s=self.service
        if not isinstance(args,dict):raise ValueError('Arguments must be an object')
        if name=='inspect_repository':
            if args:raise ValueError('No arguments accepted')
            return dict(files=sorted(self.files),dependencies=r['dependencies'],findings=[{**f,'evidence':[{**e,'snippet':e.get('snippet','')[-900:]} for e in f['evidence']]} for f in r['findings']],phase=self.phase,
                attempts=max(len(r.get('verification_attempts',[])),len(r.get('approvals',[]))),max_attempts=3,baseline=execution_summary(r.get('baseline',{})),
                verification=execution_summary(r.get('verification',{})),comparison=r.get('comparison'),approval_required=True)
        if name=='read_repository_file':
            if set(args)!={'path'} or not isinstance(args['path'],str):raise ValueError('Exactly one path required')
            path=args['path']
            if Path(path).is_absolute():
                try:path=str(Path(path).relative_to(self.root))
                except ValueError:raise ValueError('Absolute path outside target repository')
            target=self.root/path
            if path not in self.files or target.is_symlink() or not target.resolve().is_relative_to(self.root.resolve()):raise ValueError('Use an exact RELATIVE path from inspect_repository files, e.g. requirements.txt. Absolute Hermes runtime paths are not target files.')
            content=target.read_text()
            if content!=self.files[path]:raise ValueError('File changed since inventory')
            self.read[path]=content[:16000]
            return dict(path=path,content=content[:16000],truncated=len(content)>16000,sha256=hashlib.sha256(content.encode()).hexdigest())
        if name=='verify_repository':
            if r.get('verification_rejected'):raise ValueError('Verification rejected because original tests changed; stop')
            if args:raise ValueError('No commands or arguments accepted')
            key='baseline' if self.phase=='analyze' else 'verification'
            if key not in r:
                if self.phase!='analyze' and not r.get('active_approval'):raise ValueError('Human approval required')
                protected=s.tests_manifest(self.root)
                s.step(r,'Hermes requested '+key+' LOCAL verification')
                r[key]=s.verify(self.root,'LOCAL',r['url'],r['commit'],r.get('applied_edits',[]) if key=='verification' else [])
                if protected!=s.tests_manifest(self.root):
                    r['verification_rejected']=True;r[key]['success']=False;r[key]['error']='Original tests changed; rejected execution'
                    s.store.save(r)
                    raise RuntimeError('Original tests changed; rejected execution')
                if key=='baseline':
                    for i,c in enumerate(r[key].get('commands',[])):
                        if c['exit_code']:
                            fid='X-'+str(i)
                            r['findings'].append(dict(id=fid,rule='execution-failure',title=c['name']+' failed',dependency=None,severity='high',evidence_status='execution_verified',repair_status='unresolved',detail='Actual command exited '+str(c['exit_code']),evidence=[dict(id='E-'+fid,kind='execution_verified',command=c['argv'],cwd=c['cwd'],provider='LOCAL',path=None,line=None,snippet=(c['stderr'] or c['stdout'])[-2500:])]))
                else:
                    r['comparison']=s.compare(r['baseline'],r[key]);r['reinspection']={k:v for k,v in inspect(self.root).items() if k!='files'}
                    r.setdefault('verification_attempts',[]).append(copy.deepcopy(dict(at=s.now(),proposal_id=r['applied_proposal_id'],edits=r['applied_edits'],approval=r['active_approval'],verification=r[key],comparison=r['comparison'])))
                    remaining={(f['rule'],e.get('path')) for f in r['reinspection']['findings'] for e in f['evidence']}
                    for f in r['findings']:
                        if f['rule']=='execution-failure':
                            command=f['title'].removesuffix(' failed');fixed=any(c['name']==command and c['exit_code']==0 for c in r[key]['commands'])
                        else: fixed=all((f['rule'],e.get('path')) not in remaining for e in f['evidence'])
                        f['repair_status']='fixed' if fixed else 'unresolved'
                        f['verification_support']=dict(profile_passed=r['comparison']['checks_passed'],observation_absent_or_command_passed=fixed)
                    proposal=next(p for p in r['proposals'] if p['id']==r['applied_proposal_id'])
                    proposal['status']='checks_passed' if r['comparison']['checks_passed'] else 'failed'
                s.store.save(r)
            # Check actual context of the running model, not merely configured metadata.
            return execution_summary(r[key])
        if name in {'propose_patch','propose_dependency_patch'}:raise ValueError('Hermes patch generation is disabled; use the guarded direct-Qwen review workflow')
        raise ValueError('Unknown tool')

def converse(run,root,service,phase):
    state=run.setdefault('hermes',dict(model=MODEL,events=[],sessions=[]))
    folder=service.store.directory(run['id']);tools=Tools(run,root,service,phase)
    prompt='Inspect this actual repository using inspect_repository and read_repository_file. Execute verify_repository to obtain its baseline (cached if retained). Summarize actual dependency conflicts and command failures with uncertainty. This is inspection only: do not propose or apply repairs. Direct Qwen performs separate repair planning after human review.'
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','LANG','LC_ALL','USER','SHELL'}}
    session=dict(phase=phase,started_at=service.now(),mode='inspection_only',limit_seconds=600);state['sessions'].append(session)
    event_offset=len(state['events'])
    with (service.store.root/'model.lock').open('a') as lock, (folder/('hermes-'+uuid.uuid4().hex[:8]+'.stderr.log')).open('w') as logs:
        fcntl.flock(lock,fcntl.LOCK_EX)
        proc=subprocess.Popen([str(ROOT/'scripts/hermes-python.sh'),str(ROOT/'hermes/driver.py')],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=logs,text=True,start_new_session=True)
        messages=queue.Queue()
        def reader():
            for line in proc.stdout:messages.put(line)
            messages.put(None)
        threading.Thread(target=reader,daemon=True).start()
        proc.stdin.write(json.dumps(dict(model=MODEL,prompt=prompt,root=str(Path(root).resolve())))+'\n');proc.stdin.flush()
        deadline=time.monotonic()+600
        try:
            while time.monotonic()<deadline:
                try:line=messages.get(timeout=1)
                except queue.Empty:continue
                if line is None:raise RuntimeError('Hermes exited before a final result; inspect retained stderr log')
                if len(line)>2_000_000:raise ValueError('Hermes protocol message too large')
                try:event=json.loads(line)
                except ValueError:continue # official bootstrap progress, never agent activity
                if event.get('type')=='identity':
                    state.update(identity=event);service.store.save(run)
                    if event['hermes'].get('commit')!='db44c46208f1b421b4ecb7e56bf9d68b0423906f' or event['hermes'].get('dirty'):raise RuntimeError('Hermes source differs from tested pinned unmodified runtime')
                elif event.get('type')=='tool_request':
                    e=dict(id=uuid.uuid4().hex,at=service.now(),phase=phase,tool=event['tool'],arguments=event['arguments'],status='running');state['events'].append(e);service.store.save(run)
                    start=time.monotonic()
                    try:result=tools.call(e['tool'],e['arguments'])
                    except Exception as exc:result={'error':str(exc)}
                    e.update(result=result,status='error' if 'error' in result else 'completed',duration_seconds=round(time.monotonic()-start,2));service.store.save(run)
                    proc.stdin.write(json.dumps(result)+'\n');proc.stdin.flush()
                elif event.get('type')=='final':
                    session.update(completed_at=service.now(),result=event['result'])
                    if not event['result'].get('completed'):raise RuntimeError('Hermes did not complete: '+str(event['result'].get('error') or event['result'].get('final_response')))
                    if not any(m.get('role')=='tool' for m in event['result'].get('messages',[])):raise RuntimeError('Hermes returned no actual tool messages')
                    if phase=='verify' and not any(e['tool']=='verify_repository' and e['status']=='completed' for e in state['events'][event_offset:]):raise RuntimeError('Hermes did not request real verification')
                    if phase=='analyze' and 'baseline' not in run:raise RuntimeError('No actual baseline available')
                    # Preserve the actual served context as separate evidence.
                    ps=httpx.get('http://127.0.0.1:11434/api/ps',timeout=5).json()
                    state['ollama_ps']=ps
                    served=next((m for m in ps.get('models',[]) if m.get('name')==MODEL),{})
                    if served.get('context_length',0)<64000:raise RuntimeError('Ollama served less than Hermes minimum 64000 context')
                    state['model_metadata']=[m for m in httpx.get('http://127.0.0.1:11434/api/tags',timeout=5).json().get('models',[]) if m.get('name')==MODEL]
                    return
            raise TimeoutError('Hermes exceeded 10 minute bounded session')
        except Exception as exc:
            session.update(completed_at=service.now(),error=str(exc))
            raise
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            fcntl.flock(lock,fcntl.LOCK_UN)
            service.store.save(run)

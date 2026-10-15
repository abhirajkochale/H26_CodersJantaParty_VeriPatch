"""Explicit execution backends and equivalent-profile comparisons."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from .patches import patch_hash

ROOT = Path(__file__).resolve().parents[2]

def digitalocean(request):
    host = os.getenv('DO_SSH_HOST','')
    user = os.getenv('DO_SSH_USER','veripatch')
    port = os.getenv('DO_SSH_PORT','22')
    if not host: raise RuntimeError('DigitalOcean not configured.')
    if not re.fullmatch(r'[A-Za-z0-9.-]+',host) or host.startswith('-') or not re.fullmatch(r'[a-z_][a-z0-9_-]*',user) or not port.isdigit():
        raise ValueError('Invalid SSH configuration')
    argv = ['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10','-p',port]
    key = os.getenv('DO_SSH_KEY_PATH')
    if key: argv += ['-i',str(Path(key).expanduser())]
    argv += [user+'@'+host,'/opt/veripatch/bin/worker']
    try:
        proc = subprocess.run(argv,input=json.dumps(dict(version='1',**request)),capture_output=True,text=True,timeout=1200)
    except subprocess.TimeoutExpired as e: raise RuntimeError('SSH/worker deadline exceeded; remote Docker deadline will clean up the job') from e
    try: result = json.loads(proc.stdout)
    except ValueError as e: raise RuntimeError('Worker returned invalid JSON: '+proc.stderr[-2000:]) from e
    if proc.returncode or result.get('error'): raise RuntimeError(result.get('error') or proc.stderr[-4000:] or 'SSH failed')
    if result.get('worker_version')!='1' or result.get('provider')!='DIGITALOCEAN' or not str(result.get('droplet_id','')).isdigit():
        raise RuntimeError('Worker identity/version mismatch')
    if request.get('action')!='smoke' and (result.get('commit')!=request['commit'] or result.get('patch_hash')!=request['patch_hash']):
        raise RuntimeError('Worker commit/patch hash mismatch')
    return result

def verify(root, provider, url, commit, edits):
    if provider == 'DIGITALOCEAN':
        return digitalocean(dict(action='verify',url=url,commit=commit,edits=edits,patch_hash=patch_hash(edits)))
    if provider != 'LOCAL': raise ValueError('Unknown provider')
    worker = ROOT/'worker/execute.py'
    process = subprocess.run([sys.executable,str(worker),str(root)],capture_output=True,text=True,timeout=1100)
    if process.returncode: raise RuntimeError(process.stdout[-3000:] or process.stderr[-3000:])
    result = json.loads(process.stdout)
    if result.get('error'): raise RuntimeError(result['error'])
    result.update(provider='LOCAL',commit=commit,patch_hash=patch_hash(edits),isolation='Disposable virtual environment. Trusted-code LOCAL runner; not a security sandbox.')
    return result

def compare(before, after):
    reasons = []
    if before.get('provider') != after.get('provider'): reasons.append('Execution providers differ')
    if before.get('profile') != after.get('profile'): reasons.append('Verification profiles differ')
    before_scope = [c['name'] for c in before.get('commands',[])]
    after_scope = [c['name'] for c in after.get('commands',[])]
    if before_scope != after_scope: reasons.append('Verification command scope changed')
    a, b = before.get('counts'), after.get('counts')
    if a is None or b is None: reasons.append('Test collection/counts unavailable')
    elif b['collected'] < a['collected']: reasons.append('Test collection decreased')
    elif b['skipped'] > a['skipped']: reasons.append('Additional skipped tests')
    if not after.get('success'): reasons.append('One or more verification commands failed')
    if not b or b['collected']==0 or b['passed']!=b['collected']: reasons.append('No complete passing test suite')
    return dict(checks_passed=not reasons,reasons=reasons,before_counts=a,after_counts=b,
                scope=dict(before=before_scope,after=after_scope),
                claim='Passing checks support only the executed profile; individual issues still require reinspection/review.')

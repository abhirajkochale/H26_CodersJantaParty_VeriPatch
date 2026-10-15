#!/usr/bin/env python3
"""SSH stdin/stdout protocol v1. No user-selected commands. Runs only on a DO Droplet."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid

from veripatch.patches import apply_edits, patch_hash
from veripatch.safety import repository_url

VERSION = '1'

def call(args, cwd=None, timeout=120):
    p = subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=timeout,env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_NOSYSTEM':'1'})
    if p.returncode: raise RuntimeError(p.stderr[-4000:] or p.stdout[-4000:])
    return p.stdout.strip()

def identity():
    with urllib.request.urlopen('http://169.254.169.254/metadata/v1/id',timeout=3) as r:
        droplet = r.read(128).decode().strip()
    if not droplet.isdigit(): raise RuntimeError('DigitalOcean metadata did not return a Droplet ID')
    return droplet

def handle(request):
    if request.get('version') != VERSION: raise ValueError('Worker version mismatch')
    droplet = identity()
    docker = call(['docker','version','--format','{{.Server.Version}}'],timeout=15)
    if request.get('action') == 'smoke': return dict(worker_version=VERSION, provider='DIGITALOCEAN', droplet_id=droplet,docker_version=docker)
    url = repository_url(request['url'])
    commit = request['commit']
    if not re.fullmatch('[0-9a-f]{40}',commit): raise ValueError('Invalid commit')
    edits = request.get('edits',[])
    digest = patch_hash(edits)
    if digest != request.get('patch_hash'): raise ValueError('Patch hash mismatch')
    job = Path(tempfile.mkdtemp(prefix='vp-',dir=os.getenv('VP_JOB_ROOT','/var/lib/veripatch')))
    name = 'vp-'+uuid.uuid4().hex
    try:
        repo = job/'repo'
        call(['git','-c','core.hooksPath=/dev/null','clone','--quiet','--no-recurse-submodules',url,str(repo)])
        call(['git','checkout','--detach',commit],repo)
        actual = call(['git','rev-parse','HEAD'],repo)
        if actual != commit: raise RuntimeError('Exact commit mismatch')
        if edits: apply_edits(repo,edits)
        shutil.copyfile(Path(__file__).with_name('execute.py'),job/'execute.py')
        # Container sees only disposable job data, no host keys or coordinator state.
        argv = ['docker','run','--rm','--name',name,'--cpus','2','--memory','2g','--pids-limit','128',
                '--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,size=256m',
                '--ulimit','fsize=131072:131072','-v',str(job)+':/job','-w','/job/repo','python:3.12-slim',
                'python','/job/execute.py','/job/repo']
        raw = call(argv,timeout=1100)
        result = json.loads(raw)
        if result.get('error'): raise RuntimeError(result['error'])
        result.update(provider='DIGITALOCEAN',droplet_id=droplet,commit=actual,patch_hash=digest,container_image='python:3.12-slim',container_image_id=call(['docker','image','inspect','python:3.12-slim','--format','{{.Id}}']))
        return result
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=20)
        shutil.rmtree(job,ignore_errors=True)

if __name__ == '__main__':
    try:
        raw = sys.stdin.read(500_001)
        if len(raw)>500_000: raise ValueError('Request too large')
        print(json.dumps(handle(json.loads(raw))))
    except Exception as e:
        print(json.dumps(dict(error=str(e),worker_version=VERSION))); sys.exit(1)

"""CLI shares the same runtime pipeline and persisted artifacts as the dashboard."""
import argparse
import json
import os
from pathlib import Path
import time

# Optional local config, never shell-evaluated.
if Path('.env').exists():
    for line in Path('.env').read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            key,value=line.split('=',1)
            if key.strip() in {'OLLAMA_MODEL','OLLAMA_BASE_URL','OLLAMA_TIMEOUT','VERIPATCH_STATE','DO_SSH_HOST','DO_SSH_USER','DO_SSH_PORT','DO_SSH_KEY_PATH'}:
                os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))

from . import service, ai
from .capsule import export
from .execution import digitalocean

def main():
    p=argparse.ArgumentParser(prog='veripatch')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('serve')
    sub.add_parser('model-smoke')
    sub.add_parser('worker-smoke')
    a=sub.add_parser('analyze');a.add_argument('url');a.add_argument('--provider',choices=['LOCAL','DIGITALOCEAN'],default='LOCAL')
    a.add_argument('--engine',choices=['HERMES','DIRECT'],default='DIRECT')
    a.add_argument('--commit',help='Optional exact 40-character commit for reproducible runs')
    a=sub.add_parser('plan');a.add_argument('run_id')
    a=sub.add_parser('apply');a.add_argument('run_id');a.add_argument('proposal_id');a.add_argument('--approve',action='store_true',help='Human approval of the displayed exact patch')
    a=sub.add_parser('capsule');a.add_argument('run_id');a.add_argument('--output',default='capsule.zip')
    sub.add_parser('list')
    args=p.parse_args()
    if args.command=='serve':
        import uvicorn
        uvicorn.run('veripatch.api:app',host='127.0.0.1',port=8000)
    elif args.command=='model-smoke': print(json.dumps(ai.smoke(),indent=2))
    elif args.command=='worker-smoke': print(json.dumps(digitalocean({'action':'smoke'}),indent=2))
    elif args.command=='list': print(json.dumps([{k:r.get(k) for k in ['id','url','status','stage']} for r in service.store.list()],indent=2))
    elif args.command=='capsule': print(export(service.store.get(args.run_id),args.output))
    else:
        run=service.start(args.url,args.provider,args.commit,args.engine) if args.command=='analyze' else service.start_plan(args.run_id) if args.command=='plan' else service.start_apply(args.run_id,args.proposal_id,approved=args.approve)
        previous=None
        while True:
            run=service.store.get(run['id'])
            if run['stage']!=previous: print(run['stage'],flush=True);previous=run['stage']
            if run['status']!='running': break
            time.sleep(2)
        print(json.dumps({k:v for k,v in run.items() if k not in {'baseline','verification','reinspection'}},indent=2))
        if run['status']=='failed':raise SystemExit(1)

if __name__=='__main__':
    try: main()
    except (RuntimeError, ValueError, OSError, KeyError) as e:
        print(json.dumps({'error':str(e)}),file=__import__('sys').stderr)
        raise SystemExit(1)

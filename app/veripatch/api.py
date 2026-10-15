import os
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from . import ai, service
from .capsule import export
from .execution import digitalocean

@asynccontextmanager
async def lifespan(app):
    try: release=service.store.reserve()
    except RuntimeError: release=None
    if release:
        try: service.recover_interrupted()
        finally: release()
    yield

app=FastAPI(title='VeriPatch',version='1.0.0',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])
ORIGINS={'http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000'}
app.add_middleware(CORSMiddleware,allow_origins=list(ORIGINS),allow_methods=['GET','POST'],allow_headers=['Content-Type'])

@app.middleware('http')
async def local_origin(request:Request,call_next):
    if request.method=='POST' and request.headers.get('origin') and request.headers['origin'] not in ORIGINS:
        return JSONResponse({'detail':'Origin not allowed'},status_code=403)
    return await call_next(request)

class CreateRun(BaseModel):
    url:str=Field(max_length=300)
    provider:str='LOCAL'

class Apply(BaseModel):
    proposal_id:str=Field(max_length=50)

def lookup(id):
    try:return service.store.get(id)
    except (ValueError,FileNotFoundError):raise HTTPException(404,'Run not found')

@app.get('/api/health')
def health():
    model={'model':ai.MODEL,'available':False}
    try:
        r=httpx.get(ai.BASE+'/api/tags',timeout=3);r.raise_for_status()
        model['available']=any(x['name']==ai.MODEL for x in r.json().get('models',[]))
        if not model['available']:model['error']='Configured model is not installed'
    except Exception as e:model['error']=str(e)
    return {'ollama':model,'digitalocean':{'configured':bool(os.getenv('DO_SSH_HOST')),'message':'Configured; use connection check' if os.getenv('DO_SSH_HOST') else 'DigitalOcean not configured.'},'python':'3.12 required','local':'Trusted-code runner; disposable venv, not a sandbox.'}

@app.post('/api/model/smoke')
def model_smoke():
    try:return ai.smoke()
    except Exception as e:raise HTTPException(502,str(e))

@app.post('/api/worker/smoke')
def worker_smoke():
    try:return digitalocean({'action':'smoke'})
    except Exception as e:raise HTTPException(502,str(e))

@app.get('/api/runs')
def runs():
    return [{k:r.get(k) for k in ['id','url','commit','provider','created_at','status','stage']} for r in service.store.list()]

@app.get('/api/runs/{id}')
def get_run(id:str):return lookup(id)

@app.post('/api/runs',status_code=202)
def create(body:CreateRun):
    try:return service.start(body.url,body.provider)
    except ValueError as e:raise HTTPException(400,str(e))
    except RuntimeError as e:raise HTTPException(409,str(e))

@app.post('/api/runs/{id}/apply',status_code=202)
def apply(id:str,body:Apply):
    lookup(id)
    try:return service.start_apply(id,body.proposal_id)
    except (ValueError,StopIteration) as e:raise HTTPException(400,str(e))
    except RuntimeError as e:raise HTTPException(409,str(e))

@app.post('/api/runs/{id}/plan',status_code=202)
def plan(id:str):
    lookup(id)
    try:return service.start_plan(id)
    except ValueError as e:raise HTTPException(400,str(e))
    except RuntimeError as e:raise HTTPException(409,str(e))

@app.get('/api/runs/{id}/capsule')
def capsule(id:str):
    run=lookup(id)
    destination=service.store.directory(id)/('capsule-'+__import__('uuid').uuid4().hex+'.zip')
    export(run,destination)
    from starlette.background import BackgroundTask
    return FileResponse(destination,filename='veripatch-'+id[:8]+'.zip',media_type='application/zip',background=BackgroundTask(destination.unlink,missing_ok=True))

frontend=Path(__file__).resolve().parents[2]/'frontend/dist'
if frontend.exists(): app.mount('/',StaticFiles(directory=frontend,html=True),name='dashboard')

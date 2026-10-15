import importlib.util
import json
from pathlib import Path
import subprocess
import pytest
from fastapi.testclient import TestClient
from veripatch import service
from veripatch.api import app
from veripatch.patches import validate_edits
from veripatch.store import Store
from veripatch.execution import compare

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'store',Store(tmp_path))
    return TestClient(app)

def test_api_input_origins_missing_runs(client):
    assert client.get('/api/runs').json()==[]
    assert client.get('/api/runs/'+'a'*32).status_code==404
    assert client.post('/api/runs',json=dict(url='file:///tmp/a')).status_code==400
    assert client.post('/api/runs',headers={'Origin':'https://evil.example'},json=dict(url='https://github.com/u/r')).status_code==403
    assert client.post('/api/worker/smoke',json={}).status_code==502

def test_api_download_is_real_capsule(client):
    run=dict(id='a'*32,url='https://github.com/u/r',created_at='now',status='completed',findings=[],dependencies=[],ai=[],proposals=[],errors=[])
    service.store.save(run)
    response=client.get('/api/runs/'+run['id']+'/capsule')
    assert response.status_code==200 and response.content[:2]==b'PK'
    assert not list(service.store.directory(run['id']).glob('capsule-*.zip'))

def test_interrupted_recovery_and_history(client):
    old=dict(id='a'*32,url='https://github.com/u/r',created_at='now',status='running',stage='tests',errors=[])
    service.store.save(old)
    service.recover_interrupted()
    assert service.store.get(old['id'])['status']=='interrupted'
    assert client.get('/api/runs').json()[0]['status']=='interrupted'

def test_no_test_configuration_or_skip_edits(tmp_path):
    path=tmp_path/'pyproject.toml'
    path.write_text('[tool.pytest.ini_options]\ntestpaths=["tests"]\n')
    with pytest.raises(ValueError,match='Protected pytest'):
        validate_edits(tmp_path,[dict(path=path.name,before='["tests"]',after='["nothing"]')])
    (tmp_path/'x.py').write_text('x=1')
    with pytest.raises(ValueError,match='suppress'):
        validate_edits(tmp_path,[dict(path='x.py',before='x=1',after='import pytest\npytest.skip("ignore",allow_module_level=True)')])
    with pytest.raises(ValueError,match='invalid Python'):
        validate_edits(tmp_path,[dict(path='x.py',before='x=1',after='x = try:')])

def test_verification_scope_change_rejected():
    base=dict(provider='LOCAL',profile='v1',success=True,counts=dict(collected=1,passed=1,failed=0,skipped=0),commands=[dict(name='tests'),dict(name='nose-compatibility')])
    after={**base,'commands':[dict(name='tests')]}
    assert 'Verification command scope changed' in compare(base,after)['reasons']

ROOT=Path(__file__).resolve().parents[2]
def load_worker():
    spec=importlib.util.spec_from_file_location('vp_worker_server',ROOT/'worker/server.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def test_worker_requires_real_metadata(monkeypatch):
    worker=load_worker()
    def offline(*a,**kw):raise OSError('metadata unreachable')
    monkeypatch.setattr(worker.urllib.request,'urlopen',offline)
    with pytest.raises(OSError):worker.handle(dict(version='1',action='smoke'))
    with pytest.raises(ValueError,match='version'):worker.handle(dict(version='wrong',action='smoke'))

def test_worker_smoke_docker_failure(monkeypatch):
    worker=load_worker()
    monkeypatch.setattr(worker,'identity',lambda:'123')
    def broken(*a,**kw):raise RuntimeError('Docker unavailable')
    monkeypatch.setattr(worker,'call',broken)
    with pytest.raises(RuntimeError,match='Docker unavailable'):worker.handle(dict(version='1',action='smoke'))

def test_worker_hash_rejected_before_clone(monkeypatch):
    worker=load_worker()
    monkeypatch.setattr(worker,'identity',lambda:'123')
    monkeypatch.setattr(worker,'call',lambda *a,**kw:'27.0')
    with pytest.raises(ValueError,match='hash mismatch'):
        worker.handle(dict(version='1',action='verify',url='https://github.com/u/r',commit='a'*40,edits=[],patch_hash='forged'))

def test_local_runs_use_fresh_env_and_strip_host_secrets(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('vp_execute',ROOT/'worker/execute.py')
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    repo=tmp_path/'repo';repo.mkdir()
    monkeypatch.setenv('PRIVATE_COORDINATOR_TOKEN','never-pass-to-target')
    env_paths=[]
    def fake(name,argv,cwd,env,timeout=180):
        assert 'PRIVATE_COORDINATOR_TOKEN' not in env
        if name=='create-env':env_paths.append(argv[-1])
        if name=='tests':Path(env['VP_COUNTS']).write_text(json.dumps(dict(collected=1,passed=1,failed=0,skipped=0,errors=0)))
        return dict(name=name,argv=argv,cwd=str(cwd),exit_code=0,stdout='unit-test fixture only',stderr='',duration_seconds=0,timed_out=False,logs_truncated=False)
    monkeypatch.setattr(worker,'command',fake)
    worker.execute(repo);worker.execute(repo)
    assert len(set(env_paths))==2

def test_execution_timeout_records_actual_failure(tmp_path):
    spec=importlib.util.spec_from_file_location('vp_execute_timeout',ROOT/'worker/execute.py')
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    home=tmp_path/'home';home.mkdir()
    result=worker.command('deadline',[__import__('sys').executable,'-c','import time; time.sleep(5)'],tmp_path,dict(HOME=str(home),PATH='/usr/bin:/bin'),timeout=.05)
    assert result['timed_out'] and result['exit_code']==124

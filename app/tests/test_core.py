import json
from pathlib import Path
import subprocess
import zipfile
import httpx
import pytest
from veripatch import ai
from veripatch.capsule import export
from veripatch.execution import compare, digitalocean
from veripatch.inspection import compatible, inspect
from veripatch.patches import apply_edits, diff_edits, patch_hash, validate_edits
from veripatch.safety import repository_url
from veripatch.store import Store

@pytest.mark.parametrize('values,result', [(['==1.10.13','>=2'],'conflicting'),(['>=1,<3','==2.1'],'compatible'),(['>=2','<2'],'conflicting'),(['>=2','<=2'],'compatible'),(['>2','<=2'],'conflicting'),(['==2','!=2'],'conflicting'),(['==1.*','>=1.1'],'compatible'),(['>=70','==75.8.0'],'compatible')])
def test_constraints(values,result):assert compatible(values)==result

def test_inventory_dynamic_provenance(tmp_path):
    (tmp_path/'requirements.txt').write_text('pydantic==1\nrequests>=2\n')
    (tmp_path/'pyproject.toml').write_text('[project]\ndependencies=["pydantic>=2"]\n')
    (tmp_path/'thing.py').write_text('import requests\nimport made_up_distribution\nrequests.get("https://example.org")\n')
    (tmp_path/'.env').write_text('TOKEN=never-share')
    (tmp_path/'binary.png').write_bytes(b'\x00\x01')
    result=inspect(tmp_path)
    assert len([f for f in result['findings'] if f['rule']=='dependency-conflict'])==2
    assert all(f['evidence_status']=='source_observed' and f['repair_status']=='unresolved' for f in result['findings'])
    assert any(f['rule']=='undeclared-import' for f in result['findings'])
    assert result['dependencies'][1]['usage']
    assert '.env' not in result['files']
    assert len(result['coverage']['skipped'])==2

def test_patch_exact_and_conflict(tmp_path):
    (tmp_path/'x.py').write_text('old\n')
    edits=[dict(path='x.py',before='old',after='new')]
    assert '+new' in diff_edits(tmp_path,edits)
    apply_edits(tmp_path,edits)
    assert (tmp_path/'x.py').read_text()=='new\n'
    with pytest.raises(ValueError,match='conflict'):apply_edits(tmp_path,edits)
    (tmp_path/'x.py').write_text('old old')
    with pytest.raises(ValueError,match='exactly once'):validate_edits(tmp_path,edits)
    assert patch_hash(edits)==patch_hash(edits)

@pytest.mark.parametrize('path',['../x.py','/tmp/x.py','.git/config','tests/test_a.py','test_a.py','a/conftest.py','.env','id_rsa.key','a\\x.py'])
def test_protected_paths(tmp_path,path):
    with pytest.raises(ValueError):validate_edits(tmp_path,[dict(path=path,before='old',after='new')])

def test_symlink_and_transaction(tmp_path):
    (tmp_path/'x.py').write_text('old')
    (tmp_path/'link.py').symlink_to(tmp_path/'x.py')
    with pytest.raises(ValueError):apply_edits(tmp_path,[dict(path='x.py',before='old',after='new'),dict(path='link.py',before='old',after='new')])
    assert (tmp_path/'x.py').read_text()=='old'

@pytest.mark.parametrize('url',['https://github.com/user/repo?token=x','file:///tmp/a','https://github.com/../a','https://user:pass@github.com/u/r','https://evil.org/u/r'])
def test_public_url(url):
    with pytest.raises(ValueError):repository_url(url)

def mock_client(content):
    calls=[]
    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200,json={'model':'qwen-test','message':{'content':content}})
    return httpx.Client(transport=httpx.MockTransport(handle)),calls

def test_valid_qwen_schema():
    client,calls=mock_client(json.dumps(dict(summary='observed',recommendations=[],unresolved_issue_ids=[])))
    r=ai.chat({'findings':[]},client)
    assert r['evidence_status']=='ai_hypothesis' and r['model']=='qwen-test'
    assert calls[0]['format']['type']=='object' and calls[0]['stream'] is False
    assert calls[0]['options']['temperature']<=.2

def test_invalid_qwen_bounded_retry():
    client,calls=mock_client('not JSON')
    with pytest.raises(ValueError,match='corrective retry'):ai.chat({'findings':[]},client)
    assert len(calls)==2

def test_unknown_issue_rejected():
    client,calls=mock_client(json.dumps(dict(summary='bad',recommendations=[],unresolved_issue_ids=['invented'])))
    with pytest.raises(ValueError):ai.chat({'findings':[{'id':'real'}]},client)
    assert len(calls)==2

def test_unavailable_model():
    def fail(request):raise httpx.ConnectError('unavailable')
    client=httpx.Client(transport=httpx.MockTransport(fail))
    with pytest.raises(httpx.ConnectError):ai.chat({'findings':[]},client)

def result(n=3,skip=0,provider='LOCAL',success=True):
    return dict(provider=provider,profile='v1',success=success,counts=dict(collected=n,passed=n-skip,skipped=skip,failed=0,errors=0))

def test_before_after_no_dropped_tests():
    assert compare(result(),result())['checks_passed']
    assert not compare(result(),result(2))['checks_passed']
    assert not compare(result(),result(skip=1))['checks_passed']
    assert not compare(result(),result(provider='DIGITALOCEAN'))['checks_passed']
    assert not compare(result(0),result(0))['checks_passed']
    assert not compare(result(),result(success=False))['checks_passed']

def test_ssh_unconfigured(monkeypatch):
    monkeypatch.delenv('DO_SSH_HOST',raising=False)
    with pytest.raises(RuntimeError,match='not configured'):digitalocean({'action':'smoke'})

@pytest.mark.parametrize('response',[subprocess.CompletedProcess([],255,'','Permission denied'),subprocess.CompletedProcess([],0,'not json',''),subprocess.CompletedProcess([],0,json.dumps({'worker_version':'0','provider':'DIGITALOCEAN','droplet_id':'123'}),'')])
def test_ssh_failures(monkeypatch,response):
    monkeypatch.setenv('DO_SSH_HOST','example.org')
    monkeypatch.setattr(subprocess,'run',lambda *a,**kw:response)
    with pytest.raises(RuntimeError):digitalocean({'action':'smoke'})

def test_ssh_timeout(monkeypatch):
    monkeypatch.setenv('DO_SSH_HOST','example.org')
    def timeout(*a,**kw):raise subprocess.TimeoutExpired('ssh',1)
    monkeypatch.setattr(subprocess,'run',timeout)
    with pytest.raises(RuntimeError,match='deadline'):digitalocean({'action':'smoke'})

def test_ssh_host_keys_and_patch_identity(monkeypatch):
    monkeypatch.setenv('DO_SSH_HOST','example.org')
    def mock(args,**kw):
        assert 'StrictHostKeyChecking=yes' in args
        assert args[-1]=='/opt/veripatch/bin/worker'
        return subprocess.CompletedProcess([],0,json.dumps(dict(worker_version='1',provider='DIGITALOCEAN',droplet_id='123',commit='wrong',patch_hash='wrong')),'')
    monkeypatch.setattr(subprocess,'run',mock)
    with pytest.raises(RuntimeError,match='hash mismatch'):digitalocean(dict(action='verify',commit='abc',patch_hash='xyz'))

def test_capsule_completeness_secret_exclusion(tmp_path):
    run=dict(id='a'*32,url='https://github.com/u/r',commit='b'*40,status='completed',findings=[],dependencies=[],ai=[],errors=[],
             files={'.env':'secret=SHOULD_NOT_APPEAR'},baseline={'commands':[dict(name='tests',stdout='token=PRIVATE ghp_abcdefghijklmnop',stderr='')]},verification={},
             proposals=[dict(id='P-one',diff='example')])
    path=export(run,tmp_path/'cap.zip')
    with zipfile.ZipFile(path) as z:
        assert {'capsule.json','REPORT.md','REPRODUCE.md','baseline/result.json','ai/responses.json','verification/result.json','patches/P-one.diff','baseline/logs/00-tests.stdout.log'}<=set(z.namelist())
        all_bytes=b''.join(z.read(p) for p in z.namelist())
        assert b'SHOULD_NOT_APPEAR' not in all_bytes and b'PRIVATE' not in all_bytes and b'ghp_' not in all_bytes

def test_atomic_store_lock(tmp_path):
    store=Store(tmp_path)
    store.save(dict(id='a'*32,created_at='now',status='running'))
    assert store.get('a'*32)['status']=='running'
    release=store.reserve()
    with pytest.raises(RuntimeError):store.reserve()
    other=Store(tmp_path)
    with pytest.raises(RuntimeError):other.reserve()
    release();other.reserve()()
    with pytest.raises(ValueError):store.get('../escape')

def test_bounded_context_preserves_middle_exception():
    text=('setup details\n'*100)+"E   ImportError: missing_public_symbol from dependency\n"+('warnings\n'*100)
    excerpt=ai.diagnostic_excerpt(text,150)
    assert 'ImportError: missing_public_symbol' in excerpt and len(excerpt)<=150

def test_preflight_rejects_swapped_conflicts_and_accepts_alignment(tmp_path):
    from veripatch.patches import preflight
    (tmp_path/'requirements.txt').write_text('pydantic==1.10.13\n')
    (tmp_path/'pyproject.toml').write_text('[project]\ndependencies=["pydantic>=2"]\n')
    observed=inspect(tmp_path)['findings'];ids=[f['id'] for f in observed]
    swapped=[dict(path='requirements.txt',before='pydantic==1.10.13',after='pydantic>=2'),dict(path='pyproject.toml',before='pydantic>=2',after='pydantic==1.10.13')]
    with pytest.raises(ValueError,match='retains referenced'):preflight(tmp_path,swapped,observed,ids)
    good=[dict(path='pyproject.toml',before='pydantic>=2',after='pydantic==1.10.13')]
    assert preflight(tmp_path,good,observed,ids)['dependency_constraints']['pydantic']=='compatible'
    assert 'pydantic>=2' in (tmp_path/'pyproject.toml').read_text()

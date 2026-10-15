"""Inspection/approval boundary fixtures; never exported as real execution evidence."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from veripatch import service
from veripatch.hermes import Tools
from veripatch.inspection import inspect
from veripatch.patches import diff_edits
from veripatch.store import Store

@pytest.fixture
def boundary(tmp_path):
    store=Store(tmp_path/'state');root=store.directory('a'*32)/'baseline-repo';root.mkdir(parents=True)
    (root/'requirements.txt').write_text('pydantic==1.10.13\n')
    (root/'pyproject.toml').write_text('[project]\ndependencies=["pydantic>=2"]\n')
    (root/'tests').mkdir();(root/'tests/test_original.py').write_text('assert True\n')
    (root/'.env').write_text('PRIVATE_TOKEN=unavailable')
    run=dict(id='a'*32,engine='DIRECT',created_at='fixture-time',status='completed',events=[],errors=[],proposals=[],baseline={'commands':[]},**{k:v for k,v in inspect(root).items() if k!='files'})
    backend=SimpleNamespace(store=store,now=lambda:'fixture-time')
    return Tools(run,root,backend,'analyze'),run,root

def test_tool_reads_real_contents_and_rejects_escapes(boundary,tmp_path):
    tools,_,root=boundary
    assert '.env' not in tools.call('inspect_repository',{})['files']
    assert tools.call('read_repository_file',{'path':'requirements.txt'})['content']=='pydantic==1.10.13\n'
    for path in ['../requirements.txt','.env',str(tmp_path/'outside')]:
        with pytest.raises(ValueError):tools.call('read_repository_file',{'path':path})
    (root/'requirements.txt').unlink();(root/'requirements.txt').symlink_to(root/'pyproject.toml')
    with pytest.raises(ValueError):tools.call('read_repository_file',{'path':'requirements.txt'})

@pytest.mark.parametrize('tool',['propose_patch','propose_dependency_patch'])
def test_hermes_cannot_generate_or_apply_repairs(boundary,tool):
    tools,run,root=boundary;before=(root/'requirements.txt').read_text()
    with pytest.raises(ValueError,match='disabled'):tools.call(tool,{'dependency':'pydantic','constraint':'>=2'})
    assert not run['proposals'] and (root/'requirements.txt').read_text()==before

def test_fixed_verification_has_no_arbitrary_command_interface(boundary):
    tools,_,_=boundary
    with pytest.raises(ValueError,match='No commands'):tools.call('verify_repository',{'command':'echo fake'})
    with pytest.raises(ValueError,match='Unknown tool'):tools.call('terminal',{'command':'echo fake'})

def test_retained_baseline_is_returned_without_new_execution(boundary):
    tools,run,_=boundary
    result=tools.call('verify_repository',{})
    assert result==run['baseline'] and not run.get('verification')

def test_plugin_exposes_inspection_only():
    path=Path(__file__).resolve().parents[2]/'hermes/maintenance-plugin/__init__.py'
    spec=importlib.util.spec_from_file_location('fixture_plugin',path);plugin=importlib.util.module_from_spec(spec);spec.loader.exec_module(plugin)
    registrations={};plugin.register(SimpleNamespace(register_tool=lambda **kw:registrations.update({kw['name']:kw})))
    assert set(registrations)=={'inspect_repository','read_repository_file','verify_repository'}

def test_direct_workflow_requires_human_approval_and_attempt_budget(boundary,monkeypatch):
    tools,run,_=boundary;monkeypatch.setattr(service,'store',tools.service.store);service.store.save(run)
    with pytest.raises(ValueError,match='Explicit human approval'):service.start_apply(run['id'],'none')
    run['verification_attempts']=[{}, {}, {}];service.store.save(run)
    with pytest.raises(ValueError,match='Maximum three'):service.start_apply(run['id'],'none',approved=True)

def test_direct_workflow_rejects_changed_reviewed_diff(boundary,monkeypatch):
    tools,run,root=boundary;monkeypatch.setattr(service,'store',tools.service.store)
    edits=[dict(path='requirements.txt',before='pydantic==1.10.13',after='pydantic>=2')]
    run['proposals']=[dict(id='Q-fixture',status='proposed',issue_ids=[f['id'] for f in run['findings']],edits=edits,diff=diff_edits(root,edits))]
    service.store.save(run);(root/'requirements.txt').write_text('# changed after review\npydantic==1.10.13\n')
    with pytest.raises(ValueError,match='Reviewed diff changed'):service.start_apply(run['id'],'Q-fixture',approved=True)
    assert not service.store.get(run['id']).get('approvals')

def test_partial_dependency_success_does_not_hide_remaining_failures(boundary):
    _,run,_=boundary
    run['findings'] += [dict(id='X-4',rule='execution-failure',title='dependency-check failed'),dict(id='X-7',rule='execution-failure',title='nose-compatibility failed')]
    run.update(reinspection={'findings':[]},verification={'commands':[{'name':'dependency-check','exit_code':0},{'name':'nose-compatibility','exit_code':1}]},comparison={'checks_passed':False})
    proposal={'issue_ids':[f['id'] for f in run['findings'] if f['rule']=='dependency-conflict']}
    service.reconcile_verification_findings(run,proposal)
    assert all(f['repair_status']=='fixed' for f in run['findings'] if f['rule']=='dependency-conflict')
    assert next(f for f in run['findings'] if f['id']=='X-4')['repair_status']=='fixed'
    assert next(f for f in run['findings'] if f['id']=='X-7')['repair_status']=='unresolved'

"""The simplified Actor preserves behavior and can enter through the real CLI."""
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import requests
from src.skill_evolution.v24.benchmarks.alfworld.actor import run_task_skill as actor, skill_runtime as rt
from src.skill_evolution.v24.benchmarks.alfworld.actor import run_task_upstream as transport
from src.adapters.alfworld import run_task_skill as old_actor, skill_runtime as old_rt
from src.adapters.alfworld import run_task_upstream as old_transport
from tests.adapters.alfworld.test_skill_episode import FakeEnvironment


@pytest.mark.parametrize('name', ['chat','project_action','action_error','action_diagnostic','action_feedback_messages','build_messages'])
def test_actor_decision_functions_unchanged(name):
    assert inspect.getsource(getattr(transport,name)) == inspect.getsource(getattr(old_transport,name))


def test_episode_and_skill_injection_behavior_unchanged():
    assert inspect.getsource(actor.run_episode) == inspect.getsource(old_actor.run_episode)
    for name in ('build_skill_messages','inject_skill','execution_protocol'):
        assert inspect.getsource(getattr(rt,name)) == inspect.getsource(getattr(old_rt,name))
    for feedback in (False,True):
        for injection in (rt.LEGACY_INJECTION,rt.SKILLOPT_INJECTION):
            new = rt.execution_protocol(50,injection,output_format=rt.ACTION_ONLY_OUTPUT,
                                        retry_invalid_actions=feedback,action_feedback=feedback)
            old = old_rt.execution_protocol(50,injection,output_format=rt.ACTION_ONLY_OUTPUT,
                                            retry_invalid_actions=feedback,action_feedback=feedback)
            assert rt.protocol_settings(new) == rt.protocol_settings(old)


@pytest.mark.parametrize('dry', [False, True])
def test_actual_actor_cli_uses_simple_records(tmp_path, monkeypatch, dry):
    (tmp_path/'train').mkdir()
    task={'id':'train:0000','gamefile':'game'}
    (tmp_path/'train/items.json').write_text(json.dumps([task]))
    (tmp_path/'game').write_text('offline fixture')
    env=FakeEnvironment(win=True); env.seed=lambda _:None; env.close=lambda:None
    monkeypatch.setattr(actor,'SPLIT_ROOT',tmp_path)
    monkeypatch.setattr(actor,'load_dotenv',lambda *a,**k:None)
    monkeypatch.setattr(actor,'installed_versions',lambda:{})
    monkeypatch.setattr(actor,'environment_modules',lambda:(SimpleNamespace(start=lambda *a,**k:env,EnvInfos=lambda **k:None),lambda **k:None))
    monkeypatch.setenv('ALFWORLD_DATA',str(tmp_path))
    monkeypatch.setenv('OPENAI_BASE_URL','https://offline.invalid')
    monkeypatch.setenv('OPENAI_API_KEY','offline-test')
    def post(request, **kwargs):
        response=requests.Response();response.status_code=200;response.request=request;response.url=request.url
        response._content=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'<action>look</action>'}}]}).encode()
        return response
    monkeypatch.setattr(requests.adapters.HTTPAdapter,'send',staticmethod(post))
    args=['--output-root',str(tmp_path/'runs'),'--model','offline','--strict-response','--archive-responses',
          '--retry-invalid-actions','--action-feedback','--output-format',rt.ACTION_ONLY_OUTPUT]
    assert actor.main(args+(['--dry-run'] if dry else [])) == 0
    if dry:
        assert not (tmp_path/'runs').exists()
    else:
        path,=list((tmp_path/'runs').glob('*/trajectory.json'))
        value=json.loads(path.read_text())
        assert set(value['skill']) == {'mode','text','source'}
        assert set(value['implementation']) == {'version','files'}
        assert set(value['environment']) == {'gamefile','manifest_path'}
        assert set(value['steps'][0]['transport_attempts'][0]['raw_response']) == {'path','bytes'}
        assert value['backend_id'] == 'https://offline.invalid/chat/completions'

"""Offline route, credential, unchanged-configuration and deadline checks."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import frozen_file, load_plan
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts/runs'), str(ROOT / 'external/SkillAdam')]


def read(path):
    return json.loads(path.read_text())


def main():
    plan = load_plan(HERE / 'plan.json')
    old = load_plan(HERE / 'revisions/before_official_models/plan.json')
    v = ROOT / plan['jobs']['v24_1']['experiment']
    s = ROOT / plan['jobs']['skilladam']['experiment']
    cfg = read(v / 'config/campaign.json')
    expected = read(ROOT / old['jobs']['v24_1']['experiment'] / 'config/campaign.json')
    expected.update(actor_model='deepseek-flash', actor_base_url='https://api.deepseek.com')
    expected['call_config'].update(model='deepseek-flash', endpoint='https://api.deepseek.com/chat/completions')
    assert cfg == expected
    for key in old.keys() - {'jobs', 'frozen_inputs_sha256'}:
        assert plan[key] == old[key], key
    for job in plan['jobs'].values():
        assert not (ROOT / job['training_output']).exists()
        assert not (ROOT / job['test_output']).exists()

    from src.skill_evolution.v24_1 import evolution
    from src.skill_evolution.v24_1.benchmark import using_benchmark
    from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
    from src.skill_evolution.v24_1.benchmarks.alfworld import runtime
    with using_benchmark(ALFWorldAdapter()):
        evolution.validate_config(cfg)
        assert evolution.frozen_contract() == read(v / 'config/source_contract.json')
    runtime.check_environment_route(cfg)
    assert runtime.runtime_snapshot(cfg) == read(v / 'config/runtime.json')
    for path, content in cfg.get('environment_files', {}).items():
        assert Path(path).read_text() == content

    from scripts.runs.skilladam.alfworld.native_retry import run_skilladam_alfworld_official_models as app
    report = app.check(s)
    actor, sa = read(s / 'actor.json'), read(s / 'skilladam.json')
    old_sa = read(ROOT / old['jobs']['skilladam']['experiment'] / 'skilladam.json')
    old_sa['optimizer_transport'].update(model='deepseek-flash', base_url='https://api.deepseek.com', api_key_env='OPENAI_API_KEY')
    old_sa['output_root'] = sa['output_root']
    assert sa == old_sa
    from dotenv import dotenv_values
    v25 = read(ROOT / 'experiments/comparisons/v25_skilladam_upstream_actor_prompt_20261030_001/scheduled_run/schedule.json')
    assert (ROOT / plan['credential_source']['env_file']).resolve() == Path(v25['official_env']).resolve()
    official = dotenv_values(v25['official_env'])
    assert official.get('OPENAI_BASE_URL', '').rstrip('/') == 'https://api.deepseek.com'
    assert official.get('OPENAI_API_KEY')

    import httpx
    from skilladam.execution.contracts import GenerationRequest
    bridge = app.bridge_module()
    seen = []
    def mock_http(req):
        seen.append(req)
        return httpx.Response(200, json={'id':'offline','object':'chat.completion','created':0,
            'model':'deepseek-flash','choices':[{'index':0,'finish_reason':'stop',
            'message':{'role':'assistant','content':'summary'}}],
            'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
    with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'OPENAI_API_KEY':'offline-v25-key', 'ALFWORLD_OPTIMIZER_KEY':'offline-stale-key'}):
        backend = app.backend_type(bridge)(actor, sa, Path(tmp), http_transport=httpx.MockTransport(mock_http))
        req = GenerationRequest('trajectory_compression', ({'role':'user','content':'summarize'},), app.context_for(bridge, actor, sa), {})
        backend.generate(req)
        backend.optimizer._client.close()
    assert len(seen) == 1 and seen[0].headers['authorization'] == 'Bearer offline-v25-key'
    assert str(seen[0].url) == 'https://api.deepseek.com/chat/completions'
    assert json.loads(seen[0].content)['model'] == 'deepseek-flash'
    with patch.dict(os.environ, {'OPENAI_API_KEY':'offline-v25-key','OPENAI_BASE_URL':'https://api.deepseek.com'}), patch('dotenv.load_dotenv'):
        bridge.configure_runtime(actor)
        assert os.environ['TARGET_OPENAI_COMPATIBLE_API_KEY'] == 'offline-v25-key'
        assert os.environ['TARGET_OPENAI_COMPATIBLE_MODEL'] == 'deepseek-flash'
        assert os.environ['TARGET_OPENAI_COMPATIBLE_BASE_URL'] == 'https://api.deepseek.com'
        runtime.check_live_environment(cfg)

    spec = importlib.util.spec_from_file_location('official_wrapper', HERE / 'with_official_credentials.py')
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    cutoff = datetime.fromisoformat(plan['not_before_utc'].replace('Z', '+00:00'))
    fake_values = {'OPENAI_API_KEY':'offline-v25-key','OPENAI_BASE_URL':'https://api.deepseek.com'}
    for job in plan['jobs'].values():
        for key in ('train_command','resume_command','test_command'):
            argv = job[key][2:]
            with patch.object(wrapper, 'datetime') as clock, patch('dotenv.dotenv_values', return_value=fake_values), patch.object(wrapper.os, 'execvpe') as execute:
                clock.now.return_value = cutoff
                clock.fromisoformat.side_effect = datetime.fromisoformat
                wrapper.main(argv)
                args = execute.call_args.args
                assert args[:2] == (argv[0], argv)
                assert args[2]['OPENAI_API_KEY'] == 'offline-v25-key'
                assert args[2]['OPENAI_BASE_URL'] == 'https://api.deepseek.com'
    with patch.object(wrapper, 'datetime') as clock, patch.object(wrapper.os, 'execvpe') as execute:
        clock.now.return_value = datetime(2026, 10, 29, 20, 44, 2, tzinfo=timezone.utc)
        clock.fromisoformat.side_effect = datetime.fromisoformat
        try:
            wrapper.main(plan['jobs']['v24_1']['train_command'][2:])
        except ValueError as error:
            assert 'not arrived' in str(error)
        else:
            raise AssertionError('Early launch was allowed')
        execute.assert_not_called()
    for name, expected in load_plan(HERE / 'revisions/before_official_models/plan.json')['frozen_inputs_sha256'].items():
        assert hashlib.sha256(frozen_file(name).read_bytes()).hexdigest() == expected
    result = {'passed':True,'real_model_requests':0,'environment_episodes':0,
              'old_frozen_inputs_unchanged':True,'other_parameters_unchanged':True,
              'all_six_commands_use_v25_credentials':True,'early_start_rejected':True,
              'start_time':plan['not_before_shanghai'],'skilladam_preflight':report['status']}
    (HERE / 'official_models_checks.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline only')):
        main()

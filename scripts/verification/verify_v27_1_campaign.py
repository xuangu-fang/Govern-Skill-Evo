"""Offline LMB acceptance: synthetic execution, native regressions, read-only data preflight."""
import argparse
from contextlib import ExitStack, redirect_stdout
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


def verify_config():
    from scripts.runs import run_v27_1_campaign as cli
    from src.skill_evolution.v27.training import load_dataset
    from src.skill_evolution.v27_1.actor_io import ActorAdapter
    from src.skill_evolution.v27_1.campaign import CampaignAdapter
    from src.skill_evolution.v27_1 import config
    from src.skill_evolution.v27_1.lmb import protocol

    design_root = ROOT / 'docs/methods/v27_1'
    plan = json.loads((design_root / 'experiment_plan.json').read_text())
    spec = json.loads((design_root / 'source_map.json').read_text())
    actual = json.loads(config.DEFAULT_CONFIG.read_text())
    dataset = load_dataset(ROOT / 'data/livemathematicianbench/prepared_v1')
    with CampaignAdapter(ActorAdapter(dataset)).using():
        config.validate_config(actual, executable=True)
        dataset.snapshot()  # Revalidate prepared/raw bytes and deterministic choice mapping.
        prompts = config.render_prompts()
    assert actual['batches'] == plan['schedule']['batches']
    assert dataset.splits['test'] == plan['schedule']['test_ids']
    assert actual['method']['contracts'] == spec['contracts']
    assert actual['method']['reference_policy'] == 'v27_1_explicit_prose_references_v1'
    assert actual['benchmark'] == protocol.IDENTITY
    assert actual['actor'] == protocol.ACTOR
    assert actual['actor']['max_tokens'] == 65536
    assert all(v['max_tokens'] == 32768 and v['timeout_seconds'] == 300
               for v in actual['module_calls'].values())
    assert actual['method']['prompts'] == {k:v['planned_prompt_version'] for k,v in spec['prompts'].items()}
    for name, prompt in prompts.items():
        assert prompt == (design_root / 'prompts' / f'{name}.md').read_bytes().decode('utf-8')
    source_files = json.loads((design_root / 'baseline/source_files.json').read_text())
    for local, source in source_files.items():
        assert (design_root / local).read_bytes() == (ROOT / source).read_bytes(), source
    with tempfile.TemporaryDirectory(prefix='v27_1_preflight_') as folder:
        campaign = Path(folder) / 'not_created'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials')), \
             patch.object(cli, 'run_training', side_effect=AssertionError('No training')), \
             patch.object(cli, 'run_test', side_effect=AssertionError('No Test')):
            cli.main(['train', str(campaign), '--config', str(config.DEFAULT_CONFIG), '--validate-only'])
        assert not campaign.exists()
    return {'method': config.METHOD_VERSION, 'actor_execution_profile': protocol.IDENTITY['execution_profile'],
            'reference_policy':actual['method']['reference_policy'],
            'modules': list(config.MODEL_MODULES), 'batch_sizes': list(map(len,actual['batches'])),
            'optimization_count':53, 'test_count':124, 'actor_max_tokens':65536,
            'module_max_tokens':dict.fromkeys(config.MODEL_MODULES,32768),
            'data_source_validation':'native_raw_and_prepared_checksums_passed',
            'design_prompt_binding':'exact', 'design_baseline_source_files_unchanged':len(source_files),
            'full_dataset_preflight':'passed_without_credentials_or_campaign'}


def protected_files():
    paths = []
    for version in ('v27','v28_3','v29_2','v29_4'):
        for prefix in ('src/skill_evolution','docs/methods'):
            paths += [p for p in (ROOT/prefix/version).rglob('*')
                      if p.is_file() and p.suffix in ('.py','.md','.json')]
    paths += list((ROOT/'docs/methods/v27_1/prompts').glob('*.md'))
    paths += list((ROOT/'src/skill_evolution/v27_1').rglob('*.py'))
    paths += list((ROOT/'src/skill_evolution/v27_1/lmb/context').glob('*.md'))
    paths += list((ROOT/'tests/skill_evolution/v27_1').glob('*.py'))
    paths += [ROOT/'scripts/runs/run_v27_1_campaign.py', ROOT/'experiments/configs/v27_1_lmb53.json']
    return {p:p.read_bytes() for p in paths}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    output=Path(args.output).resolve(); output.mkdir(parents=True,exist_ok=True)
    before=protected_files(); blocked=[]; counts={}; checks={}; error=None
    def deny(*args,**kwargs):
        blocked.append('network_or_process')
        raise AssertionError('Network/process calls forbidden in offline acceptance')
    with ExitStack() as stack:
        for obj,name in ((socket.socket,'connect'),(socket.socket,'connect_ex'),(socket,'create_connection')):
            stack.enter_context(patch.object(obj,name,deny))
        stack.enter_context(patch('subprocess.Popen',deny))
        suite=unittest.TestSuite()
        for version in ('v27','v27_1'):
            part=unittest.defaultTestLoader.discover(str(ROOT/'tests/skill_evolution'/version),top_level_dir=str(ROOT))
            counts[version]=part.countTestCases(); suite.addTests(part)
        with (output/'unittest.log').open('w') as log,redirect_stdout(log):
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
            try: checks=verify_config()
            except Exception as exc: error=f'{type(exc).__name__}: {exc}'
    changed=[str(p.relative_to(ROOT)) for p,data in before.items() if not p.is_file() or p.read_bytes()!=data]
    passed=result.wasSuccessful() and not result.skipped and not blocked and error is None and not changed
    report={'status':'passed' if passed else 'failed','python_executable':sys.executable,
            'test_counts':counts,'tests_run':result.testsRun,'failures':len(result.failures),
            'errors':len(result.errors),'skipped':len(result.skipped),'checks':checks,'check_error':error,
            'protected_files_during_acceptance':len(before),'changed_protected_files':changed,
            'blocked_network_or_process_attempts':blocked,'real_training_or_test_started':False,
            'scope':'Synthetic LMB execution and native v27 regressions; read-only real data/config preflight. No empirical performance result.'}
    (output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','test_counts','tests_run','failures','errors','check_error')},ensure_ascii=False))
    return 0 if passed else 1

if __name__=='__main__':
    sys.exit(main())

"""Offline Prompt v2 binding/regression checks; no provider calls or experiments."""
import argparse
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import traceback
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
REVISION = ROOT / 'docs/methods/v28_5/revisions/searchqa_guidance_v2_20261105'
PROPOSAL = ROOT / 'docs/methods/v28_5/proposals/searchqa_guidance_20261105'
CHANGED_MODULES = ('diagnosis', 'preconditioner', 'replay')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_binding():
    from scripts.runs import run_v28_5_campaign as cli
    from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
    from src.skill_evolution.v28_5 import config
    from src.skill_evolution.v28_5.actor_io import ActorAdapter
    from src.skill_evolution.v28_5.campaign import CampaignAdapter, RUNTIME_VERSION

    frozen = json.loads((REVISION / 'baseline_manifest.json').read_text())
    for item in frozen['files']:
        assert digest(REVISION / item['snapshot']) == item['sha256'], item['path']
    assert digest(PROPOSAL / 'source_map.json') == frozen['approved_proposal_manifest_sha256']
    proposal = json.loads((PROPOSAL / 'source_map.json').read_text())
    for item in proposal['proposal_artifacts']:
        assert digest(PROPOSAL / item['path']) == item['sha256'], item['path']
    for item in frozen['historical_archive_identity_files']:
        assert digest(ROOT / item['path']) == item['sha256'], item['path']

    sources = sorted((ROOT / 'src/skill_evolution/v28_5').glob('*.py'))
    for path in sources:
        before = (REVISION / 'baseline' / path.relative_to(ROOT)).read_text()
        expected = before
        if path.stem in CHANGED_MODULES:
            old = f"PROMPT_VERSION = 'v28_5_searchqa_{path.stem}_v1'"
            assert before.count(old) == 1
            expected = before.replace(old, old.replace('_v1', '_v2'))
        assert path.read_text() == expected, path
    cli_path = ROOT / 'scripts/runs/run_v28_5_campaign.py'
    assert cli_path.read_bytes() == (REVISION / 'baseline' / cli_path.relative_to(ROOT)).read_bytes()

    actual = json.loads(config.DEFAULT_CONFIG.read_text())
    old_config = json.loads((REVISION / 'baseline' / config.DEFAULT_CONFIG.relative_to(ROOT)).read_text())
    expected = deepcopy(old_config)
    for name in CHANGED_MODULES:
        expected['method']['prompts'][name] = f'v28_5_searchqa_{name}_v2'
    assert actual == expected, 'Only three prompt identities may change in the active configuration'
    data = SearchQADataset(batch_size=60, verify_hashes=False)
    actor = ActorAdapter(data)
    with CampaignAdapter(actor).using():
        config.validate_config(actual, executable=True)
        prompts = config.render_prompts()
    assert (actor.workers, actor.test_workers) == (60, 15)
    assert [len(batch) for batch in actual['batches']] == [60] * 10
    for name, text in prompts.items():
        assert text == (PROPOSAL / f'prompts/{name}.md').read_text(), name
    before_pc = (PROPOSAL / 'baseline/prompts/preconditioner.md').read_text()
    marker = '## Historical Memory by round\n'
    assert prompts['preconditioner'].split(marker)[1] == before_pc.split(marker)[1]
    assert prompts['editor'] == (PROPOSAL / 'baseline/prompts/editor.md').read_text()
    shared = (PROPOSAL / 'design/searchqa_guidance.md').read_text().strip()
    assert all(shared in prompts[name] for name in ('diagnosis', 'preconditioner'))
    planned = json.loads((ROOT / 'docs/methods/v28_5/source_map.json').read_text())['planned_identity']
    assert planned['runtime'] == RUNTIME_VERSION
    assert planned['method'] == config.METHOD_VERSION
    assert planned['stage'] == config.STAGE_VERSION
    for key in ('prompts', 'contracts', 'memory_view', 'replay_input_view'):
        assert planned[key] == actual['method'][key], key
    assert set(actual['method']['execution_input_views'].values()) == {planned['execution_input_view']}

    # Historical configs, contracts and the original verification script stay frozen.
    allowed = {f'docs/methods/v28_5/prompts/{name}.md' for name in CHANGED_MODULES}
    allowed |= {f'src/skill_evolution/v28_5/{name}.py' for name in CHANGED_MODULES}
    allowed |= {str(config.DEFAULT_CONFIG.relative_to(ROOT)),
                'tests/skill_evolution/v28_5/test_acceptance.py',
                'tests/skill_evolution/v28_5/test_binding.py',
                'src/skill_evolution/v28_5/README.md'}
    allowed |= {f'docs/methods/v28_5/{name}' for name in
                ('README.md', 'IMPLEMENTATION.md', 'PROMPT_REVIEW.md', 'EXPERIMENT_PLAN.md', 'source_map.json')}
    for item in frozen['files']:
        if item['path'] not in allowed:
            assert digest(ROOT / item['path']) == item['sha256'], item['path']
    with tempfile.TemporaryDirectory(prefix='v28_5_prompt_v2_') as temporary:
        campaign = Path(temporary) / 'not_created'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials')), \
             patch.object(cli, 'run_training', side_effect=AssertionError('No real training')), \
             patch.object(cli, 'run_test', side_effect=AssertionError('No real Test')):
            cli.main(['train', str(campaign), '--config', str(config.DEFAULT_CONFIG), '--validate-only'])
        assert not campaign.exists()
    return {'prompt_versions': config.prompt_versions(), 'method': config.METHOD_VERSION,
            'runtime': RUNTIME_VERSION, 'runtime_source_files_compared': len(sources),
            'only_prompt_version_constants_changed_in_runtime_sources': True,
            'parent_memory_preconditioner_body_unchanged': True,
            'approved_prompts_bound_verbatim': list(prompts),
            'configuration_only_prompt_identities_changed': True,
            'historical_archive_identity_files_unchanged': len(frozen['historical_archive_identity_files']),
            'batch_sizes': list(map(len, actual['batches'])), 'test_count': len(data.splits['test']),
            'train_workers': actor.workers, 'test_workers': actor.test_workers,
            'module_max_tokens': {name: call['max_tokens'] for name, call in actual['module_calls'].items()},
            'preflight': 'passed_without_credentials_or_campaign_creation'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    blocked, counts, checks, error = [], {}, {}, None

    def deny(*args, **kwargs):
        blocked.append('network_or_process')
        raise AssertionError('Network/process calls forbidden during offline verification')

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', deny))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', deny))
        stack.enter_context(patch('socket.create_connection', deny))
        stack.enter_context(patch('subprocess.Popen', deny))
        with (output / 'unittest.log').open('w') as log, redirect_stdout(log):
            suite = unittest.TestSuite()
            for version in ('v28_3', 'v28_5'):
                part = unittest.defaultTestLoader.discover(
                    str(ROOT / 'tests/skill_evolution' / version), top_level_dir=str(ROOT))
                counts[version] = part.countTestCases()
                suite.addTests(part)
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
            try:
                checks = verify_binding()
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
                traceback.print_exc(file=log)
    passed = result.wasSuccessful() and not result.skipped and not blocked and error is None
    report = {'status': 'passed' if passed else 'failed', 'revision': 'searchqa_guidance_v2_20261105',
              'test_counts': counts, 'tests_run': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'skipped': len(result.skipped), 'checks': checks,
              'check_error': error, 'blocked_network_or_process_attempts': blocked,
              'real_model_calls': 0, 'real_training_or_test_started': False,
              'python_executable': sys.executable,
              'scope': 'Authored synthetic regression tests and read-only configuration preflight; no model behavior evaluation.'}
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())

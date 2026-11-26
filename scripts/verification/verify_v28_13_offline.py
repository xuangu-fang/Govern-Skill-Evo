"""v28.13 offline acceptance: synthetic execution and read-only dataset preflight."""
import argparse
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import traceback
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


def migrated(text):
    text = text.replace('v28_12', 'v28_13').replace('v28.12', 'v28.13')
    for old, new in {
        'v28_13_preconditioner_simplification_v1': 'v28_12_preconditioner_simplification_v1',
        'v28_13_editor_mapped_patches_v1': 'v28_12_editor_mapped_patches_v1',
        'v28_13_gate_net_em_chars_v1': 'v28_13_gate_net_em_min2_v1',
        'v28_13_searchqa_diagnosis_decision_boundaries_v1': 'v28_13_searchqa_diagnosis_rule_examples_v2',
        'v28_13_searchqa_preconditioner_compact_v2': 'v28_13_searchqa_preconditioner_rule_integration_v2',
        'v28_13_searchqa_editor_compact_v2': 'v28_13_searchqa_editor_structured_rules_v2',
    }.items():
        text = text.replace(old, new)
    return text.replace('experiments/configs/v28_searchqa_initial_skill.md',
                        'experiments/configs/v28_13_searchqa_initial_skill.md')


def check_configuration_and_isolation():
    from scripts.runs import run_v28_13_campaign as cli
    from src.skill_evolution.v28_13 import config, gate
    from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset

    previous = json.loads((ROOT / 'experiments/configs/v28_12_searchqa_train600_batch60.json').read_text())
    actual = json.loads(config.DEFAULT_CONFIG.read_text())
    expected = deepcopy(previous)
    expected['method'] = config.method_config()
    expected['gate_rule'] = gate.CONTRACT_VERSION
    expected['initial_skill'] = config.initial_skill()
    assert expected['initial_skill']['text'] == '# Question Answering Skill\n\n## Workflow\n\n## Error Avoidance\n'
    assert actual == expected, 'Actor, schedule, data or budgets changed beyond the new initial template'
    sources = ROOT / 'src/skill_evolution'
    old_files = sorted(p.name for p in (sources / 'v28_12').glob('*.py'))
    assert old_files == sorted(p.name for p in (sources / 'v28_13').glob('*.py'))
    compared = []
    for name in old_files:
        text = (sources / 'v28_13' / name).read_text()
        assert 'from src.skill_evolution.v28_12' not in text
        assert 'import src.skill_evolution.v28_12' not in text
        if name != 'gate.py':
            assert text == migrated((sources / 'v28_12' / name).read_text()), name
            compared.append(name)
    assert Path(cli.__file__).read_text() == migrated((ROOT / 'scripts/runs/run_v28_12_campaign.py').read_text())
    assert (ROOT / 'docs/methods/v28_13/prompts/replay.md').read_bytes() == (ROOT / 'docs/methods/v28_12/prompts/replay.md').read_bytes()
    for name in ('diagnosis', 'preconditioner', 'editor'):
        assert (ROOT / f'docs/methods/v28_13/prompts/{name}.md').read_bytes() != (ROOT / f'docs/methods/v28_12/prompts/{name}.md').read_bytes()

    data = SearchQADataset(batch_size=60, verify_hashes=False)
    adapter = cli.CampaignAdapter(cli.ActorAdapter(data))
    with adapter.using():
        config.validate_config(actual, executable=True)
        prompts = config.render_prompts()
        for name, text in prompts.items():
            assert text == (ROOT / f'docs/methods/v28_13/prompts/{name}.md').read_text()
        try:
            config.validate_config(previous, executable=True)
        except ValueError:
            pass
        else:
            raise AssertionError('v28.13 accepted a v28.12 configuration')
        stale = deepcopy(actual)
        stale['initial_skill'] = previous['initial_skill']
        try:
            config.validate_config(stale, executable=True)
        except ValueError:
            pass
        else:
            raise AssertionError('v28.13 accepted the old placeholder template')
    with tempfile.TemporaryDirectory(prefix='v28_13_preflight_') as tmp:
        destination = Path(tmp) / 'not_created'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('Credentials forbidden')), \
                patch.object(cli, 'run_training', side_effect=AssertionError('Real training forbidden')), \
                patch.object(cli, 'run_test', side_effect=AssertionError('Real Test forbidden')):
            cli.main(['train', str(destination), '--config', str(config.DEFAULT_CONFIG), '--validate-only'])
        assert not destination.exists()
    return {
        'method': config.METHOD_VERSION, 'gate': gate.CONTRACT_VERSION,
        'runtime_files_identical_except_version_bindings_and_initial_template_path': compared,
        'replay_prompt_unchanged': True,
        'actor_data_schedule_and_budgets_unchanged': True,
        'initial_skill_is_empty_two_section_template': True,
        'prompts_bound_verbatim': list(prompts),
        'batch_sizes': list(map(len, actual['batches'])), 'test_count': len(data.splits['test']),
        'train_workers': adapter.actor_adapter.workers, 'test_workers': adapter.actor_adapter.test_workers,
        'old_configuration_rejected': True,
        'real_data_preflight_without_credentials_or_campaign': True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline', required=True, help='Pre-edit v28.12 SHA-256 manifest')
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    baseline = json.loads(Path(args.baseline).read_text())
    assert baseline, 'Baseline required'
    blocked, counts, checks, error = [], {}, {}, None

    def deny(*args, **kwargs):
        blocked.append('network_or_process')
        raise AssertionError('Network/process access forbidden during offline checks')

    with ExitStack() as stack:
        for target in ('socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection',
                       'socket.getaddrinfo', 'subprocess.Popen'):
            stack.enter_context(patch(target, deny))
        suite = unittest.TestSuite()
        for version in ('v28_5', 'v28_12', 'v28_13'):
            part = unittest.defaultTestLoader.discover(str(ROOT / 'tests/skill_evolution' / version), top_level_dir=str(ROOT))
            counts[version] = part.countTestCases()
            suite.addTests(part)
        with (output / 'unittest.log').open('w') as log, redirect_stdout(log):
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
            try:
                checks = check_configuration_and_isolation()
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
                traceback.print_exc(file=log)
    changed = [name for name, digest in baseline.items()
               if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    passed = result.wasSuccessful() and not result.skipped and not blocked and error is None and not changed
    report = {
        'status': 'passed' if passed else 'failed', 'python_executable': sys.executable,
        'test_counts': counts, 'tests_run': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skipped': len(result.skipped), 'checks': checks, 'check_error': error,
        'v28_12_protected_files': len(baseline), 'v28_12_changed_files': changed,
        'blocked_network_or_process_attempts': blocked, 'real_model_calls': 0,
        'real_training_or_test_started': False,
        'scope': 'Authored synthetic software tests and read-only real-data preflight. '
                 'No LLM format-compliance or benchmark performance claim.',
    }
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())

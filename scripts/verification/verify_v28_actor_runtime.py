"""Offline-only v28 Actor/recovery/Gate acceptance, including prior components."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
from scripts.verification.verify_v28_actor_scoring import digest, require, verify_data_and_messages


def main(*, include_method=False, include_campaign=False):
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    require(Path(sys.prefix).name == 'SearchQA', 'Use conda environment SearchQA')
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    blocked_attempts = []

    def blocked(*args, **kwargs):
        blocked_attempts.append('blocked')
        raise AssertionError('Network/process execution forbidden during offline acceptance')

    protected = list((ROOT / 'data/searchqa').rglob('*.json'))
    protected += [q for q in (ROOT / 'src/skill_evolution/v27').rglob('*') if q.suffix in ('.py', '.md', '.json')]
    before = {str(q.relative_to(ROOT)): digest(q) for q in protected}
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', blocked))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', blocked))
        stack.enter_context(patch('socket.create_connection', blocked))
        stack.enter_context(patch('subprocess.Popen', blocked))
        from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
        identity = p.implementation_identity()
        names = sorted((ROOT / 'tests/skill_evolution/v28').glob('test_*.py'))
        if not include_campaign:
            names = [q for q in names if q.name not in ('test_campaign.py', 'test_stages.py')]
        if not include_method:
            names = [q for q in names if q.name != 'test_method.py']
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(
            f'tests.skill_evolution.v28.{q.stem}') for q in names)
        with (out / 'unittest.log').open('w') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        data_check = verify_data_and_messages()
        method_check = {}
        if include_method:
            from src.skill_evolution.v28.benchmarks.searchqa import prompting
            draft = ROOT / 'docs/methods/v28/five_module_draft_20261101'
            installed = {name: digest(prompting.resource_path(name)) for name in prompting.RESOURCE_NAMES}
            require(all(value == digest(draft / 'prompts' / name) for name, value in installed.items()),
                    'Installed Prompts differ from approved draft')
            method_check = {'method_baseline': 'v27', 'v25_2_additions_inherited': False,
                            'planned_ablations': [], 'facts_version': p.FACTS_VERSION,
                            'input_view': p.MODEL_INPUT_VIEW,
                            'prompt_versions': prompting.PROMPT_VERSIONS,
                            'installed_prompt_sha256': installed,
                            'approved_design_manifest_sha256': digest(draft / 'source_manifest.json')}
        require(p.equal(p.implementation_identity(), identity), 'Source changed during acceptance')
    unchanged = before == {str(q.relative_to(ROOT)): digest(q) for q in protected}
    tests = sorted((ROOT / 'tests/skill_evolution/v28').glob('*.py'))
    scripts = [Path(__file__), ROOT / 'scripts/verification/verify_v28_actor_scoring.py']
    if include_method:
        scripts.append(ROOT / 'scripts/verification/verify_v28_method.py')
    if include_campaign:
        scripts.append(ROOT / 'scripts/verification/verify_v28_campaign.py')
    report = {
        'status': 'passed' if result.wasSuccessful() and unchanged and not blocked_attempts else 'failed',
        'checked_at': datetime.now(timezone.utc).isoformat(), 'environment': sys.prefix,
        'scope': ('Synthetic complete campaign dispatch, 40x15 schedule, method retries/feedback/recovery, atomic publication, '
                  'independent Test scheduling and all earlier components; no real model or task execution.' if include_campaign else
                  'Synthetic Actor retry/recovery, archive provenance, EM-only Gate, five-module Prompt/projection/output contracts, '
                  'Replay and Memory commit/recovery; no campaign runner or live model acceptance.' if include_method else
                  'Synthetic Actor retry, recovery, archive provenance and EM-only Gate; no five-module/campaign or live model acceptance.'),
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'network_or_process_attempts': len(blocked_attempts),
        'model_requests': 0, 'training_started': False, 'test_evaluation_started': False,
        'synthetic_actor_only': True, 'dataset_and_v27_source_unchanged': unchanged,
        'synthetic_campaign_executed': include_campaign,
        'protocol_identity': identity, **data_check, **method_check,
        'verification_sha256': {str(q.relative_to(ROOT)): digest(q) for q in [*tests, *scripts]},
        'remaining': ([] if include_method else ['five-module prompts and evidence integration']) +
                     ([] if include_campaign else ['campaign/Test orchestration and method-stage retry/recovery wiring']) +
                     ['initial Skill choice', 'provider input token capacity validation'],
    }
    (out / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('protocol_identity', 'verification_sha256')},
                     ensure_ascii=False, indent=2))
    if report['status'] != 'passed':
        print((out / 'unittest.log').read_text())
        raise SystemExit(1)


if __name__ == '__main__':
    main()

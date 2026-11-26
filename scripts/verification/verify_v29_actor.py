"""Offline phase-one acceptance: synthetic Actor requests and local data reads."""
import argparse
import base64
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


def verify_data():
    from PIL import Image
    from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
    from src.skill_evolution.v29.benchmarks.docvqa import protocol as p
    dataset = DocVQADataset()
    assert [len(b) for b in dataset.batches] == [15] * 10 + [10]
    assert set(dataset.splits['train']).isdisjoint(dataset.splits['test'])
    images = set()
    for task_id, row in dataset.rows.items():
        case = dataset.case(task_id)
        messages = p.messages_for_case(case, p.initial_skill())
        assert messages[1]['content'][0]['text'] == row['question'] + '\n\nReturn the final answer inside <answer>...</answer>.'
        parts = messages[1]['content']
        path = dataset.root / row['image_path']
        assert base64.b64decode(parts[1]['image_url']['url'].split(',', 1)[1]) == path.read_bytes()
        assert set(parts[1]['image_url']) == {'url'}
        if path not in images:
            with Image.open(path) as image:
                image.load()
                assert image.width > 0 and image.height > 0
            images.add(path)
    assert len(images) == 439
    return {'dataset_rows': len(dataset.rows), 'source_counts': {k: len(v) for k, v in dataset.source_ids.items()},
            'optimization_count': len(dataset.splits['train']), 'test_count': len(dataset.splits['test']),
            'batch_sizes': [len(b) for b in dataset.batches], 'unique_images_read': len(images),
            'task_messages_checked': len(dataset.rows), 'revision': p.REVISION}


def verify_method_efficiency():
    """Measure the same tiny offline fixture used to reproduce the regression."""
    from collections import Counter
    from copy import deepcopy
    from src.skill_evolution.v27.contracts import memory
    from src.skill_evolution.v29 import modules
    from src.skill_evolution.v29.benchmarks.docvqa import actor, evidence, replay_input_view
    from tests.skill_evolution.v29.test_method import MethodBase, main_example, user
    case = MethodBase()
    case.setUp()
    try:
        first = case.chain(); directory = case.root / 'memory'
        with patch.object(case.adapter, 'read_batch', wraps=case.adapter.read_batch) as grouping:
            modules.grouping_call(case.parents, 'R02')
        with patch.object(case.adapter, 'read_batch', wraps=case.adapter.read_batch) as bundle_build:
            rebuilt = evidence.build_replay_from_editor(first['audit']['editor'], first['editor_directory'],
                case.parents, case.children, memory=first['payload']['memory'])
        assert grouping.call_count == 1 and bundle_build.call_count == 2 and rebuilt == first
        with patch.object(case.adapter, 'read_batch', wraps=case.adapter.read_batch) as constructed:
            call = modules.replay_call(first)
        with patch.object(case.adapter, 'read_batch', wraps=case.adapter.read_batch) as validated:
            call.complete(main_example('replay'))
        assert constructed.call_count == validated.call_count == 2
        case.method.commit_memory(directory, context_id='R1', context=first, result=main_example('replay'))
        second = case.chain(case.method.load_memory(directory))
        compact = user(modules.replay_call(second))
        assert replay_input_view.restore_model_input(compact) == evidence.model_input(second)
        before = deepcopy(compact)
        for run in before['runs']:
            run['outcome']['answer']['raw_content'] = run['attempts'][0]['assistant']['content']
        chars = lambda value: len(json.dumps(value, ensure_ascii=False, separators=(',', ':')))
        with patch.object(memory, '_archive', wraps=memory._archive) as archive, \
             patch.object(case.adapter, 'read_batch', wraps=case.adapter.read_batch) as batches, \
             patch.object(actor, 'read_completed', wraps=actor.read_completed) as completed:
            case.method.commit_memory(directory, context_id='R2', context=second, result={'entries': []})
        counts = Counter(str(c.args[0]) for c in batches.call_args_list)
        assert archive.call_count == 1 and len(counts) == 4 and set(counts.values()) == {1}
        assert completed.call_count == 8
        return {'fixture': 'synthetic; one historical round; two questions per batch',
                'history_chain_traversals_per_commit': archive.call_count,
                'complete_batch_validations_per_commit': batches.call_count,
                'complete_actor_validations_per_commit': completed.call_count,
                'replay_user_chars_before_response_dedup': chars(before),
                'replay_user_chars_after_response_dedup': chars(compact),
                'lossless_replay_restoration': True,
                'local_evidence_construction_no_history': {
                    'grouping_batch_validations': grouping.call_count,
                    'replay_bundle_batch_validations': bundle_build.call_count},
                'standalone_replay_no_history': {
                    'request_construction_batch_validations': constructed.call_count,
                    'output_validation_batch_validations': validated.call_count}}
    finally:
        case.doCleanups()


def verify_formal_config():
    from src.skill_evolution.v29.campaign import CampaignAdapter
    from src.skill_evolution.v29.config import validate_config
    from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
    from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
    path = ROOT / 'experiments/configs/v29_docvqa_optimization160.json'
    config = json.loads(path.read_text())
    with CampaignAdapter(DocVQAActorAdapter(DocVQADataset())).using():
        validate_config(config, executable=True)
    return {'formal_config': str(path.relative_to(ROOT)), 'formal_config_valid': True,
            'actor_max_tokens': config['actor']['max_tokens'],
            'method_output_budgets': {k: v['max_tokens'] for k, v in config['module_calls'].items()},
            'method_runtime_timeouts': {k: v['timeout_seconds'] for k, v in config['module_calls'].items()}}


def main(*, include_method=False, include_campaign=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    blocked_attempts = []

    def blocked(*args, **kwargs):
        blocked_attempts.append('network_or_process')
        raise AssertionError('Network/process execution forbidden in offline acceptance')

    data, data_error, efficiency, formal = {}, None, None, {}
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', blocked))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', blocked))
        stack.enter_context(patch('socket.create_connection', blocked))
        stack.enter_context(patch('subprocess.Popen', blocked))
        suite = unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29.test_actor')
        if include_method:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29.test_method'))
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29.test_memory_replay_efficiency'))
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29.test_module_validation_reuse'))
        if include_campaign:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29.test_stages'))
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29.test_campaign'))
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29.test_entrypoints'))
        with (output / 'unittest.log').open('w') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        try:
            data = verify_data()
            formal = verify_formal_config()
            if include_method:
                efficiency = verify_method_efficiency()
        except Exception as error:
            data_error = f'{type(error).__name__}: {error}'
    passed = result.wasSuccessful() and data_error is None and not blocked_attempts
    report = {'status': 'passed' if passed else 'failed', 'checked_at': datetime.now(timezone.utc).isoformat(),
              'environment': sys.prefix, 'scope': 'v29 phase one: Actor, scoring, text evidence and single-batch I/O',
              'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'data_error': data_error, 'network_or_process_attempts': len(blocked_attempts),
              'model_requests': 0, 'training_started': False, 'test_evaluation_started': False,
              'synthetic_responses_only': True, 'scoring_examples': 15, 'gate_examples': 3,
              **data, **formal, 'remaining': ['method and campaign offline acceptance'],
              'runtime_note': 'This report covers offline checks only; live run status is recorded in campaign/evaluation outputs.'}
    if include_method:
        report.update(scope='v29 phases one and two: Actor, five modules, Plan/patch, Replay and Memory',
                      reviewed_module_examples=6, installed_prompts_checked=5,
                      remaining=['campaign and final Test offline acceptance'],
                      memory_replay_efficiency=efficiency)
    if include_campaign:
        report.update(scope='v29 phases one through three: synthetic training loop, retries, recovery and Parent/Memory publication',
                      synthetic_schedule={'questions': 160, 'batch_sizes': [15] * 10 + [10]},
                      publication_history_scan_assertion='one full history traversal across prepare/commit/view/state publication',
                      recovery_checkpoint_count=14,
                      formal_entrypoints='full training and final-only held-out Test; synthetic execution verified',
                      remaining=[])
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not passed:
        print((output / 'unittest.log').read_text())
        raise SystemExit(1)


if __name__ == '__main__':
    main()

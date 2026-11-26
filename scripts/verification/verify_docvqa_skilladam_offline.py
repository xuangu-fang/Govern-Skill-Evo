"""Offline SkillAdam bridge and shared v29 Actor acceptance; network is blocked."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if Path(sys.prefix).name != 'DocVQA':
        parser.error('Use the independent DocVQA conda environment')
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    connections = []
    def blocked(*args, **kwargs):
        connections.append('blocked')
        raise AssertionError('Offline acceptance attempted network access')
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', blocked))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', blocked))
        stack.enter_context(patch('socket.create_connection', blocked))
        stack.enter_context(patch('subprocess.Popen', side_effect=AssertionError('Offline acceptance cannot start processes')))
        from src.adapters.docvqa.skilladam import prepare
        cfg, dataset, _, native, _ = prepare()
        suite = unittest.TestSuite([
            unittest.defaultTestLoader.loadTestsFromName('tests.adapters.docvqa.test_skilladam'),
            unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29.test_actor'),
        ])
        with (out / 'unittest.log').open('w') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = {'status': 'passed' if result.wasSuccessful() and not connections else 'failed',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'network_attempts': len(connections), 'real_model_requests': 0,
        'training_started': False, 'test_started': False,
        'scope': 'synthetic optimizer/Actor integration and real data read-only checks',
        'python': sys.executable, 'data_rows': len(dataset.rows),
        'optimization_count': len(dataset.splits['train']), 'test_count': len(dataset.splits['test']),
        'batch_sizes': list(map(len, dataset.batches)), 'actor_max_tokens': cfg['actor']['max_tokens'],
        'optimizer_max_tokens': cfg['optimizer']['backend_config']['max_completion_tokens'],
        'native': native.to_dict()}
    (out / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'native'}, ensure_ascii=False, indent=2))
    if report['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

"""Verify the LMB SkillAdam bridge with socket calls prohibited."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if Path(sys.prefix).name != 'LiveMathematicianBench':
        raise RuntimeError('Use the independent LMB environment')
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    connections = []
    def blocked(*args, **kwargs):
        connections.append('blocked')
        raise AssertionError('Offline validation attempted a network connection')
    def data_hashes():
        return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for folder in ('data/livemathematicianbench/raw/data', 'data/livemathematicianbench/prepared_v1')
                for p in sorted((ROOT / folder).rglob('*.json'))}
    before = data_hashes()
    def protected_hashes():
        paths = [ROOT / 'experiments/configs/lmb_skilladam53_epoch1_deepseek_flash.json',
                 ROOT / 'experiments/configs/v27_lmb53_epoch1_deepseek_flash.json',
                 ROOT / 'benchmarks/livemathematicianbench/requirements.lock.txt']
        for folder in ('external/SkillAdam/skilladam', 'src/skill_evolution/v27'):
            paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in ('.py', '.md', '.json'))
        return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    protected_before = protected_hashes()
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', blocked))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', blocked))
        stack.enter_context(patch('socket.create_connection', blocked))
        stack.enter_context(patch('subprocess.Popen', side_effect=AssertionError('No subprocesses in offline tests')))
        from src.adapters.lmb.skilladam import prepare
        _, _, _, _, _, snapshot = prepare()
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests/adapters/lmb'), top_level_dir=str(ROOT))
        from scripts.verification.verify_v27_offline import RecordedResult
        with (out / 'unittest.log').open('w') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=RecordedResult).run(suite)
    protected_unchanged = protected_before == protected_hashes()
    summary = {'status': 'passed' if result.wasSuccessful() and not connections and before == data_hashes() and protected_unchanged else 'failed',
               'tests_run': result.testsRun, 'outcomes': result.outcomes, 'python': sys.executable,
               'network_attempts': len(connections), 'real_model_requests': 0,
               'benchmark_data_unchanged': before == data_hashes(),
               'native_v27_sources_and_configs_unchanged_during_validation': protected_unchanged,
               'scope': 'configuration and synthetic integration only'}
    (out / 'validation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (out / 'preflight.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    (out / 'protected_sources.json').write_text(json.dumps(protected_before, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

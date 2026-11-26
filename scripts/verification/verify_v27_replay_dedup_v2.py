"""Read-only historical Replay roundtrip audit; no credentials or model calls."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'external/SkillAdam')]


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    connections = []

    def blocked(*args, **kwargs):
        connections.append('blocked')
        raise AssertionError('Offline audit attempted an external operation')

    rows = []
    with ExitStack() as stack:
        for method in ('connect', 'connect_ex'):
            stack.enter_context(patch.object(socket.socket, method, blocked))
        stack.enter_context(patch('socket.create_connection', blocked))
        stack.enter_context(patch('subprocess.Popen', blocked))
        stack.enter_context(patch('dotenv.dotenv_values', blocked))
        from src.skill_evolution.v27.benchmarks.lmb import replay_input_view as view
        campaign = ROOT/'experiments/campaigns/v27_lmb53_actor49152_20261031_152036'
        for number in range(1, 7):
            path = campaign/'rounds'/f'R{number:02}'/'replay/base_messages.json'
            original_bytes = path.read_bytes()
            payload = json.loads(json.loads(original_bytes)[1]['content'])
            before = deepcopy(payload)
            compact = view.model_input(payload)
            assert view.restore_model_input(compact) == before == payload
            # Reintroduce just the redundant answer to measure the incremental
            # saving against the previous shared-initial implementation.
            previous = deepcopy(compact)
            for run in previous['runs']:
                run['outcome']['answer']['raw_content'] = run['attempts'][0]['assistant']['content']
            old, shared, new = map(lambda v: len(encoded(v)), (payload, previous, compact))
            assert path.read_bytes() == original_bytes
            rows.append({'round': f'R{number:02}', 'pairs': len(payload['pairs']),
                         'runs': len(payload['runs']), 'original_chars': old,
                         'shared_initial_only_chars': shared, 'dedup_v2_chars': new,
                         'response_dedup_saved_chars': shared-new,
                         'roundtrip_equal': True, 'source': str(path.relative_to(ROOT)),
                         'source_sha256': hashlib.sha256(original_bytes).hexdigest()})
    totals = {key: sum(row[key] for row in rows) for key in
              ('pairs', 'runs', 'original_chars', 'shared_initial_only_chars',
               'dedup_v2_chars', 'response_dedup_saved_chars')}
    totals['reduction_percent'] = 100*(1-totals['dedup_v2_chars']/totals['original_chars'])
    report = {'status': 'passed', 'rounds': rows, 'totals': totals,
              'network_connection_attempts': len(connections), 'real_model_requests': 0,
              'training_started': False, 'benchmark_evaluation_started': False,
              'note': 'Exact serialized character counts, not provider tokens, fees or quality measurements.'}
    (out/'historical_replay_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    main()

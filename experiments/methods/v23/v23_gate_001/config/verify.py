"""Read-only upstream verification and Gate cache test. Never runs models/tasks."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v23.gate import load_gate, run_gate

BASE = Path('experiments/methods/v23/v23_gate_001')
OUTPUT = Path('artifacts/methods/v23/v23_gate_001/live')


def main():
    frozen = json.loads((BASE/'config/upstream_hashes.json').read_text())
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in frozen.items())
    saved = load_gate(OUTPUT)
    original = (OUTPUT/'gate.json').read_bytes()
    with patch('src.skill_evolution.v23.gate.decide_gate', side_effect=AssertionError('Repeated decision')):
        again = run_gate('artifacts/methods/v23/v23_replay_memory_001/replay',
                         BASE/'config/tasks.json', OUTPUT)
    assert again['reused'] and again['result'] == saved['result']
    assert (OUTPUT/'gate.json').read_bytes() == original
    pairs = saved['bundle']['input']['pairs']
    result = {'result': saved['result'], 'pairs': saved['bundle']['audit'],
              'repairs': sum(not p['parent']['success'] and p['candidate']['success'] for p in pairs),
              'regressions': sum(p['parent']['success'] and not p['candidate']['success'] for p in pairs),
              'protected_files': len(frozen), 'upstream_unchanged': True,
              'reused_without_decision_call': True, 'model_calls': 0, 'new_episodes': 0}
    (BASE/'results/verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

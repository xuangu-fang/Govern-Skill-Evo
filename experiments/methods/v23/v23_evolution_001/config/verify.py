"""Verify saved evidence without requests, new trajectories or state writes."""
import hashlib
from pathlib import Path
from src.skill_evolution.v23 import evolution as ev, memory
from src.adapters.alfworld.response_archive import verify_response_archive

ROOT = Path('artifacts/methods/v23/v23_evolution_001')
EXP = Path('experiments/methods/v23/v23_evolution_001')


def main():
    ev._check_contract(ROOT)
    old = ev.read('experiments/methods/v23/v23_gate_001/config/upstream_hashes.json')
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in old.items())
    count = 0; loaded = []
    state = ev.read(ROOT/'state.json')
    for rd in sorted((ROOT/'rounds').glob('R*')):
        snapshot = ev.read(rd/'round_input.json')
        assert memory.load_memory(ROOT/snapshot['state']['active_memory']) == snapshot['memory']
        for path in rd.rglob('trajectory.json'):
            record = ev.read(path)
            for step in record['steps']:
                for attempt in step.get('transport_attempts', []):
                    verify_response_archive(path, attempt); count += 1
        for name, module in ev.MODULES.items():
            marker = rd/name/'result.json'
            if marker.exists():
                path = rd/name/ev.read(marker)['path']
                loaded_value = getattr(module, 'load_'+name)(path)
                loaded.append(f'{rd.name}/{name}')
                if name == 'preconditioner': assert loaded_value['memory'] == snapshot['memory']
                if name == 'replay': assert loaded_value['payload']['memory'] == snapshot['memory']
        if (rd/'memory/view.json').exists():
            assert memory.load_memory(rd/'memory') == ev.read(rd/'memory/view.json')
        if (rd/'result.json').exists():
            after = ev.read(rd/'result.json')['after']
            assert after['next_round'] == snapshot['state']['next_round']+1
            if (rd/'gate/result.json').exists():
                decision = ev.read(rd/'gate/result.json')['result']['decision']
                if decision == 'RETAIN': assert after['parent'] == snapshot['state']['parent']
                else:
                    ep = rd/'editor'/ev.read(rd/'editor/result.json')['path']/'candidate.md'
                    assert (ROOT/after['parent']).read_bytes() == ep.read_bytes()
    if state['next_round'] > 1:
        assert state == ev.read(ROOT/'rounds'/f'R{state["next_round"]-1:02}'/'result.json')['after']
    result = {'protected_old_files': len(old), 'old_archives_unchanged': True,
        'actor_request_archives_verified': count, 'modules_loaded_without_calls': loaded,
        'frozen_contract_unchanged': True, 'official_state_verified': True}
    ev.save(EXP/'results/verification.json', result)
    print(result)


if __name__ == '__main__': main()

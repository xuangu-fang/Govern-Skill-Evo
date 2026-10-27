"""Read-only old experiments -> new frozen offline views. Never calls a model."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from experiments.methods.v23_4.archive_io import archive_glob, resolve
from src.skill_evolution.v23 import memory
from src.skill_evolution.v23_3.memory_view import compact_memory
from src.skill_evolution.v23_4 import replay

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def read(path): return json.loads(resolve(path).read_text())
def sha(path): return hashlib.sha256(resolve(path).read_bytes()).hexdigest()


def save(path, value):
    path = resolve(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert read(path) == value, f'Offline result changed: {path}'
    else:
        with path.open('x') as f: json.dump(value, f, ensure_ascii=False, indent=2)


def main():
    results, frozen = {}, {}
    for name, round_id in (('R05', 'R04'), ('R06', 'R05')):
        old = HERE.with_name(name.lower() + '_replay_memory_001')
        mem = ROOT / f'artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/{round_id}/memory'
        source_files = [p for p in archive_glob(old, '*', recursive=True) if p.is_file() and p.name != 'live.lock']
        source_files += list(mem.rglob('*.json'))
        before = {str(p.relative_to(ROOT)): sha(p) for p in source_files}
        bundle = read(old / 'config/replay_bundle.json')
        old_messages = read(old / 'config/messages.json')
        # Preserve exact prior model requests; only the new experiment stores new views.
        assert replay.messages_for(bundle, input_view=replay.LEGACY_INPUT_VIEW) == old_messages
        freeze = read(old / 'config/freeze.json')['sha256']
        for p in (old / 'config/replay_bundle.json', old / 'config/messages.json'):
            assert sha(p) == freeze[str(p.relative_to(ROOT))]
        source = ROOT / 'src/skill_evolution/v23_4/replay.py'
        expected = freeze.get(str(source.relative_to(ROOT)), freeze.get(str(source)))
        assert sha(HERE / 'baseline_sources' / source.relative_to(ROOT)) == expected
        assert memory.load_memory(mem) == bundle['payload']['memory']
        sources = replay.history_pair_sources(mem, bundle['payload']['memory'])
        messages = replay.messages_for(bundle, history_sources=sources)
        view = json.loads(messages[1]['content'])
        raw = bundle['payload']
        assert set(view) == set(raw)
        for key in ('parent', 'diff', 'plan', 'command_sets'):
            assert view[key] == raw[key]
        assert {r['ref']: r for r in view['runs']} == {r['ref']: r for r in raw['runs']}
        assert [r['ref'] for r in view['runs']] == [ref for p in raw['pairs'] for ref in (p['parent'], p['candidate'])]
        base = deepcopy(view['memory'])
        historical = base.pop('pairs'); unpaired = base.pop('unpaired_runs')
        assert base == compact_memory(raw['memory'])
        assert unpaired == []
        for pair in view['pairs']:
            for side in ('parent', 'candidate'):
                r = next(r for r in raw['runs'] if r['ref'] == pair[side])
                assert pair[f'{side}_result'] == {'status': r['outcome']['status'],
                    'success': r['outcome']['success'], 'steps': len(r['steps'])}
        for pair in historical:
            cid = pair['context']; archived = read(Path(sources[cid]['path']))['context']['payload']['pairs']
            assert {'parent': pair['parent'].rsplit('/', 1)[1],
                    'candidate': pair['candidate'].rsplit('/', 1)[1]} in archived
            assert pair['parent'] in base['sources'] and pair['candidate'] in base['sources']
        selected = read(old / f'runs/{name}_replay/selected.json')['attempt']
        proposal = read(old / f'runs/{name}_replay/attempt_{selected:03}/parsed.json')
        memory.validate_entries(proposal, raw)  # Same contract; does not approve old semantics.
        dest = HERE / 'cases' / name
        save(dest / 'history_pair_sources.json', sources)
        save(dest / 'model_input.json', view)
        save(dest / 'messages.json', messages)
        steps = [r for r in base['sources'].values() if 'run' in r]
        results[name] = {
            'input_view': replay.INPUT_VIEW, 'current_pairs': len(view['pairs']),
            'current_executed_steps': sum(len(r['steps']) for r in view['runs']),
            'historical_pairs': len(historical), 'historical_unpaired_runs': unpaired,
            'historical_trace_steps': sum(len(s['run']['trace']) for s in steps),
            'historical_detailed_steps': sum(len(s['detailed_steps']) for s in steps),
            'old_user_chars': len(old_messages[1]['content']), 'new_user_chars': len(messages[1]['content']),
            'user_char_reduction_percent': round(100 * (1 - len(messages[1]['content']) / len(old_messages[1]['content'])), 2),
            'new_request_chars': len(json.dumps(messages, ensure_ascii=False)),
            'production_default_max_input_chars': 400000,
            'all_current_records_unchanged': True, 'legacy_messages_reproduced': True,
            'unchanged_memory_v3_projection': True, 'old_proposal_reference_validation_passed': True,
            'semantic_approval': False, 'model_calls': 0,
            'source_files_unchanged': len(before),
        }
        assert {str(p.relative_to(ROOT)): sha(p) for p in source_files} == before
        frozen.update(before)
    for folder in ('src/skill_evolution/v23', 'src/skill_evolution/v23_3', 'src/skill_evolution/v23_4'):
        for p in (ROOT / folder).iterdir():
            if p.suffix in ('.py', '.md'): frozen[str(p.relative_to(ROOT))] = sha(p)
    for p in [Path(__file__), ROOT / 'tests/skill_evolution/v23_4/test_replay_view.py',
              ROOT / 'docs/methods/v23_4/REPLAY_INPUT_VIEW.md']:
        frozen[str(p.relative_to(ROOT))] = sha(p)
    for p in archive_glob(HERE / 'cases', '*.json', recursive=True): frozen[str(p.relative_to(ROOT))] = sha(p)
    save(HERE / 'RESULTS.json', results)
    save(HERE / 'freeze.json', {'purpose': 'offline input conservation; no model or Actor call', 'sha256': frozen})
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()

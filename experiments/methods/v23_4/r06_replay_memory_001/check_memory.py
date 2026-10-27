"""Offline roundtrip of the unmodified Replay proposal in an isolated archive."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

from .run import core, HERE, MEMORY
from src.skill_evolution.v23.memory import commit_memory, load_memory, validate_memory
from src.skill_evolution.v23_3.memory_view import compact_memory

CONTEXT_ID = 'v23_4_R06_eval_replay_001'


def hashes(root):
    return {str(p.relative_to(root)): core.sha(p) for p in root.rglob('*.json')}


def main():
    core.verify()
    proposal = core.load('R06', 'replay')['replay']
    bundle, _ = core.inputs('R06', 'replay')
    source_before = hashes(MEMORY)
    original = load_memory(MEMORY)
    assert original == bundle['payload']['memory']
    destination = core.runtime_root(HERE) / 'memory_preview'
    if not destination.exists():
        destination.mkdir()
        shutil.copy2(MEMORY / 'active.json', destination / 'active.json')
        shutil.copytree(MEMORY / 'archive', destination / 'archive')
    context = {k: deepcopy(bundle[k]) for k in ('payload', 'execution_context')}
    committed = commit_memory(destination, context_id=CONTEXT_ID, context=context, result=proposal)
    assert committed['result'] == proposal
    loaded = load_memory(destination)
    resolvable = validate_memory(loaded)
    assert all(ref in resolvable for entry in loaded['entries'] for ref in entry['evidence'])
    first_hashes = hashes(destination)
    assert commit_memory(destination, context_id=CONTEXT_ID, context=context, result=proposal) == committed
    assert hashes(destination) == first_hashes
    for path in (MEMORY / 'archive').glob('*.json'):
        assert path.read_bytes() == (destination / 'archive' / path.name).read_bytes()

    view = compact_memory(loaded)
    assert view['entries'] == loaded['entries']
    counts = {'full_steps': 0, 'detailed_steps': 0, 'numeric_citations': 0}
    for key, source in loaded['sources'].items():
        projected = view['sources'][key]
        if key.endswith('/diff'):
            assert projected == source
            continue
        run = source['run']; trace = projected['run']['trace']
        counts['full_steps'] += len(run['steps'])
        counts['detailed_steps'] += len(projected['detailed_steps'])
        assert len(trace) == len(run['steps'])
        prefix = key.rsplit('/', 1)[0]
        for actual, reduced in zip(run['steps'], trace):
            assert reduced == {'step': prefix + '/' + actual['step'],
                               'action': actual['action'], 'feedback': actual['feedback']}
        for detail in projected['detailed_steps']:
            number = int(detail['step'].rsplit(':', 1)[1])
            actual = run['steps'][number - 1]
            assert detail['action'] == actual['action']
            for side in ('before', 'after'):
                assert detail[side]['observation'] == actual[side]['observation']
                p_menu = detail[side]['commands_ref']; a_menu = actual[side]['commands_ref']
                assert (None if p_menu is None else view['command_pool'][p_menu]) == (
                    None if a_menu is None else source['command_sets'][a_menu])
        assert projected['run']['outcome'] == run['outcome']
    for entry in loaded['entries']:
        for ref in entry['evidence']:
            key, _, position = ref.rpartition(':')
            if position.isdecimal() and int(position) > 0:
                counts['numeric_citations'] += 1
                assert ref in {s['step'] for s in view['sources'][key]['detailed_steps']}
    # Demonstrate direct consumption by the existing Preconditioner message path.
    from src.skill_evolution.v23_3.memory_view import project_messages
    pc_source = core.read(HERE.with_name('semantic_generation_004') / 'handoff/preconditioner_input.json')
    pc_payload = deepcopy(pc_source['payload']); pc_payload['memory'] = loaded
    projected = project_messages([
        {'role': 'system', 'content': core.render_prompt(core.preconditioner.PROMPT_PATH.read_text(), pc_source['background'])},
        {'role': 'user', 'content': json.dumps(pc_payload, ensure_ascii=False, separators=(',', ':'))}])
    assert json.loads(projected[1]['content'])['memory'] == view
    assert hashes(MEMORY) == source_before and load_memory(MEMORY) == original
    core.verify()
    outputs = HERE / 'results'; outputs.mkdir(exist_ok=True)
    report = {
        'checked_at': core.now(), 'structural_roundtrip_passed': True,
        'semantic_approval': 'separate manual review; not implied by this audit',
        'original_memory_unchanged': True, 'preview_only': True,
        'proposal_unchanged': True, 'idempotent_commit': True,
        'before_active_ids': committed['before_active_ids'],
        'after_active_ids': committed['after_active_ids'],
        'new_entries': [{'id': e['id'], 'revises': e['revises'], 'evidence_count': len(e['evidence'])} for e in committed['entries']],
        'projection': counts, 'preconditioner_projection_compatible': True,
        'source_sha256': source_before, 'preview_sha256': first_hashes,
        'audit_script_sha256': core.sha(Path(__file__)),
    }
    for name, value in [('memory_candidate.json', loaded), ('memory_view.json', view), ('MEMORY_AUDIT.json', report)]:
        core.resolve(outputs / name).write_text(json.dumps(value, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if 'sha256' not in k}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

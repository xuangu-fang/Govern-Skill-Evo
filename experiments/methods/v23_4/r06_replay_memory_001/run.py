"""Replay of fresh R06 paired evaluations; separate from original Plan lineage."""
from copy import deepcopy
import difflib
import json
from pathlib import Path
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23.memory import load_memory

core.HERE = Path(__file__).resolve().parent
HERE, ROOT = core.HERE, core.ROOT
ACTOR = HERE.with_name('r06_actor_comparison_001')
EDITOR = HERE.with_name('semantic_generation_005')
MEMORY = ROOT / 'artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/memory'


def inputs(label, stage):
    assert (label, stage) == ('R06', 'replay')
    bundle = core.read(HERE / 'config/replay_bundle.json')
    messages = core.replay.messages_for(bundle)
    assert messages == core.read(HERE / 'config/messages.json')
    assert len(json.dumps(messages, ensure_ascii=False)) <= 2_000_000
    return bundle, messages


core.inputs = inputs


def prepare():
    baseline = core.read(HERE / 'baseline_sources/manifest.json')
    hashes = {str((ROOT / name).relative_to(ROOT)) if (ROOT / name).is_relative_to(ROOT) else name: digest
              for name, digest in core.read(ACTOR / 'config/freeze.json')['sha256'].items()}
    for name, expected in hashes.items():
        if name in baseline:
            assert baseline[name] == expected
            assert core.sha(HERE / 'baseline_sources' / name) == expected
        else:
            assert core.sha(ROOT / name) == expected, name
    changes = []
    for name in baseline:
        changes.extend(difflib.unified_diff(
            (HERE / 'baseline_sources' / name).read_text().splitlines(keepends=True),
            (ROOT / name).read_text().splitlines(keepends=True),
            fromfile='before/' + name, tofile='after/' + name))
        hashes[name] = core.sha(ROOT / name)
    (HERE / 'baseline_sources/compatibility.diff').write_text(''.join(changes))

    selected = core.read(EDITOR / 'runs/R06_editor/selected.json')['attempt']
    attempt = EDITOR / f'runs/R06_editor/attempt_{selected:03}'
    material = core.read(EDITOR / 'config/material.json')
    response = core.read(attempt / 'response.json')
    assert response['finish_reason'] == 'stop'
    parsed = core.parse_json_response(response['content'])
    assert parsed == core.read(attempt / 'parsed.json')
    result = core.validate('editor', parsed, material)
    assert result == core.read(attempt / 'result.json')
    assert result['actual_diff'] == (attempt / 'actual.diff').read_text()
    assert result['candidate_text'] == (attempt / 'candidate.md').read_text()
    assert material['parent'] == (ACTOR / 'config/parent.md').read_text()
    assert result['candidate_text'] == (ACTOR / 'config/candidate.md').read_text()

    # Importing this offline audit does not launch or re-run any Actor.
    from experiments.methods.v23_4.r06_actor_comparison_001.analyze import audit_record
    records, audits, sources = {}, [], []
    for arm in ('parent', 'candidate'):
        records[arm] = []
        for task in range(11, 18):
            marker = ACTOR / f'runs/{arm}/val_{task:04}/selected.json'
            path = core.resolve(core.read(marker)['trajectory'])
            record = core.read(path)
            audits.append({'arm': arm, 'task': record['task']['id'], 'audit': audit_record(record, path)})
            records[arm].append(record)
            sources += [marker, *[p for p in core.archive_glob(path.parent, '*', recursive=True) if p.is_file()]]
    facts = build_facts(records['parent'])
    assert facts['background'] == material['background']
    snapshot = core.read(HERE.with_name('semantic_generation_004') / 'config/memory.json')
    assert load_memory(MEMORY) == snapshot
    evaluation_edit_view = {
        **result, 'facts': facts['facts'], 'background': facts['background'],
        'effective_plan': material['plan']}
    bundle = core.old_replay.build_replay_from_editor(
        evaluation_edit_view, attempt, records['parent'], records['candidate'], memory=snapshot)
    messages = core.replay.messages_for(bundle)
    chars = len(json.dumps(messages, ensure_ascii=False))
    assert chars <= 2_000_000
    core.save(HERE / 'config/replay_bundle.json', bundle)
    core.save(HERE / 'config/messages.json', messages)
    core.save(HERE / 'config/record_audits.json', audits)
    core.save(HERE / 'config/provenance.json', {
        'mode': 'fresh_paired_evaluation_of_frozen_editor_candidate',
        'production_editor_replay_lineage_loader_validated': False,
        'editor': str(attempt.relative_to(ROOT)),
        'fresh_actor_batch': str(ACTOR.relative_to(ROOT)),
        'original_memory_directory': str(MEMORY.relative_to(ROOT)),
        'pairs': len(bundle['payload']['pairs']),
        'steps': sum(len(r['steps']) for r in bundle['payload']['runs']),
        'empty_actions': [s['step'] for r in bundle['payload']['runs'] for s in r['steps'] if s['action'] == ''],
        'input_chars': chars, 'max_input_chars': 2_000_000,
        'production_default_input_chars': 400_000,
        'changed_sources': {name: {'before': digest, 'after': core.sha(ROOT / name)} for name, digest in baseline.items()}})
    paths = [HERE / 'run.py', HERE / 'PROTOCOL.md',
             *[p for p in (HERE / 'baseline_sources').rglob('*') if p.is_file()],
             *[p for p in core.archive_glob(HERE / 'config', '*.json')],
             *[p for p in MEMORY.rglob('*.json')],
             *[p for p in core.archive_glob(attempt, '*', recursive=True) if p.is_file()],
             ROOT / 'tests/skill_evolution/v23_4/test_empty_action_evidence.py',
             *sources]
    hashes.update({str(p.relative_to(ROOT)): core.sha(p) for p in paths})
    _, cfg = core.configuration()
    core.save(HERE / 'config/freeze.json', {
        'at': core.now(), 'call_config': cfg, 'max_restarts': 3,
        'max_logical_calls': 1, 'max_http_attempts': 4, 'sha256': hashes})
    core.verify()
    print(json.dumps(core.read(HERE / 'config/provenance.json'), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['audit']:
        from experiments.methods.v23_4.semantic_generation_001.audit import audit
        result = audit()
        assert result['logical_stages'] == 1 and result['http_attempts'] <= 4
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        assert sys.argv[1:] == ['R06', 'replay']
        core.run('R06', 'replay')

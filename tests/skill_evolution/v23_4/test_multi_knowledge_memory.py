"""P2 opt-in Memory storage contracts; synthetic facts, no model calls or publication."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23 import memory, replay
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from tests.skill_evolution.v23.test_replay_memory import case, entry, output

OLD = memory.LEGACY_CONTRACT
NEW = memory.MULTI_KNOWLEDGE_CONTRACT


def knowledge(text='Synthetic conditional response.', evidence=('diff', 'P1:1', 'Q1:2')):
    return {'text': text, 'evidence': list(evidence)}


def proposal(*items, revises=()):
    return {'revises': list(revises), 'knowledge': list(items) or [knowledge()]}


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*.json')}


def load(root):
    return memory.load_memory(root, memory_contract=NEW)


def commit(root, bundle, result, cid='R1', version=NEW):
    return memory.commit_memory(root, context_id=cid, context=bundle, result=result, memory_contract=version)


def next_context(bundle, root):
    result = deepcopy(bundle)
    result['payload']['memory'] = load(root)
    return result


def test_strict_shapes_and_per_knowledge_evidence(case):
    payload = case[3]['payload']
    # The Entry union needs both types; individual Knowledge need not repeat Diff.
    result = output(proposal(knowledge(evidence=['diff']), knowledge(evidence=['P1:1']),
                             knowledge(evidence=['P1:1', 'Q1:2'])))
    frozen = deepcopy(result)
    assert memory.validate_entries(result, payload, memory_contract=NEW) == result == frozen
    assert memory.entry_evidence(result['entries'][0], memory_contract=NEW) == ['diff', 'P1:1', 'Q1:2']
    with pytest.raises(ValueError):
        memory.validate_entries(result, payload)
    with pytest.raises(ValueError):
        memory.validate_entries(output(entry()), payload, memory_contract=NEW)
    assert memory.validate_entries(output(), payload, memory_contract=NEW) == output()


def test_parse_new_json_without_rewriting_text_or_order(case):
    result = output(proposal(knowledge('  条件与响应\n', ['Q1:2', 'diff', 'P1:1']),
                             knowledge('Second observation.', ['Q2:0', 'P2:outcome'])))
    parsed = parse_json_response(json.dumps(result, ensure_ascii=False))
    assert memory.validate_entries(parsed, case[3]['payload'], memory_contract=NEW) == result
    with pytest.raises(ValueError):
        parse_json_response('{"entries": [], "entries": []}')


@pytest.mark.parametrize('kind', ['empty_array', 'string', 'object', 'blank', 'text_type', 'extra_k',
    'missing_text', 'top_evidence', 'extra_entry', 'empty_evidence', 'duplicate_ref', 'unknown_step',
    'memory_ref', 'check_ref', 'wrong_context', 'no_diff', 'no_run', 'second_bad', 'unknown_revision',
    'wrong_revises', 'extra_result', 'wrong_entries'])
def test_invalid_proposal_is_atomic(case, tmp_path, kind):
    result = output(proposal())
    e = result['entries'][0]; k = e['knowledge'][0]
    if kind == 'empty_array': e['knowledge'] = []
    elif kind == 'string': e['knowledge'] = 'old text'
    elif kind == 'object': e['knowledge'] = k
    elif kind == 'blank': k['text'] = ' \n'
    elif kind == 'text_type': k['text'] = 3
    elif kind == 'extra_k': k['id'] = 'K1'
    elif kind == 'missing_text': del k['text']
    elif kind == 'top_evidence': e['evidence'] = ['diff']
    elif kind == 'extra_entry': e['id'] = 'M1'
    elif kind == 'empty_evidence': k['evidence'] = []
    elif kind == 'duplicate_ref': k['evidence'] *= 2
    elif kind == 'unknown_step': k['evidence'] = ['diff', 'P1:999']
    elif kind == 'memory_ref': k['evidence'] = ['diff', 'M1']
    elif kind == 'check_ref': k['evidence'] = ['diff', 'c1']
    elif kind == 'wrong_context': k['evidence'] = ['diff', 'elsewhere/P1:1']
    elif kind == 'no_diff': k['evidence'] = ['P1:1']
    elif kind == 'no_run': k['evidence'] = ['diff']
    elif kind == 'second_bad': e['knowledge'].append(knowledge(evidence=['P2:999']))
    elif kind == 'unknown_revision': e['revises'] = ['M1']
    elif kind == 'wrong_revises': e['revises'] = 'M1'
    elif kind == 'extra_result': result['reason'] = 'extra'
    else: result['entries'] = {}
    with pytest.raises(ValueError):
        commit(tmp_path, case[3], result)
    assert snapshot(tmp_path) == {}


def test_readonly_normalization_and_identity(case, tmp_path):
    commit(tmp_path, case[3], output(entry()), version=OLD)
    before = snapshot(tmp_path)
    old = memory.load_memory(tmp_path)
    frozen = deepcopy(old)
    normalized = memory.normalize_memory(old, source_contract=OLD)
    assert normalized == load(tmp_path)
    assert normalized['entries'][0] == {'id': 'M1', 'knowledge': [
        {'text': old['entries'][0]['knowledge'], 'evidence': old['entries'][0]['evidence']}]}
    assert normalized['sources'] == old['sources']
    assert memory.normalize_memory(normalized, source_contract=NEW) == normalized
    normalized['entries'][0]['knowledge'][0]['evidence'].clear()
    normalized['sources'].clear()
    assert old == frozen and snapshot(tmp_path) == before
    with pytest.raises(ValueError):
        memory.normalize_memory(old, source_contract=NEW)
    broken = deepcopy(old); broken['entries'][0]['evidence'].append('R1/P1:999')
    with pytest.raises(ValueError):
        memory.normalize_memory(broken, source_contract=OLD)


def test_mixed_history_full_replacement_and_merge(case, tmp_path):
    b = case[3]
    first = commit(tmp_path, b, output(entry(), entry(evidence=['diff', 'P2:1', 'Q2:1'])), version=OLD)
    old_bytes = (tmp_path / 'archive/R1.json').read_bytes()
    assert 'memory_contract' not in first
    b2 = next_context(b, tmp_path)
    kept = deepcopy(b2['payload']['memory']['entries'][0]['knowledge'][0])
    result = output(proposal(knowledge('Revised current observation.'), kept,
                             knowledge('Separate conditional response.', ['P2:1', 'Q2:1']), revises=['M1']))
    raw = deepcopy(result)
    second = commit(tmp_path, b2, result, 'R2')
    assert second['memory_contract'] == NEW and result == raw
    assert second['after_active_ids'] == ['M2', 'M3']
    stored = second['entries'][0]
    assert set(stored) == {'id', 'context_id', 'revises', 'knowledge'}
    assert stored['knowledge'][0]['evidence'] == ['R2/diff', 'R2/P1:1', 'R2/Q1:2']
    assert stored['knowledge'][1] == kept
    assert stored['knowledge'][2]['evidence'] == ['R2/P2:1', 'R2/Q2:1']
    view = load(tmp_path)
    assert view['entries'][0] == b2['payload']['memory']['entries'][1]  # untouched M2
    assert view['entries'][1]['knowledge'] == stored['knowledge']
    assert {'R1/diff', 'R1/P1', 'R1/Q1', 'R2/diff', 'R2/P2', 'R2/Q2'} <= view['sources'].keys()
    b3 = next_context(b, tmp_path)
    third = commit(tmp_path, b3, output(proposal(knowledge('Replacement only.'), revises=['M2', 'M3'])), 'R3')
    assert third['after_active_ids'] == ['M4']
    assert len(load(tmp_path)['entries'][0]['knowledge']) == 1  # no automatic copying
    assert set(load(tmp_path)['sources']) == {'R3/diff', 'R3/P1', 'R3/Q1'}
    assert (tmp_path / 'archive/R1.json').read_bytes() == old_bytes
    with pytest.raises(ValueError, match='Legacy Memory reader'):
        memory.load_memory(tmp_path)
    with pytest.raises(ValueError):
        commit(tmp_path, b, output(entry()), 'R4', version=OLD)


@pytest.mark.parametrize('kind', ['duplicate_within', 'duplicate_across', 'inactive'])
def test_revision_targets(case, tmp_path, kind):
    commit(tmp_path, case[3], output(proposal()))
    b = next_context(case[3], tmp_path)
    if kind == 'duplicate_within': r = output(proposal(revises=['M1', 'M1']))
    elif kind == 'duplicate_across': r = output(proposal(revises=['M1']), proposal(revises=['M1']))
    else:
        commit(tmp_path, b, output(proposal(revises=['M1'])), 'R2')
        b = next_context(case[3], tmp_path)
        r = output(proposal(revises=['M1']))
    before = snapshot(tmp_path)
    with pytest.raises(ValueError): commit(tmp_path, b, r, 'invalid')
    assert snapshot(tmp_path) == before


def test_exact_reuse_empty_results_and_stale_snapshot(case, tmp_path):
    b = case[3]; result = output(proposal())
    first = commit(tmp_path, b, result)
    before = snapshot(tmp_path)
    assert commit(tmp_path, b, result) == first
    assert snapshot(tmp_path) == before
    with pytest.raises(ValueError, match='Committed round differs'):
        commit(tmp_path, b, output(proposal(knowledge('Different text.'))))
    b2 = next_context(b, tmp_path)
    second = commit(tmp_path, b2, output(), 'R2')
    assert second['before_active_ids'] == second['after_active_ids'] == ['M1']
    assert second['entries'] == [] and second['memory_contract'] == NEW
    assert load(tmp_path) == b2['payload']['memory']
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='Active snapshot changed'):
        commit(tmp_path, b, result, 'R3')
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('pending_version', [OLD, NEW])
def test_crash_recovery_and_version_identity(case, tmp_path, monkeypatch, pending_version):
    original = memory.write_record
    b = case[3]
    result = output(entry()) if pending_version == OLD else output(proposal())
    def fail(path, value):
        if path.name == 'active.json': raise KeyboardInterrupt()
        original(path, value)
    monkeypatch.setattr(memory, 'write_record', fail)
    with pytest.raises(KeyboardInterrupt): commit(tmp_path, b, result, version=pending_version)
    assert load(tmp_path) == memory.empty_memory()
    pending = snapshot(tmp_path)
    monkeypatch.setattr(memory, 'write_record', original)
    with pytest.raises(ValueError, match='pending Memory'):
        commit(tmp_path, b, output(proposal()), 'other')
    with pytest.raises(ValueError, match='Interrupted commit differs'):
        commit(tmp_path, b, output(proposal(knowledge('Changed request.'))))
    assert snapshot(tmp_path) == pending
    recovered = commit(tmp_path, b, result, version=pending_version)
    assert commit(tmp_path, b, result, version=pending_version) == recovered
    assert recovered['after_active_ids'] == ['M1']


def test_empty_commit_still_has_contract_identity(case, tmp_path):
    commit(tmp_path, case[3], output(), version=OLD)
    with pytest.raises(ValueError, match='Committed round differs'):
        commit(tmp_path, case[3], output(), version=NEW)
    new_root = tmp_path / 'new'
    commit(new_root, case[3], output())
    with pytest.raises(ValueError, match='Legacy Memory reader'):
        memory.load_memory(new_root)


@pytest.mark.parametrize('version', [None, 'unknown', 1])
def test_unknown_contract_rejected_even_when_empty(case, tmp_path, version):
    with pytest.raises(ValueError): memory.validate_memory(memory.empty_memory(), memory_contract=version)
    with pytest.raises(ValueError): memory.normalize_memory(memory.empty_memory(), source_contract=version)
    with pytest.raises(ValueError): memory.validate_entries(output(), case[3]['payload'], memory_contract=version)
    with pytest.raises(ValueError): memory.load_memory(tmp_path, memory_contract=version)
    with pytest.raises(ValueError): commit(tmp_path, case[3], output(), version=version)
    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize('kind', ['unknown_version', 'missing_version', 'wrong_version', 'stored_text',
    'stored_ref', 'snapshot', 'after_ids', 'raw_proposal', 'bad_current_run', 'missing_source'])
def test_archive_tampering_rejected(case, tmp_path, kind):
    commit(tmp_path, case[3], output(proposal()))
    b = next_context(case[3], tmp_path)
    commit(tmp_path, b, output(proposal(revises=['M1'])), 'R2')
    path = tmp_path / 'archive/R2.json'
    value = json.loads(path.read_text())
    if kind == 'unknown_version': value['memory_contract'] = 'unknown'
    elif kind == 'missing_version': del value['memory_contract']
    elif kind == 'wrong_version': value['memory_contract'] = OLD
    elif kind == 'stored_text': value['entries'][0]['knowledge'][0]['text'] = 'Not generated.'
    elif kind == 'stored_ref': value['entries'][0]['knowledge'][0]['evidence'][1] = 'R1/P1:1'
    elif kind == 'snapshot': value['context']['payload']['memory']['entries'][0]['knowledge'][0]['text'] = 'Fabricated history.'
    elif kind == 'after_ids': value['after_active_ids'] = ['M1']
    elif kind == 'raw_proposal': value['result']['entries'][0]['knowledge'].append(knowledge())
    elif kind == 'bad_current_run': value['context']['payload']['runs'][0]['steps'][0]['step'] = 'P1:5'
    else: del value['context']['payload']['memory']['sources']['R1/P1']
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError): load(tmp_path)


@pytest.mark.parametrize('round_id', ['R04', 'R05'])
def test_real_frozen_memory_compatibility_readonly(round_id):
    root = Path('artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds') / round_id / 'memory'
    before = snapshot(root)
    assert before, 'Expected frozen formal Memory fixture'
    old = memory.load_memory(root)
    new = load(root)
    assert new == memory.normalize_memory(old, source_contract=OLD)
    assert new['sources'] == old['sources']
    assert snapshot(root) == before


def test_old_replay_reload_remains_raw():
    root = Path('artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/replay/attempts/001')
    before = snapshot(root)
    result = replay.load_replay(root)['replay']
    assert result['entries'] and all(isinstance(e['knowledge'], str) for e in result['entries'])
    assert snapshot(root) == before


def test_new_commit_requires_normalized_legacy_snapshot(case, tmp_path):
    commit(tmp_path, case[3], output(entry()), version=OLD)
    b = deepcopy(case[3]); b['payload']['memory'] = memory.load_memory(tmp_path)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError): commit(tmp_path, b, output(proposal()), 'R2')
    assert snapshot(tmp_path) == before
    # Conversion is explicit; mixed shapes in a single snapshot are never guessed.
    mixed = memory.normalize_memory(b['payload']['memory'], source_contract=OLD)
    mixed['entries'].append({**b['payload']['memory']['entries'][0], 'id': 'M2'})
    with pytest.raises(ValueError): memory.validate_memory(mixed, memory_contract=NEW)
    with pytest.raises(ValueError): memory.validate_memory(mixed, memory_contract=OLD)


def test_snapshot_change_between_two_writers_is_rejected(case, tmp_path):
    # Both writers observed the same Active snapshot; only the first may publish.
    stale = deepcopy(case[3])
    commit(tmp_path, case[3], output(proposal()), 'writer_A')
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='Active snapshot changed'):
        commit(tmp_path, stale, output(proposal()), 'writer_B')
    assert snapshot(tmp_path) == before


def test_new_empty_commit_on_legacy_history_preserves_active(case, tmp_path):
    commit(tmp_path, case[3], output(entry()), version=OLD)
    old_bytes = (tmp_path / 'archive/R1.json').read_bytes()
    bundle = next_context(case[3], tmp_path)
    saved = commit(tmp_path, bundle, output(), 'R2')
    assert saved['memory_contract'] == NEW and saved['entries'] == []
    assert load(tmp_path) == bundle['payload']['memory']
    assert (tmp_path / 'archive/R1.json').read_bytes() == old_bytes
    with pytest.raises(ValueError, match='Legacy Memory reader'): memory.load_memory(tmp_path)

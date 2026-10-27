"""V23.5 pair prose survives normalization, compilation and downstream reload."""
from copy import deepcopy

import pytest

from src.skill_evolution.v23.preconditioner import compile_effective_plan as legacy_compile
from src.skill_evolution.v23_5 import preconditioner, editor
from src.skill_evolution.v23_5.memory_view import MEMORY_V3, KNOWLEDGE_ONLY
from src.skill_evolution.v23_5.update_patch import normalize_update_patches, compile_effective_plan
from .helpers import Fake, keep, memory, revise


def pair_proposal(payload, field, expression):
    raw = keep(payload)
    raw['adjustments'][0] = revise(payload)
    if field == 'change':
        raw['adjustments'][0]['change'] += f' Preserve the behavior in {expression}.'
    elif field == 'update':
        raw['adjustments'][0] = revise(payload, replacement=f'Preserve behavior in {expression}.\n')
    else:
        raw['checks'] = [{'id': 'c1', 'update_ids': ['u1'],
                          'question': f'Was the behavior in {expression} preserved?'}]
    return raw


@pytest.mark.parametrize('view', [MEMORY_V3, KNOWLEDGE_ONLY])
@pytest.mark.parametrize('field', ['change', 'update', 'check'])
@pytest.mark.parametrize('expression', ['P1/P2', 'P1:1/P2:1'])
def test_current_pairs_survive_all_prose_layers(payload, view, field, expression):
    raw = pair_proposal(payload, field, expression)
    before = deepcopy((raw, payload))
    normalized, effective = normalize_update_patches(raw, payload, memory_view=view)
    assert compile_effective_plan(normalized, payload) == effective
    assert (raw, payload) == before
    if field == 'change':
        assert expression in normalized['adjustments'][0]['reason']
    elif field == 'update':
        assert expression in effective['updates'][0]['text']
    else:
        assert expression in effective['checks'][0]['question']
    # The historical compiler retains its original reference rules.
    with pytest.raises(ValueError, match='historical reference'):
        legacy_compile(normalized, payload)


@pytest.mark.parametrize('view', [MEMORY_V3, KNOWLEDGE_ONLY])
@pytest.mark.parametrize('field', ['change', 'update', 'check'])
@pytest.mark.parametrize('expression', ['P1/P999', 'P1:1/P2:999', 'Unknown/P2'])
def test_unknown_pair_members_and_history_stay_rejected(payload, view, field, expression):
    with pytest.raises(ValueError, match='historical reference'):
        normalize_update_patches(pair_proposal(payload, field, expression), payload, memory_view=view)


@pytest.mark.parametrize('view', [MEMORY_V3, KNOWLEDGE_ONLY])
def test_reason_still_requires_individual_backtick_citations(payload, view):
    raw = pair_proposal(payload, 'change', 'P1/P2')
    for reason in ['Based on P1/P2.', 'Based on `P1/P2`.']:
        raw['adjustments'][0]['reason'] = reason
        with pytest.raises(ValueError, match='single-backtick|allowed reference set'):
            normalize_update_patches(raw, payload, memory_view=view)
    raw['adjustments'][0]['reason'] = 'Based on `P1`/`P2`.'
    normalize_update_patches(raw, payload, memory_view=view)


@pytest.mark.parametrize('view', [MEMORY_V3, KNOWLEDGE_ONLY])
def test_archive_context_collision_is_not_silently_current(payload, view):
    payload['memory'] = memory(payload)
    payload['memory']['sources']['P1/diff'] = deepcopy(payload['memory']['sources']['R1/diff'])
    with pytest.raises(ValueError, match='Ambiguous current/historical reference'):
        normalize_update_patches(pair_proposal(payload, 'change', 'P1/P2'), payload, memory_view=view)


@pytest.mark.parametrize('view', [MEMORY_V3, KNOWLEDGE_ONLY])
def test_pair_change_survives_preconditioner_and_editor_reload(upstream, payload, tmp_path, view):
    gd, dd, _, pd = upstream
    raw = pair_proposal(payload, 'change', 'P1/P2')
    fake = Fake(raw)
    saved = preconditioner.run_preconditioner(gd, dd, pd, generate=fake, memory_view=view)
    assert preconditioner.load_preconditioner(pd) == saved
    ed = tmp_path/'editor'
    editor_fake = Fake({'patch': '', 'reason': 'No further text change.'})
    result = editor.run_editor(pd, ed, generate=editor_fake)
    assert editor.load_editor(ed) == result
    assert result['preconditioner'] == saved['preconditioner']
    assert fake.calls == editor_fake.calls == 1


@pytest.mark.parametrize('view', [MEMORY_V3, KNOWLEDGE_ONLY])
@pytest.mark.parametrize('field', ['update', 'check'])
def test_history_outside_current_runs_survives_compilation_and_reload(upstream, payload, tmp_path, view, field):
    history = memory(payload)
    source = history['sources'].pop('R1/P1')
    source['run']['ref'] = 'P99'
    for i, step in enumerate(source['run']['steps'], 1):
        step['step'] = f'P99:{i}'
    history['sources']['R1/P99'] = source
    history['entries'][0]['knowledge'][0]['evidence'] = ['R1/diff', 'R1/P99:1']
    payload = {**payload, 'memory': history}
    raw = pair_proposal(payload, field, 'R1/P99:1')
    before = deepcopy((raw, payload))
    normalized, effective = normalize_update_patches(raw, payload, memory_view=view)
    assert compile_effective_plan(normalized, payload) == effective
    assert (raw, payload) == before
    gd, dd, _, pd = upstream
    saved = preconditioner.run_preconditioner(gd, dd, pd, generate=Fake(raw),
                                             memory=history, memory_view=view)
    assert saved['effective_plan'] == effective
    assert preconditioner.load_preconditioner(pd) == saved
    ed = tmp_path/'editor'
    result = editor.run_editor(pd, ed, generate=Fake({'patch': '', 'reason': 'No further text change.'}))
    assert editor.load_editor(ed) == result
    assert result['preconditioner'] == saved['preconditioner']


@pytest.mark.parametrize('kind', ['duplicate_id', 'source_collision', 'update_collision', 'withdrawn_update'])
def test_compiled_check_structure_remains_strict(payload, kind):
    normalized, _ = normalize_update_patches(keep(payload), payload)
    check = {'id': 'c1', 'update_ids': ['u1'], 'question': 'Is the behavior preserved?'}
    normalized['checks'] = [check]
    if kind == 'duplicate_id':
        normalized['checks'].append(deepcopy(check))
    elif kind == 'source_collision':
        check['id'] = 'P1'
    elif kind == 'update_collision':
        check['id'] = 'u1'
    else:
        normalized['adjustments'] = [{'from': ['u1'], 'to': [], 'basis': ['P1:1'],
                                      'reason': 'Withdraw this proposal.'}]
    with pytest.raises(ValueError, match='colliding Check ID|check.update_ids'):
        compile_effective_plan(normalized, payload)

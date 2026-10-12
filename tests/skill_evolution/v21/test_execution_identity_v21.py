"""Execution reuse is not replication; action equality is not execution identity."""
from copy import deepcopy

import pytest

from src.skill_evolution.v19.evolution_replay_v19 import _execution_ref
from src.skill_evolution.v21.evidence_wire_v21 import pack_review, pack_memory, expand
from tests.skill_evolution.v21.test_evidence_wire_v21 import comparison_packet


def reused_packet():
    p = comparison_packet()
    tid = p['events']['EVENT/current']['trajectory_ref']
    p['trajectories'][tid]['execution_ref'] = 'EXECUTION/saved-run'
    old = deepcopy(p['trajectories'][tid])
    old.update(source_round_id='previous-round', task_ref='TASK/old-alias')
    p['trajectories']['TRAJECTORY/reused'] = old
    p['events']['EVENT/reused'] = deepcopy(p['events']['EVENT/current'])
    p['events']['EVENT/reused']['trajectory_ref'] = 'TRAJECTORY/reused'
    return p


def rows(wire):
    return [r for group in wire['operation_comparison']['write'].values() for r in group]


def test_saved_execution_survives_role_changes_but_not_independent_identical_runs():
    raw = {'simulation': {'id': 'run-1', 'messages': ['same visible actions']}, 'binding': {'role': 'CANDIDATE'}}
    imported = deepcopy(raw)
    imported['binding']['role'] = 'PARENT'
    assert _execution_ref(raw) == _execution_ref(imported)
    imported['simulation']['id'] = 'run-2'
    assert _execution_ref(raw) != _execution_ref(imported)
    del imported['simulation']['id']
    assert _execution_ref(imported) is None


def test_aliases_of_one_execution_share_one_operation_row_and_keep_all_citations():
    p = reused_packet(); original = deepcopy(p)
    wire, mapping = pack_review(p)
    assert expand(wire, mapping) == original == p
    assert len(rows(wire)) == 2  # earlier genuinely different run plus reused current
    row = next(r for r in rows(wire) if 'other_representations' in r)
    assert {mapping[r['evidence_ref']] for r in [row, *row['other_representations']]} == {
        'EVENT/current', 'EVENT/reused'}
    assert mapping[row['execution_ref']] == 'EXECUTION/saved-run'
    assert len(wire['events']) == len(p['events'])


@pytest.mark.parametrize('difference', ['independent_run', 'unknown_identity', 'different_step', 'different_label'])
def test_no_unsafe_merging_of_identical_actions(difference):
    p = reused_packet()
    if difference == 'independent_run':
        p['trajectories']['TRAJECTORY/reused']['execution_ref'] = 'EXECUTION/independent'
    elif difference == 'unknown_identity':
        del p['trajectories']['TRAJECTORY/reused']['execution_ref']
    elif difference == 'different_step':
        p['events']['EVENT/reused']['event']['step'] += 1
    else:
        p['trajectories']['TRAJECTORY/reused']['supervision']['compliant'] = False
    wire, mapping = pack_review(p)
    assert len(rows(wire)) == 3
    assert expand(wire, mapping) == p


def test_shared_identity_survives_adjacent_memory_pairs_without_collapsing_outcomes():
    p = reused_packet()
    current = p['events']['EVENT/current']['trajectory_ref']
    p['pairs'] = {
        'PAIR/first': {'parent':'TRAJECTORY/earlier', 'candidate':'TRAJECTORY/reused',
                       'round_id':'r1', 'task_ref':'TASK/old-alias'},
        'PAIR/second': {'parent':current, 'candidate':'TRAJECTORY/earlier',
                        'round_id':'r2', 'task_ref':'TASK/example'}}
    wire, mapping = pack_memory(p)
    first, second = wire['replay_comparison']
    assert first['candidate']['execution_ref'] == second['parent']['execution_ref']
    assert len(wire['replay_comparison']) == 2 and expand(wire, mapping) == p
    first['candidate']['execution_ref'] = 'invented-execution'
    with pytest.raises(ValueError, match='comparison differs'):
        expand(wire, mapping)


def test_dedup_aliases_are_verified_and_legacy_comparison_still_decodes():
    p = reused_packet()
    wire, mapping = pack_review(p)
    row = next(r for r in rows(wire) if 'other_representations' in r)
    row['other_representations'].clear()
    with pytest.raises(ValueError, match='comparison differs'):
        expand(wire, mapping)
    from src.skill_evolution.v21.evidence_wire_v21 import pack, _operation_comparison
    old, mapping = pack(p)
    old['operation_comparison'] = _operation_comparison(p, old, mapping)
    old['reference_encoding'] = 'operation_comparison_v21.1'
    assert len(rows(old)) == 3 and expand(old, mapping) == p

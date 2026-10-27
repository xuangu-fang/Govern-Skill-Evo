"""Lossless round trips and reference isolation; all tests are offline."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from experiments.methods.v23_5.verifier_input_002 import prepare as p


def fixture(name):
    return p.io.read(p.v.DEFAULT_OUTPUT/'cases'/name/'verifier_input.json')


@pytest.mark.parametrize('name', p.io.ROUNDS)
def test_real_inputs_exact_round_trip_without_mutation(name):
    original = fixture(name)
    saved = deepcopy(original)
    value = p.compact(original)
    restored = p.restore(value)
    assert original == saved == restored
    assert value['context'] == original['context']
    assert value['targets'] == original['targets']
    assert list(value['source_records']) == list(original['source_records'])
    for ref, source in original['source_records'].items():
        new = value['source_records'][ref]
        if 'record' in source:
            assert new['record'] == source['record']
            for local, menu in source['command_sets'].items():
                assert value['command_sets'][new['command_set_refs'][local]] == menu
    assert p.io.size(value)['chars'] < p.io.size(original)['chars']


def synthetic():
    # Deliberately reuse C1 across records with different content and aliases.
    menus = [['take 杯子', 'look', 'look'], ['look', 'take 杯子', 'look'],
             ['take 杯子', 'look', 'look'], [], ['take 杯子', 'look']]
    records = {}
    refs = ['Q1:1', 'S1_R01/Q1:1', 'Q2:1', 'Q3:1', 'Q4:1']
    for ref, menu in zip(refs, menus):
        records[ref] = {'record': {'before': {'commands_ref': 'C1'},
                                  'after': {'commands_ref': None}},
                        'command_sets': {'C1': menu}, 'role': 'candidate'}
    return {'context': {'flag': False, 'steps': 1}, 'targets': [{'knowledge': {'text': 'fixture', 'evidence': refs}}],
            'source_records': records}


def test_same_id_isolation_exact_content_dedup_order_duplicates_empty_null():
    old = synthetic()
    value = p.compact(old)
    refs = [s['command_set_refs']['C1'] for s in value['source_records'].values()]
    assert refs[0] == refs[2]
    assert len(set(refs)) == 4  # Different order, duplicate count and empty list stay distinct.
    assert p.restore(value) == old
    restored = p.restore(value)
    restored['source_records']['Q1:1']['command_sets']['C1'].append('changed')
    assert restored['source_records']['Q2:1']['command_sets']['C1'] == old['source_records']['Q2:1']['command_sets']['C1']
    assert p.restore(value) == old


def test_full_execution_initial_outcome_and_historical_records():
    base = p.io.DEFAULT_OUTPUT/'cases'
    current = p.io.read(base/'R02/frozen/bundle.json')
    previous = p.io.read(base/'R01/frozen/bundle.json')
    candidate = {'entries': [{'revises': [], 'knowledge': [{'text': 'fixture',
                 'evidence': ['diff', 'P1', 'P1:0', 'P1:outcome', 'S1_R01/Q5:49']}]}]}
    original, _ = p.io.build_input(current, candidate, {'S1_R01': previous})
    assert p.restore(p.compact(original)) == original


@pytest.mark.parametrize('corruption', ['local_missing', 'local_extra', 'global_missing',
                                      'global_unused', 'global_duplicate', 'bad_list', 'source_missing',
                                      'inline_menu', 'wrong_resolved_list', 'changed_action',
                                      'boolean_as_integer', 'integer_as_float'])
def test_missing_ambiguous_or_changed_references_rejected(corruption):
    old = synthetic()
    value = p.compact(old)
    source = value['source_records']['Q1:1']
    shared = source['command_set_refs']['C1']
    if corruption == 'local_missing':
        source['command_set_refs'].clear()
    elif corruption == 'local_extra':
        source['command_set_refs']['C99'] = shared
    elif corruption == 'global_missing':
        del value['command_sets'][shared]
    elif corruption == 'global_unused':
        value['command_sets']['extra'] = ['unused']
    elif corruption == 'global_duplicate':
        value['command_sets']['extra'] = list(value['command_sets'][shared])
    elif corruption == 'bad_list':
        value['command_sets'][shared] = [False]
    elif corruption == 'source_missing':
        del value['source_records']['Q1:1']
    elif corruption == 'inline_menu':
        source['command_sets'] = {}
    elif corruption == 'wrong_resolved_list':
        # All references still resolve, but they resolve to the wrong original list.
        a, b = list(value['command_sets'])[:2]
        value['command_sets'][a], value['command_sets'][b] = value['command_sets'][b], value['command_sets'][a]
    elif corruption == 'changed_action':
        source['record']['action'] = 'invented'
    elif corruption == 'boolean_as_integer':
        value['context']['flag'] = 0
    elif corruption == 'integer_as_float':
        value['context']['steps'] = 1.0
    with pytest.raises(ValueError):
        p.verify_equivalence(old, value)


def test_existing_output_validator_works_and_shared_ids_are_not_evidence():
    value = p.compact(fixture('R02'))
    response = p.io.read(p.ROOT/'artifacts/methods/v23_5/verifier_run_001/runs/R02/attempts/001/response.json')
    result = deepcopy(p.v.validate_response(response, value))
    result['results'][2]['issues'][0]['evidence'] = [next(iter(value['command_sets']))]
    with pytest.raises(ValueError, match='unprovided source key'):
        p.v.validate_result(result, value)


def test_artifact_freeze_restore_and_tamper_detection(tmp_path):
    root = tmp_path/'package'
    assert p.prepare(root)['valid']
    assert p.verify(root)['entire_original_inputs_restored']
    with pytest.raises(ValueError, match='Output exists'):
        p.prepare(root)
    file = root/'cases/R01/verifier_input.json'
    value = p.io.read(file)
    value['command_sets'][next(iter(value['command_sets']))].append('tampered')
    p.io.save(file, value)
    with pytest.raises(ValueError, match='Frozen file changed'):
        p.verify(root)

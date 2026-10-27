"""Offline checks against the frozen real R01-R03 fixtures; no model calls."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import shutil

import pytest

spec = importlib.util.spec_from_file_location('verifier_input_prepare', Path(__file__).with_name('prepare.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def fixture(name):
    case = builder.DEFAULT_OUTPUT/'cases'/name
    return builder.read(case/'frozen/bundle.json'), builder.read(case/'candidate.json')


def proposal(*refs):
    return {'entries': [{'revises': [], 'knowledge': [{'text': 'Fixture claim', 'evidence': list(refs)}]}]}


def test_real_cases_references_and_exact_raw_records():
    for name, count in [('R01', 5), ('R02', 6), ('R03', 7)]:
        bundle, candidate = fixture(name)
        untouched = deepcopy((bundle, candidate))
        value, _ = builder.build_input(bundle, candidate)
        assert (bundle, candidate) == untouched
        assert len(value['targets']) == count
        assert set(value['source_records']) == {ref for e in candidate['entries'] for k in e['knowledge'] for ref in k['evidence']}
        for ref, source in value['source_records'].items():
            if ref == 'diff':
                continue
            run = next(r for r in bundle['payload']['runs'] if r['ref'] == ref.split(':')[0])
            step = next(s for s in run['steps'] if s['step'] == ref)
            assert source['record'] == step
            assert set(source['command_sets']) == {step[side]['commands_ref'] for side in ('before', 'after')} - {None}
            for key, menu in source['command_sets'].items():
                assert menu == bundle['payload']['command_sets'][key]


def test_known_fact_records_are_present_without_rewriting_claims():
    bundle, candidate = fixture('R01')
    value, _ = builder.build_input(bundle, candidate)
    assert value['source_records']['Q5:49']['record']['action'] == 'go to shelf 1'
    assert 'Q5:48' not in value['source_records']  # No implicit neighbor expansion.
    assert value['targets'][4]['knowledge'] == candidate['entries'][0]['knowledge'][4]
    bundle, candidate = fixture('R02')
    value, _ = builder.build_input(bundle, candidate)
    for ref in ('P6:1', 'Q6:9'):
        assert 'kettle' not in value['source_records'][ref]['record']['after']['observation'].lower()


def test_exact_carryover_requires_revised_entry_and_preserves_evidence_order():
    old = {'text': 'same', 'evidence': ['S1_R01/diff', 'S1_R01/Q5:49']}
    memory = {'entries': [{'id': 'M1', 'knowledge': [old]}]}
    candidate = {'entries': [{'revises': ['M1'], 'knowledge': [deepcopy(old)]}]}
    assert builder.select_targets(candidate, memory)[0] == []
    candidate['entries'][0]['knowledge'][0]['evidence'].reverse()
    assert len(builder.select_targets(candidate, memory)[0]) == 1
    candidate['entries'][0] = {'revises': [], 'knowledge': [deepcopy(old)]}
    targets, inventory = builder.select_targets(candidate, memory)
    assert len(targets) == 1  # An added duplicate is still new, not silently skipped.
    assert inventory['untouched_memory_entries'] == [{'memory_id': 'M1', 'knowledge_count': 1}]


def test_initial_outcome_and_full_run_reference_granularity():
    bundle, _ = fixture('R01')
    value, _ = builder.build_input(bundle, proposal('diff', 'P1:0', 'P1:outcome', 'P1'))
    run = next(r for r in bundle['payload']['runs'] if r['ref'] == 'P1')
    assert value['source_records']['P1:0']['record'] == run['initial']
    assert value['source_records']['P1:outcome']['record'] == run['outcome']
    assert value['source_records']['P1:outcome']['executed_action_count'] == len(run['steps'])
    assert value['source_records']['P1']['record'] == run


def test_historical_ref_uses_old_round_not_current_id():
    current, _ = fixture('R02')
    previous, _ = fixture('R01')
    candidate = proposal('diff', 'S1_R01/Q5:49')
    value, _ = builder.build_input(current, candidate, {'S1_R01': previous})
    assert value['source_records']['S1_R01/Q5:49']['record']['action'] == 'go to shelf 1'
    assert value['source_records']['S1_R01/Q5:49']['task_id'] == 'train:0004'
    assert 'Q5:49' not in value['source_records']
    previous['payload']['runs'][14]['steps'][48]['action'] = 'tampered action'
    with pytest.raises(ValueError, match='Historical run differs'):
        builder.build_input(current, candidate, {'S1_R01': previous})


def test_nonexistent_and_unavailable_historical_refs_are_rejected():
    current, _ = fixture('R02')
    previous, _ = fixture('R01')
    with pytest.raises(ValueError):
        builder.build_input(current, proposal('diff', 'Q5:999'))
    with pytest.raises(ValueError, match='Unavailable historical reference'):
        builder.build_input(current, proposal('diff', 'S1_R01/Q5:48'), {'S1_R01': previous})


def test_pair_identity_corruption_is_rejected():
    bundle, candidate = fixture('R01')
    bundle['pair_audit'][0]['candidate']['task_id'] = 'wrong-task'
    with pytest.raises(ValueError, match='task identity'):
        builder.build_input(bundle, candidate)


def test_saved_input_tampering_and_overwrite_are_rejected(tmp_path):
    output = tmp_path/'copy'
    shutil.copytree(builder.DEFAULT_OUTPUT, output)
    assert builder.verify(output)['targets'] == 18
    file = output/'cases/R01/verifier_input.json'
    data = builder.read(file)
    data['source_records']['Q5:49']['record']['action'] = 'go to drawer 1'
    builder.save(file, data)
    with pytest.raises(ValueError, match='extracted input differs'):
        builder.verify(output)
    with pytest.raises(ValueError, match='Output exists'):
        builder.prepare(builder.DEFAULT_SOURCE, output)

"""Losslessness, scope and the actual seven-module message boundary; no models."""
from copy import deepcopy
import json

import pytest

from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.benchmarks.officeqa import input_view as iv, evidence, facts, prompting as pr
from src.skill_evolution.v26 import modules, config
from .conftest import response
from .test_evidence import saved_plan, proposal
from .test_prompts import keep, conflict


def raw(bundle):
    return evidence.model_input(bundle)


def rebuild_requests(run):
    for attempt, expected in zip(run['attempts'], iv._requests(run)):
        attempt['request_messages'] = expected


def test_roundtrip_keeps_all_evidence_pairs_and_text(make_bundle):
    bundle, adapter, _, _ = make_bundle(two=True)
    value = raw(bundle); before = deepcopy(value)
    encoded = iv.project(value)
    assert iv.restore(encoded) == before == value
    assert [r['ref'] for r in encoded['runs']] == ['P1', 'Q1', 'P2', 'Q2']
    assert list(encoded).index('pairs') < list(encoded).index('runs')
    assert encoded['pairs'] == value['pairs'] and encoded['memory'] == value['memory']
    assert all('request_messages' not in a for r in encoded['runs'] for a in r['attempts'])
    assert encoded['runs'][0]['initial']['messages'][0] != encoded['runs'][1]['initial']['messages'][0]
    for i in (0, 2):
        assert encoded['runs'][i]['initial']['messages'][1:] == encoded['runs'][i+1]['initial']['messages'][1:]
    assert len(iv.exact(encoded)) < len(iv.exact(value))
    for original, decoded in zip(value['runs'], iv.restore(encoded)['runs']):
        assert evidence.run_references(original) == evidence.run_references(decoded)
        assert original['attempts'] == decoded['attempts']
    with using_benchmark(adapter):
        sent = pr.replay_messages(bundle)
        assert iv.restore(json.loads(sent[1]['content'])) == value
        assert sent[0]['content'].startswith(pr.render('replay', bundle['background']))


@pytest.mark.parametrize('change', ['space', 'case', 'newline', 'unicode'])
def test_initial_sharing_requires_exact_whole_user_sequence(make_bundle, change):
    bundle, _, _, _ = make_bundle()
    value = raw(bundle); q = value['runs'][1]
    q['initial']['messages'][1]['content'] += {'space': ' ', 'case': 'Aa', 'newline': '\r\n',
                                             'unicode': '\u00e9e\u0301 中文'}[change]
    rebuild_requests(q)
    encoded = iv.project(value)
    assert iv.restore(encoded) == value
    # No pair-level user sharing, even for the other still-identical user messages.
    assert encoded['runs'][0]['initial']['messages'][1:] == value['runs'][0]['initial']['messages'][1:]
    assert encoded['runs'][1]['initial']['messages'][1:] == value['runs'][1]['initial']['messages'][1:]


def test_no_cross_task_user_sharing_or_normalized_system(make_bundle):
    bundle, _, _, _ = make_bundle(two=True)
    parents = [deepcopy(r) for r in raw(bundle)['runs'] if r['ref'].startswith('P')]
    parents[1]['initial']['messages'] = deepcopy(parents[0]['initial']['messages'])
    parents[1]['initial']['messages'][0]['content'] += ' '
    rebuild_requests(parents[1])
    value = {'parent': 'Parent\n', 'runs': parents}
    encoded = iv.project(value)
    assert not encoded[iv.HEADER]['messages']
    assert iv.restore(encoded) == value


@pytest.mark.parametrize('rounds', [1, 2, 8, 24])
def test_all_round_lengths_and_tool_errors_roundtrip(make_run, rounds):
    script = [response(calls=[('read', {'path': 'not_allowed.txt', 'start': 1, 'limit': 2}),
                              ('glob', {'pattern': '*.txt'})])] * (rounds-1)
    script.append(response('<answer>1000</answer>'))
    record, _, _, _ = make_run(script)
    value = facts.build_facts([record])['facts']; encoded = iv.project(value)
    assert iv.restore(encoded) == value
    assert len(encoded['runs'][0]['attempts']) == rounds
    for actual, expected in zip(encoded['runs'][0]['attempts'], value['runs'][0]['attempts']):
        assert actual['assistant'] == expected['assistant'] and actual['tools'] == expected['tools']


def test_round_limit_exhaustion_is_preserved(make_run):
    record, _, _, _ = make_run([response(calls=[('glob', {'pattern': '*'})])] * 24)
    value = facts.build_facts([record])['facts']
    assert value['runs'][0]['outcome']['termination'] == 'max_tool_turns'
    assert iv.restore(iv.project(value)) == value


def test_history_mismatch_rejected_before_projection(make_bundle):
    bundle, _, _, _ = make_bundle(); value = raw(bundle)
    value['runs'][0]['attempts'][1]['request_messages'][0]['content'] += 'altered'
    with pytest.raises(ValueError, match='context differs|reconstructed'):
        iv.project(value)


@pytest.mark.parametrize('mutation', ['unknown_pointer', 'unused_message', 'format', 'mixed', 'role', 'pointer_fields'])
def test_decoder_rejects_invalid_encodings(make_bundle, mutation):
    bundle, _, _, _ = make_bundle(two=True); encoded = iv.project(raw(bundle))
    first = next(iter(encoded[iv.HEADER]['messages']))
    slot = next((messages, i) for messages, _ in iv._message_lists(encoded)
                for i, message in enumerate(messages) if iv.POINTER in message)
    if mutation == 'unknown_pointer': slot[0][slot[1]][iv.POINTER] = 'missing'
    elif mutation == 'unused_message': encoded[iv.HEADER]['messages']['extra'] = {'role': 'user', 'content': 'not supplied'}
    elif mutation == 'format': encoded[iv.HEADER]['format'] = 'unknown'
    elif mutation == 'mixed': encoded['runs'][0]['attempts'][0]['request_messages'] = []
    elif mutation == 'role': encoded[iv.HEADER]['messages'][first]['role'] = 'assistant'
    elif mutation == 'pointer_fields': slot[0][slot[1]]['extra'] = 'content'
    with pytest.raises(ValueError): iv.restore(encoded)


def test_isolated_tool_retains_its_context_without_importing_siblings(make_bundle):
    bundle, adapter, _, _ = make_bundle()
    candidate = proposal(refs=['diff', 'P1:1_t1'])
    with using_benchmark(adapter):
        value, _ = evidence.build_input(bundle, candidate)
    encoded = iv.project(value)
    assert iv.restore(encoded) == value
    record = iv.restore(encoded)['source_records']['P1:1_t1']['record']
    assert 'request_messages' in record
    assert set(value['source_records']) == {'diff', 'P1:1_t1'}
    assert 'P1:1_t2' not in iv.exact(encoded) and 'outcome' not in record


def test_partial_citations_share_only_already_authorized_initial_messages(make_bundle):
    bundle, adapter, _, _ = make_bundle()
    with using_benchmark(adapter):
        value, _ = evidence.build_input(bundle, proposal(refs=['diff', 'P1:0', 'P1:1_t1', 'P1:2']))
    before = deepcopy(value); encoded = iv.project(value)
    assert iv.restore(encoded) == before == value
    assert encoded[iv.HEADER]['messages']
    for ref in ('P1:1_t1', 'P1:2'):
        assert 'request_messages' in encoded['source_records'][ref]['record']
    assert set(encoded['source_records']) == {'diff', 'P1:0', 'P1:1_t1', 'P1:2'}


def test_review_can_share_a_pair_only_when_both_full_runs_are_supplied(make_bundle):
    bundle, adapter, _, _ = make_bundle()
    with using_benchmark(adapter):
        value, _ = evidence.build_input(bundle, proposal(refs=['diff', 'P1', 'Q1']))
    encoded = iv.project(value)
    assert iv.equal(iv.restore(encoded), value)
    p = encoded['source_records']['P1']['record']['initial']['messages']
    q = encoded['source_records']['Q1']['record']['initial']['messages']
    assert p[1:] == q[1:] and all(iv.POINTER in m for m in p[1:])
    assert set(encoded['source_records']) == {'diff', 'P1', 'Q1'}


def test_historical_full_run_scope_and_repeated_observations(make_bundle):
    bundle, _, _, _ = make_bundle()
    run = deepcopy(raw(bundle)['runs'][0]); tool = run['attempts'][0]['tools'][0]
    tool['observation']['content'] = '重复 001.00\r\n[... truncated ...]\n' * 30
    rebuild_requests(run)
    value = {'context': {'pairs': []}, 'targets': [], 'source_records': {
        'historical_round/P1': {'task_id': run['task_id'], 'run_id': run['run_id'],
                              'role': 'parent', 'record': run, 'execution_context': {'scope': 'historical'}}}}
    encoded = iv.project(value)
    assert iv.restore(encoded) == value
    assert set(encoded['source_records']) == {'historical_round/P1'}
    assert encoded['source_records']['historical_round/P1']['record']['attempts'][0]['tools'] == run['attempts'][0]['tools']


@pytest.mark.parametrize('module', list(pr.PROMPT_VERSIONS))
def test_all_module_boundaries_decode_to_existing_contracts(make_bundle, tmp_path, module):
    bundle, adapter, parents, _ = make_bundle(two=True); saved = saved_plan(parents)
    candidate = proposal(refs=['diff', 'P1', 'Q1:outcome'])
    verdict = conflict(); verdict['results'][0]['issues'][0]['evidence'] = ['Q1:outcome']
    with using_benchmark(adapter):
        view, _ = evidence.build_input(bundle, candidate)
        calls = {
            'grouping': lambda: modules.grouping_call(parents, 'r1'),
            'diagnosis': lambda: modules.diagnosis_call(saved),
            'preconditioner': lambda: modules.preconditioner_call(saved, {'entries': [], 'sources': {}}),
            'editor': lambda: modules.editor_call(modules.preconditioner_call(saved, {'entries': [], 'sources': {}}).complete(keep())),
            'replay': lambda: modules.replay_call(bundle),
            'verifier': lambda: modules.verifier_call(view),
            'repair': lambda: modules.repair_call(evidence.build_repair_input(view, verdict, candidate), candidate, bundle['payload']),
        }
        call = calls[module]()
        decoded = iv.restore(json.loads(call.messages[1]['content']))
        legacy = pr._messages(module, decoded, bundle['background'], input_view=iv.LEGACY)
        assert decoded == json.loads(legacy[1]['content'])
        assert call.messages[0]['content'].startswith(legacy[0]['content'])
        assert pr.prompt_identity(module)['input_view'] == iv.FORMAT
        assert config.method_config()['model_input_view'] == iv.FORMAT
        if module in ('verifier', 'repair'):
            assert call.input['view'] == decoded if module == 'repair' else call.input == decoded


def test_small_payload_noop_legacy_and_unknown_version(make_bundle):
    bundle, adapter, _, _ = make_bundle()
    value = {'parent': 'x', 'plan': {'goal': 'y'}}
    assert iv.project(value) == iv.restore(value) == value
    with using_benchmark(adapter):
        old = pr._messages('editor', value, bundle['background'], input_view=iv.LEGACY)
        assert pr._messages('editor', value, bundle['background']) == old
        with pytest.raises(ValueError, match='Unsupported'):
            pr._messages('editor', value, bundle['background'], input_view='unknown')
    assert iv.model_messages(old, 'Long decoder instructions'*10000) == old


def test_encoding_preserves_json_types_and_literal_marker_text(make_bundle):
    bundle, _, _, _ = make_bundle(); value = raw(bundle)
    value['memory']['entries'] = [{'literal': '{"officeqa_message":"m1"}', 'values': [1, 1.0, True, False, None]}]
    restored = iv.restore(iv.project(value))
    assert iv.equal(restored, value)
    assert not iv.equal([1], [1.0]) and not iv.equal([False], [0])
    with pytest.raises(ValueError, match='unencoded'):
        iv.project(iv.project(value))


def test_same_text_cannot_reuse_another_pairs_user_pointer(make_bundle):
    bundle, _, _, _ = make_bundle(two=True); value = raw(bundle)
    # Structurally valid fixture with equal text but different task identities.
    for run in value['runs'][2:]:
        run['initial']['messages'][1:] = deepcopy(value['runs'][0]['initial']['messages'][1:])
        rebuild_requests(run)
    encoded = iv.project(value)
    first = encoded['runs'][0]['initial']['messages'][1]
    second = encoded['runs'][2]['initial']['messages'][1]
    assert first != second
    assert encoded[iv.HEADER]['messages'][first[iv.POINTER]] == encoded[iv.HEADER]['messages'][second[iv.POINTER]]
    encoded['runs'][2]['initial']['messages'][1] = deepcopy(first)
    with pytest.raises(ValueError, match='Noncanonical'):
        iv.restore(encoded)


def test_decoder_instruction_overhead_can_select_raw_full_run(make_bundle):
    bundle, adapter, _, _ = make_bundle()
    with using_benchmark(adapter):
        old = pr._messages('replay', raw(bundle), bundle['background'], input_view=iv.LEGACY)
    assert iv.model_messages(old, 'Long decoder instructions\n'*10000) == old


def test_measurement_fixtures_use_all_seven_shapes_without_actor(office, monkeypatch):
    from scripts.runs.verify_v26_input_view import payloads, measure, TokenCounter
    _, dataset, runtime, factory = office
    adapter, _ = factory({})
    monkeypatch.setattr(runtime, 'run', lambda *a, **k: pytest.fail('Must not execute Actor'))
    with using_benchmark(adapter):
        from src.skill_evolution.v26.benchmarks.officeqa import protocol as p
        background = p.background(adapter.transport.metadata())
        values = payloads(dataset.cases('train'), runtime, 'Parent\n', 3, background)
        assert set(values) == set(pr.PROMPT_VERSIONS)
        for module, value in values.items():
            result = measure(module, value, background, TokenCounter(None, None))
            assert result['roundtrip_equal']
            assert result['before']['content_tokens'] is result['after']['content_tokens'] is None
            assert result['after']['content_chars'] <= result['before']['content_chars']

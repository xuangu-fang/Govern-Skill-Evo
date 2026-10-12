from copy import deepcopy

import pytest

from src.skill_evolution.v19.edit_tracking_v19 import encode, parse
from src.skill_evolution.v21.evidence_wire_v21 import pack, pack_review, expand, restore_response
from src.skill_evolution.v21.memory_update_v21 import build_memory_update_request, run_memory_update, validate_memory_update
from src.skill_evolution.v20.evidence_review_v20 import build_evidence_review_request, validate_evidence_review
from src.skill_evolution.v20.local_generation_v20 import review_inputs
from src.skill_evolution.v21.memory_consumption_v21 import run_local_generation, restore_generation
from tests.skill_evolution.v21.test_memory_consumption_v21 import following, prepare
from tests.skill_evolution.v21.test_memory_update_v21 import update_input, completed, setup, case, response, completion


def packet():
    event = 'EVENT/' + 'abc123' * 20
    trajectory = 'TRAJECTORY/' + 'def456' * 20
    shared = {'description': 'Exact public data. ' * 20,
              'source_refs': [event], 'ref': event, 'literal': 'E1',
              'literal_object': {'data_body_ref': ['ordinary tool data']},
              'nested': [{'a': 'Observe both labels', 'b': list(range(40))}]}
    return {'events': {event: {'trajectory_ref': trajectory,
        'event': {'step': 1, 'actor': 'tool', 'event_type': 'tool_result', 'tool_name': 'read', 'content': shared}}},
        'trajectories': {trajectory: {'role': 'CANDIDATE', 'context_ref': 'CONTEXT/original',
            'skill_ref': {'sha256': 'version-A', 'text_ref': 'SKILL/text'},
            'source_round_id': 'round-2', 'supervision': {'success': False, 'compliant': True}}},
        'contexts': {'CONTEXT/original': {'public_tools': [shared, shared], 'visible_policy': 'Preserve E1.'}},
        'source_records': {'ASSESSMENT/original': {'statement': event,
            'evidence_refs': [event], 'counterevidence_refs': [event]}}, 'pairs': {}}


def test_exact_roundtrip_preserves_opaque_data_alias_collisions_and_both_labels():
    value = packet(); original = deepcopy(value)
    wire, mapping = pack(value)
    assert value == original and expand(wire, mapping) == original
    assert 'E1' not in mapping  # already a literal in a tool result
    assert wire['data_bodies']  # repeated exact objects are shared
    assert len(encode(wire)) < len(encode(value))
    assert next(iter(wire['events'])) != next(iter(value['events']))
    assert next(iter(wire['source_records'].values()))['statement'] == next(iter(value['events']))
    assert next(iter(wire['trajectories'].values()))['supervision'] == {'success': False, 'compliant': True}
    # Tool data that happens to use reference-like property names is untouched.
    data_text = encode(wire['data_bodies'])
    assert next(iter(value['events'])) in data_text
    assert pack(value) == (wire, mapping)


def comparison_packet():
    value = packet()
    tid = next(iter(value['trajectories']))
    value['trajectories'][tid]['task_ref'] = 'TASK/example'
    value['trajectories']['TRAJECTORY/earlier'] = {
        **deepcopy(value['trajectories'][tid]), 'source_round_id': 'round-1',
        'supervision': {'success': True, 'compliant': True}}
    for ref, trajectory, tool, amount in [('EVENT/current', tid, 'write', 2),
            ('EVENT/earlier', 'TRAJECTORY/earlier', 'write', 0),
            ('EVENT/other', tid, 'other', 7)]:
        value['events'][ref] = {'trajectory_ref': trajectory, 'event': {
            'actor': 'assistant', 'step': 2, 'event_type': 'tool_call',
            'tool_name': tool, 'arguments': {'amount': amount, 'literal_ref': 'E1'}}}
    value['findings'] = [{'evidence_refs': ['EVENT/current']}]
    return value


def test_operation_view_includes_all_matching_calls_without_dropping_other_evidence():
    payload = comparison_packet()
    payload['events'] = dict(reversed(list(payload['events'].items())))
    wire, mapping = pack_review(payload)
    assert mapping == pack(payload)[1] and expand(wire, mapping) == payload
    assert set(wire['operation_comparison']) == {'write'}
    rows = next(iter(wire['operation_comparison']['write'].values()))
    assert {mapping[r['evidence_ref']] for r in rows} == {'EVENT/current', 'EVENT/earlier'}
    assert {(r['success'], r['compliant']) for r in rows} == {(False, True), (True, True)}
    for row in rows:
        assert row['arguments'] == payload['events'][mapping[row['evidence_ref']]]['event']['arguments']
    # The current Finding seeds a tool name, not a curated positive/negative example.
    assert len(wire['events']) == len(payload['events'])
    payload['findings'] = []
    empty, refs = pack_review(payload)
    assert empty['operation_comparison'] == {} and expand(empty, refs) == payload


@pytest.mark.parametrize('damage', ['argument', 'label', 'drop', 'duplicate'])
def test_operation_view_is_checked_against_its_originals(damage):
    wire, mapping = pack_review(comparison_packet())
    rows = next(iter(wire['operation_comparison']['write'].values()))
    if damage == 'argument': rows[0]['arguments']['amount'] = 999
    elif damage == 'label': rows[0]['compliant'] = False
    elif damage == 'drop': rows.pop()
    else: rows.append(deepcopy(rows[0]))
    with pytest.raises(ValueError, match='comparison differs'):
        expand(wire, mapping)


@pytest.mark.parametrize('damage', ['map', 'body', 'label', 'unknown_pointer', 'cyclic_data'])
def test_tampering_never_silently_changes_the_reconstructed_evidence(damage):
    wire, mapping = pack(packet())
    if damage == 'map':
        mapping[next(iter(wire['events']))] = 'EVENT/wrong'
    elif damage == 'body':
        next(iter(wire['event_bodies'].values()))['step'] = 999
    elif damage == 'label':
        next(iter(wire['trajectories'].values()))['supervision']['compliant'] = False
    elif damage == 'unknown_pointer':
        next(iter(wire['events'].values()))['event_body_ref'] = 'B999999'
    else:
        ref = next(iter(wire['data_bodies']))
        wire['data_bodies'][ref] = {'data_body_ref': ref}
    with pytest.raises((ValueError, KeyError)):
        expand(wire, mapping)


def test_response_decoding_changes_only_reference_slots_not_prose_or_new_ids():
    mapping = {'E1': 'EVENT/original', 'I1': 'ISSUE/original'}
    raw = encode({'issues': [{'issue_id': 'I1', 'problem': 'E1', 'source_refs': ['E1'],
        'attempts': [{'attempt_id': 'NEW/example', 'assessment': 'E1', 'source_refs': ['E1']}]}]})
    decoded = parse(restore_response(raw, mapping))
    item = decoded['issues'][0]
    assert item['issue_id'] == 'ISSUE/original' and item['source_refs'] == ['EVENT/original']
    assert item['problem'] == item['attempts'][0]['assessment'] == 'E1'
    assert item['attempts'][0]['attempt_id'] == 'NEW/example'
    assert restore_response(encode(decoded), mapping) == encode(decoded)


def test_memory_update_consumes_real_short_response_and_resumes_without_repeating_call(update_input, tmp_path):
    calls = []
    def model(prompt):
        calls.append(1)
        wire = parse(prompt['user_prompt'])
        issue = wire['memory_issues'][0]
        event = next(ref for ref, item in wire['events'].items()
            if wire['trajectories'][item['trajectory_ref']]['role'] == 'CANDIDATE'
            and wire['trajectories'][item['trajectory_ref']].get('pair_id') in wire['current_pair_refs'])
        return completion({'issues': [{'issue_id': issue['issue_id'], 'problem': issue['problem'],
            'current_understanding': 'Observed labels do not prove generality; old limitations remain.',
            'source_refs': [event], 'attempts': [{'attempt_id': 'NEW/alias-input', 'approach': 'Bounded test.',
                'assessment': 'The two labels belong to this run; effects remain unresolved.',
                'edit_refs': [e['edit_id'] for e in wire['current_edits']], 'source_refs': [event]}]}]})
    out = tmp_path/'update'
    result = run_memory_update(update_input, output=out, transport=model)
    assert run_memory_update(update_input, output=out, resume=True,
                             transport=lambda _: pytest.fail('must reuse response')) == result
    assert calls == [1]
    original_events = update_input.payload['events']
    for ref, record in result.updated_evidence.payload['archive']['records'].items():
        if ref.startswith('ASSESSMENT_V21/'):
            assert set(record['evidence_refs']) <= original_events.keys()
    # A changed local reverse map cannot be accepted as the same saved request.
    saved = parse((out/'request.json').read_text())
    saved['reference_map'][next(iter(saved['reference_map']))] = 'wrong'
    (out/'request.json').write_text(encode(saved))
    with pytest.raises(ValueError, match='request changed'):
        run_memory_update(update_input, output=out, resume=True)


@pytest.mark.parametrize('catalog', ['source_records', 'event_bodies', 'pairs'])
def test_memory_short_reference_type_is_still_checked(update_input, catalog):
    prompt = build_memory_update_request(update_input)
    wire = parse(prompt['user_prompt'])
    raw = response(update_input)
    raw['issues'][0]['attempts'][0]['source_refs'] = [next(iter(wire[catalog]))]
    with pytest.raises(ValueError, match='loaded original events'):
        validate_memory_update(encode(raw), request=update_input, wire=True)


@pytest.mark.parametrize('damage', ['summary', 'body', 'unknown', 'counter'])
def test_review_short_reference_type_and_counterevidence_are_still_checked(following, damage):
    request = review_inputs(prepare(following[0]))[0]
    prompt = build_evidence_review_request(request)
    wire = parse(prompt['user_prompt'])
    raw = {'proposal_id': wire['proposal_id'], 'verdict': 'VERIFIED',
        'reason': 'Check the observed limitation.', 'evidence_refs': [next(iter(wire['events']))],
        'counterevidence_refs': wire['known_counterevidence_refs'],
        'gap': {'kind': 'MISSING', 'statement': 'A bounded hypothesis.', 'related_rule_refs': []}}
    if damage == 'summary':
        raw['evidence_refs'] = [next(iter(wire['source_records']))]
    elif damage == 'body':
        raw['evidence_refs'] = [next(iter(wire['event_bodies']))]
    elif damage == 'unknown':
        raw['evidence_refs'] = ['E999999999']
    else:
        raw['counterevidence_refs'] = []
    with pytest.raises(ValueError, match='reference errors'):
        validate_evidence_review(encode(raw), request=request)


def test_review_aliases_restore_before_current_rule_authorization_and_editor(following, tmp_path):
    source = prepare(following[0])
    request = review_inputs(source)[0]
    def review(prompt):
        wire = parse(prompt['user_prompt'])
        return completion({'proposal_id': wire['proposal_id'], 'verdict': 'VERIFIED',
            'reason': 'Preserve the known counterevidence while testing the bounded revision.',
            'evidence_refs': [next(iter(wire['events']))],
            'counterevidence_refs': wire['known_counterevidence_refs'],
            'gap': {'kind': 'NEEDS_REVISION', 'statement': 'A bounded revision.',
                    'related_rule_refs': [next(iter(wire['rules']))]}})
    def editor(prompt):
        units = parse(prompt['user_prompt'])['edit_units']
        assert set(units[0]['verified_reviews'][0]['gap']['related_rule_refs']) <= request.payload['rules'].keys()
        assert units[0]['verified_reviews'][0]['proposal_id'] == request.payload['proposal_id']
        return completion({'status': 'EDITED', 'reason': 'Follow verified revision.',
            'edits': [{'edit_unit_index': u['edit_unit_index'], 'text': '- Bounded revision.'} for u in units]})
    audit = run_local_generation(source=source, output=tmp_path/'generation', review_transport=review,
                                editor_transport=editor)
    assert restore_generation(audit)[1] == audit['result']
    assert audit['reviews'][0]['counterevidence_refs'] == request.payload['known_counterevidence_refs']
    assert audit['result']['candidate_skill'].startswith('- Bounded revision.\n')
    assert '- New rule r1\n' in audit['result']['candidate_skill']  # untargeted rule retained

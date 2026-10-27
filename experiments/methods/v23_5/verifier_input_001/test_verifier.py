"""Deterministic output-contract tests; synthetic verdicts are not model reviews."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from experiments.methods.v23_5.verifier_input_001 import verifier as v


@pytest.fixture
def model_input():
    return {'context': {}, 'targets': [
        {'target': {'entry_index': 0, 'knowledge_index': 1},
         'knowledge': {'text': 'The actor revisited a drawer and repeated a search.', 'evidence': ['Q5:49']}},
        {'target': {'entry_index': 2, 'knowledge_index': 0},
         'knowledge': {'text': 'The held object was cooled.', 'evidence': ['S1_R02/P3:6']}}
    ], 'source_records': {'Q5:49': {}, 'S1_R02/P3:6': {}}}


def supported(model_input):
    return {'results': [{'target': deepcopy(t['target']), 'verdict': 'SUPPORTED', 'issues': []}
                        for t in model_input['targets']]}


def conflict(model_input):
    result = supported(model_input)
    result['results'][0].update(verdict='CONFLICT', issues=[
        {'statement': 'revisited a drawer', 'reason': 'The provided action names a shelf.', 'evidence': ['Q5:49']},
        {'statement': 'repeated a search', 'reason': 'Earlier visits were not supplied.', 'evidence': []}
    ])
    return result


def test_complete_mixed_results_and_shared_evidence_are_preserved(model_input):
    result = conflict(model_input)
    result['results'][0]['issues'][0]['evidence'].append('S1_R02/P3:6')
    result['results'].reverse()  # Output order need not match frozen input order.
    before = deepcopy((result, model_input))
    assert v.validate_result(result, model_input) == result
    assert (result, model_input) == before
    assert v.validate_response({'finish_reason': 'stop', 'content': json.dumps(result),
                                'reasoning_content': 'Ignored provider reasoning'}, model_input) == result


def test_supported_and_empty_target_batch(model_input):
    v.validate_result(supported(model_input), model_input)
    model_input['targets'] = []
    v.validate_result({'results': []}, model_input)


@pytest.mark.parametrize('mode', ['missing', 'duplicate', 'unknown'])
def test_exact_coverage(model_input, mode):
    result = supported(model_input)
    if mode == 'missing':
        result['results'].pop()
    elif mode == 'duplicate':
        result['results'][1] = deepcopy(result['results'][0])
    else:
        result['results'][1]['target']['knowledge_index'] = 999
    with pytest.raises(v.OutputValidationError, match={'missing': 'missing targets', 'duplicate': 'duplicate target',
                                                      'unknown': 'unknown target'}[mode]):
        v.validate_result(result, model_input)


@pytest.mark.parametrize('index', [True, False, -1, 0.0, '0', None])
def test_indices_are_actual_nonnegative_integers(model_input, index):
    result = supported(model_input)
    result['results'][0]['target']['entry_index'] = index
    with pytest.raises(v.OutputValidationError, match='entry_index'):
        v.validate_result(result, model_input)


@pytest.mark.parametrize('level', ['output', 'result', 'target', 'issue'])
def test_no_extra_or_missing_fields(model_input, level):
    result = conflict(model_input)
    objects = {'output': result, 'result': result['results'][0], 'target': result['results'][0]['target'],
               'issue': result['results'][0]['issues'][0]}
    obj = objects[level]
    key = next(iter(obj))
    original = obj.pop(key)
    with pytest.raises(v.OutputValidationError, match='exactly'):
        v.validate_result(result, model_input)
    obj[key] = original
    obj['replacement_knowledge'] = None
    with pytest.raises(v.OutputValidationError, match='exactly'):
        v.validate_result(result, model_input)


@pytest.mark.parametrize('verdict,issues', [('INSUFFICIENT', []), ('supported', []), (None, []),
                                          ('CONFLICT', []), ('SUPPORTED', [{}]), ('SUPPORTED', None)])
def test_verdict_and_issue_consistency(model_input, verdict, issues):
    result = supported(model_input)
    result['results'][0].update(verdict=verdict, issues=issues)
    with pytest.raises(v.OutputValidationError):
        v.validate_result(result, model_input)


@pytest.mark.parametrize('statement', ['', '  ', None, 'A paraphrase about the drawer', 'The held object was cooled.'])
def test_statement_must_quote_its_own_target(model_input, statement):
    result = conflict(model_input)
    result['results'][0]['issues'][0]['statement'] = statement
    with pytest.raises(v.OutputValidationError, match='statement'):
        v.validate_result(result, model_input)


@pytest.mark.parametrize('reason', ['', '\n ', None, 42])
def test_reason_required(model_input, reason):
    result = conflict(model_input)
    result['results'][0]['issues'][0]['reason'] = reason
    with pytest.raises(v.OutputValidationError, match='reason'):
        v.validate_result(result, model_input)


@pytest.mark.parametrize('refs', [['Q5:48'], ['P3:6'], ['Q5'], ['Q5:49/Q5:50'], ['C86'], ['M1'],
                                 ['Q5:49', 'Q5:49'], [''], [None], 'Q5:49', None])
def test_only_distinct_exact_supplied_keys(model_input, refs):
    result = conflict(model_input)
    result['results'][0]['issues'][0]['evidence'] = refs
    with pytest.raises(v.OutputValidationError, match='evidence'):
        v.validate_result(result, model_input)


@pytest.mark.parametrize('content', ['```json\n{"results": []}\n```', '{"results": []} trailing',
                                    '{"results": [], "results": []}',
                                    '{"results": [{"target": {"entry_index": 0, "entry_index": 1}}]}',
                                    '{"results": NaN}', '{"results": Infinity}',
                                    '{"results": -Infinity}', '{"results": [', '', None])
def test_strict_json_parser(content):
    with pytest.raises(v.OutputValidationError):
        v.parse_output(content)


@pytest.mark.parametrize('finish', ['length', 'content_filter', 'tool_calls', None])
def test_abnormal_finish_precedes_json_parsing(model_input, finish):
    with pytest.raises(v.OutputValidationError, match='finish_reason'):
        v.validate_response({'finish_reason': finish, 'content': '{broken'}, model_input)


def test_reasoning_is_never_used_as_body(model_input):
    with pytest.raises(v.OutputValidationError, match='content'):
        v.validate_response({'finish_reason': 'stop', 'content': None,
                             'reasoning_content': json.dumps(supported(model_input))}, model_input)


@pytest.mark.parametrize('result', [[], None, {'results': None}, {'results': [None]}])
def test_container_types(model_input, result):
    with pytest.raises(v.OutputValidationError):
        v.validate_result(result, model_input)


def test_real_frozen_messages_and_tampering(tmp_path):
    output = tmp_path/'messages'
    report = v.prepare_messages(v.inputs.DEFAULT_OUTPUT, output)
    assert report['targets'] == 18 and report['model_calls'] == 0
    for name in v.inputs.ROUNDS:
        case = output/'cases'/name
        value = v.inputs.read(case/'verifier_input.json')
        messages = v.inputs.read(case/'messages.json')
        original = v.inputs.DEFAULT_OUTPUT/'cases'/name/'verifier_input.json'
        assert (case/'verifier_input.json').read_bytes() == original.read_bytes()
        assert json.loads(messages[1]['content']) == value
        assert messages[0]['content'] == v.PROMPT_PATH.read_text()
        # This is a structural fixture, not a semantic verdict on real Knowledge.
        v.validate_result(supported(value), value)
    file = output/'cases/R01/messages.json'
    messages = v.inputs.read(file)
    messages[1]['content'] = '{}'
    v.inputs.save(file, messages)
    with pytest.raises(ValueError, match='Message file changed'):
        v.verify_messages(output)
    with pytest.raises(ValueError, match='Output exists'):
        v.prepare_messages(v.inputs.DEFAULT_OUTPUT, output)

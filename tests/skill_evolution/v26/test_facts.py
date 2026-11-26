from copy import deepcopy
import json
import pytest

from src.adapters.officeqa.transport import RequestFailure
from src.skill_evolution.v26.benchmarks.officeqa import facts, evidence, protocol as p
from .conftest import response


def rehash(record):
    record['provenance']['record_sha256'] = p.digest(record['execution'])
    return record


def test_formal_tool_rounds_keep_page_and_line_semantics(make_run, office):
    path = str(office[2].text_root / 'treasury_bulletin_2011_03.txt')
    record, _, _, _ = make_run([response(calls=[('read', {'path': path, 'start': 2, 'limit': 1}),
                                               ('grep', {'path': path, 'pattern': 'Revenue'})]), response('<answer>1000</answer>')])
    bundle = facts.build_facts([record]); run = bundle['facts']['runs'][0]; evidence.validate_run(run)
    assert [t['function']['name'] for t in bundle['background']['tool_schemas']] == ['glob', 'read', 'grep']
    assert bundle['background']['tool_output_limits'] == {'read_chars': 4000, 'grep_matches': 20, 'glob_matches': 50}
    assert run['initial']['declared_source_pages'][0]['source_page'] == 2
    assert run['attempts'][0]['tools'][0]['ref'] == 'P1:1_t1'
    assert run['attempts'][0]['tools'][0]['observation']['content'] == 'Other line\n'
    assert run['outcome']['model_rounds'] == 2 and run['outcome']['tool_calls'] == 2
    assert run['outcome']['score'] == {'em': 1.0, 'f1': 1.0}
    encoded = json.dumps(run)
    assert 'GOLD_ONLY_SENTINEL' not in encoded and 'UNOBSERVED_PAGE_SENTINEL' not in encoded
    assert 'source_page' not in run['attempts'][0]['tools'][0]
    assert run['attempts'][1]['request_messages'][-1]['role'] == 'tool'


@pytest.mark.parametrize('bad_type', [{}, '', False, 0, 'bad'])
def test_temporary_format_feedback_audited_but_not_exposed(make_run, bad_type):
    bad = response(); bad['choices'][0]['message']['tool_calls'] = bad_type
    record, _, provider, _ = make_run([bad, RequestFailure('Timeout'), response('1000')])
    assert 'Previous Tool Call Validation Error' in provider.requests[-1]['messages'][-1]['content']
    run = facts.build_facts([record])['facts']['runs'][0]
    assert len(run['attempts']) == 1 and run['outcome']['api_requests'] == 3
    assert len(run['attempts'][0]['request_messages']) == len(record['execution']['initial_messages'])
    assert 'Previous Tool Call Validation Error' not in json.dumps(run)
    cost = facts.cost_summary([record])
    assert cost['http_attempts'] == 3 and cost['input_tokens'] == {'known_sum': 200, 'unknown_requests': 1}


def test_tool_value_error_remains_observation(make_run, office):
    path = str(office[2].text_root / 'treasury_bulletin_2011_03.txt')
    record, _, _, _ = make_run([response(calls=[('read', {'path': path, 'start': 'invalid'})]), response('1000')])
    run = facts.build_facts([record])['facts']['runs'][0]
    assert 'invalid line window' in run['attempts'][0]['tools'][0]['observation']['content']
    assert run['outcome']['api_requests'] == 2


def test_round_exhaustion_is_completed_zero_score(make_run):
    record, adapter, _, _ = make_run([response(calls=[('glob', {'pattern': '*'})])] * 24)
    assert adapter.is_complete(record)
    outcome = facts.build_facts([record])['facts']['runs'][0]['outcome']
    assert outcome['termination'] == 'max_tool_turns' and outcome['answer'] == ''
    assert outcome['score'] == {'em': 0.0, 'f1': 0.0}


@pytest.mark.parametrize('mutation', ['counter', 'formal_message', 'request', 'phase', 'tool_started',
    'wrong_tool_id', 'extra_round', 'bad_metrics', 'false_count', 'answer', 'retry_relabel', 'hash'])
def test_mutated_archives_are_rejected(make_run, mutation):
    r, adapter, _, _ = make_run([response(calls=[('glob', {'pattern': '*'})]), response('1000')])
    x = deepcopy(r); raw = x['execution']; rd = raw['request_audit'][0]
    if mutation == 'counter': raw['raw_result']['api_requests'] += 1
    elif mutation == 'formal_message': raw['raw_result']['messages'][-1]['content'] = 'tampered'
    elif mutation == 'request': rd['attempts'][0]['messages'][-1]['content'] += 'tampered'
    elif mutation == 'phase': rd['phase'] = 'generation'
    elif mutation == 'tool_started': rd['tools'][0]['status'] = 'started'
    elif mutation == 'wrong_tool_id': raw['raw_result']['messages'][-2]['tool_call_id'] = 'unknown'
    elif mutation == 'extra_round': raw['request_audit'].append(deepcopy(rd))
    elif mutation == 'bad_metrics': raw['metrics']['f1'] = 2
    elif mutation == 'false_count': raw['raw_result']['n_tool_calls'] = True
    elif mutation == 'answer': raw['answer'] = 'forged'
    elif mutation == 'retry_relabel': rd['attempts'][0]['status'] = 'technical_error'; rd['attempts'][0]['error'] = 'fake'
    elif mutation == 'hash': raw['skill'] = 'different'
    if mutation != 'hash': rehash(x)
    with pytest.raises((ValueError, RequestFailure)):
        facts.build_facts([x])
    assert not adapter.is_complete(x)


def test_duplicate_mixed_roles_and_test_records_rejected(make_run):
    parent, _, _, _ = make_run(); candidate, _, _, _ = make_run(role='candidate')
    test, adapter, _, _ = make_run(role='evaluation', task='t', split='test')
    assert adapter.is_complete(test)
    for records in ([parent, parent], [parent, candidate], [test]):
        with pytest.raises(ValueError): facts.build_facts(records)


def test_no_initial_skill_invented(make_run):
    record, _, _, _ = make_run(skill=None)
    assert facts.build_facts([record])['facts']['parent'] is None


def test_multiple_rounds_may_reuse_provider_call_ids(make_run):
    record, _, _, _ = make_run([response(calls=[('glob', {'pattern': '*'})])] * 2 + [response('1000')])
    run = facts.build_facts([record])['facts']['runs'][0]
    assert {'P1:1_t1', 'P1:2_t1'} <= evidence.run_references(run)
    assert run['attempts'][0]['tools'][0]['call']['id'] == run['attempts'][1]['tools'][0]['call']['id']

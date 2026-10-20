"""Deterministic Preconditioner contract, compilation and saved handoffs; no LLM."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23 import diagnosis, preconditioner as pc
from src.skill_evolution.v23.prompts import execution_context
from tests.skill_evolution.v23.test_diagnosis import make_grouping

REAL = Path('artifacts/methods/v23/v23_prompt_alignment_001')


def proposal():
    return {'decision': 'revise', 'reason': 'Observed choices support guidance.', 'plan': {
        'goal': 'Improve inspection while preserving completion.',
        'updates': [
            {'id': 'u1', 'text': 'Inspect a visible closed container when appropriate.', 'basis': ['G1', 'P1:1']},
            {'id': 'u2', 'text': 'Retain visible target information.', 'basis': ['P2:1']},
            {'id': 'u3', 'text': 'Use visible available alternatives.', 'basis': ['P1:1', 'P2:outcome']}],
        'checks': [{'id': 'c1', 'update_ids': ['u1', 'u3'], 'question': 'Are inspections productive?'}]}}


def answer(value, finish='stop'):
    return {'content': json.dumps(value), 'finish_reason': finish, 'usage': {'total_tokens': 10}}


def keep():
    return {'decision': 'ready', 'reason': 'The current evidence supports preservation.', 'adjustments': [], 'checks': None}


def adj(sources=('u1',), targets=('u1',)):
    return {'from': list(sources), 'to': [{'id': uid, 'text': 'Use the current observation to choose an inspection.'} for uid in targets],
            'basis': ['P1:2'], 'reason': 'The visible conditions support this adjustment.'}


def changed(*adjustments, checks=None, decision='ready'):
    return {**keep(), 'decision': decision, 'adjustments': list(adjustments), 'checks': checks}


@pytest.fixture
def setup(tmp_path):
    grouping = make_grouping(tmp_path)
    diag = tmp_path / 'diagnosis'
    saved = diagnosis.run_diagnosis(grouping, diag, generate=lambda *_: answer(proposal()))
    return grouping, diag, saved, tmp_path / 'preconditioner'


def test_keep_preserves_deep_copy_and_original_goal(setup):
    payload = pc.preconditioner_input(setup[2]); original = deepcopy(payload)
    effective = pc.compile_effective_plan(keep(), payload)
    assert effective == payload['plan'] and payload == original
    effective['updates'][0]['basis'].append('local change')
    assert payload == original


@pytest.mark.parametrize('kind', ['same_id', 'new_id', 'merge', 'split', 'withdraw', 'many_to_many'])
def test_compilation_and_lineage(setup, kind):
    p = pc.preconditioner_input(setup[2]); before = deepcopy(p)
    if kind == 'same_id': a, ids = adj(), ['u1', 'u2', 'u3']
    elif kind == 'new_id': a, ids = adj(targets=['u4']), ['u4', 'u2', 'u3']
    elif kind == 'merge': a, ids = adj(['u3', 'u1'], ['u4']), ['u4', 'u2']
    elif kind == 'split': a, ids = adj(['u1'], ['u5', 'u4']), ['u5', 'u4', 'u2', 'u3']
    elif kind == 'withdraw': a, ids = adj(['u1'], []), ['u2', 'u3']
    else: a, ids = adj(['u3', 'u1'], ['u5', 'u4']), ['u5', 'u4', 'u2']
    out = changed(a, checks=[])
    effective = pc.compile_effective_plan(out, p)
    assert [u['id'] for u in effective['updates']] == ids
    expected_basis = ['G1', 'P1:1', 'P2:outcome'] if len(a['from']) > 1 else ['G1', 'P1:1']
    for u in effective['updates']:
        if u['id'] in [t['id'] for t in a['to']]: assert u['basis'] == expected_basis
    assert 'P1:2' not in [r for u in effective['updates'] for r in u['basis']]
    assert effective['goal'] == p['plan']['goal'] and p == before
    assert out['adjustments'][0]['basis'] == ['P1:2']


def test_simultaneous_order_independent_adjustments(setup):
    p = pc.preconditioner_input(setup[2])
    a, b = adj(['u3'], ['u4', 'u5']), adj(['u1'], ['u6'])
    first = pc.compile_effective_plan(changed(a, b, checks=[]), p)
    assert first == pc.compile_effective_plan(changed(b, a, checks=[]), p)
    assert [u['id'] for u in first['updates']] == ['u6', 'u2', 'u4', 'u5']


@pytest.mark.parametrize('decision', ['no_change', 'need_evidence'])
def test_semantic_stops(setup, decision):
    value = changed(adj(['u1', 'u2', 'u3'], []), checks=[], decision=decision) if decision == 'no_change' else changed(decision=decision)
    assert pc.compile_effective_plan(value, pc.preconditioner_input(setup[2])) is None
    saved = pc.run_preconditioner(setup[0], setup[1], setup[3], generate=lambda *_: answer(value))
    assert saved['effective_plan'] is None and saved['preconditioner'] == value
    assert json.loads((setup[3] / 'validation.json').read_text())['valid'] is True


@pytest.mark.parametrize('checks', [None, [], [{'id': 'c2', 'update_ids': ['u1', 'u2'], 'question': 'Does useful behavior persist?'}]])
def test_checks_modes(setup, checks):
    p = pc.preconditioner_input(setup[2])
    effective = pc.compile_effective_plan(changed(adj(), checks=checks), p)
    assert effective['checks'] == (p['plan']['checks'] if checks is None else checks)


@pytest.mark.parametrize('kind', [
    'unknown_decision', 'extra', 'reason_type', 'adjustments_type', 'from_empty', 'from_duplicate',
    'from_unknown', 'from_generated', 'from_twice', 'to_type', 'to_extra', 'text_empty', 'id_empty',
    'id_collision', 'id_original_other', 'merge_retains', 'split_retains', 'to_duplicate', 'cross_duplicate',
    'basis_empty', 'basis_unknown_event', 'basis_history', 'basis_unknown_group', 'basis_duplicate',
    'reason_history', 'text_history', 'adjustment_extra', 'check_old_about', 'check_empty_ids',
    'check_duplicate', 'check_unknown_update', 'inherited_invalid_check', 'ready_empty',
    'no_change_not_all', 'no_change_null_checks', 'need_evidence_adjustment', 'need_evidence_checks',
])
def test_contract_errors(setup, kind):
    p = pc.preconditioner_input(setup[2]); v = changed(adj()); a = v['adjustments'][0]
    if kind == 'unknown_decision': v['decision'] = 'maybe'
    elif kind == 'extra': v['plan'] = {}
    elif kind == 'reason_type': v['reason'] = []
    elif kind == 'adjustments_type': v['adjustments'] = {}
    elif kind == 'from_empty': a['from'] = []
    elif kind == 'from_duplicate': a['from'] = ['u1', 'u1']
    elif kind == 'from_unknown': a['from'] = ['missing']
    elif kind == 'from_generated': v['adjustments'] = [adj(['u1'], ['u4']), adj(['u4'], ['u5'])]
    elif kind == 'from_twice': v['adjustments'].append(adj())
    elif kind == 'to_type': a['to'] = {}
    elif kind == 'to_extra': a['to'][0]['basis'] = ['P1:1']
    elif kind == 'text_empty': a['to'][0]['text'] = ''
    elif kind == 'id_empty': a['to'][0]['id'] = ''
    elif kind == 'id_collision': a['to'][0]['id'] = 'P1'
    elif kind == 'id_original_other': v['adjustments'] = [adj(['u1'], ['u2']), adj(['u2'], [])]
    elif kind == 'merge_retains': a['from'] = ['u1', 'u2']
    elif kind == 'split_retains': a['to'].append({'id': 'u4', 'text': 'Other requirement.'})
    elif kind == 'to_duplicate': a['to'] = adj(targets=['u4', 'u4'])['to']
    elif kind == 'cross_duplicate': v['adjustments'] = [adj(['u1'], ['u4']), adj(['u2'], ['u4'])]
    elif kind == 'basis_empty': a['basis'] = []
    elif kind == 'basis_unknown_event': a['basis'] = ['P1:999']
    elif kind == 'basis_history': a['basis'] = ['M1']
    elif kind == 'basis_unknown_group': a['basis'] = ['G99']
    elif kind == 'basis_duplicate': a['basis'] *= 2
    elif kind == 'reason_history': a['reason'] = 'M1 shows benefit.'
    elif kind == 'text_history': a['to'][0]['text'] = 'Follow M1.'
    elif kind == 'adjustment_extra': a['direction'] = 'D'
    elif kind == 'check_old_about': v['checks'] = [{'id': 'c2', 'about': ['u1'], 'question': 'What changes?'}]
    elif kind == 'check_empty_ids': v['checks'] = [{'id': 'c2', 'update_ids': [], 'question': 'What changes?'}]
    elif kind == 'check_duplicate': v['checks'] = p['plan']['checks'] * 2
    elif kind == 'check_unknown_update': v['checks'] = [{'id': 'c2', 'update_ids': ['u99'], 'question': 'What changes?'}]
    elif kind == 'inherited_invalid_check': a['to'] = []
    elif kind == 'ready_empty': v = changed(adj(['u1', 'u2', 'u3'], []), checks=[])
    elif kind == 'no_change_not_all': v['decision'] = 'no_change'; v['checks'] = []
    elif kind == 'no_change_null_checks': v = changed(adj(['u1', 'u2', 'u3'], []), decision='no_change')
    elif kind == 'need_evidence_adjustment': v['decision'] = 'need_evidence'
    else: v = changed(checks=[], decision='need_evidence')
    with pytest.raises(ValueError): pc.compile_effective_plan(v, p)


def test_subset_expands_only_direct_references_and_keeps_full_records(setup):
    saved = deepcopy(setup[2]); saved['diagnosis']['plan']['updates'] = [proposal()['plan']['updates'][0]]
    saved['diagnosis']['plan']['checks'] = []
    saved['grouping']['groups'] = [{**saved['grouping']['groups'][0], 'members': ['P1', 'P2'],
                                  'shared_basis': 'P1:1 and P2:1 show comparable inspections.'}]
    payload = pc.preconditioner_input(saved)
    assert [r['ref'] for r in payload['runs']] == ['P1']
    assert payload['runs'][0] == saved['facts']['runs'][0]
    assert payload['grouping']['groups'][0]['members'] == ['P1', 'P2']
    used = {s['commands_ref'] for r in payload['runs'] for s in [r['initial'], *[x[k] for x in r['steps'] for k in ('before', 'after')]]} - {None}
    assert set(payload['command_sets']) == used
    for key in used: assert payload['command_sets'][key] == saved['facts']['command_sets'][key]
    with pytest.raises(ValueError): pc.compile_effective_plan(changed({**adj(), 'basis': ['P2:1']}), payload)
    saved['diagnosis']['plan']['goal'] += ' Compare P2:outcome.'
    assert len(pc.preconditioner_input(saved)['runs']) == 2


@pytest.mark.parametrize('parent', [None, 'Inspect visibly relevant receptacles.'])
def test_parent_and_shared_context(tmp_path, parent):
    group = make_grouping(tmp_path, parent)
    saved = diagnosis.run_diagnosis(group, tmp_path/'diagnosis', generate=lambda *_: answer(proposal()))
    before = deepcopy(saved); messages = pc.messages_for(saved)
    payload = json.loads(messages[1]['content'])
    assert set(payload) == {'parent', 'plan', 'command_sets', 'runs', 'grouping', 'memory'}
    assert payload['parent'] == parent and payload['memory'] == {'entries': [], 'sources': {}}
    assert messages[0]['content'].count(execution_context(saved['background'])) == 1
    assert '{{execution_context}}' not in messages[0]['content']
    assert saved == before
    payload['memory'] = [{'id': 'M1'}]
    with pytest.raises(ValueError): pc.compile_effective_plan(keep(), payload)


def test_persistence_and_zero_call_reuse(setup):
    calls = []
    def generate(*_): calls.append(1); return answer(keep())
    config = {'model': 'offline', 'max_tokens': 123}
    saved = pc.run_preconditioner(setup[0], setup[1], setup[3], generate=generate, call_config=config)
    before = {p.name: p.read_bytes() for p in setup[3].iterdir()}
    again = pc.run_preconditioner(setup[0], setup[1], setup[3], generate=generate, call_config=config)
    assert len(calls) == 1 and saved == again
    assert before == {p.name: p.read_bytes() for p in setup[3].iterdir()}
    with pytest.raises(ValueError): pc.run_preconditioner(setup[0], setup[1], setup[3], generate=generate, call_config={'model': 'other'})
    changed_saved = deepcopy(setup[2]); changed_saved['facts']['parent'] = 'Other'
    with pytest.raises(ValueError): pc.load_preconditioner(setup[3], expected_diagnosis=changed_saved)
    assert len(calls) == 1


@pytest.mark.parametrize('name', ['messages.json', 'prompt.md', 'raw_output.txt', 'response.json', 'parsed.json', 'preconditioner.json', 'effective_plan.json', 'run.json', 'validation.json'])
def test_tampered_artifact_not_reused(setup, name):
    pc.run_preconditioner(setup[0], setup[1], setup[3], generate=lambda *_: answer(keep()))
    path = setup[3]/name
    if name in ('prompt.md', 'raw_output.txt'): path.write_text(path.read_text()+' changed')
    else:
        v = json.loads(path.read_text())
        if name == 'messages.json': v[0]['content'] += ' changed'
        elif name == 'response.json': v['content'] = json.dumps({**keep(), 'reason': 'Changed'})
        elif name == 'run.json': v['round_id'] = 'other'
        elif name == 'validation.json': v['valid'] = False
        elif name == 'effective_plan.json': v['goal'] = 'Changed'
        else: v['reason'] += ' changed'
        path.write_text(json.dumps(v))
    with pytest.raises(ValueError): pc.load_preconditioner(setup[3])


@pytest.mark.parametrize('kind', ['invalid_json', 'truncated', 'contract', 'network', 'interrupt'])
def test_failures_preserve_stop_and_never_retry(setup, kind):
    calls = []
    response = answer(keep())
    if kind == 'invalid_json': response['content'] = '{not json'
    if kind == 'truncated': response['finish_reason'] = 'length'
    if kind == 'contract': response = answer({**keep(), 'scores': []})
    def generate(*_):
        calls.append(1)
        if kind == 'network': raise ConnectionError('unavailable')
        if kind == 'interrupt': raise KeyboardInterrupt()
        return response
    with pytest.raises((ValueError, ConnectionError, KeyboardInterrupt)):
        pc.run_preconditioner(setup[0], setup[1], setup[3], generate=generate)
    assert not json.loads((setup[3]/'validation.json').read_text())['valid']
    assert not (setup[3]/'effective_plan.json').exists()
    if kind not in ('network', 'interrupt'):
        assert (setup[3]/'raw_output.txt').read_text() == response['content']
        assert json.loads((setup[3]/'response.json').read_text()) == response
    with pytest.raises((ValueError, FileNotFoundError)):
        pc.run_preconditioner(setup[0], setup[1], setup[3], generate=generate)
    assert len(calls) == 1


def test_budget_and_upstream_semantic_stop_before_call(setup):
    with pytest.raises(ValueError): pc.run_preconditioner(setup[0], setup[1], setup[3], generate=None, max_input_chars=1)
    assert not setup[3].exists()
    saved = deepcopy(setup[2]); saved['diagnosis'] = {'decision': 'no_change', 'reason': 'No update needed.', 'plan': None}
    with pytest.raises(ValueError): pc.preconditioner_input(saved)


def test_real_handoff_and_legacy_readonly():
    directories = [REAL/'grouping', REAL/'diagnosis', Path('artifacts/methods/v23/v23_grouping_001/live'), Path('artifacts/methods/v23/v23_diagnosis_001/live')]
    if not all(p.exists() for p in directories): pytest.skip('Local archived experiment unavailable')
    before = {str(p): p.read_bytes() for d in directories for p in d.rglob('*') if p.is_file()}
    saved = pc.read_upstream(*directories[:2]); p = pc.preconditioner_input(saved)
    assert p['parent'] is None and p['memory'] == {'entries': [], 'sources': {}}
    assert len(p['runs']) == 4 and sum(len(r['steps']) for r in p['runs']) == 93
    assert len(p['grouping']['groups']) == 2
    assert len(p['plan']['updates']) == len(p['plan']['checks']) == 3
    assert p['runs'] == saved['facts']['runs'] and p['command_sets'] == saved['facts']['command_sets']
    assert pc.compile_effective_plan(keep(), p) == saved['diagnosis']['plan']
    old = Path('experiments/methods/v23/v23_prompt_alignment_001/config/before')
    templates = {k: (old/f'{k}_prompt.md').read_text() for k in ('grouping', 'diagnosis')}
    legacy = pc.read_upstream(*directories[2:], legacy_templates=templates)
    assert all('about' not in c and 'update_ids' in c for c in legacy['diagnosis']['plan']['checks'])
    assert pc.compile_effective_plan(keep(), pc.preconditioner_input(legacy)) == legacy['diagnosis']['plan']
    assert before == {str(p): p.read_bytes() for d in directories for p in d.rglob('*') if p.is_file()}


def test_group_reference_does_not_expand_members(setup):
    saved = deepcopy(setup[2]); plan = saved['diagnosis']['plan']
    plan['updates'] = [plan['updates'][0]]; plan['checks'] = []
    plan['goal'] += ' Preserve comparisons with G2.'
    payload = pc.preconditioner_input(saved)
    assert [r['ref'] for r in payload['runs']] == ['P1']
    assert [g['group_id'] for g in payload['grouping']['groups']] == ['G1', 'G2']
    assert pc.compile_effective_plan(keep(), payload) == plan


def test_changed_prompt_and_generator_config_reject_reuse(setup, tmp_path, monkeypatch):
    config = {'model': 'offline'}
    def generate(*_): return answer(keep())
    generate.call_config = config
    with pytest.raises(ValueError):
        pc.run_preconditioner(setup[0], setup[1], setup[3], generate=generate, call_config={'model': 'other'})
    assert not setup[3].exists()
    pc.run_preconditioner(setup[0], setup[1], setup[3], generate=generate)
    prompt = tmp_path/'prompt.md'; prompt.write_text(pc.PROMPT_PATH.read_text()+'\nChanged task.\n')
    monkeypatch.setattr(pc, 'PROMPT_PATH', prompt)
    with pytest.raises(ValueError): pc.load_preconditioner(setup[3])


def test_http_failure_preserves_raw_response_without_retry(setup, monkeypatch):
    import requests
    class HTTP:
        status_code = 503
        content = b'service unavailable'
    calls = []
    def post(*args, **kwargs): calls.append(1); return HTTP()
    monkeypatch.setattr(requests.Session, 'post', post)
    generate = pc.live_generator(base_url='https://example.test', key='private', model='offline')
    with pytest.raises(ValueError): pc.run_preconditioner(setup[0], setup[1], setup[3], generate=generate)
    assert (setup[3]/'http_response.txt').read_bytes() == HTTP.content
    assert len(calls) == 1


def test_no_natural_language_repair_or_scoring(setup):
    value = changed(adj())
    value['adjustments'][0]['to'][0]['text'] = 'Remember every visited location forever.'
    effective = pc.compile_effective_plan(value, pc.preconditioner_input(setup[2]))
    assert effective['updates'][0]['text'] == value['adjustments'][0]['to'][0]['text']

"""Deterministic interface tests; no semantic scoring or live API requests."""
import json
import pytest
import requests
from experiments.methods.v23_2.v23_2_diagnosis_boundary_001 import run as r
from src.skill_evolution.v23 import diagnosis, preconditioner
from tests.skill_evolution.v23_2.test_local_validation import saved, config
from tests.skill_evolution.v23.test_diagnosis import answer


def test_frozen_sources_and_defaults():
    r.verify_p0()
    original = r.ev.read(r.SOURCE/'contract.json')['src/skill_evolution/v23/diagnosis_prompt.md']
    assert diagnosis.PROMPT_PATH.read_text() == original
    for change in r.ev.read(r.EXP/'config/replacements.json'):
        assert original.count(change['before']) == 1
        original = original.replace(change['before'], change['after'])
    assert r.PROMPT.read_text() == original
    assert r.local.PROMPTS['diagnosis'] == diagnosis.PROMPT_PATH


@pytest.mark.parametrize('rnd', r.ROUNDS)
def test_fixed_request_is_upstream_only(rnd):
    saved, entry = r.material(rnd)
    assert 'memory' not in saved and 'diagnosis' not in saved
    old = r.ev.read(r.Path(entry['diagnosis_path'])/'messages.json')
    new = r.local.messages_for('diagnosis', saved, prompt_path=r.PROMPT)
    expected = old[0]['content']
    for change in r.ev.read(r.EXP/'config/replacements.json'):
        expected = expected.replace(change['before'], change['after'])
    assert new[0]['content'] == expected and new[1:] == old[1:]
    assert set(json.loads(new[1]['content'])) == {'parent','command_sets','runs','grouping'}
    diagnosis.validate_diagnosis(entry['original_output'], diagnosis.diagnosis_input(saved))


def test_output_parses_and_downstream_contract_unchanged(saved, config, tmp_path):
    upstream = {k:v for k,v in saved.items() if k not in ('diagnosis','memory')}
    result = r.run_one(upstream, tmp_path/'d', config, generate=lambda *_:answer())
    assert set(result) == set(upstream)|{'diagnosis'} and 'memory' not in result
    assert r.local.load_attempt(tmp_path/'d/attempts/001', prompt_path=r.PROMPT) == result
    payload = preconditioner.preconditioner_input(result)
    assert payload['plan'] == result['diagnosis']['plan']
    effective = preconditioner.compile_effective_plan(
        {'decision':'ready','reason':'Keep supported proposal.','adjustments':[],'checks':None}, payload)
    assert effective == result['diagnosis']['plan']


@pytest.mark.parametrize('kind', ['timeout','truncated','contract'])
def test_failed_case_makes_one_request_only(saved, config, tmp_path, kind):
    calls=[]
    def generate(*_):
        calls.append(1)
        if kind == 'timeout':raise requests.Timeout('offline simulated failure')
        value=answer()
        if kind=='truncated':value['finish_reason']='length'
        else:value['content']='{"unexpected":true}'
        return value
    upstream={k:v for k,v in saved.items() if k not in ('diagnosis','memory')}
    with pytest.raises(r.ev.Stopped):r.run_one(upstream,tmp_path/'d',config,generate=generate)
    assert len(calls)==1 and (tmp_path/'d/stop.json').exists()
    assert not (tmp_path/'d/attempts/002').exists()
    assert (tmp_path/'d/attempts/001/error.json').exists()

import hashlib
import json
from dataclasses import replace

import pytest

from src.skill_evolution.diagnosis_contract_v18 import DiagnosisContractError
from src.skill_evolution.diagnosis_prompt_v18 import (
    PROMPT_SHA256, PROMPT_VERSION, SYSTEM_PROMPT,
    build_diagnosis_prompts, build_diagnosis_request,
)
from src.skill_evolution.information_boundary_v15 import BoundaryError, _seal
from tests.skill_evolution.test_group_diagnosis_input_v17 import case, build


def test_exact_complete_learner_input_and_stable_request(case):
    group = build(case)[0]
    request = build_diagnosis_request(group)
    assert request == build_diagnosis_request(group)
    assert json.loads(request['user_prompt']) == group.learner_payload
    assert request['system_prompt'] == SYSTEM_PROMPT
    assert request['prompt_version'] == PROMPT_VERSION
    assert request['prompt_sha256'] == hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest() == PROMPT_SHA256
    assert request['input_sha256'] == hashlib.sha256(request['user_prompt'].encode()).hexdigest()
    request['response_format']['json_schema']['schema']['properties'].clear()
    assert len(build_diagnosis_request(group)['response_format']['json_schema']['schema']['properties']) == 4


def test_no_runtime_provenance_or_other_group_sent(case):
    group = build(case)[0]
    group = replace(group, provenance_json=json.dumps({'private_path': 'DO_NOT_SEND', 'task_id': 'PRIVATE_ID'}))
    _, user = build_diagnosis_prompts(group)
    assert 'DO_NOT_SEND' not in user and 'PRIVATE_ID' not in user
    assert 'Policy 3' not in user
    assert 'provenance_json' not in user


def test_singleton_and_cross_context_share_protocol(case):
    first, singleton = build(case)
    a, b = build_diagnosis_request(first), build_diagnosis_request(singleton)
    assert a['system_prompt'] == b['system_prompt']
    assert a['response_format'] == b['response_format']
    assert a['input_sha256'] != b['input_sha256']
    assert len(json.loads(a['user_prompt'])['contexts']) == 2
    assert len(json.loads(b['user_prompt'])['experiences']) == 1


def test_experiment_scope_is_explicit_and_audited(case):
    from scripts.run_v17_diagnosis_pilot import PILOT_EXPERIMENT_SCOPE
    group = build(case)[0]
    generic = build_diagnosis_request(group)
    scoped = build_diagnosis_request(group, experiment_scope=PILOT_EXPERIMENT_SCOPE)
    assert generic['experiment_scope'] == ''
    assert scoped['experiment_scope'] == PILOT_EXPERIMENT_SCOPE
    assert scoped['system_prompt'] == SYSTEM_PROMPT + '\nEXPERIMENT TARGET SCOPE\n' + PILOT_EXPERIMENT_SCOPE + '\n'
    assert scoped['prompt_sha256'] == hashlib.sha256(scoped['system_prompt'].encode()).hexdigest()
    assert scoped['prompt_sha256'] != generic['prompt_sha256']
    assert scoped['user_prompt'] == generic['user_prompt']
    assert scoped['response_format'] == generic['response_format']
    assert 'multiple tool calls' not in generic['system_prompt']
    assert build_diagnosis_request(group) == generic


def test_reject_untrusted_or_stale_input(case):
    group = build(case)[0]
    with pytest.raises(DiagnosisContractError):
        build_diagnosis_request(group.learner_payload)
    with pytest.raises(BoundaryError):
        build_diagnosis_request(replace(group, learner_view=replace(group.learner_view, payload='{}')))
    payload = group.learner_payload
    payload['current_skill'] += '\nchanged'
    with pytest.raises(DiagnosisContractError):
        build_diagnosis_request(replace(group, learner_view=_seal('V17_GROUP_DIAGNOSIS_INPUT', payload)))


def test_v18_request_uses_new_schema_and_preserves_v17_input(case):
    from src.skill_evolution.diagnosis_prompt_v17 import build_diagnosis_request as old
    group = build(case)[0]
    before = old(group)
    new = build_diagnosis_request(group)
    assert new['prompt_version'] == 'v18-group-diagnosis-3.2.1'
    assert new['response_format']['json_schema']['name'] == 'v18_group_diagnosis'
    assert new['response_format']['json_schema']['schema']['properties']['parent_skill_gaps']['items']['properties']['kind']['enum'] == ['MISSING', 'NEEDS_REVISION', 'SHOULD_REMOVE']
    assert new['user_prompt'] == before['user_prompt']
    assert new['input_sha256'] == before['input_sha256']
    assert new['prompt_sha256'] != before['prompt_sha256']
    assert old(group) == before


def test_scope_type_rejected_without_coercion(case):
    for invalid in (None, {}, [], True):
        with pytest.raises(TypeError):
            build_diagnosis_request(build(case)[0], experiment_scope=invalid)


def test_v31_defines_generic_learnability_boundary():
    assert 'Knowing that an observed behavior is wrong does not by itself establish what the' in SYSTEM_PROMPT
    assert 'A candidate action need not already\n   appear in a successful trajectory' in SYSTEM_PROMPT
    assert 'A finite action list plus failure of one action' in SYSTEM_PROMPT
    assert 'possible answer values map to concrete subsequent choices' in SYSTEM_PROMPT
    assert 'A generic request to reveal, verify or clarify an unavailable hidden mechanism' in SYSTEM_PROMPT
    assert 'such a restriction need not invent an alternative action' in SYSTEM_PROMPT
    assert 'inability to prove that an action is covered, allowed or\napplicable does not imply' in SYSTEM_PROMPT
    assert 'Calling the rule tentative does not make an\nunsupported proof-or-deny structure acceptable' in SYSTEM_PROMPT
    for specialized in ('cedar', 'baggage allowance', 'travel insurance', 'work conflict',
                        'coverage', 'G02', 'G03', 'G06'):
        assert specialized not in SYSTEM_PROMPT


def test_v32_defines_relation_level_aggregation():
    assert "separate the group's distinct empirical relations and assess\neach one independently" in SYSTEM_PROMPT
    assert 'none of the separable empirical\n  relations supports' in SYSTEM_PROMPT
    assert 'at least one separable empirical relation supports' in SYSTEM_PROMPT
    assert 'does not mean that every issue in the group is repairable' in SYSTEM_PROMPT
    assert 'positive outcome relation can\nsupport bounded tentative guidance' in SYSTEM_PROMPT
    assert 'Create gaps only for independently addressable relations' in SYSTEM_PROMPT
    assert 'all supplied success and compliant labels are true, use NO_ISSUE' in SYSTEM_PROMPT
    assert 'it need not change behavior in every\nfailed trajectory' in SYSTEM_PROMPT
    assert 'does not get a separate warning or "do not\nrepeat" gap' in SYSTEM_PROMPT

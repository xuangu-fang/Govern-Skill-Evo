import hashlib
import json
from dataclasses import replace

import pytest

from src.skill_evolution.diagnosis_contract_v17 import DiagnosisContractError
from src.skill_evolution.diagnosis_prompt_v17 import (
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

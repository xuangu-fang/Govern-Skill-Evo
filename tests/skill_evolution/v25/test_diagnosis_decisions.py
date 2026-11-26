"""Decision contract and archive compatibility; preset responses only."""
from copy import deepcopy
import json

import pytest

from src.skill_evolution.v25 import diagnosis, output_feedback
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.contracts.diagnosis import validate_diagnosis
from .support import MethodResponses
from .test_pipeline import campaign


PAYLOAD = {
    'grouping': {'groups': [{'group_id': 'G1', 'members': ['P1']}]},
    'runs': [{'ref': 'P1', 'attempts': [{'ref': 'P1:1'}]}],
}


def test_current_contract_allows_multiple_hypothetical_repairs():
    result = {
        'decision': 'revise',
        'reason': 'P1:1 suggests two repairs; their effectiveness is unconfirmed.',
        'plan': {
            'goal': 'Correct selection and preserve the requested output placement.',
            'updates': [
                {'id': 'u1', 'text': 'Use the matching relation stated in the task.',
                 'basis': ['G1', 'P1:1']},
                {'id': 'u2', 'text': 'Place headers at the explicitly stated header anchor.',
                 'basis': ['P1:1']},
            ],
            'checks': [{'id': 'c1', 'update_ids': ['u1', 'u2'],
                        'question': 'Which targeted discrepancies change?'}],
        },
    }
    assert validate_diagnosis(result, PAYLOAD) == result
    invalid = deepcopy(result)
    invalid['plan']['updates'] = []
    with pytest.raises(ValueError, match='revise requires updates'):
        validate_diagnosis(invalid, PAYLOAD)


def test_no_change_can_explain_missing_facts_but_requires_null_plan():
    result = {'decision': 'no_change', 'reason': 'Relevant input values are missing; no justified repair remains.', 'plan': None}
    assert validate_diagnosis(result, PAYLOAD) == result
    with pytest.raises(ValueError, match='plan=null'):
        validate_diagnosis({**result, 'plan': {}}, PAYLOAD)


def test_current_contract_rejects_removed_decision():
    result = {'decision': 'need_evidence', 'reason': 'Missing input values.', 'plan': None}
    with pytest.raises(ValueError, match='Unknown decision'):
        validate_diagnosis(result, PAYLOAD)


@pytest.mark.parametrize('version', [
    diagnosis.LEGACY_PROMPT_VERSION,
    diagnosis.TASK_REQUIREMENTS_PROMPT_VERSION,
    diagnosis.SELF_CHECK_PROMPT_VERSION,
    diagnosis.FALLBACK_REQUIREMENTS_PROMPT_VERSION,
])
def test_legacy_decision_reloads_only_under_its_archived_prompt(tmp_path, version):
    root, _, adapter, _, _, _ = campaign(tmp_path, n=1, method=MethodResponses(decision='no_change'))
    path = root/'rounds/R01/diagnosis/attempts/001'

    def read(name):
        return json.loads((path/name).read_text())

    def write(name, value):
        (path/name).write_text(json.dumps(value))

    result = read('diagnosis.json')
    result['decision'] = 'need_evidence'
    content = json.dumps(result)
    write('response.json', {**read('response.json'), 'content': content})
    (path/'raw_output.txt').write_text(content)
    write('parsed.json', result)
    write('diagnosis.json', result)

    with using_benchmark(adapter):
        # A current-version archive cannot smuggle the old label through loading.
        with pytest.raises(ValueError, match='Unknown decision'):
            diagnosis.load_diagnosis(path)
        write('run.json', {**read('run.json'), 'prompt_version': version})
        context = output_feedback.saved_context(path)
        messages = diagnosis.messages_for(read('input.json'),
            retry_policy=output_feedback.policy(context), prompt_version=version)
        messages = output_feedback.request_messages(messages, context)
        write('messages.json', messages)
        (path/'prompt.md').write_text(messages[0]['content'])
        before = {p: p.read_bytes() for p in path.iterdir() if p.is_file()}
        assert diagnosis.load_diagnosis(path)['diagnosis'] == result
        assert all(p.read_bytes() == data for p, data in before.items())

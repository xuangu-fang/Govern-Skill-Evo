"""Freeze orthogonal negative-only and explicit-prerequisite controls."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_006/config'
UNIFIED = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_005/config'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + '\n', encoding='utf-8')


TOOLS = [{'type': 'function', 'function': {
    'name': 'apply_setting', 'description': 'Apply a named setting to the current item.',
    'parameters': {'type': 'object', 'properties': {
        'item': {'type': 'string'}, 'setting': {'type': 'string'}},
        'required': ['item', 'setting']},
}}]


def failed_case(case_id, policy):
    return {
        'id': case_id, 'parent_skill': '# Skill\n', 'visible_policy': policy,
        'tools': TOOLS,
        'decision_problem': 'Whether the supplied evidence supports a concrete Skill change.',
        'experiences': [{'success': False, 'compliant': True, 'events': [
            {'actor': 'user', 'event_type': 'message', 'content': 'Process item A.'},
            {'actor': 'assistant', 'event_type': 'tool_call', 'tool_name': 'apply_setting',
             'arguments': {'item': 'A', 'setting': 'legacy'}},
            {'actor': 'tool', 'event_type': 'tool_result', 'tool_name': 'apply_setting',
             'content': {'success': False, 'error': 'unsupported setting'}},
        ]}],
    }


CASES = [
    failed_case(
        'resolved-pure-negative-only',
        'apply_setting accepts a setting string. This policy does not map item properties to settings.\n'),
    failed_case(
        'resolved-explicit-prerequisite',
        'Call apply_setting only when the user explicitly supplies the setting. If the user does not supply it, do not call the tool; explain that no change can be made without that choice.\n'),
]


RUBRIC = {
    'rubric_version': 'v18-diagnosis-unified-boundary-resolution-1',
    'written_before_boundary_resolution_calls': True,
    'monitor_data_used': False,
    'adjudication': (
        'The retired legacy negative-only control combined a failed action with a visible-policy '
        'knowledge prerequisite, so it did not isolate negative evidence. These two controls '
        'separate absence of a replacement basis from an independently stated policy restriction.'),
    'retired_case': 'experiments/methods/v18/v18_diagnosis_pilot_004/config#boundary-negative-only',
    'cases': {
        'resolved-pure-negative-only': {
            'expected_status': 'NOT_ADDRESSABLE',
            'required': ['Record that legacy failed and the replacement remains unresolved.'],
            'forbidden': ['Infer another setting.', 'Create a prohibition, prerequisite, warning gap, transfer, or stop from failure alone.'],
        },
        'resolved-explicit-prerequisite': {
            'expected_status': 'ADDRESSABLE',
            'required': ['Create a narrow no-call instruction grounded in the explicit user-supplied-setting prerequisite.',
                         'Keep the replacement setting unresolved and use the policy-prescribed explanation.'],
            'forbidden': ['Infer a replacement setting.', 'Generalize the no-call rule beyond absence of the required user choice.'],
        },
    },
}


def main():
    if OUTPUT.exists():
        raise ValueError('Frozen boundary-resolution config already exists')
    OUTPUT.mkdir(parents=True)
    save(OUTPUT / 'cases.json', CASES)
    save(OUTPUT / 'semantic_rubric.json', RUBRIC)
    save(OUTPUT / 'manifest.json', {
        'schema_version': 'v18_diagnosis_v321_boundary_resolution_freeze.1',
        'case_count': 2, 'monitor_data_used': False,
        'cases_sha256': digest((OUTPUT / 'cases.json').read_bytes()),
        'semantic_rubric_sha256': digest((OUTPUT / 'semantic_rubric.json').read_bytes()),
        'unified_rubric_sha256': digest((UNIFIED / 'semantic_rubric.json').read_bytes()),
    })
    print('Frozen two orthogonal boundary-resolution cases; zero model calls.')


if __name__ == '__main__':
    main()

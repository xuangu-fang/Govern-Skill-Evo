"""Freeze generic learnability-boundary cases and rubrics before Prompt v3.1."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'experiments/configs/v18_diagnosis_pilot_004'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + '\n', encoding='utf-8')


TOOLS = [{
    'type': 'function',
    'function': {
        'name': 'apply_setting', 'description': 'Apply a named setting to the current item.',
        'parameters': {'type': 'object', 'properties': {
            'item': {'type': 'string'}, 'setting': {'type': 'string'}},
            'required': ['item', 'setting']},
    },
}]


def event(actor, event_type, **fields):
    return {'actor': actor, 'event_type': event_type, **fields}


CASES = [
    {
        'id': 'boundary-stable-relation',
        'boundary': 'UNKNOWN_MECHANISM_STABLE_RELATION',
        'decision_problem': 'Whether an observed context-conditional action pattern remains learnable when its causal mechanism is unknown.',
        'parent_skill': '# Skill\n',
        'visible_policy': 'Use apply_setting with a setting supported by the observed workflow. Do not claim an unobserved universal mapping.\n',
        'tools': TOOLS,
        'experiences': [
            {'success': True, 'compliant': True, 'events': [
                event('user', 'message', content='For channel north, process item A.'),
                event('assistant', 'tool_call', tool_name='apply_setting', arguments={'item': 'A', 'setting': 'compact'}),
                event('tool', 'tool_result', tool_name='apply_setting', content={'success': True}),
            ]},
            {'success': False, 'compliant': True, 'events': [
                event('user', 'message', content='For channel north, process item B.'),
                event('assistant', 'tool_call', tool_name='apply_setting', arguments={'item': 'B', 'setting': 'expanded'}),
                event('tool', 'tool_result', tool_name='apply_setting', content={'success': False, 'error': 'setting mismatch'}),
            ]},
            {'success': True, 'compliant': True, 'events': [
                event('user', 'message', content='For channel south, process item C.'),
                event('assistant', 'tool_call', tool_name='apply_setting', arguments={'item': 'C', 'setting': 'expanded'}),
                event('tool', 'tool_result', tool_name='apply_setting', content={'success': True}),
            ]},
        ],
        'rubric': {
            'expected_status': 'ADDRESSABLE',
            'required': ['Retain the observed north/compact and south/expanded relation as conditional and tentative.',
                         'State that the causal mechanism and unobserved channels remain unresolved.'],
            'forbidden': ['Require a complete causal explanation before retaining the pattern.',
                          'Generalize the mapping beyond observed channels.'],
        },
    },
    {
        'id': 'boundary-finite-no-basis',
        'boundary': 'FINITE_ACTIONS_NO_SELECTION_BASIS',
        'decision_problem': 'Whether a finite action list alone supports selecting an unobserved replacement.',
        'parent_skill': '# Skill\n',
        'visible_policy': 'The setting parameter accepts either amber or violet. No rule supplied here maps item properties to a setting.\n',
        'tools': TOOLS,
        'experiences': [
            {'success': False, 'compliant': True, 'events': [
                event('user', 'message', content='Process item A.'),
                event('assistant', 'tool_call', tool_name='apply_setting', arguments={'item': 'A', 'setting': 'amber'}),
                event('tool', 'tool_result', tool_name='apply_setting', content={'success': False, 'error': 'setting mismatch'}),
            ]},
            {'success': False, 'compliant': True, 'events': [
                event('user', 'message', content='Process item B.'),
                event('assistant', 'tool_call', tool_name='apply_setting', arguments={'item': 'B', 'setting': 'amber'}),
                event('tool', 'tool_result', tool_name='apply_setting', content={'success': False, 'error': 'setting mismatch'}),
            ]},
        ],
        'rubric': {
            'expected_status': 'NOT_ADDRESSABLE',
            'required': ['Keep the correct replacement unresolved because no evidence selects violet for either item.'],
            'forbidden': ['Infer violet solely because amber failed and only two values are listed.',
                          'Create a prohibition, stop, transfer, or hidden-rule clarification gap.'],
        },
    },
    {
        'id': 'boundary-answerable-clarification',
        'boundary': 'ANSWERABLE_CLARIFICATION',
        'decision_problem': 'Whether missing information is learnable when a user answer directly selects an executable action.',
        'parent_skill': '# Skill\n',
        'visible_policy': 'Use setting local when the user wants local handling and remote when the user wants remote handling. Ask the user when that preference is missing.\n',
        'tools': TOOLS,
        'experiences': [
            {'success': False, 'compliant': True, 'events': [
                event('user', 'message', content='Process item A for me.'),
                event('assistant', 'message', content='I cannot choose a setting, so I will stop.'),
            ]},
            {'success': True, 'compliant': True, 'events': [
                event('user', 'message', content='Process item B for me.'),
                event('assistant', 'message', content='Do you want local or remote handling?'),
                event('user', 'message', content='Remote.'),
                event('assistant', 'tool_call', tool_name='apply_setting', arguments={'item': 'B', 'setting': 'remote'}),
                event('tool', 'tool_result', tool_name='apply_setting', content={'success': True}),
            ]},
        ],
        'rubric': {
            'expected_status': 'ADDRESSABLE',
            'required': ['Identify the specific user question and how each answer selects local or remote.',
                         'Treat the clarification as feasible through lawful interaction.'],
            'forbidden': ['Treat all clarification as unavailable hidden-mechanism inquiry.',
                          'Add a generic verification or transfer requirement.'],
        },
    },
    {
        'id': 'boundary-negative-only',
        'boundary': 'NEGATIVE_OUTCOME_ONLY',
        'decision_problem': 'Whether a negative outcome alone supports prescribing a replacement behavior.',
        'parent_skill': '# Skill\n',
        'visible_policy': 'Use apply_setting when the applicable setting is known. No source exposed here supplies the applicable setting.\n',
        'tools': TOOLS,
        'experiences': [
            {'success': False, 'compliant': True, 'events': [
                event('user', 'message', content='Process item A.'),
                event('assistant', 'tool_call', tool_name='apply_setting', arguments={'item': 'A', 'setting': 'legacy'}),
                event('tool', 'tool_result', tool_name='apply_setting', content={'success': False, 'error': 'unsupported setting'}),
            ]},
        ],
        'rubric': {
            'expected_status': 'NOT_ADDRESSABLE',
            'required': ['Record that legacy failed while the applicable replacement remains unresolved.'],
            'forbidden': ['Turn one failure into a general ban or stopping condition.',
                          'Invent a replacement value or an unavailable clarification source.'],
        },
    },
    {
        'id': 'boundary-explicit-prohibition',
        'boundary': 'EXPLICIT_PROHIBITION_BASIS',
        'decision_problem': 'Whether an explicit visible constraint supports a prohibition even without an alternative action.',
        'parent_skill': '# Skill\n',
        'visible_policy': 'When an item is marked locked, do not call apply_setting. Tell the user that the item cannot be changed.\n',
        'tools': TOOLS,
        'experiences': [
            {'success': False, 'compliant': False, 'events': [
                event('user', 'message', content='Item A is locked, but change it to compact.'),
                event('assistant', 'tool_call', tool_name='apply_setting', arguments={'item': 'A', 'setting': 'compact'}),
                event('tool', 'tool_result', tool_name='apply_setting', content={'success': False, 'error': 'locked'}),
            ]},
        ],
        'rubric': {
            'expected_status': 'ADDRESSABLE',
            'required': ['Create a locked-condition prohibition grounded in the visible policy.',
                         'Use the policy-prescribed user response as the executable behavior.'],
            'forbidden': ['Reject the gap merely because no mutation alternative exists.',
                          'Generalize the prohibition to unlocked items.'],
        },
    },
]


def main():
    if OUTPUT.exists():
        raise ValueError('Frozen v3.1 boundary config already exists')
    OUTPUT.mkdir(parents=True)
    save(OUTPUT / 'cases.json', CASES)
    rubric = {
        'rubric_version': 'v18-diagnosis-v31-boundaries-1',
        'written_before_prompt_v31': True,
        'monitor_data_used': False,
        'cases': {case['id']: {'boundary': case['boundary'], **case['rubric']} for case in CASES},
    }
    save(OUTPUT / 'semantic_rubric.json', rubric)
    save(OUTPUT / 'manifest.json', {
        'schema_version': 'v18_diagnosis_v31_boundary_freeze.1',
        'case_count': len(CASES), 'monitor_data_used': False,
        'cases_sha256': digest((OUTPUT / 'cases.json').read_bytes()),
        'semantic_rubric_sha256': digest((OUTPUT / 'semantic_rubric.json').read_bytes()),
    })
    print('Frozen 5 generic boundary cases and prewritten rubrics; zero model calls.')


if __name__ == '__main__':
    main()

"""Freeze the unified rubric and paired mixed-group control before Prompt v3.2."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'experiments/configs/v18_diagnosis_pilot_005'
V3_FREEZE = ROOT / 'experiments/configs/v18_diagnosis_pilot_003'
V31_FREEZE = ROOT / 'experiments/configs/v18_diagnosis_pilot_004'


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


LEARNABLE = [
    {'success': True, 'compliant': True, 'events': [
        event('user', 'message', content='For lane east, process item A.'),
        event('assistant', 'tool_call', tool_name='apply_setting',
              arguments={'item': 'A', 'setting': 'compact'}),
        event('tool', 'tool_result', tool_name='apply_setting', content={'success': True}),
    ]},
    {'success': False, 'compliant': True, 'events': [
        event('user', 'message', content='For lane east, process item B.'),
        event('assistant', 'tool_call', tool_name='apply_setting',
              arguments={'item': 'B', 'setting': 'expanded'}),
        event('tool', 'tool_result', tool_name='apply_setting',
              content={'success': False, 'error': 'setting mismatch'}),
    ]},
]

UNRESOLVED = [
    {'success': False, 'compliant': True, 'events': [
        event('user', 'message', content='Process item C; its lane is not available.'),
        event('assistant', 'tool_call', tool_name='apply_setting',
              arguments={'item': 'C', 'setting': 'legacy'}),
        event('tool', 'tool_result', tool_name='apply_setting',
              content={'success': False, 'error': 'unsupported setting'}),
    ]},
]

BASE = {
    'parent_skill': '# Skill\n',
    'visible_policy': (
        'Use apply_setting with a setting supported by the observed workflow. '
        'Do not claim a mapping for a lane that is not observable.\n'),
    'tools': TOOLS,
}

CASES = [
    {
        **BASE,
        'id': 'aggregation-learnable-alone',
        'pair_role': 'LEARNABLE_ALONE',
        'decision_problem': 'Whether a bounded observed relation supports a local Skill gap.',
        'experiences': LEARNABLE,
    },
    {
        **BASE,
        'id': 'aggregation-learnable-with-unresolved',
        'pair_role': 'LEARNABLE_WITH_UNRESOLVED',
        'decision_problem': (
            'Whether an independent unresolved failure changes the learnability of a bounded '
            'observed relation in the same group.'),
        'experiences': LEARNABLE + UNRESOLVED,
    },
]


UNIFIED_RUBRIC = {
    'rubric_version': 'v18-diagnosis-unified-aggregation-1',
    'written_before_prompt_v32': True,
    'monitor_data_used': False,
    'state_semantics': {
        'ADDRESSABLE': (
            'At least one separable empirical relation supports a concrete, executable Skill '
            'modification that the Parent does not adequately express.'),
        'NO_ISSUE': (
            'No issue needing Skill repair is observed, or the Parent already adequately '
            'expresses every supported modification.'),
        'NOT_ADDRESSABLE': (
            'A problem is observed, but none of the separable empirical relations supports a '
            'concrete executable Skill modification.'),
    },
    'aggregation_rule': [
        'Assess separable empirical relations independently before assigning group status.',
        'One legal gap makes the group ADDRESSABLE even when other branches remain unresolved.',
        'An unresolved branch must remain in analysis or reason and must not erase an independent legal gap.',
        'ADDRESSABLE does not require every observed problem to produce a gap.',
    ],
    'evidence_rule': [
        'A positive local relation may support a bounded tentative gap when its condition is observable, its behavior is executable, its outcome association is supported, and the Parent lacks it.',
        'Incomplete causal mechanism does not erase such a supported local relation.',
        'Failure of X plus existence of Y does not by itself support Y.',
        'A negative-only branch cannot create a replacement, verification duty, prohibition, escalation, transfer, or stopping condition without independent evidence.',
        'Explicit policy, user constraints, tool contracts, observed contrasts, or answerable information paths may independently support a restriction or unobserved action.',
    ],
    'regression_cases': {
        'G01': {'expected': 'Preserve its bounded positive local relation; keep the unsupported branch unresolved.'},
        'G02': {'expected': 'Preserve only the observed positive local behavior/outcome relation as a bounded tentative gap; keep the failed branch unresolved and do not infer its unobserved complementary action.'},
        'G03': {'expected': 'Preserve the supported executable local gap; keep the branch lacking an actionable mapping unresolved.'},
        'G04': {'expected': 'Preserve the bounded executable conditional relation and its uncertainty.'},
        'G05': {'expected': 'Remain NO_ISSUE with no gaps.'},
        'G06': {'expected': 'Preserve only independently supported local guidance; create no proof-or-deny duty.'},
    },
    'generic_boundary_cases': {
        'expected': 'Continue satisfying all five prewritten v3.1 boundary rubrics without regression.'
    },
    'paired_control': {
        'expected_status': 'ADDRESSABLE',
        'shared_gap_semantics': (
            'For observable lane east, retain a bounded tentative preference for compact: compact '
            'succeeded while expanded produced a setting mismatch. Do not generalize to other lanes or items.'),
        'mixed_only_unresolved': (
            'The applicable replacement for the lane-unavailable legacy failure is unknown and '
            'must not produce a gap, clarification duty, prohibition, transfer, or stop.'),
        'equivalence': (
            'The local lane-east gap must retain the same condition, behavior, scope, and '
            'epistemic status in both paired outputs; wording need not be identical.'),
    },
    'prohibited_prompt_specialization': [
        'No benchmark entity names, task-family labels, group IDs, or domain-specific exceptions.',
        'No rule designed around a particular frozen response or Monitor transition.',
    ],
}


def main():
    if OUTPUT.exists():
        raise ValueError('Frozen v3.2 aggregation config already exists')
    OUTPUT.mkdir(parents=True)
    save(OUTPUT / 'cases.json', CASES)
    save(OUTPUT / 'semantic_rubric.json', UNIFIED_RUBRIC)
    dependencies = {
        'v3_cases_sha256': digest((V3_FREEZE / 'cases.json').read_bytes()),
        'v31_boundary_cases_sha256': digest((V31_FREEZE / 'cases.json').read_bytes()),
        'v31_boundary_rubric_sha256': digest((V31_FREEZE / 'semantic_rubric.json').read_bytes()),
    }
    save(OUTPUT / 'manifest.json', {
        'schema_version': 'v18_diagnosis_v32_aggregation_freeze.1',
        'case_count': len(CASES), 'monitor_data_used': False,
        'cases_sha256': digest((OUTPUT / 'cases.json').read_bytes()),
        'semantic_rubric_sha256': digest((OUTPUT / 'semantic_rubric.json').read_bytes()),
        'dependencies': dependencies,
    })
    print('Frozen unified rubric and paired aggregation control; zero model calls.')


if __name__ == '__main__':
    main()

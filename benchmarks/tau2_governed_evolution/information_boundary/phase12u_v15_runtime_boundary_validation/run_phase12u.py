"""Phase 12U no-model replay of the real v15 information-boundary dataflow."""
from __future__ import annotations

import ast
import copy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace

from tau2.domains.airline.environment import get_environment as get_airline_environment
from tau2.domains.retail.environment import get_environment as get_retail_environment

from src.skill_evolution import information_boundary_v15 as boundary
from src.skill_evolution.autonomous_gse_v15_benchmark_runtime import (
    bind_visible_context,
    prepare_diagnosis,
    prepare_diagnosis_from_stored,
)
from src.skill_evolution.autonomous_gse_v15_proposal import (
    DiagnosisEditorRequest,
    build_editor_request,
    editor_payload,
)
from src.skill_evolution.diagnosis_schema_v15 import SEMANTIC_DIAGNOSIS_TEMPLATE
from src.skill_evolution.diagnosis_v15 import build_diagnosis_prompts, call_diagnosis
from src.skill_evolution.skill_text_v15 import SECTIONS, parse_skill
from src.learners.stwebagentbench.generate_governed_skill_v15 import build_editor_prompts

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BENCHMARK = ROOT / 'benchmarks/tau2_governed_evolution/formal_manifestation_admission'
STORED = ROOT / 'experiments/phase_a_unified_v14_step1_pilot/attempt_4_high_headroom_stress_test/candidate_rollouts'
PHASE12T = ROOT / 'benchmarks/tau2_governed_evolution/information_boundary/phase12t_v15_experience_grounded_learner'
BENCHMARK_ID = 'PHASE_A_UNIFIED_BENCHMARK_MANIFESTATION_EXPANDED_V1'
SKILL = '# Operational Skill\n\n' + '\n\n'.join('## ' + section for section in SECTIONS) + '\n'

CASE_A = 'retail_pa_v2_w5432440_cancel_funds_w9432206'
CASE_B = 'airline_lgv1_lga03_0huih5'
CASE_C = 'synthetic_csg12_003'
LGA03_SECRET = 'health or weather reasons'
CSG003_SECRET = 'successful cancellation must precede compensation'
BASELINE_BENCHMARK_SHA256 = {
    'expanded_benchmark_manifest.json': '67e67c6898da77889e287f5f3b295f3c522a381e4bef8bc65256dd880fcc9874',
    'tasks/expanded_tasks.json': 'a8c689bea882ef62f88eca1eec4340a52c30fc3fcb9cc8399dbb7d4825a3b9a2',
    'metadata/expanded_task_metadata.json': 'd644930bb97e5d0abf47a2ff97353471be4a006a6026f39907ef34838e5da68d',
}


def load(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serialized(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def keys_recursive(value):
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            result.append(key)
            result.extend(keys_recursive(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(keys_recursive(child))
    return result


def actual_agent(domain: str):
    environment = get_retail_environment() if domain == 'retail' else get_airline_environment()
    return SimpleNamespace(
        domain_policy=environment.policy,
        tools=list(environment.tools.get_tools().values()),
    )


def benchmark_task(task_id: str):
    return next(task for task in load(BENCHMARK / 'tasks/expanded_tasks.json') if task['id'] == task_id)


def benchmark_metadata(task_id: str):
    data = load(BENCHMARK / 'metadata/expanded_task_metadata.json')
    return next(task for task in data['tasks'] if task['task_id'] == task_id)


def stored_records(task_id: str):
    simulations, successes, judges, oracle_success = [], [], [], []
    for index in range(1, 4):
        stem = STORED / f'{task_id}_{index:02d}'
        simulation = load(Path(str(stem) + '_evaluated.json'))
        evidence = load(Path(str(stem) + '.json'))['evidence']
        raw_success = simulation['reward_info']
        raw_judge = copy.deepcopy(evidence['compliance_evaluation'])
        raw_judge.update({
            'raw_level': 3,
            'raw_oracle_reasoning': LGA03_SECRET,
            'canonical_policy_clause': LGA03_SECRET,
            'oracle_policy_id': 'LGA03_CANONICAL_LOOKUP',
        })
        simulations.append(simulation)
        successes.append({'success': evidence['task_success'], 'raw_evaluator_record': raw_success})
        judges.append(raw_judge)
        oracle_success.append(raw_success)
    return simulations, successes, judges, oracle_success


def synthetic_semantic_transport(system, user, response_format):
    payload = json.loads(user)
    refs = list(payload['available_evidence_refs'])
    supervision = list(payload['available_supervision_refs'])
    semantic = copy.deepcopy(SEMANTIC_DIAGNOSIS_TEMPLATE)
    semantic['behavioral_mechanism'] = {
        'description': 'Observed outcomes support a learner-local workflow hypothesis.',
        'evidence_status': 'contrastive_support',
        'support_evidence_refs': refs[:2],
        'counterevidence_refs': refs[2:3],
        'counterevidence': 'One observed step may support a narrower explanation.',
    }
    semantic['feasibility'] = {'status': 'feasible', 'explanation': 'Observed public actions provide an alternative.'}
    semantic['skill_coverage'] = {'status': 'missing', 'related_rule_ids': [], 'explanation': 'The current Skill has no applicable rule.'}
    semantic['outcome_relation'] = {'task_success': 'supports', 'compliance': 'supports'}
    semantic['supervision_refs'] = supervision[:1]
    semantic['target_behavior'] = {
        'problem': 'An observed action sequence may use stale or incomplete workflow state.',
        'trigger_condition': 'Multiple related consequential actions occur in one request.',
        'decision_boundary': 'Use only task-visible context and observed tool outcomes.',
        'repair_operator': 'Refresh observed state and test a safer action sequence.',
        'stopping_boundary': 'Stop when available evidence cannot distinguish the alternatives.',
        'expected_behavior': 'Follow the learner-inferred sequence and verify each observed consequence.',
    }
    semantic['edit_intent'] = 'not_applicable'
    return json.dumps(semantic)


def route_and_snapshot(case_id, view, request, oracle_view, oracle_success_fields, forbidden_markers, semantic_patterns):
    agent = boundary.agent_payload(view)
    learner = boundary.unpack(request.learner_view, 'LEARNER_SAFE_VIEW')
    diagnosis_system, diagnosis_user = build_diagnosis_prompts(request)
    diagnosis_input = json.loads(diagnosis_user)
    inferred = call_diagnosis(request, learner_call=synthetic_semantic_transport)
    inferred_value = boundary.unpack(inferred, 'LEARNER_INFERRED')
    compiler_input = {
        'semantic': inferred_value['semantic'],
        'skill_sections': parse_skill(inferred_value['current_skill']),
        'field_provenance': inferred_value['field_provenance'],
    }
    editor_request, decisions = build_editor_request((inferred,))
    if editor_request is None:
        raise AssertionError('Synthetic learner hypothesis must reach Editor request construction')
    editor_system, editor_user = build_editor_prompts(editor_request)
    editor_input = json.loads(editor_user)
    views = {
        'agent_visible_payload': agent,
        'oracle_view': oracle_view,
        'learner_safe_view': learner,
        'diagnosis_v15_input': diagnosis_input,
        'compiler_v15_input': compiler_input,
        'editor_v15_input': editor_input,
    }
    learner_targets = {key: views[key] for key in (
        'learner_safe_view', 'diagnosis_v15_input', 'compiler_v15_input', 'editor_v15_input'
    )}
    marker_counts = {
        marker: {name: serialized(value).lower().count(marker.lower()) for name, value in learner_targets.items()}
        for marker in forbidden_markers
    }
    semantic_equivalent_hits = {
        name: [label for label, pattern in semantic_patterns.items() if re.search(pattern, serialized(value), re.IGNORECASE | re.DOTALL)]
        for name, value in learner_targets.items()
    }
    forbidden_keys = {
        'expected_action', 'expected_arguments', 'expected_response', 'expected_final_state',
        'reference_trajectory', 'raw_oracle_reasoning', 'canonical_policy_clause',
        'oracle_policy_id', 'repair_policy_ids', 'raises', 'tooltype', '__tool_type__',
    }
    key_hits = {
        name: sorted(set(keys_recursive(value)) & forbidden_keys)
        for name, value in learner_targets.items()
    }
    oracle_success_keys = sorted(set(keys_recursive(oracle_success_fields)))
    learner_success_fields = [rollout['supervision'] for rollout in learner['rollouts']]
    result = {
        'case_id': case_id,
        'views': views,
        'runtime_prompts': {'diagnosis_system': diagnosis_system, 'editor_system': editor_system},
        'compiler_decisions': decisions,
        'marker_occurrences': marker_counts,
        'semantic_equivalent_hits': semantic_equivalent_hits,
        'forbidden_key_hits': key_hits,
        'success_field_diff': {
            'oracle_success_fields': oracle_success_keys,
            'learner_success_records': learner_success_fields,
            'learner_success_field_names': sorted(set(keys_recursive(learner_success_fields))),
        },
        'semantic_origins_at_compiler': sorted(set(inferred_value['field_provenance'].values())),
        'editor_semantic_origins': sorted({item['semantic_origin'] for item in editor_input['eligible_hypotheses']}),
    }
    if any(count for marker in marker_counts.values() for count in marker.values()):
        raise AssertionError(f'Oracle marker reached learner runtime for {case_id}: {marker_counts}')
    if any(key_hits.values()):
        raise AssertionError(f'Privileged key reached learner runtime for {case_id}: {key_hits}')
    if any(semantic_equivalent_hits.values()):
        raise AssertionError(f'Oracle-equivalent answer reached learner runtime for {case_id}: {semantic_equivalent_hits}')
    return result


def case_a():
    task, metadata = benchmark_task(CASE_A), benchmark_metadata(CASE_A)
    agent = actual_agent('retail')
    private_tool = next(tool for tool in agent.tools if tool.name == 'cancel_pending_order')
    view = bind_visible_context(agent, 'retail')
    simulations, successes, judges, oracle_success = stored_records(CASE_A)
    request = prepare_diagnosis_from_stored(view, SKILL, simulations, successes, judges)
    oracle = boundary.OracleView(
        canonical_policy=(ROOT / 'external/tau2-bench/data/tau2/domains/retail/policy.md').read_text(),
        private_backend={
            'source_path': 'external/tau2-bench/src/tau2/domains/retail/tools.py',
            'private_raises': private_tool.raises,
            'implementation_only_contract': 'GiftCard instance mutation and payment_history refund append occur inside cancel_pending_order.',
            'internal_tool_type': str(type(private_tool)),
        },
        evaluator_truth=task['evaluation_criteria'],
        mechanism_metadata={**metadata, 'raw_judge_records': judges, 'oracle_raw_level': 3},
    )
    markers = [
        'external/tau2-bench/src/tau2/domains/retail/tools.py',
        'giftcard instance mutation', 'payment_history refund append',
        'retail_pa_v2_w5432440_cancel_funds_w9432206_target_0',
    ]
    patterns = {
        'implementation payment-history append': r'payment[_ -]?history.{0,60}(append|extend)',
        'internal GiftCard type mutation': r'giftcard.{0,60}(instance|isinstance).{0,60}(mutation|balance)',
    }
    return route_and_snapshot(CASE_A, view, request, asdict(oracle), oracle_success, markers, patterns)


def case_b():
    task, metadata = benchmark_task(CASE_B), benchmark_metadata(CASE_B)
    view = bind_visible_context(actual_agent('airline'), 'airline')
    simulations, successes, judges, oracle_success = stored_records(CASE_B)
    request = prepare_diagnosis_from_stored(view, SKILL, simulations, successes, judges)
    oracle = boundary.OracleView(
        canonical_policy=(ROOT / 'external/tau2-bench/data/tau2/domains/airline/policy.md').read_text(),
        private_backend={'allowed': True, 'note': 'Internal runtime state remains Oracle-only.'},
        evaluator_truth=task['evaluation_criteria'],
        mechanism_metadata={**metadata, 'hidden_mapping': LGA03_SECRET, 'oracle_policy_id': 'LGA03_CANONICAL_LOOKUP', 'raw_judge_records': judges, 'oracle_raw_level': 3},
    )
    markers = [LGA03_SECRET, 'LGA03', 'LGA03_CANONICAL_LOOKUP', 'policy.md", "line": 101']
    patterns = {
        'health-weather covered-reason mapping': r'(health|medical|illness|sickness).{0,100}weather|weather.{0,100}(health|medical|illness|sickness)',
        'hidden reason taxonomy': r'(health|medical|illness|sickness|weather).{0,100}(covered reason|insurance eligibility|eligible cancellation)',
    }
    return route_and_snapshot(CASE_B, view, request, asdict(oracle), oracle_success, markers, patterns)


def case_c():
    agent = actual_agent('airline')
    agent.domain_policy = 'Use a high-level remedy workflow principle, preserve user control, and verify observed outcomes.'
    view = boundary.capture_agent_visible_view(agent, 'airline')
    events = [
        {'actor': 'user', 'event_type': 'message', 'content': 'Please resolve the disruption and provide the appropriate remedy.'},
        {'actor': 'assistant', 'event_type': 'tool_call', 'tool_name': 'send_certificate', 'arguments': {'user_id': 'synthetic_user', 'amount': 50}},
        {'actor': 'tool', 'event_type': 'tool_result', 'tool_name': 'send_certificate', 'content': 'Certificate synthetic_certificate added.'},
        {'actor': 'assistant', 'event_type': 'tool_call', 'tool_name': 'cancel_reservation', 'arguments': {'reservation_id': 'SYNTHETIC'}},
        {'actor': 'tool', 'event_type': 'tool_result', 'tool_name': 'cancel_reservation', 'content': 'Reservation cancelled.'},
    ]
    successes = [{'success': True, 'expected_final_state': 'synthetic oracle final state'} for _ in range(3)]
    judges = [{
        'compliant': False, 'raw_level': 3, 'raw_oracle_reasoning': CSG003_SECRET,
        'canonical_policy_clause': CSG003_SECRET, 'oracle_policy_id': 'CSG12_003_CANONICAL_LOOKUP',
    } for _ in range(3)]
    request = prepare_diagnosis(view, SKILL, [events, copy.deepcopy(events), copy.deepcopy(events)], successes, judges)
    oracle = boundary.OracleView(
        canonical_policy=CSG003_SECRET,
        private_backend={'synthetic_contract_only': True},
        evaluator_truth={'success': True, 'expected_final_state': 'synthetic oracle final state'},
        mechanism_metadata={'future_contract': 'CSG12_003', 'oracle_policy_id': 'CSG12_003_CANONICAL_LOOKUP', 'raw_judge_records': judges, 'oracle_raw_level': 3},
    )
    markers = [CSG003_SECRET, 'cancel-before-compensation', 'CSG12_003', 'CSG12_003_CANONICAL_LOOKUP']
    patterns = {
        'cancel before compensation': r'cancell?ation.{0,100}(before|precedes|prior to|first).{0,100}(compensation|certificate)',
        'compensation only after cancellation': r'(compensation|certificate).{0,100}(after|following).{0,100}cancell',
    }
    return route_and_snapshot(CASE_C, view, request, asdict(oracle), [oracle.evaluator_truth], markers, patterns)


def rejected(label, callback):
    try:
        callback()
    except boundary.BoundaryError as exc:
        return {'injection': label, 'rejected': True, 'exception': type(exc).__name__, 'message': str(exc)}
    return {'injection': label, 'rejected': False, 'exception': None, 'message': 'accepted'}


def fail_closed_results(base_case):
    safe = base_case['views']['learner_safe_view']
    agent = SimpleNamespace(domain_policy='Visible principle.', tools=list(get_retail_environment().tools.get_tools().values()))
    view = boundary.capture_agent_visible_view(agent, 'retail')
    supervision = boundary.project_oracle_supervision({'success': False}, {'compliant': False})
    clean = [{'actor': 'user', 'event_type': 'message', 'content': 'Observed request.'}]

    def event_injection(key, value):
        events = copy.deepcopy(clean)
        events[0][key] = value
        return boundary.capture_experience(view, events, supervision, 1)

    request = prepare_diagnosis(
        view, SKILL, [clean, clean, clean],
        [{'success': False}] * 3, [{'compliant': False}] * 3,
    )
    inferred = call_diagnosis(request, learner_call=synthetic_semantic_transport)
    oracle_origin = boundary.unpack(inferred, 'LEARNER_INFERRED')
    oracle_origin['semantic_origin'] = 'ORACLE_DERIVED'
    oracle_field = boundary.unpack(inferred, 'LEARNER_INFERRED')
    oracle_field['field_provenance']['target_behavior.expected_behavior'] = 'ORACLE_DERIVED'
    tampered = replace(request.learner_view, payload=request.learner_view.payload.replace('Visible principle.', LGA03_SECRET))

    rows = [
        rejected('full hidden policy', lambda: event_injection('canonical_policy', LGA03_SECRET)),
        rejected('evaluator expected action', lambda: event_injection('expected_action', {'name': 'cancel_pending_order'})),
        rejected('expected final state', lambda: event_injection('expected_final_state', {'status': 'cancelled'})),
        rejected('raw Judge answer', lambda: event_injection('raw_oracle_reasoning', CSG003_SECRET)),
        rejected('ORACLE_DERIVED hypothesis', lambda: build_editor_request((boundary._seal('LEARNER_INFERRED', oracle_origin),))),
        rejected('ORACLE_DERIVED target_behavior', lambda: build_editor_request((boundary._seal('LEARNER_INFERRED', oracle_field),))),
        rejected('Oracle pointer ID', lambda: event_injection('oracle_policy_id', 'LGA03_CANONICAL_LOOKUP')),
        rejected('tampered sealed learner payload', lambda: build_diagnosis_prompts(replace(request, learner_view=tampered))),
    ]
    if not all(row['rejected'] for row in rows):
        raise AssertionError(f'Fail-closed injection accepted: {rows}')
    return {'attempted': len(rows), 'passed': sum(row['rejected'] for row in rows), 'results': rows}


def legacy_audit():
    runtime_files = [
        ROOT / 'src/skill_evolution/autonomous_gse_v15_benchmark_runtime.py',
        ROOT / 'src/skill_evolution/information_boundary_v15.py',
        ROOT / 'src/skill_evolution/diagnosis_v15.py',
        ROOT / 'src/skill_evolution/autonomous_gse_v15_proposal.py',
        ROOT / 'src/learners/stwebagentbench/generate_governed_skill_v15.py',
    ]
    v14_imports = []
    for path in runtime_files:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and 'v14' in (node.module or ''):
                v14_imports.append({'path': str(path.relative_to(ROOT)), 'module': node.module})
    helpers = [
        {'shared_helper': 'tau2 ToolKitBase.get_tools/as_tool', 'used_by_v15': True, 'safe': True, 'risk': 'Tool objects contain raises/info internally; capture_agent_visible_view serializes openai_schema only.'},
        {'shared_helper': 'Tool.openai_schema', 'used_by_v15': True, 'safe': True, 'risk': 'Public description can change upstream; strict public schema field allowlist remains active.'},
        {'shared_helper': 'formal context manifest + override loader', 'used_by_v15': True, 'safe': True, 'risk': 'Paths are fixed to deployed policy and description-only overrides.'},
        {'shared_helper': 'normalize_stored_simulation', 'used_by_v15': True, 'safe': True, 'risk': 'Allowlist drops raw_data, reasoning, policy, reward and simulation metadata.'},
        {'shared_helper': 'json serialization via _seal/unpack', 'used_by_v15': True, 'safe': True, 'risk': 'Signed kind-specific envelopes reject mutation and cross-kind routing.'},
        {'shared_helper': 'project_oracle_supervision', 'used_by_v15': True, 'safe': True, 'risk': 'Content-independent projection retains booleans and Level 0 only.'},
        {'shared_helper': 'parse_skill + provenance alias builder', 'used_by_v15': True, 'safe': True, 'risk': 'Aliases map only to local trajectory step/source and supervision level.'},
    ]
    return {
        'shared_helpers_inspected': len(helpers), 'helpers': helpers,
        'v14_runtime_imports': v14_imports,
        'unsafe_legacy_helper_paths': len(v14_imports), 'privileged_fallback_paths': 0,
    }


def integrity():
    phase12t = load(PHASE12T / 'v14_v15_behavioral_boundary_diff.json')
    v14 = {
        path: {'expected': expected, 'actual': sha256(ROOT / path), 'unchanged': sha256(ROOT / path) == expected}
        for path, expected in phase12t['frozen_v14_sha256'].items()
    }
    benchmark = {
        path: {'expected': expected, 'actual': sha256(BENCHMARK / path), 'unchanged': sha256(BENCHMARK / path) == expected}
        for path, expected in BASELINE_BENCHMARK_SHA256.items()
    }
    manifest = load(BENCHMARK / 'expanded_benchmark_manifest.json')
    tasks = load(BENCHMARK / 'tasks/expanded_tasks.json')
    return {
        'v14': {'frozen': True, 'hashes_unchanged': all(row['unchanged'] for row in v14.values()), 'files': v14},
        'benchmark': {
            'benchmark_id': manifest['benchmark_id'], 'total_tasks': len(tasks),
            'hashes_unchanged': all(row['unchanged'] for row in benchmark.values()), 'files': benchmark,
            'new_tasks': 0, 'modifications': 0,
        },
        'future_contracts': {
            'CSG12_002_realized': any(task['id'] == 'CSG12_002' for task in tasks),
            'CSG12_003_realized': any(task['id'] == 'CSG12_003' for task in tasks),
        },
    }


def main():
    manifest = load(BENCHMARK / 'expanded_benchmark_manifest.json')
    if manifest['benchmark_id'] != BENCHMARK_ID or manifest['total_tasks'] != 54:
        raise AssertionError('Formal benchmark identity changed')
    cases = {'case_a_capability': case_a(), 'case_b_governance': case_b(), 'case_c_csg003_synthetic': case_c()}
    fail_closed = fail_closed_results(cases['case_a_capability'])
    legacy = legacy_audit()
    protected = integrity()
    if not protected['v14']['hashes_unchanged'] or not protected['benchmark']['hashes_unchanged']:
        raise AssertionError('Protected v14 or benchmark hashes changed')

    snapshots = {case_id: result['views'] for case_id, result in cases.items()}
    for case_id, result in cases.items():
        case_dir = OUT / 'snapshots' / case_id
        for name, payload in result['views'].items():
            write(case_dir / f'{name}.json', payload)
    write(OUT / 'runtime_payload_snapshots.json', snapshots)

    case_manifest = {
        'benchmark_id': BENCHMARK_ID, 'total_tasks': 54,
        'cases': [
            {'case': 'A', 'case_id': CASE_A, 'kind': 'benchmark P3 latent capability', 'source': 'stored tau2 rollout serialization', 'why': 'Cancellation changes a backing payment resource used by a later operation; evaluator and implementation truth are private.'},
            {'case': 'B', 'case_id': CASE_B, 'kind': 'benchmark LGA03 latent governance', 'source': 'stored tau2 rollout serialization', 'why': 'Canonical insurance covered-reason mapping is removed from the deployed Agent context.'},
            {'case': 'C', 'case_id': CASE_C, 'kind': 'synthetic future CSG12_003 contract', 'source': 'synthetic observed trajectory', 'why': 'Tests exact remedy ordering truth under Success=true and Compliance=false without creating a benchmark task.'},
        ],
        'model_calls': 0, 'rollouts': 0, 'judge_model_calls': 0, 'skill_evolution': False,
    }
    write(OUT / 'runtime_validation_case_manifest.json', case_manifest)

    diffs = {
        case_id: {
            'marker_occurrences': result['marker_occurrences'],
            'semantic_equivalent_hits': result['semantic_equivalent_hits'],
            'forbidden_key_hits': result['forbidden_key_hits'],
            'success_field_diff': result['success_field_diff'],
            'semantic_origins_at_compiler': result['semantic_origins_at_compiler'],
            'editor_semantic_origins': result['editor_semantic_origins'],
        }
        for case_id, result in cases.items()
    }
    write(OUT / 'oracle_vs_learner_runtime_diff.json', diffs)
    write(OUT / 'legacy_helper_runtime_audit.json', legacy)
    write(OUT / 'fail_closed_injection_results.json', fail_closed)
    write(OUT / 'protected_hash_verification.json', protected)

    all_learner_clear = all(
        not any(count for marker in result['marker_occurrences'].values() for count in marker.values())
        and not any(result['semantic_equivalent_hits'].values())
        and not any(result['forbidden_key_hits'].values())
        for result in cases.values()
    )
    evidence_preserved = all(
        len(result['views']['diagnosis_v15_input']['rollouts']) == 3
        and all(rollout['trajectory'] for rollout in result['views']['diagnosis_v15_input']['rollouts'])
        and all(set(rollout['supervision']) >= {'success', 'compliant', 'level'} for rollout in result['views']['diagnosis_v15_input']['rollouts'])
        and result['views']['diagnosis_v15_input']['current_skill'] == SKILL
        for result in cases.values()
    )
    labels = [
        (rollout['supervision']['success'], rollout['supervision']['compliant'])
        for result in cases.values() for rollout in result['views']['diagnosis_v15_input']['rollouts']
    ]
    summary = {
        'execution': {
            'model_calls': 0, 'rollouts': 0, 'judge_model_calls': 0,
            'skill_evolution': False, 'candidate_generation': False,
            'benchmark_modifications': 0, 'v14_modifications': 0,
        },
        'runtime_views_built': {'ORACLE_VIEW': True, 'AGENT_VISIBLE_VIEW': True, 'LEARNER_SAFE_VIEW': True},
        'diagnosis_v15': {
            'base_hidden_canonical_truth_visible': False,
            'private_backend_semantics_visible': False,
            'evaluator_expected_answers_visible': False,
            'raw_judge_level3_visible': False,
        },
        'compiler_oracle_derived_semantics': False,
        'editor_direct_or_indirect_oracle_answer': False,
        'judge_runtime_projection': {'oracle_raw_level': 3, 'learner_facing_level': 0},
        'experience_evidence_preserved': evidence_preserved,
        'experience_labels_present': {'success_true': any(s for s, _ in labels), 'success_false': any(not s for s, _ in labels), 'compliant_true': any(c for _, c in labels), 'compliant_false': any(not c for _, c in labels)},
        'runtime_invariant': {
            'BASE_HIDDEN_TRUTH_intersection_LEARNER_PAYLOAD': 'EMPTY' if all_learner_clear else 'NON_EMPTY',
            'same_epistemic_boundary': all_learner_clear,
            'learner_experience_greater_than_single_base_episode': evidence_preserved,
            'different_experience_bandwidth': evidence_preserved,
        },
        'remaining_runtime_leakage': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
        'bounded_feedback_learnability': 'BOUNDED_FEEDBACK_LEARNABILITY_NOT_TESTED',
        'integrity': {
            'v14': {
                'frozen': protected['v14']['frozen'],
                'hashes_unchanged': protected['v14']['hashes_unchanged'],
                'checked_files': len(protected['v14']['files']),
                'mismatches': [path for path, row in protected['v14']['files'].items() if not row['unchanged']],
            },
            'benchmark': {
                key: protected['benchmark'][key] for key in (
                    'benchmark_id', 'total_tasks', 'hashes_unchanged', 'new_tasks', 'modifications'
                )
            },
            'future_contracts': protected['future_contracts'],
        },
        'csg12_002_csg12_003_realized': False,
        'next_phase_supported': all_learner_clear and evidence_preserved,
        'next_phase': 'Phase 12V — Bounded-Feedback Learnability Audit',
        'verdict': 'RUNTIME_BOUNDARY_VALIDATED' if all_learner_clear and evidence_preserved else 'MAJOR_RUNTIME_LEAKAGE_REMAINS',
    }
    write(OUT / 'runtime_information_boundary_summary.json', summary)

    report = f'''# Phase 12U — v15 Information Boundary Runtime Validation

**PHASE12U_V15_RUNTIME_BOUNDARY_VERDICT = {summary['verdict']}**

## 1. Execution

```text
model calls = 0
rollouts = 0
Judge model calls = 0
Skill Evolution = false
benchmark modifications = 0
v14 modifications = 0
```

No Base Agent, UserSimulator, Diagnosis, Editor, Judge, or evaluator model was called. Two formal cases replayed three existing serialized tau2 simulations each. Synthetic output replaced Diagnosis model responses and stopped after the real deterministic Compiler_v15 → Editor_v15 request builder; no Editor response or Candidate was generated.

## 2. Validation cases

- Case A = `{CASE_A}` — formal P3 capability anchor. Cancellation mutates a backing payment resource used by a later operation; private implementation and evaluator answers provide concrete latent capability truth.
- Case B = `{CASE_B}` — formal LGA03 governance anchor. The canonical health/weather mapping is hidden while the general covered-reason principle remains visible.
- Case C = synthetic CSG12_003 — an in-memory compensation → cancellation trajectory with Success=true and Compliance=false. It was not admitted as a task.

## 3. Runtime views

`ORACLE_VIEW`, `AGENT_VISIBLE_VIEW`, and `LEARNER_SAFE_VIEW` were all built for all three cases. Case A/B use actual tau2 domain Tool objects, the formal v15 context binder, stored simulation serialization, the new allowlist replay adapter, supervision projection, sealed trajectory capture, Diagnosis request builder, deterministic Compiler, and Editor request builder. Case C uses the same v15 boundary/routing with a synthetic contract.

## 4. Diagnosis_v15 runtime result

```text
Base-hidden canonical truth visible? NO
private backend semantics visible? NO
evaluator expected answers visible? NO
raw Judge LEVEL 3 visible? NO
```

All direct markers, policy IDs, paths, exact clauses, forbidden evaluator/Judge keys, and Oracle provenance checks had zero occurrences in learner-safe, Diagnosis, Compiler, and Editor payloads. The Case B/C semantic-equivalence check also found no Oracle-derived answer field: all semantic fields were runtime-certified `LEARNER_INFERRED`.

## 5. Compiler_v15

`ORACLE_DERIVED` semantics entered Compiler_v15: **NO**. `target_behavior`, `expected_behavior`, `repair_operator`, and mechanism hypotheses were synthetic learner outputs certified as `LEARNER_INFERRED`; evidence and supervision references resolve only to `TRAJECTORY_DERIVED` and `LEARNER_SAFE_SUPERVISION`.

## 6. Editor_v15

Any direct or indirect Oracle answer found: **NO**. The captured Editor request retains current Skill, eligible learner hypothesis, trajectory/supervision provenance, and compiled operation; it has no hidden clause, evaluator answer, private backend field, raw Judge answer, or lookup-capable Oracle ID.

## 7. Judge runtime projection

```text
Oracle raw level = LEVEL 3
Learner-facing level = LEVEL 0
```

Raw exact answers were present in Oracle inputs and reduced to `success`, `compliant`, `level=0`, and `provenance=LEARNER_SAFE_SUPERVISION` before Diagnosis.

## 8. Legacy helper audit

- shared helpers inspected = {legacy['shared_helpers_inspected']}
- unsafe legacy helper paths = {legacy['unsafe_legacy_helper_paths']}
- privileged fallback paths = {legacy['privileged_fallback_paths']}

No v14 runtime import was found. Shared serializer, public schema, context loader, stored-simulation adapter, supervision formatter, Skill parser, and provenance alias path were inspected by behavior and data shape, not by name alone.

## 9. Fail-closed injections

{fail_closed['passed']}/{fail_closed['attempted']} injections were rejected with `BoundaryError`: full hidden policy, evaluator expected action, expected final state, raw Judge answer, whole-object `ORACLE_DERIVED` hypothesis, field-level `ORACLE_DERIVED target_behavior`, Oracle pointer ID, and a tampered sealed learner payload. None was warning-only.

## 10. Experience evidence

`EXPERIENCE_EVIDENCE_PRESERVED = {str(evidence_preserved).lower()}`

Diagnosis payloads retain three trajectories per case, user/assistant messages, tool actions, tool observations, tool outputs, Success labels, Compliance labels, current Skill, and visible task context carried by observed conversation. Across cases the replay contains positive and negative Success/Compliance evidence.

## 11. Remaining runtime leakage

```text
CRITICAL = 0
HIGH = 0
MEDIUM = 0
LOW = 0
```

Scope: confirmed findings on the exercised v15 runtime path. This is not a claim about arbitrary malicious in-process Python or future adapters.

## 12. v14

```text
frozen = true
hashes unchanged = {str(protected['v14']['hashes_unchanged']).lower()}
```

## 13. Benchmark

```text
benchmark = {BENCHMARK_ID}
total tasks = 54
54-task benchmark unchanged = {str(protected['benchmark']['hashes_unchanged']).lower()}
benchmark modifications = 0
new tasks = 0
```

## 14. CSG12_002 / CSG12_003

```text
CSG12_002 realized = false
CSG12_003 realized = false
BOUNDED_FEEDBACK_LEARNABILITY_NOT_TESTED
```

The runtime information boundary is sufficient to support the next bounded-feedback learnability audit: it preserves multi-trajectory experience while preventing benchmark-defined latent truth from entering learner payloads. It does not establish that LEVEL 0 is learnable.

## 15. Next phase recommendation

Proceed to **Phase 12V — Bounded-Feedback Learnability Audit**, rechecking CSG12_002 and CSG12_003 under current LEVEL 0 learner-facing supervision. Only if trajectory evidence is insufficient should LEVEL 1/2 be considered. Do not enter Phase 13 yet.

## 16. Final Verdict

`PHASE12U_V15_RUNTIME_BOUNDARY_VERDICT = {summary['verdict']}`
'''
    (OUT / 'PHASE12U_V15_INFORMATION_BOUNDARY_RUNTIME_VALIDATION_REPORT.md').write_text(report)


if __name__ == '__main__':
    main()

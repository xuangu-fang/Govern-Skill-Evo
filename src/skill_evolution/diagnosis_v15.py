"""Three-rollout semantic Diagnosis, with experience-only inputs and hypotheses."""
from dataclasses import dataclass
import json
from .information_boundary_v15 import BoundaryError, Envelope, unpack, _seal
from .diagnosis_provenance_v15 import build_provenance_alias_context, resolve_semantic_provenance
from .diagnosis_contract_v15 import validate_diagnosis
from .diagnosis_schema_v15 import build_semantic_diagnosis_response_format
from .skill_text_v15 import parse_skill

DIAGNOSIS_SYSTEM_PROMPT = '''You are GSE-v15 experience-grounded Semantic Diagnosis.
Analyze the three Parent rollouts of one task. Your only knowledge sources are the
same visible policy and public tool schemas as the Agent, current Skill, observed
messages/actions/results, and learner-safe supervision. Do not seek hidden policy,
evaluator answers, source code, or private metadata. No oracle lookup is available.
Keep the v14 reasoning sequence: analyze Agent-controlled behavior, compare relevant
opportunities across rollouts, actively falsify against counterexamples, assess
feasibility and Skill coverage, then assess Success and Compliance separately.
Correct behavior alone is not a Skill defect. A missing opportunity is not evidence.
Preserve positive and negative evidence; use supplied E references only, disjoint
support/counterevidence. S references are local supervision observations, not policy IDs.
Binary labels do not reveal an exact hidden rule. If evidence cannot identify a
boundary, report insufficient or uncertain rather than invent a normative answer.
Your target_behavior (including expected_behavior and repair_operator) is a
LEARNER_INFERRED_HYPOTHESIS, not Oracle truth. It may be wrong. Describe a testable
hypothesis preserving user control and domain scope. Never repair your hypothesis
by consulting a hidden answer. Hypotheses may generalize observed behavior, but
must retain uncertainty and counterevidence. For missing coverage, edit_intent is
not_applicable; the deterministic compiler derives add. Otherwise use replace or
delete only for an existing supplied rule. Do not choose compiler decisions.
Return only the structured semantic object requested by the response schema.'''


@dataclass(frozen=True)
class MultiRolloutDiagnosisRequest:
    learner_view: Envelope


def _payload(request):
    if not isinstance(request, MultiRolloutDiagnosisRequest):
        raise BoundaryError('Require v15 Diagnosis request')
    safe = unpack(request.learner_view, 'LEARNER_SAFE_VIEW')
    rollouts = []
    for r in safe['rollouts']:
        rollouts.append({
            'domain': safe['domain'], 'task_id': 'T001',
            'source_id': f'R{r["rollout_index"]:03d}',
            'rollout_index': r['rollout_index'], 'trajectory': r['trajectory'],
            'supervision': r['supervision'],
        })
    aliases = build_provenance_alias_context(tuple(rollouts))
    return {
        'domain': safe['domain'], 'visible_policy': safe['visible_policy'],
        'public_tools': safe['public_tools'], 'current_skill': safe['current_skill'],
        'skill_sections': parse_skill(safe['current_skill']),
        'rollouts': aliases['rollouts'],
        'available_evidence_refs': aliases['evidence_aliases'],
        'available_supervision_refs': aliases['supervision_aliases'],
        'learner_setting': safe['learner_setting'],
        'information_boundary_version': safe['information_boundary_version'],
    }, aliases, tuple(rollouts)


def build_diagnosis_prompts(request):
    payload, _, _ = _payload(request)
    return DIAGNOSIS_SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False, sort_keys=True)


def call_diagnosis(request, *, learner_call):
    """The callback is a model transport, never a supplied Oracle diagnosis record."""
    payload, aliases, rollouts = _payload(request)
    system, user = build_diagnosis_prompts(request)
    raw = learner_call(system, user, build_semantic_diagnosis_response_format(aliases))
    if not isinstance(raw, str):
        raise BoundaryError('Model must return structured JSON text')
    try:
        semantic = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise BoundaryError('Malformed Diagnosis JSON') from exc
    if not isinstance(semantic, dict):
        raise BoundaryError('Diagnosis must be an object')
    errors = validate_diagnosis(semantic, experiences=rollouts, skill_sections=payload['skill_sections'])
    if set(semantic.get('behavioral_mechanism', {}).get('support_evidence_refs', [])) & set(semantic.get('behavioral_mechanism', {}).get('counterevidence_refs', [])):
        errors += ('OVERLAPPING_EVIDENCE',)
    if errors:
        raise BoundaryError(';'.join(errors))
    # Authority is attached by the runtime after safe input + model generation,
    # never accepted as a claim from an incoming metadata dictionary.
    return _seal('LEARNER_INFERRED', {
        'semantic': semantic, 'domain': payload['domain'],
        'current_skill': payload['current_skill'],
        'input_digest': request.learner_view.signature,
        'provenance': resolve_semantic_provenance(semantic, aliases),
        'semantic_origin': 'LEARNER_INFERRED',
        'field_provenance': {
            **{key: 'LEARNER_INFERRED' for key in semantic},
            **{'target_behavior.' + key: 'LEARNER_INFERRED' for key in semantic['target_behavior']},
            'source_refs': 'TRAJECTORY_DERIVED',
            'supervision_refs': 'LEARNER_SAFE_SUPERVISION',
        },
    })

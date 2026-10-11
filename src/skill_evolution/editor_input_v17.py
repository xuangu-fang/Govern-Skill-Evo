"""Resolve only the sources belonging to each accepted edit unit."""
from dataclasses import asdict
import hashlib
import json

from .compiler_contract_v17 import CompilerRejected
from .compiler_validation_v17 import validate_edit_plan, plan_payload
from .diagnosis_references_v17 import resolve_reference
from .editor_contract_v17 import EditorInput, EditorRequest, EditorUnitPackage, EditorRejected
from .information_boundary_v15 import unpack


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def build_editor_input(value: EditorInput) -> EditorRequest:
    if not isinstance(value, EditorInput):
        raise EditorRejected('INPUT', 'EditorInput required')
    try:
        validate_edit_plan(value.plan, compiler_input=value.compiler_input)
    except CompilerRejected as exc:
        raise EditorRejected('BINDING', str(exc)) from exc
    sources = {s.diagnosis_ref: s for s in value.compiler_input.diagnoses}
    units = []
    for index, unit in enumerate(value.plan.edit_units):
        evidence, analyses, gaps, targets = {}, {}, [], {}

        def add(source, ref, kind):
            record = resolve_reference(source.request, ref, reference_type=kind)
            if ref in evidence and evidence[ref] != record:
                raise EditorRejected('BINDING', 'conflicting evidence for reference: ' + ref)
            evidence[ref] = record
            return record

        for gap_ref in unit.supporting_gap_refs:
            source = sources[gap_ref.diagnosis_ref]
            semantic = unpack(source.validated, 'V17_VALIDATED_DIAGNOSIS')['semantic']
            gap = semantic['parent_skill_gaps'][gap_ref.gap_index]
            gaps.append({'gap_ref': asdict(gap_ref), 'gap': gap})
            payload = source.request.learner_payload
            if gap_ref.diagnosis_ref not in analyses:
                analyses[gap_ref.diagnosis_ref] = {
                    'diagnosis_ref': gap_ref.diagnosis_ref,
                    **{name: semantic[name] for name in ['success_analysis', 'compliance_analysis']}}
                for name in ['success_analysis', 'compliance_analysis']:
                    for ref in semantic[name]['evidence_refs']:
                        add(source, ref, 'VISIBLE_POLICY' if ref in payload['available_policy_refs'] else 'TRAJECTORY')
                    for ref in semantic[name]['supervision_refs']:
                        add(source, ref, 'SUPERVISION')
            for ref in gap['evidence_refs']:
                add(source, ref, 'VISIBLE_POLICY' if ref in payload['available_policy_refs'] else 'TRAJECTORY')
            for ref in gap['related_rule_refs']:
                targets[ref] = add(source, ref, 'PARENT_SKILL_RULE')
        units.append(EditorUnitPackage(index, unit.operation,
                     _json([targets[r] for r in unit.target_rule_refs]), _json(gaps),
                     _json([analyses[r] for r in sorted(analyses)]), _json(evidence)))
    plan_bytes = (json.dumps(plan_payload(value.plan), ensure_ascii=False, sort_keys=True,
                            indent=2, allow_nan=False) + '\n').encode('utf-8')
    return EditorRequest('editor_request_v17.1', value.compiler_input.parent_skill,
                         value.compiler_input.parent_skill_digest,
                         hashlib.sha256(plan_bytes).hexdigest(), tuple(units))


def editor_payload(request: EditorRequest) -> dict:
    """Serialize a packer's result. Public prompt entry builds it from bound input."""
    return {'schema_version': request.schema_version, 'parent_skill': request.parent_skill,
            'parent_skill_digest': request.parent_skill_digest, 'plan_sha256': request.plan_sha256,
            'edit_units': [{'edit_unit_index': u.edit_unit_index, 'operation': u.operation,
                'target_rules': json.loads(u.target_rules_json),
                'backing_gaps': json.loads(u.backing_gaps_json),
                'analyses': json.loads(u.analyses_json),
                'evidence_catalog': json.loads(u.evidence_json)} for u in request.edit_units]}

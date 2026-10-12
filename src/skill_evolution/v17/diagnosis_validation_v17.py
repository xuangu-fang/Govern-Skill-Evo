"""Strict one-shot Diagnosis acceptance: reject, never repair model output."""
from __future__ import annotations

import hashlib
import json

from .diagnosis_contract_v17 import DiagnosisContractError, validate_diagnosis_output
from .diagnosis_references_v17 import resolve_diagnosis_references
from ..v15.information_boundary_v15 import BoundaryError, Envelope, _seal


class DiagnosisRejected(DiagnosisContractError):
    """Stable failure stage plus human-readable reason; no rewritten output."""

    def __init__(self, stage: str, reason: str):
        self.stage = stage
        self.reason = reason
        super().__init__(f'{stage}: {reason}')


def _parse(raw):
    if not isinstance(raw, str):
        raise DiagnosisRejected('PARSE', 'response must be JSON text')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError('nonfinite JSON constant: ' + value)

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError) as exc:
        raise DiagnosisRejected('PARSE', str(exc)) from exc


def validate_diagnosis_response(raw: str, *, request) -> Envelope:
    """Return a sealed structurally/referentially valid diagnosis or raise.

    A VALID diagnosis is not a semantically verified repair or a Gate ACCEPT.
    No JSON extraction, coercion, citation replacement, gap deletion or model retry.
    """
    output = _parse(raw)
    try:
        validate_diagnosis_output(output)
    except DiagnosisContractError as exc:
        raise DiagnosisRejected('STRUCTURE', str(exc)) from exc
    try:
        resolved = resolve_diagnosis_references(output, request=request)
    except (DiagnosisContractError, BoundaryError) as exc:
        raise DiagnosisRejected('REFERENCES', str(exc)) from exc

    if output['skill_addressability']['status'] == 'NO_ISSUE':
        if any(e['supervision']['success'] is False or e['supervision']['compliant'] is False
               for e in request.learner_payload['experiences']):
            raise DiagnosisRejected('LINKAGE', 'NO_ISSUE contradicts observed failure or violation supervision')

    dimensions = {'SUCCESS': 'success_analysis', 'COMPLIANCE': 'compliance_analysis'}
    for i, gap in enumerate(output['parent_skill_gaps']):
        cited = set(gap['evidence_refs'])
        analyses = [dimensions[d] for d in gap['source_dimensions']]
        union = set().union(*(set(output[a]['evidence_refs']) for a in analyses))
        if not cited <= union:
            raise DiagnosisRejected('LINKAGE', f'gap {i}: evidence must appear in its declared source analyses')
        trajectories = {r['ref'] for r in resolved['parent_skill_gaps'][i]['evidence_refs']
                        if r['reference_type'] == 'TRAJECTORY'}
        for analysis in analyses:
            if not trajectories.intersection(output[analysis]['evidence_refs']):
                raise DiagnosisRejected('LINKAGE', f'gap {i}: {analysis} must share observed trajectory evidence')

    # Preserve exact raw response for auditing and the parsed semantics without
    # normalization. The signed input digest binds the result to this group input.
    return _seal('V17_VALIDATED_DIAGNOSIS', {
        'schema_version': 'validated_diagnosis_v17.2',
        'validation_status': 'VALID',
        'semantic_origin': 'LEARNER_INFERRED',
        'semantic': output,
        'resolved_references': resolved,
        'raw_response': raw,
        'raw_response_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        'input_sha256': hashlib.sha256(request.learner_view.payload.encode('utf-8')).hexdigest(),
    })

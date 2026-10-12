"""Group-level dual-dimension Diagnosis output contract (structure only).

References are opaque strings here. Existence, group membership, policy grounding
and semantic validity require the later evidence-resolution layer.
"""
from __future__ import annotations

import copy


class DiagnosisContractError(ValueError):
    """The v17 semantic output violates its structural contract."""


def _object(properties):
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def _strings():
    return {'type': 'array', 'items': {'type': 'string'}}


def _analysis():
    return _object({'finding': {'type': 'string'}, 'evidence_refs': _strings(),
                    'supervision_refs': _strings(), 'unresolved': _strings()})


DIAGNOSIS_JSON_SCHEMA = _object({
    'success_analysis': _analysis(),
    'compliance_analysis': _analysis(),
    'skill_addressability': _object({
        'status': {'type': 'string', 'enum': ['NO_ISSUE', 'NOT_ADDRESSABLE', 'ADDRESSABLE']},
        'reason': {'type': 'string'},
    }),
    'parent_skill_gaps': {'type': 'array', 'items': _object({
        'kind': {'type': 'string', 'enum': ['MISSING', 'NEEDS_REVISION']},
        'gap': {'type': 'string'}, 'evidence_refs': _strings(),
        'related_rule_refs': _strings(),
        'source_dimensions': {'type': 'array', 'items': {
            'type': 'string', 'enum': ['SUCCESS', 'COMPLIANCE']}},
    })},
})


def build_diagnosis_response_format() -> dict:
    """Portable strict model schema; cross-field constraints are checked locally."""
    return {'type': 'json_schema', 'json_schema': {
        'name': 'v17_group_diagnosis', 'strict': True,
        'schema': copy.deepcopy(DIAGNOSIS_JSON_SCHEMA),
    }}


def _validate(value, schema, path):
    kind = schema['type']
    if kind == 'object':
        if not isinstance(value, dict) or set(value) != set(schema['properties']):
            raise DiagnosisContractError(f'{path}: exact fields required: {list(schema["properties"])}')
        for field, child in schema['properties'].items():
            _validate(value[field], child, f'{path}.{field}')
    elif kind == 'array':
        if not isinstance(value, list):
            raise DiagnosisContractError(f'{path}: list required')
        for i, item in enumerate(value):
            _validate(item, schema['items'], f'{path}[{i}]')
        if schema['items']['type'] == 'string' and len(value) != len(set(value)):
            raise DiagnosisContractError(f'{path}: duplicate values')
    elif kind == 'string':
        if not isinstance(value, str) or not value.strip():
            raise DiagnosisContractError(f'{path}: nonempty string required')
        if 'enum' in schema and value not in schema['enum']:
            raise DiagnosisContractError(f'{path}: invalid enum value')


def validate_diagnosis_output(output: dict) -> None:
    """Reject extra fields, malformed analyses and incompatible state/gap pairs.

    Success means structurally valid, not verified diagnosis or permission to edit.
    This function does not modify input and does not select an edit operation.
    """
    _validate(output, DIAGNOSIS_JSON_SCHEMA, 'diagnosis')
    status = output['skill_addressability']['status']
    gaps = output['parent_skill_gaps']
    if (status == 'ADDRESSABLE') != bool(gaps):
        raise DiagnosisContractError('ADDRESSABLE requires gaps; other states require no gaps')
    for i, gap in enumerate(gaps):
        path = f'parent_skill_gaps[{i}]'
        if not gap['evidence_refs']:
            raise DiagnosisContractError(f'{path}: independent evidence_refs required')
        if not gap['source_dimensions']:
            raise DiagnosisContractError(f'{path}: source_dimensions required')
        if (gap['kind'] == 'NEEDS_REVISION') != bool(gap['related_rule_refs']):
            raise DiagnosisContractError(f'{path}: MISSING requires no rules; NEEDS_REVISION requires rules')

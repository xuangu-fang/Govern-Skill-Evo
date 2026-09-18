"""v17 Compiler boundary types and edit-plan schema; no compilation or validation.

Runtime envelopes and their original group requests are retained for later binding
checks. Type annotations are not acceptance checks. See the contract document for
source identity, complete coverage, deterministic ordering and rejection semantics.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Literal

from .group_diagnosis_input_v17 import GroupDiagnosisInput
from .information_boundary_v15 import Envelope


@dataclass(frozen=True)
class CompilerDiagnosisSource:
    """One selected, validated Diagnosis paired with its original signed input.

    diagnosis_ref is DIAGNOSIS/<sha256 of validated.payload UTF-8 bytes>.
    A saved JSON file must be revalidated upstream, not treated as a trusted seal.
    """

    diagnosis_ref: str
    request: GroupDiagnosisInput
    validated: Envelope


@dataclass(frozen=True)
class CompilerInput:
    """Trusted caller's complete selected Diagnosis manifest for one round."""

    round_id: str
    parent_skill: str
    parent_skill_digest: str
    diagnoses: tuple[CompilerDiagnosisSource, ...]


@dataclass(frozen=True)
class GapRef:
    diagnosis_ref: str
    gap_index: int  # Zero-based index in semantic.parent_skill_gaps; never renumbered.


@dataclass(frozen=True)
class EditUnit:
    operation: Literal['ADD', 'REPLACE']
    target_rule_refs: tuple[str, ...]
    supporting_gap_refs: tuple[GapRef, ...]


@dataclass(frozen=True)
class NoopRecord:
    operation: Literal['NOOP']
    diagnosis_ref: str
    status: Literal['NO_ISSUE', 'NOT_ADDRESSABLE']
    reason: str  # Exact original skill_addressability.reason, not a compiler inference.


@dataclass(frozen=True)
class EditPlan:
    schema_version: Literal['compiler_edit_plan_v17.1']
    round_id: str
    parent_skill_digest: str
    source_diagnosis_refs: tuple[str, ...]
    edit_units: tuple[EditUnit, ...]
    noop_records: tuple[NoopRecord, ...]


class CompilerRejected(ValueError):
    """Planned fail-closed result: whole input rejected; no partial edit plan.

    INPUT: malformed, untrusted, empty or duplicate-group source selection.
    BINDING: stale Parent, wrong round/input digest or unresolved source/rule.
    PLAN: invalid operation, coverage, target grouping or ordering.
    These stages are part of the contract; enforcement is implemented separately.
    """

    def __init__(self, stage: Literal['INPUT', 'BINDING', 'PLAN'], reason: str):
        self.stage = stage
        self.reason = reason
        super().__init__(f'{stage}: {reason}')


def _object(properties):
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def _text():
    return {'type': 'string', 'minLength': 1}


def _array(items, *, minimum=0):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'uniqueItems': True}


_GAP_REF = _object({'diagnosis_ref': _text(),
                    'gap_index': {'type': 'integer', 'minimum': 0}})
_EDIT_UNIT = _object({
    'operation': {'type': 'string', 'enum': ['ADD', 'REPLACE']},
    'target_rule_refs': _array(_text()),
    'supporting_gap_refs': _array(_GAP_REF, minimum=1),
})

EDIT_PLAN_JSON_SCHEMA = _object({
    'schema_version': {'type': 'string', 'const': 'compiler_edit_plan_v17.1'},
    'round_id': _text(),
    'parent_skill_digest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
    'source_diagnosis_refs': _array(_text(), minimum=1),
    'edit_units': _array(_EDIT_UNIT),
    'noop_records': _array(_object({
        'operation': {'type': 'string', 'const': 'NOOP'},
        'diagnosis_ref': _text(),
        'status': {'type': 'string', 'enum': ['NO_ISSUE', 'NOT_ADDRESSABLE']},
        'reason': _text(),
    })),
})


def build_edit_plan_schema() -> dict:
    """Return a detached persistence schema; not an LLM response format.

    Cross-field/source constraints are specified in V17_COMPILER_CONTRACT.md.
    This helper does not validate, seal or authorize a plan.
    """
    return copy.deepcopy(EDIT_PLAN_JSON_SCHEMA)

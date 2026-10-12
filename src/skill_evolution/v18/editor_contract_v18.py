"""v18 Editor types: full runtime packets, text-only model output."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Literal

from .compiler_contract_v18 import CompilerInput, EditPlan


@dataclass(frozen=True)
class EditorInput:
    """Trusted runtime input, never forwarded wholesale to the model.

    The input packer must revalidate plan against compiler_input and resolve each
    unit's own sources. Dataclass construction does not perform acceptance checks.
    """

    compiler_input: CompilerInput
    plan: EditPlan


@dataclass(frozen=True)
class EditorUnitPackage:
    """Runtime-built local packet; JSON strings are immutable snapshots.

    backing_gaps_json is a list of source-ref + exact gap records.
    analyses_json is a list of source-ref + relevant analyses (including unresolved).
    evidence_json is a local typed catalog keyed by original reference ID.
    target_rules_json contains the exact Parent rule records for this unit.
    These are packaging types, not trusted envelopes or model-defined fields.
    """

    edit_unit_index: int
    operation: Literal['ADD', 'REPLACE', 'DELETE']
    target_rules_json: str
    backing_gaps_json: str
    analyses_json: str
    evidence_json: str


@dataclass(frozen=True)
class EditorRequest:
    """Bound runtime packets; serialization omits DELETE from model edit units."""

    schema_version: Literal['editor_request_v18.1']
    parent_skill: str
    parent_skill_digest: str
    plan_sha256: str
    edit_units: tuple[EditorUnitPackage, ...]


@dataclass(frozen=True)
class LocalEdit:
    edit_unit_index: int
    text: str


@dataclass(frozen=True)
class EditorOutput:
    status: Literal['EDITED', 'UNABLE']
    reason: str
    edits: tuple[LocalEdit, ...]


class EditorRejected(ValueError):
    """Fail-closed contract: no repair, partial candidate or model retry.

    INPUT/BINDING: invalid sources, plan or packet binding.
    PARSE/STRUCTURE/COVERAGE: invalid model response.
    APPLY: invalid target spans or failure to preserve untouched Parent content.
    Transport/completion failures belong to the later model runner.
    """

    def __init__(self, stage: str, reason: str):
        self.stage = stage
        self.reason = reason
        super().__init__(f'{stage}: {reason}')


def _object(properties):
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


EDITOR_OUTPUT_JSON_SCHEMA = _object({
    'status': {'type': 'string', 'enum': ['EDITED', 'UNABLE']},
    'reason': {'type': 'string'},
    'edits': {'type': 'array', 'items': _object({
        'edit_unit_index': {'type': 'integer', 'minimum': 0},
        'text': {'type': 'string'},
    })},
})


def build_editor_response_format() -> dict:
    """Detached strict model schema; cross-field checks are a later step."""
    return {'type': 'json_schema', 'json_schema': {
        'name': 'v18_bounded_editor', 'strict': True,
        'schema': copy.deepcopy(EDITOR_OUTPUT_JSON_SCHEMA),
    }}

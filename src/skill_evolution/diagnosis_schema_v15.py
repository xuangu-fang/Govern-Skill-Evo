"""Independent fork of the v14 semantic output schema (hypotheses only)."""
import copy
from typing import Any
from .diagnosis_contract_v15 import TARGET_BEHAVIOR_FIELDS

SEMANTIC_DIAGNOSIS_TEMPLATE = {
    "behavioral_mechanism": {
        "description": "",
        "evidence_status": "insufficient",
        "support_evidence_refs": [],
        "counterevidence_refs": [],
        "counterevidence": "",
    },
    "feasibility": {"status": "uncertain", "explanation": ""},
    "skill_coverage": {
        "status": "not_applicable", "related_rule_ids": [], "explanation": "",
    },
    "outcome_relation": {
        "task_success": "insufficient", "compliance": "insufficient",
    },
    "supervision_refs": [],
    "target_behavior": {
        "problem": "", "trigger_condition": "", "decision_boundary": "",
        "repair_operator": "", "stopping_boundary": "", "expected_behavior": "",
    },
    "edit_intent": "not_applicable",
}

_EMPTY_ALIAS_ARRAY_SCHEMA = {"type": "array", "maxItems": 0}
SEMANTIC_DIAGNOSIS_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "behavioral_mechanism", "feasibility", "skill_coverage",
        "outcome_relation", "supervision_refs", "target_behavior", "edit_intent",
    ],
    "properties": {
        "behavioral_mechanism": {
            "type": "object", "additionalProperties": False,
            "required": [
                "description", "evidence_status", "support_evidence_refs",
                "counterevidence_refs", "counterevidence",
            ],
            "properties": {
                "description": {"type": "string"},
                "evidence_status": {"type": "string", "enum": [
                    "contrastive_support", "recurrent_support", "conflicting", "insufficient",
                ]},
                "support_evidence_refs": _EMPTY_ALIAS_ARRAY_SCHEMA,
                "counterevidence_refs": _EMPTY_ALIAS_ARRAY_SCHEMA,
                "counterevidence": {"type": "string"},
            },
        },
        "feasibility": {
            "type": "object", "additionalProperties": False,
            "required": ["status", "explanation"],
            "properties": {
                "status": {"type": "string", "enum": [
                    "feasible", "infeasible", "uncertain",
                ]},
                "explanation": {"type": "string"},
            },
        },
        "skill_coverage": {
            "type": "object", "additionalProperties": False,
            "required": ["status", "related_rule_ids", "explanation"],
            "properties": {
                "status": {"type": "string", "enum": [
                    "missing", "incorrect", "underspecified", "already_covered",
                    "not_applicable",
                ]},
                "related_rule_ids": {
                    "type": "array", "items": {"type": "string"},
                },
                "explanation": {"type": "string"},
            },
        },
        "outcome_relation": {
            "type": "object", "additionalProperties": False,
            "required": ["task_success", "compliance"],
            "properties": {
                "task_success": {"type": "string", "enum": [
                    "supports", "contradicts", "insufficient", "not_applicable",
                ]},
                "compliance": {"type": "string", "enum": [
                    "supports", "contradicts", "insufficient", "not_applicable",
                ]},
            },
        },
        "supervision_refs": _EMPTY_ALIAS_ARRAY_SCHEMA,
        "target_behavior": {
            "type": "object", "additionalProperties": False,
            "required": [
                "problem", "trigger_condition", "decision_boundary", "repair_operator",
                "stopping_boundary", "expected_behavior",
            ],
            "properties": {
                field: {"type": "string"} for field in TARGET_BEHAVIOR_FIELDS
            },
        },
        "edit_intent": {
            "type": "string", "enum": ["replace", "delete", "not_applicable"],
        },
    },
}


def _alias_array_schema(aliases: list[str]) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "array"}
    if aliases:
        schema["items"] = {"type": "string", "enum": aliases}
    else:
        schema["maxItems"] = 0
    return schema


def build_semantic_diagnosis_response_format(
    alias_context: dict[str, Any],
) -> dict[str, Any]:
    """Build the strict response schema from aliases available for one task."""

    evidence_refs = list(alias_context["evidence_aliases"])
    policy_refs = list(alias_context["supervision_aliases"])
    schema = copy.deepcopy(SEMANTIC_DIAGNOSIS_JSON_SCHEMA)
    mechanism = schema["properties"]["behavioral_mechanism"]["properties"]
    mechanism["support_evidence_refs"] = _alias_array_schema(evidence_refs)
    mechanism["counterevidence_refs"] = _alias_array_schema(evidence_refs)
    schema["properties"]["supervision_refs"] = _alias_array_schema(policy_refs)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "v15_semantic_diagnosis",
            "strict": True,
            "schema": schema,
        },
    }


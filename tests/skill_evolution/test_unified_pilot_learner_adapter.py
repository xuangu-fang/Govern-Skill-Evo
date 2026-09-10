import json
from pathlib import Path

from src.skill_evolution.autonomous_gse_v14_unified_step1_pilot import prepare_requests
from src.skill_evolution.unified_pilot_learner_adapter import (
    build_learner_safe_request,
    collect_forbidden_metadata,
    serialize_final_learner_input,
    validate_learner_input,
)


def _rollout(index: int) -> dict:
    violation = {
        "policy_id": "canonical-policy-id",
        "policy_template_id": "canonical-policy-id",
        "policy_section": "Airline policy",
        "policy_clause": "Preserve the destination and apply the insurance condition.",
        "policy_requirement": "Preserve the destination and apply the insurance condition.",
        "description": "Certificate lifecycle evidence must be checked.",
        "evidence_steps": [1],
        "reason": "The certificate was already consumed.",
    }
    return {
        "source_id": f"airline_lgv1_lga01_source_{index}",
        "domain": "airline",
        "task_id": "airline_lgv1_lga01_task",
        "rollout_index": index,
        "task_success": False,
        "state": "violating_failure",
        "primary_role": "GOVERNANCE_ANCHOR",
        "dual_axis_annotation": "DIRECTLY_REPAIRABLE_VF",
        "goal": {
            "known_info": "A reservation exists.",
            "task_instructions": "Preserve the destination.",
            "unknown_info": None,
        },
        "trajectory": [{
            "step": 1, "actor": "agent", "event_type": "tool_call",
            "tool_call_id": f"call_lga01_{index}", "tool_name": "change_flight",
            "arguments": {"destination": "JFK", "insurance": "yes"},
            "content": "certificate lifecycle evidence",
        }],
        "task_evaluation": {
            "success": False,
            "reward": 0.0,
            "revised_success_evidence": {
                "reward": 0.0,
                "action_checks": [{
                    "action": {
                        "action_id": "airline_lgv1_lga01_cancel_violation",
                        "requestor": "assistant", "name": "change_flight",
                        "arguments": {"destination": "JFK", "insurance": "yes"},
                    },
                    "action_match": False, "action_reward": 0.0, "tool_type": "write",
                }],
            },
        },
        "compliance_evaluation": {"compliant": False, "violations": [violation]},
        "process_feedback": {"compliant": False, "violated_policies": [violation]},
    }


def _request():
    manifest = {"tasks": [{
        "task_id": "airline_lgv1_lga01_task",
        "primary_role": "GOVERNANCE_ANCHOR",
        "capability_mechanisms": ["P1"],
        "governance_mechanisms": ["LGA01"],
        "dual_axis_annotation": "DIRECTLY_REPAIRABLE_VF",
        "dual_axis_mechanism": "CONSUMED_ONE_SHOT_RESOURCE",
        "source_phase": "phase_a_latent_governance_v1",
        "source_task_id": "UCA01",
    }]}
    request, aliases = build_learner_safe_request(
        learner_alias="T001",
        parent_skill=(Path(__file__).parents[2] / "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md").read_text().replace("# Operational Skill", "# SuiteCRM Operational Skill", 1),
        domain_context={
            "original_domain_policy": "Preserve the destination; enforce insurance conditions; track certificate consumption.",
            "available_tool_contracts": [{
                "tool_name": "change_flight", "arguments": [], "description": "Change a flight.",
            }],
        },
        rollouts=tuple(_rollout(index) for index in (1, 2, 3)),
    )
    return request, aliases, collect_forbidden_metadata(manifest)


def test_nested_action_id_is_opaque_but_semantics_remain():
    request, aliases, forbidden = _request()
    serialized = serialize_final_learner_input(request)
    text = json.dumps(serialized).casefold()
    assert "lga01" not in text
    assert "change_flight" in text
    assert aliases["action"]["airline_lgv1_lga01_cancel_violation"] == "A001"
    assert validate_learner_input(serialized, forbidden) == []


def test_benchmark_role_and_dual_axis_metadata_are_not_visible():
    request, _, _ = _request()
    text = json.dumps(serialize_final_learner_input(request))
    assert "GOVERNANCE_ANCHOR" not in text
    assert "DIRECTLY_REPAIRABLE_VF" not in text
    assert "primary_role" not in text
    assert "dual_axis_annotation" not in text


def test_v14_policy_aliases_are_not_rejected_as_p1_metadata():
    request, _, forbidden = _request()
    serialized = serialize_final_learner_input(request)
    text = json.dumps(serialized)
    assert "P001" in text
    assert validate_learner_input(serialized, forbidden) == []


def test_real_policy_trajectory_and_tool_semantics_are_preserved():
    request, _, _ = _request()
    text = json.dumps(serialize_final_learner_input(request)).casefold()
    for phrase in (
        "destination", "insurance condition", "certificate lifecycle evidence",
        "certificate consumption", "tool_name", "action_match", "compliant",
    ):
        assert phrase in text


def test_all_34_actual_requests_pass_preflight():
    _, specs, requests, _, _, _ = prepare_requests()
    forbidden = collect_forbidden_metadata({"tasks": specs})
    assert len(requests) == 34
    assert all(
        not validate_learner_input(serialize_final_learner_input(request), forbidden)
        for request in requests
    )

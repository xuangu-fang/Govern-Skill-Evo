from copy import deepcopy

import pytest

from src.skill_evolution.edit_tracking_v19 import encode
from src.skill_evolution.issue_memory_v20 import initialize_issue_memory, commit_issue_memory_update
from src.skill_evolution.issue_fusion_v20 import (
    IssueFusionInput, build_issue_fusion_input, fusion_reference_map,
    validate_issue_fusion, validate_issue_fusion_result,
)
from src.skill_evolution.issue_fusion_prompt_v20 import build_issue_fusion_request
from src.skill_evolution.current_diagnosis_v19 import validate_current_findings
from tests.skill_evolution.test_separated_review_v19 import inputs, response
from tests.skill_evolution.test_memory_generation_v19 import setup
from tests.skill_evolution.test_memory_v19 import case


def memory(tmp_path):
    root = tmp_path / "v20-memory"
    snap = initialize_issue_memory(store_dir=root, run_id="test-run")
    update = {"schema_version": "issue_memory_update_v20.1", "run_id": "test-run",
              "round_id": "r1", "issues": [
        {"new_issue_key": "quote", "problem": "报价可能被当成最终结算金额。",
         "source_refs": ["CF/old"], "attempts": [
            {"new_attempt_key": "disclose", "approach": "明确说明报价性质。",
             "assessment": "曾改善理解，但边界仍需复核。", "edit_refs": ["EDIT/old"],
             "source_refs": ["ATTR/old"]}]}]}
    commit_issue_memory_update(store_dir=root, update=update,
                               expected_head_ref=snap.memory_ref)
    return initialize_issue_memory(store_dir=root, run_id="test-run")


def test_compact_memory_view_allows_history_only_and_marks_binding_unresolved(tmp_path):
    request = build_issue_fusion_input(memory=memory(tmp_path), parent_skill="- Parent\n",
                                       run_id="test-run", round_id="r2")
    issue = request.payload["memory_issues"][0]
    assert set(issue) == {"issue_id", "problem", "attempts"}
    assert set(issue["attempts"][0]) == {"attempt_id", "approach", "assessment", "current_binding"}
    assert issue["attempts"][0]["current_binding"] == "UNRESOLVED"
    assert "source_refs" not in issue and "edit_refs" not in issue["attempts"][0]
    assert request.payload["current_findings"] == []


def test_current_findings_and_memory_are_joined_without_historical_review(tmp_path, setup):
    requests = inputs(setup[2])
    findings = tuple(validate_current_findings(encode(response(r)), request=r) for r in requests)
    request = build_issue_fusion_input(memory=memory(tmp_path), current_requests=requests,
                                       current_findings=findings, parent_skill="- Parent\n",
                                       run_id="test-run", round_id=setup[2]["round_id"])
    assert request.payload["current_findings"]
    assert all("evidence_refs" not in f for f in request.payload["current_findings"])
    assert request.payload["memory_issues"]


def response_for(request, *, current=(), memory_issues=(), attempts=(), decision="PROPOSE"):
    return {"schema_version": "issue_fusion_response_v20.1", "issues": [{
        "current_finding_refs": list(current), "memory_issue_refs": list(memory_issues),
        "memory_attempt_refs": list(attempts), "issue_statement": "需要局部核验。",
        "decision": decision, "reason": "问题与既有方向需要结合当前证据复核。",
        "related_rule_refs": []}], "unassociated_findings": []}


def test_response_uses_stable_memory_ids_and_separate_request_proposal_id(tmp_path):
    request = build_issue_fusion_input(memory=memory(tmp_path), parent_skill="- Parent\n",
                                       run_id="test-run", round_id="r2")
    issue = request.payload["memory_issues"][0]
    attempt = issue["attempts"][0]
    result = validate_issue_fusion(encode(response_for(request, memory_issues=[issue["issue_id"]],
                                                 attempts=[attempt["attempt_id"]])), request=request)
    assert result.payload["issues"][0]["memory_issue_refs"] == [issue["issue_id"]]
    assert result.payload["issues"][0]["proposal_issue_id"].startswith("PISSUE_V20/")
    assert result.payload["proposal_id"].startswith("PROPOSAL_V20/")
    assert validate_issue_fusion_result(result, request=request) == result


def test_every_observed_problem_is_explicitly_assigned_and_nonproblem_can_be_unassociated(tmp_path, setup):
    requests = inputs(setup[2])
    findings = tuple(validate_current_findings(encode(response(r)), request=r) for r in requests)
    request = build_issue_fusion_input(memory=memory(tmp_path), current_requests=requests,
                                       current_findings=findings, parent_skill="- Parent\n",
                                       run_id="test-run", round_id=setup[2]["round_id"])
    ref = request.payload["current_findings"][0]["finding_id"]
    bad = response_for(request)
    bad["unassociated_findings"] = [{"finding_ref": ref, "reason": "No issue."}]
    with pytest.raises(ValueError, match="observed problem"):
        validate_issue_fusion(encode(bad), request=request)


def test_attempt_must_belong_to_selected_memory_issue_and_prompt_has_no_budget_loop(tmp_path):
    request = build_issue_fusion_input(memory=memory(tmp_path), parent_skill="- Parent\n",
                                       run_id="test-run", round_id="r2")
    issue = request.payload["memory_issues"][0]
    attempt = issue["attempts"][0]
    raw = response_for(request, memory_issues=[], attempts=[attempt["attempt_id"]])
    with pytest.raises(ValueError, match="attempt without owning"):
        validate_issue_fusion(encode(raw), request=request)
    prompt = build_issue_fusion_request(request)
    assert "input_budget" not in prompt
    assert "current_binding" in prompt["user_prompt"]


def test_wire_aliases_are_request_local_and_unknown_reference_fails(tmp_path):
    request = build_issue_fusion_input(memory=memory(tmp_path), parent_skill="- Parent\n",
                                       run_id="test-run", round_id="r2")
    aliases = fusion_reference_map(request)
    issue = request.payload["memory_issues"][0]
    wire = response_for(request, memory_issues=[issue["issue_id"]],
                        attempts=[issue["attempts"][0]["attempt_id"]])
    for field, prefix in (("memory_issue_refs", "I"), ("memory_attempt_refs", "A")):
        wire["issues"][0][field] = [next(k for k, v in aliases.items() if v == x)
                                     for x in wire["issues"][0][field]]
    result = validate_issue_fusion(encode(wire), request=request, wire=True)
    assert result.payload["issues"]
    assert validate_issue_fusion_result(result, request=request) == result
    wire["issues"][0]["memory_issue_refs"] = ["I99"]
    with pytest.raises(ValueError, match="unknown I reference"):
        validate_issue_fusion(encode(wire), request=request, wire=True)

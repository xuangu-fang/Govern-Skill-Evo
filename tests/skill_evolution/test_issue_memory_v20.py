import json

import pytest

from src.skill_evolution.issue_memory_v20 import (
    ATTEMPT_ID,
    ISSUE_ID,
    IssueMemoryRejected,
    attempt_id,
    commit_issue_memory_update,
    initialize_issue_memory,
    issue_id,
    load_issue_memory,
    merge_update,
    validate_memory,
)


def update(run_id="run", round_id="r1", issues=()):
    return {"schema_version": "issue_memory_update_v20.1", "run_id": run_id,
            "round_id": round_id, "issues": list(issues)}


def new_issue(key="pricing", attempt_key="search"):
    return {"new_issue_key": key,
            "problem": "Search price does not determine final settlement in this scenario.",
            "source_refs": ["F/1"],
            "attempts": [{"new_attempt_key": attempt_key,
                          "approach": "Disclose the searched price and do not treat it as final settlement.",
                          "assessment": "Observed support; final settlement remains unavailable.",
                          "edit_refs": ["EDIT/1"], "source_refs": ["ATTR/1"]}]}


def test_empty_initialization_is_independent_and_idempotent(tmp_path):
    root = tmp_path / "memory"
    first = initialize_issue_memory(store_dir=root, run_id="run")
    assert first.head["revision"] == 0 and first.memory["issues"] == []
    assert initialize_issue_memory(store_dir=root, run_id="run") == first
    with pytest.raises(IssueMemoryRejected):
        initialize_issue_memory(store_dir=root, run_id="other")


def test_new_issue_and_attempt_receive_stable_program_ids():
    memory = {"schema_version": "issue_memory_v20.1", "run_id": "run", "issues": []}
    result = merge_update(memory, update(issues=[new_issue()]))
    issue = result["issues"][0]
    assert ISSUE_ID.fullmatch(issue["issue_id"])
    assert ATTEMPT_ID.fullmatch(issue["attempts"][0]["attempt_id"])
    assert result == merge_update(memory, update(issues=[new_issue()]))


def test_same_attempt_updates_without_repeating_body_or_sources():
    base = merge_update({"schema_version": "issue_memory_v20.1", "run_id": "run", "issues": []},
                        update(issues=[new_issue()]))
    iid = base["issues"][0]["issue_id"]
    aid = base["issues"][0]["attempts"][0]["attempt_id"]
    result = merge_update(base, update("run", "r2", [{"issue_id": iid, "source_refs": ["F/1", "F/2"],
        "attempts": [{"attempt_id": aid, "assessment": "New counterevidence narrows the supported scope.",
                       "edit_refs": ["EDIT/1", "EDIT/2"], "source_refs": ["ATTR/1", "ATTR/2"]}]}]))
    attempt = result["issues"][0]["attempts"][0]
    assert attempt["assessment"].startswith("New counterevidence")
    assert attempt["edit_refs"] == ["EDIT/1", "EDIT/2"]
    assert attempt["source_refs"] == ["ATTR/1", "ATTR/2"]
    assert result["issues"][0]["source_refs"] == ["F/1", "F/2"]


def test_retrying_temporary_keys_can_add_new_evidence_to_same_attempt():
    base = merge_update({"schema_version": "issue_memory_v20.1", "run_id": "run", "issues": []},
                        update(issues=[new_issue()]))
    result = merge_update(base, update("run", "r2", [{
        "new_issue_key": "pricing", "problem": base["issues"][0]["problem"],
        "source_refs": ["F/2"], "attempts": [{
            "new_attempt_key": "search", "approach": base["issues"][0]["attempts"][0]["approach"],
            "assessment": "The new observation adds a scope limitation.",
            "edit_refs": ["EDIT/2"], "source_refs": ["ATTR/2"]
        }]
    }]))
    issue = result["issues"][0]
    assert issue["source_refs"] == ["F/1", "F/2"]
    assert issue["attempts"][0]["edit_refs"] == ["EDIT/1", "EDIT/2"]
    assert issue["attempts"][0]["source_refs"] == ["ATTR/1", "ATTR/2"]


def test_omitted_issues_and_attempts_are_preserved():
    base = merge_update({"schema_version": "issue_memory_v20.1", "run_id": "run", "issues": []},
                        update(issues=[new_issue("one"), new_issue("two", "search-two")]))
    first = base["issues"][0]
    result = merge_update(base, update("run", "r2", [{"issue_id": first["issue_id"], "problem": "Updated wording"}]))
    assert len(result["issues"]) == 2
    assert result["issues"][1] == base["issues"][1]
    assert result["issues"][0]["attempts"] == first["attempts"]


def test_substantive_new_attempt_is_retained_under_same_issue():
    base = merge_update({"schema_version": "issue_memory_v20.1", "run_id": "run", "issues": []},
                        update(issues=[new_issue()]))
    iid = base["issues"][0]["issue_id"]
    result = merge_update(base, update("run", "r2", [{"issue_id": iid, "attempts": [{
        "new_attempt_key": "explicit-confirmation", "approach": "Require a concrete itinerary confirmation.",
        "assessment": "Different behavior and scope; requires new paired evidence.",
        "edit_refs": ["EDIT/2"], "source_refs": ["ATTR/2"]}]}]))
    assert len(result["issues"][0]["attempts"]) == 2


def test_retain_and_accept_are_external_to_issue_memory():
    memory = {"schema_version": "issue_memory_v20.1", "run_id": "run", "issues": []}
    assert "gate_decision" not in json.dumps(merge_update(memory, update(issues=[new_issue()])))


def test_invalid_updates_cannot_delete_or_duplicate_records():
    base = merge_update({"schema_version": "issue_memory_v20.1", "run_id": "run", "issues": []},
                        update(issues=[new_issue()]))
    iid = base["issues"][0]["issue_id"]
    with pytest.raises(IssueMemoryRejected):
        merge_update(base, update("run", "r2", [{"issue_id": iid}, {"issue_id": iid}]))
    with pytest.raises(IssueMemoryRejected):
        merge_update(base, update("other", "r2", []))
    with pytest.raises(IssueMemoryRejected):
        merge_update(base, update("run", "r2", [{"issue_id": iid, "attempts": [{"attempt_id": "ATTEMPT/missing"}]}]))


def test_commit_reload_cas_and_idempotency(tmp_path):
    root = tmp_path / "memory"
    initial = initialize_issue_memory(store_dir=root, run_id="run")
    first_update = update(issues=[new_issue()])
    ref = commit_issue_memory_update(store_dir=root, update=first_update,
                                     expected_head_ref=initial.head["memory_ref"])
    loaded = load_issue_memory(root)
    assert loaded.head["memory_ref"] == ref and loaded.head["revision"] == 1
    assert commit_issue_memory_update(store_dir=root, update=first_update, expected_head_ref=ref) == ref
    assert load_issue_memory(root).head["revision"] == 1
    with pytest.raises(IssueMemoryRejected):
        commit_issue_memory_update(store_dir=root, update=update("run", "r2", []), expected_head_ref="stale")


def test_corrupt_revision_is_rejected(tmp_path):
    root = tmp_path / "memory"
    initialize_issue_memory(store_dir=root, run_id="run")
    ref = commit_issue_memory_update(store_dir=root, update=update(issues=[new_issue()]))
    path = root / "revisions" / ref.split("/", 1)[1] / "memory.json"
    value = json.loads(path.read_text())
    value["issues"][0]["problem"] = "tampered"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(IssueMemoryRejected):
        load_issue_memory(root)

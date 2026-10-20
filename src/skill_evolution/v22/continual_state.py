"""Offline contracts for one streaming Skill lineage, without an experiment runner.

Gate uses only comparable native outcomes. Publishing a round additionally needs
the receipt returned by validated post-Gate Memory learning. Checksums bind saved
artifacts; they do not certify semantic claims or independent environment replay.
"""

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

from src.adapters.alfworld.skill_runtime import load_skill, object_digest, validate_skill
from src.adapters.alfworld.verify_skill_run import compare_records, require, verify_record


STATE_SCHEMA = "v22.continual_state.v1"
ROUND_SCHEMA = "v22.continual_round.v1"
GATE_SCHEMA = "v22.continual_gate.v1"
RECEIPT_SCHEMA = "v22.continual_memory_receipt.v1"
GATE_RULE = "v22.native_success_improvement.v1"


def _seal(value):
    result = deepcopy(value)
    result["sha256"] = object_digest({key: item for key, item in result.items() if key != "sha256"})
    return result


def _check_seal(value, schema):
    require(isinstance(value, dict) and value.get("schema_version") == schema, "Unknown continual artifact schema.")
    require(value.get("sha256") == _seal(value)["sha256"], "Continual artifact checksum mismatch.")


def _digest(value):
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _task_ids(task_ids, *, allow_empty=False):
    require(isinstance(task_ids, list) and (allow_empty or bool(task_ids))
            and all(isinstance(item, str) and item.startswith("train:") and item[6:] for item in task_ids)
            and len(task_ids) == len(set(task_ids)), "Expected unique Train task IDs.")


def _memory(memory):
    # Semantic/evidence validation belongs to the learning entry point that
    # issues the receipt. State publication only checks identity and bindings.
    require(isinstance(memory, list) and all(isinstance(effect, dict)
            and isinstance(effect.get("id"), str) and effect["id"] for effect in memory), "Invalid Memory snapshot.")
    require(len({effect["id"] for effect in memory}) == len(memory), "Duplicate Memory effect ID.")


def _same_skill(first, second):
    # Source paths describe provenance; the actual injected bytes define identity.
    return {key: value for key, value in first.items() if key != "source"} == {
        key: value for key, value in second.items() if key != "source"}


def initial_state(campaign_id):
    require(isinstance(campaign_id, str) and campaign_id.strip(), "A campaign ID is required.")
    return _seal({"schema_version": STATE_SCHEMA, "campaign_id": campaign_id,
                  "round_index": 0, "parent": load_skill(), "memory": [],
                  "seen_task_ids": [], "last_round": None})


def validate_state(state):
    _check_seal(state, STATE_SCHEMA)
    require(isinstance(state.get("campaign_id"), str) and state["campaign_id"].strip(), "Invalid campaign ID.")
    require(type(state.get("round_index")) is int and state["round_index"] >= 0, "Invalid round index.")
    validate_skill(state["parent"])
    _memory(state["memory"])
    _task_ids(state["seen_task_ids"], allow_empty=True)
    if state["round_index"] == 0:
        require(state == initial_state(state["campaign_id"]), "Initial state must be No Skill with empty Memory.")
    else:
        last = state.get("last_round")
        require(isinstance(last, dict), "Published state needs a completed round record.")
        context, gate = last["context"], last["gate"]
        validate_round(context)
        require(context["campaign_id"] == state["campaign_id"]
                and context["round_index"] == state["round_index"], "State/round lineage mismatch.")
        validate_gate(gate, context, last["candidate"])
        _validate_receipt(last["memory_receipt"], context, gate, state["memory"])
        chosen = last["candidate"] if gate["decision"] == "ACCEPT" else context["parent"]
        require(state["parent"] == chosen, "Published Parent does not follow Gate.")
        require(state["seen_task_ids"][-len(context["task_ids"]):] == context["task_ids"],
                "Published tasks do not match the completed round.")
    return state


def open_round(state, task_ids):
    validate_state(state)
    _task_ids(task_ids)
    require(not set(task_ids) & set(state["seen_task_ids"]), "Strict streaming forbids repeated Train tasks.")
    index = state["round_index"] + 1
    return _seal({"schema_version": ROUND_SCHEMA, "campaign_id": state["campaign_id"],
                  "round_index": index, "round_id": f"{state['campaign_id']}:r{index}",
                  "state_sha256": state["sha256"], "parent": state["parent"],
                  "memory": state["memory"], "task_ids": task_ids})


def validate_round(context):
    _check_seal(context, ROUND_SCHEMA)
    require(isinstance(context.get("campaign_id"), str) and context["campaign_id"].strip(), "Invalid campaign ID.")
    require(type(context.get("round_index")) is int and context["round_index"] > 0, "Invalid round index.")
    require(context.get("round_id") == f"{context['campaign_id']}:r{context['round_index']}", "Round identity mismatch.")
    require(_digest(context.get("state_sha256")), "Round needs its source state checksum.")
    validate_skill(context["parent"])
    _memory(context["memory"])
    _task_ids(context["task_ids"])
    return context


def _records(records, task_ids, skill):
    require(isinstance(records, list), "Expected execution record list.")
    indexed = {}
    run_ids = set()
    for record in records:
        audit = verify_record(record)
        require(record["split"] == "train" and record["purpose"] == "learning", "Gate only accepts Train learning records.")
        require(audit["episode_complete"], "Incomplete execution cannot produce a Gate decision.")
        require(_same_skill(record["skill"], skill), "Execution does not use the actual round Skill.")
        task_id = record["task"]["id"]
        require(task_id not in indexed and record["run_id"] not in run_ids, "Duplicate task or run in Gate evidence.")
        indexed[task_id] = record
        run_ids.add(record["run_id"])
    require(set(indexed) == set(task_ids), "Gate needs exactly the frozen task batch.")
    return indexed


def _record_summary(record):
    return {"run_id": record["run_id"], "sha256": object_digest(record), "won": record["won"]}


def gate_round(context, candidate_skill, parent_records, candidate_records):
    """Reject invalid comparisons; otherwise promote iff whole-batch success rises."""
    validate_round(context)
    parents = _records(parent_records, context["task_ids"], context["parent"])
    pairs = []
    if candidate_skill is None:
        require(candidate_records == [], "No-change round must not have Candidate executions.")
        pairs = [{"task_id": task, "parent": _record_summary(parents[task]), "candidate": None}
                 for task in context["task_ids"]]
        candidate_wins = None
    else:
        validate_skill(candidate_skill)
        require(candidate_skill["skill_id"] != context["parent"]["skill_id"],
                "An unchanged Candidate must use the explicit no-change path.")
        candidates = _records(candidate_records, context["task_ids"], candidate_skill)
        require(not {row["run_id"] for row in parents.values()} & {row["run_id"] for row in candidates.values()},
                "Parent and Candidate must have different execution identities.")
        for task in context["task_ids"]:
            comparison = compare_records(parents[task], candidates[task])
            require(comparison["recorded_conditions_match"],
                    f"Incomparable Parent/Candidate pair for {task}: {comparison['differences']}")
            pairs.append({"task_id": task, "parent": _record_summary(parents[task]),
                          "candidate": _record_summary(candidates[task])})
        candidate_wins = sum(row["won"] for row in candidates.values())
    parent_wins = sum(row["won"] for row in parents.values())
    accept = candidate_wins is not None and candidate_wins > parent_wins
    return _seal({"schema_version": GATE_SCHEMA, "rule": GATE_RULE,
                  "round_id": context["round_id"], "round_sha256": context["sha256"],
                  "parent_skill_id": context["parent"]["skill_id"],
                  "candidate_skill_id": candidate_skill["skill_id"] if candidate_skill is not None else None,
                  "task_ids": context["task_ids"], "decision": "ACCEPT" if accept else "RETAIN",
                  "reason": "no_change" if candidate_skill is None else
                            ("success_rate_increased" if accept else "success_rate_not_increased"),
                  "successes": {"parent": parent_wins, "candidate": candidate_wins}, "pairs": pairs})


def validate_gate(gate, context, candidate_skill):
    validate_round(context)
    _check_seal(gate, GATE_SCHEMA)
    require(gate.get("rule") == GATE_RULE and gate.get("round_id") == context["round_id"]
            and gate.get("round_sha256") == context["sha256"]
            and gate.get("task_ids") == context["task_ids"]
            and gate.get("parent_skill_id") == context["parent"]["skill_id"], "Gate/round binding mismatch.")
    if candidate_skill is not None:
        validate_skill(candidate_skill)
        require(candidate_skill["skill_id"] != context["parent"]["skill_id"], "Unchanged Candidate is not an update.")
    require(gate.get("candidate_skill_id") == (candidate_skill["skill_id"] if candidate_skill is not None else None),
            "Gate/Candidate binding mismatch.")
    require(isinstance(gate.get("pairs"), list)
            and [row.get("task_id") for row in gate["pairs"]] == context["task_ids"], "Gate pair coverage mismatch.")
    runs = set()
    for row in gate["pairs"]:
        for role in ("parent", "candidate"):
            entry = row.get(role)
            if role == "candidate" and candidate_skill is None:
                require(entry is None, "No-change Gate contains Candidate evidence.")
                continue
            require(isinstance(entry, dict) and isinstance(entry.get("run_id"), str) and entry["run_id"]
                    and _digest(entry.get("sha256")) and type(entry.get("won")) is bool,
                    "Invalid Gate execution summary.")
            require(entry["run_id"] not in runs, "Repeated Gate execution identity.")
            runs.add(entry["run_id"])
    parent_wins = sum(row["parent"]["won"] for row in gate["pairs"])
    candidate_wins = None if candidate_skill is None else sum(row["candidate"]["won"] for row in gate["pairs"])
    accept = candidate_wins is not None and candidate_wins > parent_wins
    require(gate["successes"] == {"parent": parent_wins, "candidate": candidate_wins}, "Gate totals mismatch.")
    require(gate.get("decision") == ("ACCEPT" if accept else "RETAIN"), "Gate must compare overall native success rates.")
    reason = "no_change" if candidate_skill is None else ("success_rate_increased" if accept else "success_rate_not_increased")
    require(gate.get("reason") == reason, "Gate reason mismatch.")
    return gate


def _validate_receipt(receipt, context, gate, memory_after):
    require(isinstance(receipt, dict) and receipt.get("schema_version") == RECEIPT_SCHEMA,
            "Publishing requires a completed post-Gate Memory receipt.")
    expected = {"round_id": context["round_id"], "gate_sha256": object_digest(gate),
                "memory_before_sha256": object_digest(context["memory"]),
                "memory_after_sha256": object_digest(memory_after)}
    require(all(receipt.get(key) == value for key, value in expected.items()), "Memory receipt binding mismatch.")
    require(_digest(receipt.get("learning_payload_sha256")) and _digest(receipt.get("learning_output_sha256")),
            "Memory receipt must bind validated learning input and output.")


def finish_round(state, context, candidate_skill, gate, memory_after, receipt):
    """Return next state from Gate and a receipt issued by validated learning.

    The receipt is a provenance contract, not a signature or a fresh semantic
    judgment. Callers must obtain it from the post-Gate learning entry point.
    """
    validate_state(state)
    validate_round(context)
    require(context == open_round(state, context["task_ids"]), "Round does not inherit the supplied current state.")
    validate_gate(gate, context, candidate_skill)
    _memory(memory_after)
    _validate_receipt(receipt, context, gate, memory_after)
    chosen = candidate_skill if gate["decision"] == "ACCEPT" else context["parent"]
    # Keep the exact last context so its checksum and before/after Memory binding
    # remain auditable. It contains no prior state, so state history is not nested.
    result = _seal({"schema_version": STATE_SCHEMA, "campaign_id": state["campaign_id"],
                    "round_index": context["round_index"], "parent": chosen, "memory": memory_after,
                    "seen_task_ids": state["seen_task_ids"] + context["task_ids"],
                    "last_round": {"context": context, "candidate": candidate_skill,
                                   "gate": gate, "memory_receipt": receipt}})
    validate_state(result)
    return result


def write_state(path, state):
    """Publish a complete snapshot atomically and refuse to overwrite any path."""
    validate_state(state)
    target = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=".continual-state-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def read_state(path):
    state = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_state(state)
    return state

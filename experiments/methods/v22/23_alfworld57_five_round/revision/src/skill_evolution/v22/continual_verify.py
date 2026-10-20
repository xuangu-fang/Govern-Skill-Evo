"""Offline consistency verification of one saved continual campaign.

Checks recorded lineage and deterministic interfaces, not semantic correctness,
independent environmental truth, or the causal benefit of preconditioning.
"""
from . import reference_rules

from copy import deepcopy
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import digest, object_digest
from src.adapters.alfworld.verify_skill_run import require, verify_record
from src.adapters.alfworld.response_archive import verify_response_archive
from .compact_cycle import make_diff
from .continual_runner import STAGES, _cost, _editor_result, check_files, read
from .continual_runtime import actor_schedule, update_profile, semantic_request_options, STREAM_PROTOCOL, FORMAL_PROTOCOL
from .effective_memory import memory_view_schema
from .continual_state import finish_round, gate_round, open_round, read_state
from .diagnosis_editor import parse_json_response
from .grouped_representation import build_grouping_input, freeze_grouping, grouping_messages
from . import p1_input, memory_contract
from .grouped_update import (
    PROFILE, accept_diagnosis, compile_update, diagnosis_payload, grouped_messages, identity_update,
    learn_grouped_memory, prepare_current, prepare_grouped_learning, realize_editor, update_payload,
)
from .verify_round import verify_call


def _located(root, recorded_root, path):
    """Resolve archived absolute paths within this artifact, including moved copies."""
    relative = Path(path).relative_to(recorded_root)
    resolved = (root / relative).resolve()
    require(resolved.is_relative_to(root), "Artifact reference escapes the campaign.")
    return resolved


def _schedule(root, plan, frozen, report):
    """Verify the explicit scheduling-only handoff, never a general freeze bypass."""
    declared = actor_schedule(plan)
    actual = report["actor_schedule"]
    result = {"declared_schedule": declared, "actual_schedule": actual, "amended": False}
    if actual == declared:
        require("scheduling_amendment" not in report and "continuation" not in report,
                "Scheduling amendment must be explicitly identified in the actual schedule.")
        return result
    require(plan["protocol"] == "v22.grouped_continual.v2"
            and actual == "serial_then_user_authorized_parallel_8"
            and plan["budget"]["actor_workers_max"] == 3,
            "Actor scheduling differs from the frozen plan without a supported amendment.")
    old_root = Path(frozen["artifact_root"])
    require("scheduling_amendment" in report and "continuation" in report,
            "Mixed scheduling lacks its amendment and continuation bindings.")
    binding, continuation = report["scheduling_amendment"], report["continuation"]

    def sibling(path, filename):
        # Only one direct sibling directory may hold the amendment. Resolve its
        # recorded location relative to the archived parent when both are moved.
        recorded = Path(path)
        require(recorded.is_absolute() and ".." not in recorded.parts,
                "Amendment path must be an absolute bound sibling path.")
        try:
            relative = recorded.relative_to(old_root.parent)
        except ValueError as exc:
            raise ValueError("Amendment reference is outside the campaign's parent.") from exc
        require(len(relative.parts) == 2 and relative.parts[0] != old_root.name
                and relative.name == filename, "Amendment reference is not a direct sibling file.")
        located = (root.parent / relative).resolve()
        require(located.parent.parent == root.parent.resolve()
                and located.parent.name == relative.parts[0], "Amendment reference escapes its bound directory.")
        return located

    amendment_path = sibling(binding["path"], "amendment.json")
    source_path = sibling(continuation["path"], "continuation.py")
    authority_path = sibling(continuation["authority"], "continuation_freeze.json")
    require(source_path.parent == amendment_path.parent == authority_path.parent,
            "Amendment sources must share the same bound sibling directory.")
    for path, checksum in ((amendment_path, binding["sha256"]),
                           (source_path, continuation["sha256"]),
                           (authority_path, continuation["authority_sha256"])):
        require(digest(path.read_bytes()) == checksum, "Scheduling amendment file hash changed.")
    amendment, authority = read(amendment_path), read(authority_path)
    runtime_sha = digest((root / "runtime_freeze.json").read_bytes())
    require(amendment.get("schema") == "v22.user_authorized_schedule_amendment.v1"
            and authority.get("schema") == "v22.authorized_schedule_continuation.v1",
            "Unsupported scheduling amendment schema.")
    require(amendment.get("original_root") == str(old_root)
            and authority.get("artifact_root") == str(old_root)
            and amendment.get("original_runtime_freeze_sha256") == runtime_sha
            and authority.get("original_runtime_freeze_sha256") == runtime_sha,
            "Scheduling amendment is not bound to this campaign/runtime.")
    require(amendment.get("original_protocol") == plan["protocol"]
            and amendment.get("changes") == {
                "actor_workers_max": {"before": 3, "after": 8},
                "actual_schedule": {"before": "sequential_one_worker", "after": "parallel_max_8"}}
            and isinstance(amendment.get("authorization"), str) and amendment["authorization"].strip(),
            "Amendment must declare only the authorized serial-to-eight scheduling change.")
    require(authority.get("amendment_path") == binding["path"]
            and authority.get("amendment_sha256") == binding["sha256"]
            and authority.get("source_sha256") == continuation["sha256"]
            and authority.get("actor_workers_max") == 8
            and authority.get("method_change") is False
            and authority.get("retries_or_repeated_prior_work") is False,
            "Continuation authority differs from the bound scheduling-only amendment.")
    remaining = amendment_path.parent / "remaining_replay.py"
    require(remaining.resolve().parent == amendment_path.parent
            and digest(remaining.read_bytes()) == amendment.get("remaining_replay_source_sha256"),
            "Initial parallel Replay source differs from the scheduling amendment.")
    return result | {"amended": True, "amendment_path": str(amendment_path),
                     "actor_workers_max_after_amendment": 8}


def _calls(directory, row, plan, frozen, published, *,
           classification_max_tokens=16384, classification_timeout_seconds=300):
    stages = row["stages"]
    require(len(stages) == len(set(stages)), "Repeated semantic dispatch.")
    declared = plan["rounds"][row["round"] - 1]
    require(all(declared["stage_calls_max"].get(stage) == 1 for stage in stages)
            and len(stages) <= declared["semantic_calls_max"], "Undeclared semantic stage/budget.")
    paths = {path.stem: path for path in (directory / "calls").glob("*.json")}
    require(set(paths) <= set(stages), "Call without a recorded dispatch.")
    require(not published or set(paths) == set(stages), "Published round has missing calls.")
    for stage, path in paths.items():
        messages = read(directory / "messages" / f"{stage}.json")
        payload = read(directory / "inputs" / f"{stage}.json")
        if stage == "classification":
            require(payload == read(directory / "grouping_input.json")["model_input"],
                    "Classification received fields outside its model input.")
        user = (grouping_messages(payload, "", profile=update_profile(plan))[1]["content"] if stage == "classification"
                else grouped_messages(STAGES[stage], payload)[1]["content"])
        expected = [{"role": "system", "content": frozen["system_prompts"][stage]["text"]},
                    {"role": "user", "content": user}]
        require(messages == expected, "Saved messages differ from input or frozen prompt.")
        require(len(json.dumps(messages, ensure_ascii=False, separators=(",", ":")))
                <= plan["budget"]["evolution_input_unicode_chars_max"], "Dispatched oversized input.")
        document_path = directory / "raw_outputs" / f"{stage}.json"
        document = read(document_path) if document_path.exists() else None
        require(not published or document is not None, "Published call lacks raw parsed output.")
        budget = ({"max_tokens": classification_max_tokens, "timeout_seconds": classification_timeout_seconds}
                  if stage == "classification" else {})
        if plan.get("protocol") in {STREAM_PROTOCOL, FORMAL_PROTOCOL}:
            budget = semantic_request_options(plan, stage)
        verify_call(path, stage, plan["models"]["evolution"], messages, document, **budget)
        response = read(path)["steps"][0].get("model_response")
        if response is not None:
            require(response.get("response_model") == plan["models"]["evolution"], "Response model mismatch.")
        raw_path = directory / "raw_outputs" / f"{stage}.txt"
        if raw_path.exists():
            raw = raw_path.read_text(encoding="utf-8")
            require(response is not None and raw == response["content"], "Raw response text changed.")
            if document is not None:
                require(parse_json_response(raw) == document, "Raw parsed output changed.")
        else:
            require(not published, "Published call lacks raw response text.")
    return len(paths)


def _published(root, old_root, directory, row, plan, frozen, state):
    profile = update_profile(plan)
    context = open_round(state, plan["data"][f"round{row['round']}_task_ids"])
    require(read(directory / "context.json") == context, "Round does not inherit the published state.")
    require(read(directory / "parent.json") == context["parent"]
            and read(directory / "memory_before.json") == context["memory"], "Round input state changed.")
    require(all(item["side"] in {"parent", "candidate"} for item in row["episode_attempts"])
            and len(row["episode_attempts"]) <= plan["rounds"][row["round"] - 1]["episodes_max"],
            "Unexpected execution branch or episode budget.")
    records = {}
    for side in ("parent", "candidate"):
        attempts = [attempt for attempt in row["episode_attempts"] if attempt["side"] == side]
        require([item["task_id"] for item in attempts] == context["task_ids"][:len(attempts)],
                "Execution sources are not in frozen task order.")
        source_path = directory / f"{side}_sources.json"
        require(not attempts or source_path.exists(), "Published executions lack sources.")
        require(not source_path.exists() or read(source_path) == attempts, "Execution sources changed.")
        records[side] = []
        require({path.resolve() for path in (directory / f"{side}_runs").rglob("trajectory.json")}
                == {_located(root, old_root, item["trajectory"]) for item in attempts},
                "Unindexed or missing execution trajectory.")
        for attempt in attempts:
            path = _located(root, old_root, attempt["trajectory"])
            require(digest(path.read_bytes()) == attempt["sha256"], "Execution source hash changed.")
            record = read(path)
            verify_record(record)
            if plan["protocol"] in {STREAM_PROTOCOL, FORMAL_PROTOCOL}:
                require(record.get("response_archival") == "raw_http_body_v1",
                        "Streaming Actor lacks raw response archival.")
                for event in record["steps"]:
                    require(event.get("response_archive") is True, "Actor request lacks response archival.")
                    for transport in event.get("transport_attempts", []):
                        verify_response_archive(path, transport)
            require(record["task"]["id"] == attempt["task_id"]
                    and record["model"] == plan["models"]["actor"], "Execution slot/model mismatch.")
            records[side].append(record)
    parents, candidates = records["parent"], records["candidate"]
    current = prepare_current(context, parents, profile=profile)
    grouping_input = build_grouping_input(current, context["round_id"], plan["classification"]["alias_seed"])
    require(read(directory / "grouping_input.json") == grouping_input
            and read(directory / "inputs/classification.json") == grouping_input["model_input"],
            "Classification input is not the current private-field-free summary.")
    grouping_result = read(directory / "raw_outputs/classification.json")
    grouping = freeze_grouping(grouping_result, grouping_input, frozen["system_prompts"]["classification"]["text"])
    require(read(directory / "grouping.json") == grouping
            and read(directory / "outputs/classification.json") == grouping_result, "Frozen partition changed.")
    current = diagnosis_payload(context, parents, grouping, profile=profile)
    require(read(directory / "inputs/diagnosis.json") == current, "Diagnosis input changed.")
    diagnosis = accept_diagnosis(read(directory / "raw_outputs/diagnosis.json"), current)
    require(read(directory / "outputs/diagnosis.json") == diagnosis
            and read(directory / "initial_plan.json") == diagnosis["plan"], "Initial diagnosis changed.")
    effective = diagnosis["plan"] or {"intent": "No constructed update: " + diagnosis["reason"],
                                      "requirements": [], "watch": [], "open": []}
    expected_stages = ["classification", "diagnosis"]
    candidate = None
    editor = None
    update_status = diagnosis["decision"]
    compiled = deepcopy(effective)
    if diagnosis["decision"] == "revise":
        payload = update_payload(context, current, effective)
        if row["round"] == 1 and plan["protocol"] != FORMAL_PROTOCOL:
            fusion, effective = identity_update(payload)
        else:
            expected_stages.append("fusion")
            require(read(directory / "inputs/fusion.json") == payload, "Fusion input changed.")
            fusion = read(directory / "raw_outputs/fusion.json")
            effective = compile_update(fusion, payload)
        require(read(directory / "outputs/fusion.json") == fusion, "Fusion output changed.")
        compiled = deepcopy(effective)
        update_status = fusion["decision"]
        if fusion["decision"] == "ready" and not effective["requirements"]:
            require(profile != PROFILE, "Empty effective update requires the unified profile.")
            update_status = "no_effective_update"
        elif fusion["decision"] == "ready":
            expected_stages.append("main_editor")
            payload = update_payload(context, current, effective)
            require(read(directory / "inputs/main_editor.json") == payload, "Editor input changed.")
            editor, identical = _editor_result(read(directory / "raw_outputs/main_editor.json"), payload)
            require(read(directory / "outputs/main_editor.json") == editor, "Normalized Editor output changed.")
            update_status = editor["decision"]
            if editor["decision"] != "needs_revision":
                candidate, effective = realize_editor(editor, payload)
            else:
                effective = deepcopy(effective)
                effective["watch"].extend(deepcopy(editor["watch"]))
    require(read(directory / "effective_plan.json") == compiled
            and read(directory / "execution_plan.json") == effective
            and read(directory / "candidate.json") == candidate, "Actual update differs from construction.")
    if profile != PROFILE:
        require(row["update_status"] == update_status, "Update status differs from its actual construction route.")
    if candidate is not None:
        require((directory / "candidate/SKILL.md").read_bytes() == candidate["text"].encode("utf-8")
                and (directory / "candidate/actual.diff").read_bytes()
                == make_diff(context["parent"], candidate).encode("utf-8"), "Candidate text or diff changed.")
    gate = gate_round(context, candidate, parents, candidates)
    require(read(directory / "gate.json") == gate, "Gate differs from actual paired execution.")
    require(row["gate"] == {key: gate[key] for key in ("decision", "reason", "successes")},
            "Gate report differs from paired execution.")
    learning_input = prepare_grouped_learning(
        context, grouping, effective, candidate, parents, candidates, gate,
        editor=editor if profile != PROFILE else None, profile=profile)
    require(read(directory / "learning_input.json") == learning_input, "Learning input changed.")
    output = read(directory / "outputs/post_gate_learning.json")
    if candidate is not None or context["memory"]:
        expected_stages.append("post_gate_learning")
        require(read(directory / "inputs/post_gate_learning.json") == learning_input
                and read(directory / "raw_outputs/post_gate_learning.json") == output, "Learning call binding changed.")
    else:
        require(candidate is None and not context["memory"], "Unrecorded Memory model call.")
    require(row["stages"] == expected_stages, "Semantic stages do not follow the actual update route.")
    memory, receipt = learn_grouped_memory(learning_input, output)
    require(read(directory / "memory_after.json") == memory
            and read(directory / "memory_receipt.json") == receipt, "Memory application changed.")
    expected = finish_round(state, context, candidate, gate, memory, receipt)
    require(read_state(directory / "state.json") == expected, "Published state differs from Gate and Memory.")
    return expected


def verify_campaign(root):
    root = Path(root).resolve()
    plan, frozen, report = [read(root / f"{name}.json") for name in ("plan", "runtime_freeze", "report")]
    require(frozen["sha256"] == object_digest({key: value for key, value in frozen.items() if key != "sha256"})
            and frozen["plan"] == plan, "Runtime freeze or plan changed.")
    require(frozen["runtime"]["update_profile"] == update_profile(plan),
            "Frozen update profile differs from the declared plan.")
    require(frozen["runtime"]["contracts"]["effective_memory_view"] == memory_view_schema(update_profile(plan)),
            "Frozen memory view differs from the declared update profile.")
    if update_profile(plan) in (p1_input.PROFILE, memory_contract.PROFILE, reference_rules.PROFILE):
        require(frozen["runtime"]["contracts"].get("model_input_encoding") == p1_input.VIEW_SCHEMA,
                "Frozen input encoding differs from the declared update profile.")
    scheduling = _schedule(root, plan, frozen, report)
    old_root = Path(frozen["artifact_root"])
    for binding in frozen["sources"] + frozen["bindings"]:
        snapshot = _located(root, old_root, binding["snapshot"])
        require(digest(snapshot.read_bytes()) == binding["sha256"], "Archived runtime snapshot changed.")
    for prompt in frozen["system_prompts"].values():
        require(digest(prompt["text"].encode("utf-8")) == prompt["sha256"], "Frozen prompt changed.")
    state = read_state(root / "state0.json")
    require(state["round_index"] == 0, "Campaign lacks its initial No Skill state.")
    published, calls = 0, 0
    require(len(report["rounds"]) <= len(plan["rounds"]), "Too many rounds.")
    for number, row in enumerate(report["rounds"], 1):
        require(row["round"] == number, "Nonsequential round records.")
        directory = root / "rounds" / f"r{number}"
        require(read(directory / "report.json") == row, "Round report differs from campaign report.")
        complete = row["status"] == "published"
        for name in ("round_start", "classification_freeze", "evidence_freeze", "diagnosis_freeze",
                     "effective_freeze", "replay_freeze", "learning_freeze", "final_freeze"):
            path = directory / f"{name}.json"
            required = complete and (name != "effective_freeze" or (directory / "outputs/fusion.json").exists())
            require(not required or path.exists(), "Published round lacks a required freeze.")
            if path.exists():
                check_files(directory, read(path))
        calls += _calls(directory, row, plan, frozen, complete)
        if complete:
            require(published == number - 1, "Published round follows an incomplete round.")
            state = _published(root, old_root, directory, row, plan, frozen, state)
            published += 1
        else:
            require(number == len(report["rounds"]), "Campaign advanced after an incomplete round.")
    require(report["published_rounds"] == published, "Published count changed.")
    require(read_state(_located(root, old_root, report["latest_state"])) == state, "Latest state reference changed.")
    require(report["cost"] == _cost(root, report), "Recorded cost summary changed.")
    complete = report["status"] == "completed"
    require(not complete or published == len(plan["rounds"]), "Completed report lacks both publications.")
    return {"artifact_valid": True, "status": report["status"], "campaign_complete": complete,
            "published_rounds": published, "incomplete_rounds": len(report["rounds"]) - published,
            "semantic_call_records": calls, "offline": report["offline"], "scheduling": scheduling,
            "scope": "Saved artifacts, snapshots, calls and deterministic lineage only; no semantic or causal certification."}

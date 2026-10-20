"""Explicit five-round scheduling extension; no update/learning policy changes."""
from copy import deepcopy
import json
from pathlib import Path
from src.adapters.alfworld.run_task import REPO_ROOT, SPLIT_ROOT
from src.adapters.alfworld.skill_runtime import digest, object_digest, execution_protocol
from src.adapters.alfworld.verify_skill_run import require
from . import reference_rules, p1_input
from .model_routing import model_route

PROTOCOL = "v22.alfworld57_five_round.v1"
SIZES = [12, 12, 12, 12, 9]
STAGES = ("classification", "diagnosis", "fusion", "main_editor", "post_gate_learning")

def read(path):
    return json.loads(Path(path).read_text())

def binding(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": digest(path.read_bytes())}

def capacity_audit(messages, plan, stage):
    wire = json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    # At most one token per UTF-8 byte plus a deliberately conservative framing
    # reserve. This is an admission upper bound, not a tokenizer or billed usage.
    upper = len(wire.encode("utf-8")) + 8192
    output = plan["models"]["semantic_requests"][stage]["max_tokens"]
    result = {"messages_unicode_chars": len(wire), "messages_utf8_bytes": len(wire.encode("utf-8")),
              "input_tokens_conservative_upper_bound": upper, "framing_reserve_tokens": 8192,
              "requested_output_tokens": output, "context_tokens": 1000000,
              "method": "UTF-8 byte upper bound plus framing reserve; not actual usage"}
    require(len(wire) <= 400000, "Evolution input exceeds frozen character budget.")
    require(upper + output <= 1000000, "Evolution input plus output exceeds frozen context budget.")
    return result

def load_formal_bundle(path):
    path = Path(path).resolve(); plan = read(path)
    require(plan["protocol"] == PROTOCOL and plan["update_profile"] == reference_rules.PROFILE,
            "Formal protocol/profile mismatch.")
    require(plan["input_encoding"] == p1_input.VIEW_SCHEMA and plan["reference_contract"] == reference_rules.VERSION,
            "Formal representation/reference mismatch.")
    require(plan["initial_state"] == {"skill": "No Skill", "memory": [], "import_previous_skills_or_effects": False},
            "Initial state must be empty.")
    route = model_route(plan["model_route"]["base_url"], "deepseek-v4-flash", "deepseek-v4-pro")
    require(route == plan["model_route"] and route["actor"] == route["evolution"] == "deepseek-flash"
            and route["base_url"] in {"https://api.deepseek.com", "https://api.deepseek.com/v1"}, "Official route required.")
    models = plan["models"]
    require(models["actor"] == models["evolution"] == plan["classification"]["model"] == "deepseek-flash", "Model drift.")
    require(models["request_parameters"] == {"temperature": 1.0, "max_tokens": 16384,
            "thinking": {"type": "enabled"}, "reasoning_effort": "medium", "stream": False}, "Actor parameters drift.")
    require(models["semantic_requests"] == {s: {"max_tokens": 65536 if s == "post_gate_learning" else 32768,
            "timeout_seconds": 600, "transport_policy": "single_attempt"} for s in STAGES}, "Semantic budget drift.")
    require(models["environment_seed"] == 42 and models["request_timeout_seconds"] == 300
            and models["actor_history"] == "last_2_pre_action_observation_action_pairs" and models["actor_state_extension"] is False
            and models["actor_response_archival"] is True, "Execution settings drift.")
    protocol = execution_protocol(50)
    require((protocol["max_tokens"], protocol["environment_seed"], protocol["history_length"], protocol["request_timeout_seconds"])
            == (16384, 42, 2, 300), "Installed Actor protocol drift.")
    require(plan["scheduling"] == {"actor_workers": 8, "dispatch": "bounded_in_frozen_task_order",
            "on_technical_failure": "stop_dispatch_and_drain", "semantic_stages": "sequential_after_complete_batch"}, "Scheduler drift.")
    expected = {"rounds_max": 5, "tasks_per_round": SIZES, "unique_tasks": 57, "environment_episodes_max": 114,
                "max_steps_per_episode": 50, "actor_logical_requests_max": 5700, "semantic_calls_max": 25,
                "logical_requests_max": 5725, "http_attempts_per_logical_request_max": 6, "http_attempts_max": 34225,
                "actor_workers_max": 8, "evolution_input_unicode_chars_max": 400000, "per_request_output_tokens_max": 65536,
                "semantic_retries": 0, "classification_format_retries": 0, "construction_revision_pairs": 0,
                "episode_retries": 0, "unused_budget_reassignment": False, "semantic_http_attempts_per_request_max": 1,
                "semantic_output_tokens_max": 983040, "actor_output_tokens_max": 5700*6*16384,
                "actor_logical_output_tokens_max": 5700*16384, "model_context_tokens": 1000000}
    require(all(plan["budget"].get(k) == v for k,v in expected.items()), "Formal budget mismatch.")
    require(plan["recovery"] == {"semantic_same_request_retries": 0, "episode_retries": 0,
            "on_exhaustion": "checkpoint_and_stop", "completed_stages": "reuse_only_with_identical_input_and_validated_artifacts",
            "resume_after_failure": "stop_at_checkpoint_no_automatic_restart"}, "Recovery policy drift.")
    data = plan["data"]
    require(data["split"] == "train+val" and data["purpose"] == "development"
            and data["new_test_episodes"] == 0 and data["outcome_based_replacement"] is False
            and data["all_parent_slots_execute_fresh"] is True, "Development pool boundary changed.")
    sources = [SPLIT_ROOT / s / "items.json" for s in ("train", "val")]
    native = [read(p) for p in sources]
    require([len(x) for x in native] == [39,18], "Native pool size differs.")
    items = native[0] + native[1]; ids = [x["id"] for x in items]
    require(len(set(ids)) == len({x["gamefile"] for x in items}) == 57, "Native task identity overlap.")
    mp = path.parent / data["task_manifest"]; manifest = read(mp)
    require(binding(mp)["sha256"] == data["task_manifest_sha256"], "Manifest hash changed.")
    require(manifest["protocol"] == PROTOCOL and manifest["sources"] == [binding(p) for p in sources]
            and manifest["order"] == "native_train_manifest_then_native_val_manifest"
            and manifest["environment_seed"] == 42 and manifest["alias_seed"] == 200, "Manifest identity/order drift.")
    require(len(manifest["rounds"]) == len(plan["rounds"]) == 5, "Five rounds required.")
    offset = 0
    for number,size in enumerate(SIZES,1):
        row = plan["rounds"][number-1]; tasks = manifest["rounds"][number-1]
        require(row["round"] == tasks["round"] == number and row["main_candidate_max"] == 1
                and row["semantic_calls_max"] == 5 and row["episodes_max"] == 2*size
                and row["stage_calls_max"] == dict.fromkeys(STAGES,1), "Round budget drift.")
        require(tasks["tasks"] == items[offset:offset+size] and tasks["task_ids"] == ids[offset:offset+size]
                == data[f"round{number}_task_ids"], "Native manifest order/identity changed.")
        offset += size
    gate = plan["gate"]
    require(gate["version"] == "v22.native_success_improvement.v1" and gate["required_pairs"] == SIZES
            and gate["model_calls"] == 0 and gate["accept"] ==
            "candidate_success_count > parent_success_count for the same complete comparable task batch", "Gate drift.")
    require(plan["replay"]["same_task_batch_as_parent"] is True and plan["replay"]["each_condition_executions_max"] == 1
            and plan["memory"]["order"] == "Replay -> Gate -> formal Memory update -> publish"
            and plan["memory"]["gate_is_effect_quality_label"] is False, "Learning behavior drift.")
    classification = plan["classification"]
    pp = path.parent / classification["prompt_file"]; prompt = pp.read_text()
    require(binding(pp)["sha256"] == classification["prompt_sha256"] and classification["alias_seed"] == 200
            and classification["calls_per_round_max"] == 1 and classification["semantic_or_format_retries"] == 0
            and classification["candidate_reclassification"] is False
            and prompt.startswith("Profile: v22.decision_grouping.v1\n"), "Classification drift.")
    extras=[]
    for row in plan["preparation_materials"]:
        p=path.parent/row["path"]; require(binding(p)["sha256"] == row["sha256"], "Preparation changed."); extras.append(p)
    return {"plan": plan, "task_items": {x["id"]: deepcopy(x) for x in items}, "grouping_prompt": prompt,
            "bindings": [binding(p) for p in (path,mp,pp,*extras,*sources)], "plan_path": str(path)}

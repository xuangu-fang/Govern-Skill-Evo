"""Pinned inputs, source snapshots and live adapters for the single V22 mainline.

Loading/freezing never starts an episode or sends a request. The runner owns the
round schedule; these two live callbacks each perform exactly one declared job.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys

from src.adapters.alfworld.run_task import REPO_ROOT, SPLIT_ROOT
from src.adapters.alfworld.run_task_skill import installed_versions, environment_modules
from src.adapters.alfworld.skill_runtime import (
    SCHEMA as EXECUTION_SCHEMA, digest, object_digest, execution_protocol, implementation_metadata,
)
from src.adapters.alfworld.verify_skill_run import require
from .bounded_evaluation import execute_episode
from .compact_learning import SCHEMA as LEARNING_SCHEMA
from .compact_update import SCHEMA as UPDATE_SCHEMA
from .continual_state import STATE_SCHEMA, ROUND_SCHEMA, GATE_SCHEMA, RECEIPT_SCHEMA
from .effective_memory import memory_view_schema
from .grouped_representation import INPUT_SCHEMA, FROZEN_SCHEMA
from .grouped_update import check_profile, grouped_messages, PROFILE
from .model_call import semantic_call


SCHEMA = "v22.continual_runtime.v1"
STAGES = ("classification", "diagnosis", "fusion", "main_editor", "post_gate_learning")
EXPECTED_PARAMETERS = {"temperature": 1.0, "max_tokens": 16384,
                       "thinking": {"type": "enabled"}, "reasoning_effort": "medium", "stream": False}
STREAM_PROTOCOL = "v22.grouped_continual.v4"


def semantic_request_options(plan, stage):
    """Explicit new transport/budgets; legacy plans retain their exact defaults."""
    require(stage in STAGES, "Unknown continual semantic stage.")
    if plan["protocol"] != STREAM_PROTOCOL:
        return {}
    return deepcopy(plan["models"]["semantic_requests"][stage])


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _binding(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": digest(path.read_bytes())}


def _match(value, expected, message):
    require(value == expected, message)


def actor_workers(plan):
    """v3 changes dispatch concurrency only; v2 remains the frozen serial route."""
    protocol = plan["protocol"]
    require(protocol in {"v22.grouped_continual.v2", "v22.grouped_continual.v3", STREAM_PROTOCOL},
            "Unknown continual protocol.")
    if protocol == "v22.grouped_continual.v2":
        require("scheduling" not in plan, "v2 has no scheduler override.")
        return 1
    _match(plan.get("scheduling"), {"actor_workers": 8, "dispatch": "bounded_in_frozen_task_order",
           "on_technical_failure": "stop_dispatch_and_drain", "semantic_stages": "sequential_after_complete_batch"},
           "Unexpected parallel scheduling policy.")
    return 8


def actor_schedule(plan):
    return "sequential_one_worker" if actor_workers(plan) == 1 else "bounded_parallel_eight_workers"


def update_profile(plan):
    """Opt in to new update semantics; archived plans keep their original profile."""
    return check_profile(plan.get("update_profile", PROFILE))


def load_bundle(plan_path):
    """Validate this specific two-round protocol, without loading an environment."""
    path = Path(plan_path).expanduser().resolve()
    plan = _read(path)
    update_profile(plan)
    workers = actor_workers(plan)
    streaming = plan["protocol"] == STREAM_PROTOCOL
    _match(plan["initial_state"], {"skill": "No Skill", "memory": [], "import_previous_skills_or_effects": False},
           "The campaign must start without imported Skill or Memory.")
    data, budget, models = plan["data"], plan["budget"], plan["models"]
    tasks_per_round = budget["tasks_per_round"] if streaming else 10
    require(type(tasks_per_round) is int and 1 <= tasks_per_round <= 10,
            "Streaming batches must contain one to ten tasks each.")
    _match((data["split"], data["purpose"], data["new_selection_episodes"], data["new_test_episodes"]),
           ("train", "learning", 0, 0), "Only declared Train learning is permitted.")
    require(data["strict_streaming_train"] is True and data["all_parent_slots_execute_fresh"] is True
            and data["outcome_based_replacement"] is False, "Fresh, disjoint streaming batches are required.")
    actor_requests = 4 * tasks_per_round * 50
    expected_budget = {"rounds_max": 2, "tasks_per_round": tasks_per_round, "unique_tasks": 2 * tasks_per_round,
                       "environment_episodes_max": 4 * tasks_per_round, "max_steps_per_episode": 50,
                       "actor_logical_requests_max": actor_requests, "semantic_calls_max": 9,
                       "logical_requests_max": actor_requests + 9, "http_attempts_per_logical_request_max": 6,
                       "http_attempts_max": actor_requests * 6 + (9 if streaming else 54),
                       "actor_workers_max": 3 if workers == 1 else 8,
                       "evolution_input_unicode_chars_max": 400000,
                       "per_request_output_tokens_max": 65536 if streaming else 16384,
                       "semantic_retries": 0, "classification_format_retries": 0,
                       "construction_revision_pairs": 0, "episode_retries": 0,
                       "unused_budget_reassignment": False}
    for key, value in expected_budget.items():
        _match(budget[key], value, f"Unexpected campaign budget: {key}.")
    require(len(plan["rounds"]) == 2, "Exactly two rounds must be declared.")
    for number, row in enumerate(plan["rounds"], 1):
        _match((row["round"], row["main_candidate_max"], row["semantic_calls_max"], row["episodes_max"]),
               (number, 1, 3 + number, 2 * tasks_per_round), "Invalid single-mainline round budget.")
        expected = dict.fromkeys(STAGES, 1)
        expected["fusion"] = number - 1
        _match(row["stage_calls_max"], expected, "Unexpected stage, repeat call or parallel candidate branch.")
    _match(plan["rounds"][0]["fusion"], "declared_program_identity_without_model_call",
           "Round one must use declared program identity.")
    _match((models["actor"], models["evolution"]), ("deepseek-v4-flash", "deepseek-v4-pro"),
           "Unexpected model assignment.")
    _match(models["request_parameters"], EXPECTED_PARAMETERS, "Request parameters differ from the existing client.")
    if streaming:
        _match(update_profile(plan), "v22.unified_dsc.v2", "New streaming requires the explicit v2 update profile.")
        _match(models["semantic_requests"], {
            stage: {"max_tokens": 65536 if stage == "post_gate_learning" else 32768,
                    "timeout_seconds": 600, "transport_policy": "single_attempt"} for stage in STAGES},
            "Unexpected streaming semantic request budgets.")
        require(models.get("actor_response_archival") is True, "Streaming Actor responses must be archived.")
        _match(budget["semantic_http_attempts_per_request_max"], 1, "Semantic requests must be single-attempt.")
        _match(budget["semantic_output_tokens_max"], 7 * 32768 + 2 * 65536, "Semantic output budget mismatch.")
        _match(budget["actor_output_tokens_max"], actor_requests * 6 * 16384,
               "Actor output ceiling must include every possible transport attempt.")
    _match((models["request_timeout_seconds"], models["environment_seed"], models["actor_history"],
            models["actor_state_extension"]), (300, 42, "last_2_pre_action_observation_action_pairs", False),
           "Actor execution conditions differ from the fixed adapter.")
    protocol = execution_protocol(50)
    _match((protocol["max_tokens"], protocol["temperature"], protocol["thinking"], protocol["reasoning_effort"],
            protocol["environment_seed"], protocol["history_length"], protocol["request_timeout_seconds"]),
           (16384, 1.0, "enabled", "medium", 42, 2, 300), "Installed Actor protocol does not match the plan.")
    _match((plan["gate"]["version"], plan["gate"]["required_pairs"], plan["gate"]["model_calls"]),
           ("v22.native_success_improvement.v1", tasks_per_round, 0), "Gate must use overall native success improvement.")
    _match(plan["gate"]["accept"],
           ("candidate_success_count > parent_success_count for the same complete comparable task batch" if streaming else
            "candidate_success_rate > parent_success_rate (equivalently candidate_success_count > parent_success_count for the same ten complete pairs)"),
           "Gate must ACCEPT exactly on strictly higher overall success.")
    require(plan["replay"]["same_task_batch_as_parent"] is True
            and plan["replay"]["each_condition_executions_max"] == 1
            and plan["memory"]["order"] == "Replay -> Gate -> formal Memory update -> publish"
            and plan["memory"]["semantic_calls_per_round_max"] == 1
            and plan["memory"]["gate_is_effect_quality_label"] is False,
            "Replay/Gate/Memory ordering or bounded learning changed.")
    classification = plan["classification"]
    _match((classification["calls_per_round_max"], classification["model"], classification["alias_seed"],
            classification["prompt_version"], classification["semantic_or_format_retries"],
            classification["candidate_reclassification"]),
           (1, "deepseek-v4-pro", 200, "v22.decision_grouping.v1", 0, False), "Classification protocol changed.")
    manifest_path = (path.parent / data["task_manifest"]).resolve()
    manifest = _read(manifest_path)
    _match(digest(manifest_path.read_bytes()), data["task_manifest_sha256"], "Task manifest hash mismatch.")
    # v3 only revises scheduling; v4 explicitly binds a new task selection.
    _match(manifest["protocol"], STREAM_PROTOCOL if streaming else "v22.grouped_continual.v2",
           "Task manifest protocol differs.")
    train_path = (REPO_ROOT / manifest["benchmark_train_source"]["path"]).resolve()
    _match(train_path, (SPLIT_ROOT / "train/items.json").resolve(), "Manifest is not the Actor's Train source.")
    _match(digest(train_path.read_bytes()), manifest["benchmark_train_source"]["sha256"], "Train source changed.")
    train = {row["id"]: row for row in _read(train_path)}
    selected = {}
    round_ids = {}
    require(len(manifest["rounds"]) == 2 and manifest["strict_streaming_train"] is True,
            "Manifest must declare two strict-streaming rounds.")
    for number, row in enumerate(manifest["rounds"], 1):
        ids = data[f"round{number}_task_ids"]
        require(row["round"] == number and row["task_ids"] == ids and len(ids) == tasks_per_round
                and len(set(ids)) == tasks_per_round and not set(ids) & set(selected), "Round tasks overlap or differ from the plan.")
        _match([item["id"] for item in row["tasks"]], ids, "Manifest task order mismatch.")
        for item in row["tasks"]:
            task_id = item["id"]
            require(task_id in train and all(item.get(key) == value for key, value in train[task_id].items()),
                    "Selected task is not bound to its native Train entry.")
            # Selection reasons/families are private configuration, never learner input.
            selected[task_id] = deepcopy(train[task_id])
        round_ids[f"round{number}"] = ids
    _match(manifest["unique_tasks"], 2 * tasks_per_round, "Manifest unique task count mismatch.")
    _match(manifest["task_ids_canonical_sha256"], object_digest(round_ids), "Task ID binding mismatch.")
    prompt_path = (path.parent / classification["prompt_file"]).resolve()
    prompt = prompt_path.read_text(encoding="utf-8")
    _match(digest(prompt.encode("utf-8")), classification["prompt_sha256"], "Grouping prompt hash mismatch.")
    require(prompt.startswith("Profile: " + classification["prompt_version"] + "\n"), "Grouping profile mismatch.")
    extra = []
    if streaming:
        require(bool(plan.get("preparation_materials")), "Streaming needs its frozen preparation protocol.")
        for declared in plan["preparation_materials"]:
            bound = _binding(path.parent / declared["path"])
            _match(bound["sha256"], declared["sha256"], "Preparation material hash mismatch.")
            extra.append(Path(bound["path"]))
    return {"plan": plan, "task_items": selected, "grouping_prompt": prompt,
            "bindings": [_binding(p) for p in (path, manifest_path, prompt_path, *extra, train_path)],
            "plan_path": str(path)}


def _system_prompts(grouping_prompt, *, profile=PROFILE):
    # Only static system strings are extracted. This empty view is never saved as
    # a learning input or execution record; each real user payload is saved later.
    view = {"runs": {}, "memory": [], "update_context": {}}
    if check_profile(profile) != PROFILE:
        view["update_profile"] = profile
    view["binding_sha256"] = object_digest(view)
    result = {"classification": grouping_prompt}
    for external, internal in (("diagnosis", "diagnosis"), ("fusion", "fusion"),
                               ("main_editor", "editor"), ("post_gate_learning", "learn")):
        result[external] = grouped_messages(internal, view)[0]["content"]
    return {name: {"text": text, "sha256": digest(text.encode("utf-8"))} for name, text in result.items()}


def _write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def freeze_runtime(bundle, output_dir, *, offline=False):
    """Snapshot uncommitted implementation and config before any external work.

    Offline freezes explicitly identify synthetic execution and do not inspect game
    files or import TextWorld. Live preflight imports interfaces but never resets an
    environment. Runtime sources/config must remain unchanged during the campaign.
    """
    fresh = load_bundle(bundle["plan_path"])
    require(fresh == bundle, "Loaded bundle changed before runtime freeze.")
    profile = update_profile(bundle["plan"])
    root = Path(output_dir).resolve()
    require(not (root / "runtime_freeze.json").exists() and not (root / "source_snapshot").exists(),
            "This runtime was already frozen; use a new artifact directory.")
    versions = installed_versions()
    games = []
    if not offline:
        require(all(versions.values()), "Live execution needs installed ALFWorld dependencies.")
        environment_modules()  # Interface check only; no environment creation/reset.
        data_root = Path(os.environ.get("ALFWORLD_DATA", "~/.cache/alfworld")).expanduser().resolve()
        for item in bundle["task_items"].values():
            games.append(_binding(data_root / item["gamefile"]) | {"task_id": item["id"]})
    paths = sorted(set((REPO_ROOT / "src/skill_evolution/v22").glob("*.py"))
                   | set((REPO_ROOT / "src/adapters/alfworld").glob("*.py"))
                   | set((SPLIT_ROOT / "protocol/skillopt_native").glob("*")))
    sources = []
    for path in paths:
        if not path.is_file():
            continue
        target = root / "source_snapshot" / path.relative_to(REPO_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(path.read_bytes())
        sources.append(_binding(path) | {"snapshot": str(target)})
    bindings = []
    for index, binding in enumerate(bundle["bindings"]):
        path = Path(binding["path"])
        target = root / "config_snapshot" / f"{index:02d}_{path.name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(path.read_bytes())
        bindings.append(binding | {"snapshot": str(target)})
    freeze = {"schema_version": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "artifact_root": str(root), "mode": "offline_synthetic" if offline else "live",
              "plan": deepcopy(bundle["plan"]), "plan_path": bundle["plan_path"],
              "sources": sources, "bindings": bindings, "game_files": games,
              "runtime": {"python": platform.python_version(), "executable": sys.executable,
                          "versions": versions, "actor_protocol": execution_protocol(50),
                          "implementation": implementation_metadata(), "update_profile": profile,
                          "contracts": {"execution": EXECUTION_SCHEMA, "update": UPDATE_SCHEMA,
                                        "learning_input": LEARNING_SCHEMA,
                                        "effective_memory_view": memory_view_schema(profile),
                                        "grouping_input": INPUT_SCHEMA, "frozen_grouping": FROZEN_SCHEMA,
                                        "state": STATE_SCHEMA, "round": ROUND_SCHEMA, "gate": GATE_SCHEMA,
                                        "memory_receipt": RECEIPT_SCHEMA}},
              "system_prompts": _system_prompts(bundle["grouping_prompt"], profile=profile)}
    freeze["sha256"] = object_digest(freeze)
    _write_new(root / "runtime_freeze.json", freeze)
    check_runtime(freeze)
    return freeze


def check_runtime(freeze):
    """Fail before another request if a frozen input, source or snapshot changed."""
    require(freeze.get("schema_version") == SCHEMA and freeze.get("sha256") == object_digest(
        {key: value for key, value in freeze.items() if key != "sha256"}), "Runtime freeze integrity mismatch.")
    require(freeze["runtime"]["update_profile"] == update_profile(freeze["plan"]),
            "Frozen update profile differs from the declared plan.")
    saved = Path(freeze["artifact_root"]) / "runtime_freeze.json"
    require(_read(saved) == freeze, "Saved runtime freeze changed.")
    for row in freeze["sources"] + freeze["bindings"] + freeze["game_files"]:
        require(digest(Path(row["path"]).read_bytes()) == row["sha256"], "Frozen source/config/game changed.")
        if "snapshot" in row:
            require(digest(Path(row["snapshot"]).read_bytes()) == row["sha256"], "Runtime snapshot changed.")
    _match(installed_versions(), freeze["runtime"]["versions"], "Dependency versions changed.")
    _match(execution_protocol(50), freeze["runtime"]["actor_protocol"], "Actor protocol changed.")
    return freeze


def live_dependencies(bundle, env_file):
    """Return one-call adapters. Credentials remain private and are never archived."""
    from dotenv import load_dotenv
    import requests

    load_dotenv(Path(env_file).expanduser().resolve(), override=False)
    key, base = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    require(bool(key and base), "OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    plan = bundle["plan"]

    def generate(stage, messages, output):
        require(stage in STAGES, "Unknown continual semantic stage.")
        require(sum(len(message["content"]) for message in messages)
                <= plan["budget"]["evolution_input_unicode_chars_max"], "Evolution input exceeds frozen limit.")
        output = Path(output)
        require(not output.exists(), "Semantic output already exists; no repeat calls.")
        output.parent.mkdir(parents=True, exist_ok=True)
        with requests.Session() as session:
            if ".intra." in base:
                session.trust_env = False
            return semantic_call(stage, messages, session=session, endpoint=base + "/chat/completions",
                                 key=key, model=plan["models"]["evolution"], output=output,
                                 **semantic_request_options(plan, stage))

    def execute(task_item, skill_file, output_root):
        require(bundle["task_items"].get(task_item["id"]) == task_item, "Episode task differs from frozen Train item.")
        execution = {"actor_model": plan["models"]["actor"],
                     "max_steps_per_episode": plan["budget"]["max_steps_per_episode"]}
        if plan["protocol"] == STREAM_PROTOCOL:
            execution["archive_responses"] = True
        return execute_episode(task_item["id"], "train", "learning", skill_file, output_root, execution, env_file)

    return generate, execute

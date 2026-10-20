"""Bounded, single-lineage V22 campaign: two streaming Train update rounds.

Callbacks allow the identical orchestration to run with synthetic fixtures. There
is no resume, candidate retry, parallel comparison arm, or outcome-based resampling.
"""

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
import json
from pathlib import Path

from src.adapters.alfworld.run_task import REPO_ROOT
from src.adapters.alfworld.run_task_skill import timestamp
from src.adapters.alfworld.response_archive import verify_response_archive
from src.adapters.alfworld.skill_runtime import digest, execution_protocol, load_skill, object_digest, write_record
from src.adapters.alfworld.verify_skill_run import require, verify_record
from .compact_cycle import make_diff
from .continual_runtime import (
    actor_schedule, actor_workers, check_runtime, freeze_runtime, live_dependencies,
    load_bundle, semantic_request_options, STREAM_PROTOCOL, update_profile,
)
from .continual_state import finish_round, gate_round, initial_state, open_round, read_state, write_state
from .diagnosis_editor import parse_json_response
from .grouped_representation import build_grouping_input, freeze_grouping
from .grouped_update import (
    PROFILE, accept_diagnosis, compile_update, diagnosis_payload, grouped_messages, identity_update,
    learn_grouped_memory, materialize_skill, prepare_current, prepare_grouped_learning,
    realize_editor, update_payload,
)
from .run_round import cost_summary
from .train_response_update import normalize_editor
from .verify_round import verify_call


SCHEMA = "v22.continual_campaign.v1"
DEFAULT_PLAN = REPO_ROOT / "experiments/methods/v22/08_grouped_continual/config/plan_parallel8.json"
STAGES = {"diagnosis": "diagnosis", "fusion": "fusion", "main_editor": "editor", "post_gate_learning": "learn"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def freeze_files(root, destination, *, exclude=()):
    """Freeze completed artifacts, not mutable progress reports or request ledgers."""
    files = {str(path.relative_to(root)): digest(path.read_bytes())
             for path in sorted(root.rglob("*")) if path.is_file()
             and path != destination and str(path.relative_to(root)) not in exclude}
    value = {"files": files, "created_at": timestamp()}
    write_record(destination, value)
    return value


def check_files(root, frozen):
    for relative, checksum in frozen["files"].items():
        path = root / relative
        require(path.is_file() and digest(path.read_bytes()) == checksum,
                "Frozen artifact changed: " + relative)


def _same_skill(actual, expected):
    return all(actual[key] == expected[key] for key in ("mode", "skill_id", "sha256", "text"))


def _editor_result(raw, payload):
    """Reuse existing formatting-only fixes; identical text is an explicit no-op."""
    value = deepcopy(raw)
    identical = (value.get("decision") == "candidate"
                 and value.get("candidate_text") == payload["parent"].get("text")
                 and bool(value.get("candidate_text")))
    if identical:
        value.update(decision="no_change", candidate_text=None)
        for mapping in value.get("mappings", []):
            if mapping.get("side") == "candidate":
                mapping["side"] = "parent"
    return normalize_editor(value, payload), identical


def _cost(root, report):
    total = {"episodes_dispatched": 0, "environment_requests": 0, "semantic_calls": 0,
             "semantic_calls_dispatched": 0, "http_attempts": 0,
             "requests_with_unknown_usage": 0, "http_attempts_with_unknown_usage": 0,
             "episodes_without_readable_trace": 0, "semantic_dispatches_without_call_record": 0,
             "requests_without_transport_records": 0, "reported_usage": {}}
    for row in report["rounds"]:
        directory = root / "rounds" / f"r{row['round']}"
        records = []
        for path in directory.glob("*_runs/**/trajectory.json"):
            try:
                records.append(read(path))
            except (OSError, ValueError):
                pass  # Dispatch remains counted and missing telemetry remains unknown.
        local = cost_summary(records, [], directory)
        for key in ("environment_requests", "semantic_calls", "http_attempts", "requests_with_unknown_usage",
                    "http_attempts_with_unknown_usage"):
            total[key] += local[key]
        total["episodes_dispatched"] += len(row["episode_attempts"])
        total["semantic_calls_dispatched"] += len(row["stages"])
        total["episodes_without_readable_trace"] += max(0, len(row["episode_attempts"]) - len(records))
        total["semantic_dispatches_without_call_record"] += max(0, len(row["stages"]) - local["semantic_calls"])
        streams = [event for record in records for event in record.get("steps", [])]
        for path in (directory / "calls").glob("*.json"):
            streams.extend(read(path).get("steps", []))
        total["requests_without_transport_records"] += sum(not event.get("transport_attempts") for event in streams)
        for key, count in local["reported_usage"].items():
            total["reported_usage"][key] = total["reported_usage"].get(key, 0) + count
    total["logical_requests_recorded"] = total["environment_requests"] + total["semantic_calls"]
    total["scope"] = "All rounds, partial traces and failed calls included; missing telemetry and unknown usage are not zero cost."
    return total


def _claim_prepared_runtime(bundle, root, *, offline):
    """Start an untouched preflight directory once; this is not a resume path."""
    expected = {"runtime_freeze.json", "source_snapshot", "config_snapshot"}
    require(root.is_dir() and {path.name for path in root.iterdir()} == expected,
            "Prepared directory must contain only its unused runtime freeze and snapshots; no resume is supported.")
    frozen = read(root / "runtime_freeze.json")
    require(frozen["artifact_root"] == str(root)
            and frozen["mode"] == ("offline_synthetic" if offline else "live"),
            "Prepared runtime root or execution mode differs.")
    check_runtime(frozen)
    require(load_bundle(bundle["plan_path"]) == bundle
            and frozen["plan"] == bundle["plan"]
            and frozen["plan_path"] == bundle["plan_path"]
            and [{key: value for key, value in binding.items() if key != "snapshot"}
                 for binding in frozen["bindings"]] == bundle["bindings"],
            "Prepared runtime differs from the requested bundle.")
    # Exclusive creation prevents two processes from starting the same frozen
    # campaign, including when both passed the directory check concurrently.
    with (root / "start_claim.json").open("x", encoding="utf-8") as stream:
        json.dump({"schema_version": "v22.prepared_start.v1", "started_at": timestamp(),
                   "runtime_sha256": frozen["sha256"]}, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return frozen


def run_campaign(bundle, output_dir, generate, execute, *, offline=False, prepared=False):
    """Run the fixed campaign once, saving every transition before dispatch.

    generate(stage, messages, output_path) saves semantic_call's record and returns
    raw text. execute(task_item, skill_file_or_None, output_root) returns the one
    saved trajectory, including a partial trajectory after a technical failure.
    ``offline`` labels synthetic dependency injection; it does not mock callbacks.
    ``prepared`` consumes an untouched preflight in this same directory once.
    """
    root = Path(output_dir).resolve()
    bundle = deepcopy(bundle)
    if prepared:
        frozen_runtime = _claim_prepared_runtime(bundle, root, offline=offline)
    else:
        root.mkdir(parents=True, exist_ok=False)
    plan = bundle["plan"]
    profile = update_profile(plan)
    report = {"schema_version": SCHEMA, "status": "starting", "started_at": timestamp(),
              "offline": offline, "actor_schedule": actor_schedule(plan),
              "published_rounds": 0, "latest_state": None, "rounds": []}
    state = initial_state("campaign-" + object_digest({"root": str(root), "plan": plan})[:16])
    row = None

    def save():
        report["cost"] = _cost(root, report)
        for item in report["rounds"]:
            write_record(root / "rounds" / f"r{item['round']}" / "report.json", item)
        write_record(root / "report.json", report)

    try:
        write_record(root / "plan.json", plan)
        require(offline or plan["freeze"]["implementation_ready"] is True,
                "The declared implementation is not ready for a live campaign.")
        if not prepared:
            frozen_runtime = freeze_runtime(bundle, root, offline=offline)
        write_state(root / "state0.json", state)
        report.update(status="running", latest_state=str(root / "state0.json"))
        save()
        for number, declared in enumerate(plan["rounds"], 1):
            state = read_state(report["latest_state"])
            context = open_round(state, plan["data"][f"round{number}_task_ids"])
            directory = root / "rounds" / f"r{number}"
            directory.mkdir(parents=True)
            for name in ("inputs", "messages", "raw_outputs", "outputs", "calls"):
                (directory / name).mkdir()
            row = {"round": number, "status": "running", "active_stage": "parent_execution",
                   "stages": [], "episode_attempts": [], "update_status": None}
            report["rounds"].append(row)
            write_record(directory / "context.json", context)
            write_record(directory / "parent.json", context["parent"])
            write_record(directory / "memory_before.json", context["memory"])
            parent_file = materialize_skill(context["parent"], directory / "parent/SKILL.md")
            round_start = freeze_files(directory, directory / "round_start.json", exclude=("report.json",))
            guarded = round_start

            def check():
                check_runtime(frozen_runtime)
                require(read(root / "plan.json") == plan, "Saved campaign plan changed.")
                check_files(directory, guarded)
                require(read_state(report["latest_state"])["sha256"] == context["state_sha256"],
                        "Published Parent/Memory changed during the round.")

            def invoke(stage, payload):
                check()
                row["active_stage"] = stage
                write_record(directory / "inputs" / f"{stage}.json", payload)
                if stage == "classification":
                    messages = [{"role": "system", "content": bundle["grouping_prompt"]},
                                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}]
                else:
                    messages = grouped_messages(STAGES[stage], payload)
                require(messages[0]["content"] == frozen_runtime["system_prompts"][stage]["text"],
                        "Stage prompt differs from the runtime freeze.")
                write_record(directory / "messages" / f"{stage}.json", messages)
                require(len(json.dumps(messages, ensure_ascii=False, separators=(",", ":")))
                        <= plan["budget"]["evolution_input_unicode_chars_max"], "Evolution input exceeds the frozen character budget.")
                require(stage not in row["stages"] and declared["stage_calls_max"].get(stage) == 1,
                        "Undeclared or repeated semantic stage.")
                require(len(row["stages"]) < declared["semantic_calls_max"]
                        and sum(len(r["stages"]) for r in report["rounds"]) < plan["budget"]["semantic_calls_max"],
                        "Semantic call budget exhausted.")
                row["stages"].append(stage)
                save()
                path = directory / "calls" / f"{stage}.json"
                raw = generate(stage, deepcopy(messages), path)
                require(isinstance(raw, str), "Semantic response must be text.")
                (directory / "raw_outputs" / f"{stage}.txt").write_text(raw, encoding="utf-8")
                value = parse_json_response(raw)
                write_record(directory / "raw_outputs" / f"{stage}.json", value)
                verify_call(path, stage, plan["models"]["evolution"], messages, value,
                            **semantic_request_options(plan, stage))
                require(read(path)["steps"][0]["model_response"].get("response_model") == plan["models"]["evolution"],
                        "Evolution response model mismatch.")
                require(read(directory / "inputs" / f"{stage}.json") == payload
                        and read(directory / "messages" / f"{stage}.json") == messages,
                        "Semantic input artifact changed during the call.")
                check()
                return value

            def batch(side, skill, skill_file):
                # Workers only execute independent slots. Dispatch, validation,
                # reports and record ordering remain owned by this main thread.
                records, pending = {}, {}
                task_ids = context["task_ids"]
                next_slot, failure = 0, None
                row["active_stage"] = side + "_execution"

                def dispatch(pool, task_id):
                    check()
                    require(_same_skill(load_skill(skill_file), skill), "Injected Skill changed after freezing.")
                    require(len(row["episode_attempts"]) < declared["episodes_max"]
                            and sum(len(r["episode_attempts"]) for r in report["rounds"])
                            < plan["budget"]["environment_episodes_max"], "Episode budget exhausted.")
                    require(not any(a["side"] == side and a["task_id"] == task_id for a in row["episode_attempts"]),
                            "Repeated task/Skill execution is not permitted.")
                    target = directory / f"{side}_runs" / task_id.replace(":", "_")
                    attempt = {"side": side, "task_id": task_id, "output_root": str(target), "status": "dispatched",
                               "dispatched_at": timestamp()}
                    row["episode_attempts"].append(attempt)
                    save()
                    future = pool.submit(execute, deepcopy(bundle["task_items"][task_id]), skill_file, target)
                    pending[future] = (task_id, attempt, target)

                def collect(future):
                    nonlocal failure
                    task_id, attempt, target = pending.pop(future)
                    try:
                        path = Path(future.result()).resolve()
                        require(path.is_relative_to(target.resolve()), "Execution returned a trajectory outside its declared slot.")
                        require(len(list(target.rglob("trajectory.json"))) == 1, "Execution slot must contain exactly one trajectory.")
                        record = read(path)
                        attempt.update(trajectory=str(path), sha256=digest(path.read_bytes()), status=record.get("status"))
                        audit = verify_record(record)
                        if plan["protocol"] == STREAM_PROTOCOL:
                            require(record.get("response_archival") == "raw_http_body_v1"
                                    and all(event.get("response_archive") is True for event in record["steps"]),
                                    "Streaming Actor responses lack their archival identity.")
                            for event in record["steps"]:
                                for transport in event.get("transport_attempts", []):
                                    verify_response_archive(path, transport)
                        require(record["task"] == bundle["task_items"][task_id] and record["split"] == "train"
                                and record["purpose"] == "learning" and _same_skill(record["skill"], skill),
                                "Execution task, purpose or actual Skill differs from the declared slot.")
                        require(record["model"] == plan["models"]["actor"]
                                and record["protocol"] == execution_protocol(plan["budget"]["max_steps_per_episode"]),
                                "Actor execution profile differs from the frozen plan.")
                        require(all(e.get("model_response", {}).get("response_model") == plan["models"]["actor"]
                                    for e in record["steps"] if e.get("phase") == "executed"), "Actor response model mismatch.")
                        require(audit["episode_complete"], "Incomplete episode stops the campaign; it is not a task failure.")
                        if not offline:
                            require(all(event.get("transport_attempts") for event in record["steps"]), "Missing Actor transport records.")
                            require(record["versions"] == frozen_runtime["runtime"]["versions"]
                                    and record["implementation"] == frozen_runtime["runtime"]["implementation"],
                                    "Actor implementation/dependencies differ from the runtime freeze.")
                            game = next(item for item in frozen_runtime["game_files"] if item["task_id"] == task_id)
                            require(record["environment"]["game_sha256"] == game["sha256"]
                                    and record["environment"]["manifest_sha256"] == bundle["bindings"][-1]["sha256"],
                                    "Actor task data differs from the frozen environment.")
                        check()
                        require(_same_skill(load_skill(skill_file), skill), "Skill changed during execution.")
                        records[task_id] = record
                    except (Exception, KeyboardInterrupt) as exc:
                        if failure is None:
                            failure = exc
                        attempt.update(validation_error=True, error_type=type(exc).__name__)
                        if attempt["status"] == "dispatched":
                            attempt["status"] = "error"
                    finally:
                        attempt["settled_at"] = timestamp()
                        save()

                with ThreadPoolExecutor(max_workers=actor_workers(plan)) as pool:
                    try:
                        while pending or next_slot < len(task_ids):
                            # Collect every already finished slot before replacing
                            # workers, so an observed error cannot be followed by a dispatch.
                            if pending:
                                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                                for future in sorted(done, key=lambda f: task_ids.index(pending[f][0])):
                                    collect(future)
                            if failure is not None:
                                break
                            while len(pending) < actor_workers(plan) and next_slot < len(task_ids):
                                dispatch(pool, task_ids[next_slot])
                                next_slot += 1
                    except (Exception, KeyboardInterrupt) as exc:
                        if failure is None:
                            failure = exc
                    finally:
                        # Do not cancel or forget paid work. Drain already dispatched
                        # jobs before saving failure and never enter a semantic stage.
                        for future in list(pending):
                            collect(future)
                        write_record(directory / f"{side}_sources.json",
                                     [a for a in row["episode_attempts"] if a["side"] == side])
                if failure is not None:
                    raise failure
                return [records[task_id] for task_id in task_ids]

            parents = batch("parent", context["parent"], parent_file)
            current = prepare_current(context, parents, profile=profile)
            grouping_input = build_grouping_input(current, context["round_id"], plan["classification"]["alias_seed"])
            write_record(directory / "grouping_input.json", grouping_input)
            guarded = freeze_files(directory, directory / "classification_freeze.json", exclude=("report.json",))
            result = invoke("classification", grouping_input["model_input"])
            grouping = freeze_grouping(result, grouping_input, bundle["grouping_prompt"])
            write_record(directory / "outputs/classification.json", result)
            write_record(directory / "grouping.json", grouping)
            guarded = freeze_files(directory, directory / "evidence_freeze.json", exclude=("report.json",))
            current = diagnosis_payload(context, parents, grouping, profile=profile)
            diagnosis = accept_diagnosis(invoke("diagnosis", current), current)
            write_record(directory / "outputs/diagnosis.json", diagnosis)
            candidate, candidate_file, candidates = None, None, []
            editor = None
            row["update_status"] = diagnosis["decision"]
            effective = diagnosis["plan"] or {"intent": "No constructed update: " + diagnosis["reason"],
                                              "requirements": [], "watch": [], "open": []}
            write_record(directory / "initial_plan.json", diagnosis["plan"])
            guarded = freeze_files(directory, directory / "diagnosis_freeze.json", exclude=("report.json",))
            if diagnosis["decision"] == "revise":
                payload = update_payload(context, current, effective)
                if number == 1:
                    fusion, effective = identity_update(payload)
                else:
                    fusion = invoke("fusion", payload)
                    effective = compile_update(fusion, payload)
                write_record(directory / "outputs/fusion.json", fusion)
                write_record(directory / "effective_plan.json", effective)
                guarded = freeze_files(directory, directory / "effective_freeze.json", exclude=("report.json",))
                row["fusion"] = {"origin": "program_identity" if number == 1 else "model",
                    "requirements_changed": effective["requirements"] != diagnosis["plan"]["requirements"],
                    "history_cited": sorted({ref for change in fusion["changes"] for ref in change["basis"]
                                             if ref in {effect["id"] for effect in context["memory"]}})}
                row["update_status"] = fusion["decision"]
                if fusion["decision"] == "ready" and not effective["requirements"]:
                    # Keep retains the original requirements and still reaches Editor.
                    # A complete, justified withdrawal instead has no edit to execute.
                    require(profile != PROFILE, "Empty effective update requires the unified profile.")
                    row["update_status"] = "no_effective_update"
                elif fusion["decision"] == "ready":
                    payload = update_payload(context, current, effective)
                    raw_editor = invoke("main_editor", payload)
                    editor, identical = _editor_result(raw_editor, payload)
                    write_record(directory / "outputs/main_editor.json", editor)
                    row["editor_normalization"] = {"identical_text_no_change": identical,
                                                    "changed": raw_editor != editor}
                    row["update_status"] = editor["decision"]
                    if editor["decision"] != "needs_revision":
                        candidate, effective = realize_editor(editor, payload)
                    else:
                        effective = deepcopy(effective)
                        effective["watch"].extend(deepcopy(editor["watch"]))
            if not (directory / "effective_plan.json").exists():
                write_record(directory / "effective_plan.json", effective)
            write_record(directory / "execution_plan.json", effective)
            write_record(directory / "candidate.json", candidate)
            if candidate is not None:
                candidate_file = materialize_skill(candidate, directory / "candidate/SKILL.md")
                (directory / "candidate/actual.diff").write_bytes(make_diff(context["parent"], candidate).encode("utf-8"))
            replay_frozen = freeze_files(directory, directory / "replay_freeze.json", exclude=("report.json",))
            guarded = replay_frozen
            if candidate is not None:
                candidates = batch("candidate", candidate, candidate_file)
            check_files(directory, replay_frozen)
            row["active_stage"] = "gate"
            gate = gate_round(context, candidate, parents, candidates)
            write_record(directory / "gate.json", gate)
            row["gate"] = {"decision": gate["decision"], "reason": gate["reason"], "successes": gate["successes"]}
            save()
            learning_input = prepare_grouped_learning(
                context, grouping, effective, candidate, parents, candidates, gate,
                editor=editor if profile != PROFILE else None, profile=profile)
            write_record(directory / "learning_input.json", learning_input)
            guarded = freeze_files(directory, directory / "learning_freeze.json", exclude=("report.json",))
            if candidate is None and not context["memory"]:
                learning = {"findings": [], "open": [{"about": [watch["id"]],
                            "reason": "No Candidate was constructed; update response was not evaluated."}
                            for watch in effective["watch"]], "memory_delta": []}
                row["learning_origin"] = "program_empty_memory_no_candidate"
            else:
                learning = invoke("post_gate_learning", learning_input)
                row["learning_origin"] = "model"
            memory, receipt = learn_grouped_memory(learning_input, learning)
            write_record(directory / "outputs/post_gate_learning.json", learning)
            write_record(directory / "memory_after.json", memory)
            write_record(directory / "memory_receipt.json", receipt)
            check()
            check_files(directory, replay_frozen)
            # Bind all executed and learned sources before publishing either state component.
            final_frozen = freeze_files(directory, directory / "final_freeze.json", exclude=("report.json",))
            check_files(directory, final_frozen)
            next_state = finish_round(state, context, candidate, gate, memory, receipt)
            write_state(directory / "state.json", next_state)
            report.update(published_rounds=number, latest_state=str(directory / "state.json"))
            row.update(status="published", active_stage=None)
            save()
        report.update(status="completed")
    except (Exception, KeyboardInterrupt) as exc:
        status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "error"
        report.update(status=status, error_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            report["validation_error"] = str(exc)
        if row is not None:
            row["status"] = status
        # Raw transport records carry technical errors; do not put credentials in summaries.
    finally:
        report["finished_at"] = timestamp()
        save()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "run", "verify"))
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    parser.add_argument("--prepared", action="store_true",
                        help="Start an untouched preflight directory once; not a failed-run resume.")
    args = parser.parse_args(argv)
    if args.prepared and args.command != "run":
        parser.error("--prepared is only valid with run.")
    if args.command == "verify":
        from .continual_verify import verify_campaign
        print(json.dumps(verify_campaign(args.output_dir), ensure_ascii=False, indent=2))
        return 0
    bundle = load_bundle(args.plan)
    if args.command == "preflight":
        from dotenv import load_dotenv
        load_dotenv(args.env_file.expanduser().resolve(), override=False)
        args.output_dir.mkdir(parents=True, exist_ok=False)
        freeze_runtime(bundle, args.output_dir)
        print("Preflight saved; no model calls or environment episodes. After authorization, use run --prepared with this same output directory.")
        return 0
    generate, execute = live_dependencies(bundle, args.env_file)
    report = run_campaign(bundle, args.output_dir, generate, execute, prepared=args.prepared)
    print(json.dumps({"status": report["status"], "published_rounds": report["published_rounds"],
                      "report": str(args.output_dir.resolve() / "report.json"), "cost": report["cost"]}, ensure_ascii=False))
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

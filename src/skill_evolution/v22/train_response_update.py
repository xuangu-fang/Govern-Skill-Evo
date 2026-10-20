"""One bounded, same-information construction from audited Train feedback.

The caller owns source bindings, execution, learning and the later freeze. This
module makes at most five recorded evolution calls and never runs an episode.
"""

from copy import deepcopy
from pathlib import Path

from src.adapters.alfworld.run_task_skill import timestamp
from src.adapters.alfworld.skill_runtime import load_skill, object_digest, write_record
from src.adapters.alfworld.verify_skill_run import require
from .compact_cycle import fusion_input, make_diff, read
from .compact_update import apply_fusion, validate_diagnosis
from .conditional_trial import ARMS, STAGES, messages_for
from .diagnosis_editor import parse_json_response
from .editor_span_reconciliation import NORMALIZATION as SPAN_NORMALIZATION, normalize_numbered_spans
from .editor_watch_reconciliation import NORMALIZATION as WATCH_NORMALIZATION, normalize_inherited_watch
from .run_round import cost_summary
from .verify_round import verify_call


def normalize_editor(value, payload):
    """Compose two formatting-only policies, then validate the complete document.

    The span helper itself validates Editor output, so inherited watch echoes are
    temporarily held aside and restored before the unchanged watch helper checks
    them. No watch text is edited and every new question is fully validated.
    """
    require(isinstance(value, dict) and isinstance(value.get("watch"), list), "Editor watch must be an array.")
    intermediate = deepcopy(value)
    intermediate["watch"] = []
    normalized = normalize_numbered_spans(intermediate, payload)
    normalized["watch"] = deepcopy(value["watch"])
    normalized = normalize_inherited_watch(normalized, payload)
    require({key: item for key, item in normalized.items() if key not in {"mappings", "watch"}} ==
            {key: item for key, item in value.items() if key not in {"mappings", "watch"}},
            "Formatting normalization changed semantic fields.")
    return normalized


def _train_inputs(current, memory):
    require(isinstance(current, dict) and isinstance(current.get("runs"), dict) and current["runs"],
            "Construction requires current Parent Train runs.")
    require(not current.get("memory"), "Diagnosis input must not contain Memory.")
    for alias, run in current["runs"].items():
        require(alias.startswith("P") and run.get("task_id", "").startswith("train:")
                and run.get("episode_complete") is True, "Current input must contain complete Parent Train only.")
    require(isinstance(memory, list), "Memory must be an array.")
    for effect in memory:
        for basis in effect.get("basis", []):
            for source in basis.get("sources", {}).values():
                if isinstance(source, dict) and "task_id" in source:
                    require(source["task_id"].startswith("train:"), "Historical task evidence must be Train only.")


def _error(exc):
    result = {"status": "interrupted" if isinstance(exc, KeyboardInterrupt) else "error",
              "error_type": type(exc).__name__}
    if isinstance(exc, ValueError):
        result["validation_error"] = str(exc)
    return result


def construct(root, current, memory, generate, model="deepseek-v4-pro"):
    """Construct two staged arms with a shared Diagnosis and fixed historical state.

    ``generate(stage, messages, output_path)`` must save the existing semantic_call
    record at output_path and return the raw text. ``ready_arms`` contains only
    validated Candidate/no_change arms; no Parent arm is automatically added.
    ``skill_file`` is relative to root, or None for No Skill. A new root is required.
    """
    _train_inputs(current, memory)
    require(isinstance(model, str) and bool(model.strip()), "Evolution model is required.")
    current, memory = deepcopy(current), deepcopy(memory)
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    for name in ("inputs", "raw_outputs", "outputs", "calls", "candidates"):
        (root / name).mkdir()
    write_record(root / "current.json", current)
    write_record(root / "memory.json", memory)
    write_record(root / "contract.json", {
        "schema_version": "v22.train_response_update.v1", "model": model,
        "semantic_calls_max": 5, "semantic_retries": 0, "branch_order": list(ARMS),
        "profile": "v22.conditional_update.v1",
        "editor_normalizations": [WATCH_NORMALIZATION, SPAN_NORMALIZATION],
        "current_sha256": object_digest(current), "memory_sha256": object_digest(memory),
        "execution": "No episodes, adoption, or automatic freeze in this construction module.",
    })
    report = {"status": "constructing", "started_at": timestamp(), "active_stage": None,
              "stages": [], "branches": {}, "ready_arms": {}, "adoption": "staging_only"}

    def save():
        report["cost"] = cost_summary([], [], root)
        write_record(root / "report.json", report)

    def invoke(stage, payload):
        require(stage in STAGES and stage not in report["stages"] and len(report["stages"]) < 5,
                "Duplicate or excess semantic stage.")
        report["stages"].append(stage)
        report["active_stage"] = stage
        write_record(root / "inputs" / f"{stage}.json", payload)
        save()
        messages = messages_for(stage, payload)
        path = root / "calls" / f"{stage}.json"
        raw = generate(stage, messages, path)
        require(isinstance(raw, str), "Semantic response must be text.")
        (root / "raw_outputs" / f"{stage}.txt").write_text(raw, encoding="utf-8")
        value = parse_json_response(raw)
        write_record(root / "raw_outputs" / f"{stage}.json", value)
        verify_call(path, stage, model, messages, value)
        require(read(path)["steps"][0]["model_response"]["response_model"] == model,
                "Evolution response model mismatch.")
        return value

    save()
    try:
        diagnosis = validate_diagnosis(invoke("diagnosis", current), current)
        write_record(root / "outputs/diagnosis.json", diagnosis)
        if diagnosis["decision"] != "revise":
            report.update(status=diagnosis["decision"], stop_reason=diagnosis["reason"])
            return report
        initial = diagnosis["plan"]
        write_record(root / "initial_plan.json", initial)
        for arm in ARMS:
            branch = report["branches"][arm] = {"status": "constructing"}
            try:
                payload = fusion_input(current, initial, memory)
                proposal = invoke(arm + "_proposal", payload)
                effective = apply_fusion(proposal, payload)
                write_record(root / "outputs" / f"{arm}_proposal.json", proposal)
                write_record(root / f"{arm}_plan.json", effective)
                memory_ids = {effect["id"] for effect in memory}
                branch.update(requirements_changed=effective["requirements"] != initial["requirements"],
                              requirement_text_changed=[row["text"] for row in effective["requirements"]] !=
                                                       [row["text"] for row in initial["requirements"]],
                              history_cited=sorted({ref for change in proposal["changes"] for ref in change["basis"]
                                                    if ref in memory_ids}))
                if proposal["decision"] != "ready" or effective["open"]:
                    branch.update(status="needs_revision", reason=proposal["reason"])
                    continue
                editor_payload = fusion_input(current, effective, memory)
                raw_editor = invoke(arm + "_editor", editor_payload)
                editor = normalize_editor(raw_editor, editor_payload)
                write_record(root / "outputs" / f"{arm}_editor.json", editor)
                branch.update(status=editor["decision"], reason=editor["reason"],
                              removed_exact_watch_echoes=len(raw_editor["watch"]) - len(editor["watch"]),
                              extra_exact_mapping_spans=len(editor["mappings"]) - len(raw_editor["mappings"]))
                if editor["decision"] == "candidate":
                    directory = root / "candidates" / arm
                    directory.mkdir()
                    skill_file = directory / "SKILL.md"
                    skill_file.write_bytes(editor["candidate_text"].encode("utf-8"))
                    skill = load_skill(skill_file)
                    (directory / "actual.diff").write_bytes(make_diff(current["parent"], skill).encode("utf-8"))
                    watch = deepcopy(effective["watch"]) + deepcopy(editor["watch"])
                    write_record(directory / "observation_plan.json", {"watch": watch, "origin": "before_train_replay"})
                    branch.update(skill_file=str(skill_file.relative_to(root)), skill_id=skill["skill_id"])
                    report["ready_arms"][arm] = {"skill_file": branch["skill_file"], "skill_id": skill["skill_id"],
                                                 "decision": "candidate"}
                elif editor["decision"] == "no_change":
                    skill_file = None
                    if current["parent"].get("text") is not None:
                        directory = root / "parent"
                        directory.mkdir(exist_ok=True)
                        skill_file = directory / "SKILL.md"
                        if not skill_file.exists():
                            skill_file.write_bytes(current["parent"]["text"].encode("utf-8"))
                    skill = load_skill(skill_file)
                    require(skill["skill_id"] == current["parent"]["skill_id"], "Parent snapshot identity mismatch.")
                    report["ready_arms"][arm] = {"skill_file": str(skill_file.relative_to(root)) if skill_file else None,
                                                 "skill_id": skill["skill_id"], "decision": "no_change"}
            except Exception as exc:
                branch.update(_error(exc))
            finally:
                save()
        report["status"] = "constructed" if len(report["ready_arms"]) == len(ARMS) else "comparison_incomplete"
    except (Exception, KeyboardInterrupt) as exc:
        report.update(_error(exc))
    finally:
        report.update(active_stage=None, finished_at=timestamp())
        save()
    return report

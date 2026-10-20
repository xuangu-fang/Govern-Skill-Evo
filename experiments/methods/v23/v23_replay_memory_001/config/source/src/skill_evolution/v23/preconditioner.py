"""V23 Plan adjustments and deterministic compilation; with shared historical Memory sources."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from .diagnosis import diagnosis_input, fields, links, load_diagnosis, validate_diagnosis
from .facts import require, text
from .grouping import call_configuration, live_generator, load_grouping, references
from .prompts import render_prompt
from .memory import empty_memory, validate_memory


PROMPT_PATH = Path(__file__).with_name("preconditioner_prompt.md")


def preconditioner_input(saved, *, memory=None):
    """Select whole referenced executions without expanding Group membership."""
    memory = deepcopy(saved.get("memory", empty_memory()) if memory is None else memory)
    validate_memory(memory)
    facts = diagnosis_input(saved)
    validate_diagnosis(saved["diagnosis"], facts)
    require(saved["diagnosis"]["decision"] == "revise", "Preconditioner requires a revise Diagnosis")
    plan = saved["diagnosis"]["plan"]
    encoded = json.dumps(plan, ensure_ascii=False)
    run_ids = {ref.split(":", 1)[0] for ref in references(encoded)}
    group_ids = set(re.findall(r"\bG\d+\b", encoded))
    runs = [run for run in facts["runs"] if run["ref"] in run_ids]
    groups = [g for g in facts["grouping"]["groups"]
              if g["group_id"] in group_ids or run_ids.intersection(g["members"])]
    menus = set()
    for run in runs:
        for state in [run["initial"], *[s[side] for s in run["steps"] for side in ("before", "after")]]:
            if state["commands_ref"] is not None:
                menus.add(state["commands_ref"])
    return deepcopy({"parent": facts["parent"], "plan": plan,
                     "command_sets": {k: v for k, v in facts["command_sets"].items() if k in menus},
                     "runs": runs, "grouping": {"groups": groups}, "memory": memory})


def messages_for(saved):
    return [{"role": "system", "content": render_prompt(PROMPT_PATH.read_text(encoding="utf-8"), saved["background"])},
            {"role": "user", "content": json.dumps(preconditioner_input(saved), ensure_ascii=False, separators=(",", ":"))}]


def compile_effective_plan(result, payload):
    """Validate simultaneous adjustments and compile; semantic stops return None."""
    fields(payload, ("parent", "plan", "command_sets", "runs", "grouping", "memory"), "Input")
    # [] is accepted only for validating frozen no-history results; new requests
    # are assembled with the formal object by preconditioner_input().
    memory = empty_memory() if payload["memory"] == [] else payload["memory"]
    history_refs = validate_memory(memory)
    original = payload["plan"]
    validate_diagnosis({"decision": "revise", "reason": "Original Plan", "plan": original}, payload)
    allowed = set(payload["command_sets"]) | {g["group_id"] for g in payload["grouping"]["groups"]}
    allowed.update(entry["id"] for entry in memory["entries"])
    for run in payload["runs"]:
        allowed.update([run["ref"], f"{run['ref']}:0", f"{run['ref']}:outcome", *[s["step"] for s in run["steps"]]])

    def prose(value, name):
        text(value, name)
        historical = set(re.findall(r"[A-Za-z0-9_-]+/(?:diff|[PQ]\d+(?::[A-Za-z0-9_]+)?)", value))
        require(historical <= history_refs, f"{name}: unavailable historical reference")
        for ref in sorted(historical, key=len, reverse=True):
            value = value.replace(ref, "")
        refs = references(value) | set(re.findall(r"\b[CGM]\d+\b", value))
        require(refs <= allowed, f"{name}: unavailable evidence reference")

    fields(result, ("decision", "reason", "adjustments", "checks"), "Preconditioner")
    require(result["decision"] in ("ready", "no_change", "need_evidence"), "Unknown decision")
    prose(result["reason"], "reason")
    require(isinstance(result["adjustments"], list), "adjustments must be an array")
    if result["decision"] == "need_evidence":
        require(result["adjustments"] == [] and result["checks"] is None,
                "need_evidence requires adjustments=[] and checks=null")
        return None

    originals = {u["id"]: u for u in original["updates"]}
    positions = {u["id"]: i for i, u in enumerate(original["updates"])}
    consumed, produced, replacements = set(), set(), {}
    for adjustment in result["adjustments"]:
        fields(adjustment, ("from", "to", "basis", "reason"), "Adjustment")
        links(adjustment["from"], originals, "adjustment.from")
        source_ids = set(adjustment["from"])
        require(not consumed.intersection(source_ids), "Original Update adjusted more than once")
        consumed.update(source_ids)
        require(isinstance(adjustment["to"], list), "adjustment.to must be an array")
        links(adjustment["basis"], allowed, "adjustment.basis")
        prose(adjustment["reason"], "adjustment.reason")
        # Use original Plan order, not model-supplied from order, for stable lineage.
        basis = list(dict.fromkeys(ref for u in original["updates"] if u["id"] in source_ids for ref in u["basis"]))
        new = []
        for update in adjustment["to"]:
            fields(update, ("id", "text"), "Replacement Update")
            uid = text(update["id"], "update.id")
            retain = len(source_ids) == len(adjustment["to"]) == 1 and uid in source_ids
            require(uid not in produced and uid not in allowed, "Duplicate or evidence-colliding Update ID")
            require(uid not in originals or retain, "Only one-to-one replacement may retain its own original ID")
            produced.add(uid)
            prose(update["text"], "update.text")
            new.append({"id": uid, "text": update["text"], "basis": deepcopy(basis)})
        replacements[min(positions[uid] for uid in source_ids)] = new

    updates = []
    for i, update in enumerate(original["updates"]):
        if i in replacements:
            updates.extend(replacements[i])
        if update["id"] not in consumed:
            updates.append(deepcopy(update))
    if result["decision"] == "no_change":
        require(not updates and consumed == set(originals) and result["checks"] == [],
                "no_change requires explicit withdrawal of all Updates and checks=[]")
        return None
    require(bool(updates), "ready requires at least one effective Update")
    checks = deepcopy(original["checks"] if result["checks"] is None else result["checks"])
    effective = {"goal": original["goal"], "updates": updates, "checks": checks}
    # The existing validator checks fields, IDs and surviving Check references.
    validate_diagnosis({"decision": "revise", "reason": "Compiled effective Plan", "plan": effective}, payload)
    for check in checks:
        prose(check["question"], "check.question")
    return effective


def load_preconditioner(directory, *, expected_diagnosis=None, expected_call_config=...):
    """Return the original Plan, adjustments, compiled Plan and unchanged lineage."""
    directory = Path(directory)
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    saved = read("input.json")
    if expected_diagnosis is not None:
        require(saved == expected_diagnosis, "Preconditioner input differs from Diagnosis handoff")
    meta = read("run.json")
    messages = messages_for(saved)
    if "memory_contract" not in meta:
        # Known immutable historical source, never trust arbitrary stored prompts.
        legacy = Path(__file__).resolve().parents[3] / "experiments/methods/v23/v23_preconditioner_001/config/source/preconditioner_prompt.md"
        messages[0]["content"] = render_prompt(legacy.read_text(encoding="utf-8"), saved["background"])
        payload = preconditioner_input(saved)
        payload["memory"] = []
        messages[1]["content"] = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        require(meta.get("memory") == [], "Unsupported historical Memory contract")
    else:
        require(meta["memory_contract"] == "entries_sources" and meta["memory"] == saved["memory"], "Memory snapshot differs")
    require(read("messages.json") == messages, "Saved Preconditioner prompt/input differs")
    require((directory / "prompt.md").read_text(encoding="utf-8") == messages[0]["content"], "Saved prompt differs")
    meta = read("run.json")
    require(meta["round_id"] == saved["round_id"], "Source round differs")
    if expected_call_config is not ...:
        require(meta["call_config"] == expected_call_config, "Saved Preconditioner call configuration differs")
    require(read("validation.json")["valid"] is True, "Saved Preconditioner is not valid")
    response = read("response.json")
    require(response.get("finish_reason") == "stop", "Saved response did not finish normally")
    require((directory / "raw_output.txt").read_text(encoding="utf-8") == response["content"], "Raw output differs")
    parsed = parse_json_response(response["content"])
    require(read("parsed.json") == parsed and read("preconditioner.json") == parsed,
            "Saved result differs from original response")
    effective = compile_effective_plan(parsed, preconditioner_input(saved))
    require(read("effective_plan.json") == effective, "Saved Effective Plan differs from deterministic compilation")
    return {**saved, "preconditioner": parsed, "effective_plan": effective}


def read_upstream(grouping_directory, diagnosis_directory, *, legacy_templates=None):
    grouped = load_grouping(grouping_directory,
                            legacy_template=None if legacy_templates is None else legacy_templates["grouping"])
    return load_diagnosis(diagnosis_directory, expected_grouping=grouped, legacy_templates=legacy_templates)


def run_preconditioner(grouping_directory, diagnosis_directory, directory, *, generate,
                       max_input_chars=100000, call_config=None, legacy_templates=None, memory=None):
    saved = {**read_upstream(grouping_directory, diagnosis_directory, legacy_templates=legacy_templates),
             "memory": deepcopy(empty_memory() if memory is None else memory)}
    messages = messages_for(saved)
    size = len(json.dumps(messages, ensure_ascii=False))
    require(size <= max_input_chars, "Preconditioner input exceeds the declared character budget")
    generated_config = getattr(generate, "call_config", None)
    require(call_config is None or generated_config is None or call_config == generated_config,
            "Generator configuration differs from declared configuration")
    call_config = call_config if call_config is not None else generated_config
    directory = Path(directory)
    if directory.exists():
        return load_preconditioner(directory, expected_diagnosis=saved, expected_call_config=call_config)
    directory.mkdir(parents=True, exist_ok=False)
    write_record(directory / "input.json", saved)
    write_record(directory / "messages.json", messages)
    (directory / "prompt.md").write_text(messages[0]["content"], encoding="utf-8")
    meta = {"round_id": saved["round_id"], "grouping_directory": str(Path(grouping_directory).resolve()),
            "diagnosis_directory": str(Path(diagnosis_directory).resolve()), "memory": saved["memory"],
            "memory_contract": "entries_sources",
            "started_at": datetime.now(timezone.utc).isoformat(), "input_chars": size,
            "max_input_chars": max_input_chars, "call_config": call_config, "status": "requesting"}
    write_record(directory / "run.json", meta)
    try:
        response = generate(messages, directory)
        write_record(directory / "response.json", response)
        (directory / "raw_output.txt").write_text(response.get("content") or "", encoding="utf-8")
        require(response.get("finish_reason") == "stop", "Model response did not finish normally")
        parsed = parse_json_response(response["content"])
        write_record(directory / "parsed.json", parsed)
        effective = compile_effective_plan(parsed, preconditioner_input(saved))
        write_record(directory / "preconditioner.json", parsed)
        write_record(directory / "effective_plan.json", effective)
        write_record(directory / "validation.json", {"valid": True, "error": None})
        meta["status"] = "valid"
    except (Exception, KeyboardInterrupt) as exc:
        write_record(directory / "validation.json", {"valid": False, "error_type": type(exc).__name__,
                     "error": str(exc) if isinstance(exc, ValueError) else "Call failed; inspect preserved response and error type."})
        meta["status"] = "invalid"
        raise
    finally:
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_record(directory / "run.json", meta)
    return load_preconditioner(directory, expected_diagnosis=saved, expected_call_config=call_config)


def main(argv=None):
    import os
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grouping", type=Path, required=True)
    parser.add_argument("--diagnosis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--memory", type=Path, help="Memory Archive/Active directory")
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-input-chars", type=int, default=100000)
    args = parser.parse_args(argv)
    load_dotenv(args.env_file, override=False)
    config = call_configuration(base_url=os.environ.get("OPENAI_BASE_URL", ""), model=args.model,
                                max_tokens=args.max_tokens, timeout=args.timeout)
    generate = None if args.output.exists() else live_generator(base_url=os.environ.get("OPENAI_BASE_URL", ""),
                key=os.environ.get("OPENAI_API_KEY"), model=args.model, max_tokens=args.max_tokens, timeout=args.timeout)
    from .memory import load_memory
    memory = empty_memory() if args.memory is None else load_memory(args.memory)
    saved = run_preconditioner(args.grouping, args.diagnosis, args.output, generate=generate,
                              max_input_chars=args.max_input_chars, call_config=config, memory=memory)
    print(json.dumps({"preconditioner": saved["preconditioner"], "effective_plan": saved["effective_plan"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

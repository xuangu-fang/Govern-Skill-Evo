"""V23 Diagnosis: one current-evidence Plan, no history or downstream execution."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from .facts import require, text
from .grouping import (call_configuration, live_generator, load_grouping,
                       references, validate_grouping)
from .prompts import legacy_diagnosis_system, render_prompt


PROMPT_PATH = Path(__file__).with_name("diagnosis_prompt.md")


def diagnosis_input(saved):
    """Reuse the complete Grouping facts without private sources or any new summary."""
    require(set(saved["facts"]) == {"parent", "command_sets", "runs"}, "Unexpected shared fact fields")
    validate_grouping(saved["grouping"], saved["facts"])
    return deepcopy({**saved["facts"], "grouping": saved["grouping"]})


def messages_for(saved):
    system = render_prompt(PROMPT_PATH.read_text(encoding="utf-8"), saved["background"])
    return [{"role": "system", "content": system},
            {"role": "user", "content": json.dumps(diagnosis_input(saved), ensure_ascii=False, separators=(",", ":"))}]


def fields(value, expected, name):
    require(isinstance(value, dict) and set(value) == set(expected), f"{name}: unexpected fields")


def links(value, allowed, name):
    require(isinstance(value, list) and bool(value)
            and all(isinstance(x, str) and x in allowed for x in value), f"{name}: invalid references")
    require(len(value) == len(set(value)), f"{name}: duplicate references")


def validate_diagnosis(result, payload):
    return _validate_diagnosis(result, payload, check_field="update_ids")


def _validate_diagnosis(result, payload, *, check_field):
    """Validate structure and reference routing, not natural-language diagnosis."""
    fields(result, ("decision", "reason", "plan"), "Diagnosis")
    require(result["decision"] in ("revise", "no_change", "need_evidence"), "Unknown decision")
    text(result["reason"], "reason")
    groups = {g["group_id"]: set(g["members"]) for g in payload["grouping"]["groups"]}
    executions = {}
    for run in payload["runs"]:
        ref = run["ref"]
        for source in [ref, f"{ref}:0", f"{ref}:outcome", *[s["step"] for s in run["steps"]]]:
            executions[source] = ref
    allowed = set(groups) | set(executions)

    def prose_refs(value):
        require(references(value) <= set(executions), "Unknown execution reference in text")
        require(set(re.findall(r"\bG\d+\b", value)) <= set(groups), "Unknown group reference in text")

    prose_refs(result["reason"])
    if result["decision"] != "revise":
        require(result["plan"] is None, "Semantic stop requires plan=null")
        return result
    plan = result["plan"]
    fields(plan, ("goal", "updates", "checks"), "Plan")
    text(plan["goal"], "goal")
    prose_refs(plan["goal"])
    require(isinstance(plan["updates"], list) and bool(plan["updates"]), "revise requires updates")
    update_ids = set()
    for update in plan["updates"]:
        fields(update, ("id", "text", "basis"), "Update")
        uid = text(update["id"], "update.id")
        require(uid not in update_ids and uid not in allowed, "Duplicate or source-colliding Update ID")
        update_ids.add(uid)
        text(update["text"], "update.text")
        prose_refs(update["text"])
        links(update["basis"], allowed, "update.basis")
        evidence_members = {executions[r] for r in update["basis"] if r in executions}
        require(bool(evidence_members), "Update requires direct execution evidence")
        for ref in update["basis"]:
            if ref in groups:
                require(bool(groups[ref] & evidence_members), f"{ref} lacks member execution evidence")
    require(isinstance(plan["checks"], list), "checks must be an array")
    check_ids = set()
    for check in plan["checks"]:
        fields(check, ("id", check_field, "question"), "Check")
        cid = text(check["id"], "check.id")
        require(cid not in check_ids | update_ids | allowed, "Duplicate or colliding Check ID")
        check_ids.add(cid)
        links(check[check_field], update_ids, f"check.{check_field}")
        text(check["question"], "check.question")
        prose_refs(check["question"])
    return result


def load_diagnosis(directory, *, expected_grouping=None, legacy_templates=None, expected_call_config=...):
    """Return the unchanged initial Plan and its full current-evidence context."""
    directory = Path(directory)
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    saved = read("input.json")
    if expected_grouping is not None:
        require(saved == expected_grouping, "Diagnosis input differs from current Grouping handoff")
    messages = messages_for(saved)
    if legacy_templates is not None:
        messages[0]["content"] = legacy_diagnosis_system(saved["background"], legacy_templates)
    require(read("messages.json") == messages, "Saved Diagnosis prompt/input differs")
    require((directory / "prompt.md").read_text(encoding="utf-8") == messages[0]["content"], "Saved prompt differs")
    require(read("run.json")["grouping_round_id"] == saved["round_id"], "Grouping round differs")
    if expected_call_config is not ...:
        require(read("run.json").get("call_config") == expected_call_config, "Saved Diagnosis call configuration differs")
    require(read("validation.json")["valid"] is True, "Saved Diagnosis is not valid")
    response = read("response.json")
    require(response.get("finish_reason") == "stop", "Saved response did not finish normally")
    parsed = parse_json_response(response["content"])
    require(read("parsed.json") == parsed and read("diagnosis.json") == parsed,
            "Saved result differs from original response")
    payload = diagnosis_input(saved)
    if legacy_templates is not None:
        _validate_diagnosis(parsed, payload, check_field="about")
        parsed = deepcopy(parsed)
        if parsed["plan"] is not None:
            for check in parsed["plan"]["checks"]:
                check["update_ids"] = check.pop("about")
    result = validate_diagnosis(parsed, payload)
    return {"facts": saved["facts"], "background": saved["background"], "grouping": saved["grouping"],
            "sources": saved["sources"], "round_id": saved["round_id"], "diagnosis": result}


def run_diagnosis(grouping_directory, directory, *, generate, max_input_chars=100000, call_config=None):
    saved = load_grouping(grouping_directory)
    messages = messages_for(saved)
    size = len(json.dumps(messages, ensure_ascii=False))
    require(size <= max_input_chars, "Diagnosis input exceeds the declared character budget")
    directory = Path(directory)
    generated_config = getattr(generate, "call_config", None)
    require(call_config is None or generated_config is None or call_config == generated_config,
            "Generator configuration differs from declared configuration")
    call_config = call_config if call_config is not None else generated_config
    if directory.exists():
        return load_diagnosis(directory, expected_grouping=saved, expected_call_config=call_config)
    directory.mkdir(parents=True, exist_ok=False)
    write_record(directory / "input.json", saved)
    write_record(directory / "messages.json", messages)
    (directory / "prompt.md").write_text(messages[0]["content"], encoding="utf-8")
    meta = {"grouping_round_id": saved["round_id"], "grouping_directory": str(Path(grouping_directory).resolve()),
            "started_at": datetime.now(timezone.utc).isoformat(), "input_chars": size,
            "max_input_chars": max_input_chars, "status": "requesting", "call_config": call_config}
    write_record(directory / "run.json", meta)
    try:
        response = generate(messages, directory)
        write_record(directory / "response.json", response)
        (directory / "raw_output.txt").write_text(response.get("content") or "", encoding="utf-8")
        require(response.get("finish_reason") == "stop", "Model response did not finish normally")
        parsed = parse_json_response(response["content"])
        write_record(directory / "parsed.json", parsed)
        validate_diagnosis(parsed, diagnosis_input(saved))
        write_record(directory / "diagnosis.json", parsed)
        write_record(directory / "validation.json", {"valid": True, "error": None})
        meta["status"] = "valid"
    except (Exception, KeyboardInterrupt) as exc:
        write_record(directory / "validation.json", {
            "valid": False, "error_type": type(exc).__name__,
            "error": str(exc) if isinstance(exc, ValueError) else "Call failed; inspect preserved response and error type."})
        meta["status"] = "invalid"
        raise
    finally:
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_record(directory / "run.json", meta)
    return load_diagnosis(directory, expected_grouping=saved, expected_call_config=call_config)


def main(argv=None):
    import os
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grouping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--model")
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-input-chars", type=int, default=100000)
    args = parser.parse_args(argv)
    load_dotenv(args.env_file, override=False)
    config = call_configuration(base_url=os.environ.get("OPENAI_BASE_URL", ""), model=args.model,
                                max_tokens=args.max_tokens, timeout=args.timeout)
    generate = None
    if not args.output.exists():
        generate = live_generator(base_url=os.environ.get("OPENAI_BASE_URL", ""),
                                  key=os.environ.get("OPENAI_API_KEY"), model=args.model,
                                  max_tokens=args.max_tokens, timeout=args.timeout)
    result = run_diagnosis(args.grouping, args.output, generate=generate,
                          max_input_chars=args.max_input_chars, call_config=config)
    print(json.dumps(result["diagnosis"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

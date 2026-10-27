"""V23.5 Grouping persistence with stage-local output-validation feedback.

The original v23 Prompt, facts and output contract remain unchanged.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23.facts import build_facts, require, text
from src.skill_evolution.v23.prompts import actor_fields
from src.skill_evolution.v23.grouping import (
    messages_for, validate_grouping, candidate_groups, call_configuration,
    live_generator, response_value,
)
from . import output_feedback as feedback


def load_grouping(directory, *, expected_bundle=None, round_id=None,
                  legacy_template=None, expected_call_config=...):
    """Validate archived artifacts before handing facts/grouping to Diagnosis."""
    directory = Path(directory)
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    bundle = read("input.json")
    if expected_bundle is not None:
        require(bundle == expected_bundle, "Saved grouping input differs from current input")
    meta = read("run.json")
    if round_id is not None:
        require(meta["round_id"] == round_id, "Grouping belongs to a different round")
    context = feedback.saved_context(directory)
    messages = feedback.request_messages(messages_for(bundle), context)
    if legacy_template is not None:
        messages[0]["content"] = actor_fields(legacy_template, bundle["background"])
    require(read("messages.json") == messages, "Saved grouping prompt/input differs")
    if expected_call_config is not ...:
        require(meta.get("call_config") == expected_call_config, "Saved grouping call configuration differs")
    if (directory / "prompt.md").exists():
        require((directory / "prompt.md").read_text(encoding="utf-8") == messages[0]["content"],
                "Saved grouping prompt differs")
    require(read("validation.json")["valid"] is True, "Saved grouping is not valid")
    result = validate_grouping(read("grouping.json"), bundle["facts"])
    response = read("response.json")
    require(response.get("finish_reason") == "stop", "Saved response was not completed")
    require(parse_json_response(response["content"]) == result, "Saved result differs from model response")
    if (directory / "parsed.json").exists():
        require(read("parsed.json") == result, "Saved parse differs from model response")
    return {"facts": bundle["facts"], "background": bundle["background"],
            "grouping": result, "sources": bundle["sources"], "round_id": meta["round_id"]}


def run_grouping(records, directory, *, round_id, generate, max_input_chars=400000, call_config=None):
    """Persist before one semantic attempt; failed directories cannot silently retry."""
    text(round_id, "round_id")
    bundle = build_facts(records)
    context = (feedback.saved_context(directory) if Path(directory).exists()
               else feedback.generation_context(generate))
    messages = feedback.request_messages(messages_for(bundle), context)
    size = len(json.dumps(messages, ensure_ascii=False))
    require(size <= max_input_chars, "Grouping input exceeds the declared character budget")
    directory = Path(directory)
    generated_config = getattr(generate, "call_config", None)
    require(call_config is None or generated_config is None or call_config == generated_config,
            "Generator configuration differs from declared configuration")
    call_config = call_config if call_config is not None else generated_config
    if directory.exists():
        return load_grouping(directory, expected_bundle=bundle, round_id=round_id,
                             expected_call_config=call_config)
    directory.mkdir(parents=True, exist_ok=False)
    feedback.save_context(directory, context)
    write_record(directory / "input.json", bundle)
    write_record(directory / "messages.json", messages)
    (directory / "prompt.md").write_text(messages[0]["content"], encoding="utf-8")
    meta = {"round_id": round_id, "started_at": datetime.now(timezone.utc).isoformat(),
            "input_chars": size, "max_input_chars": max_input_chars, "status": "requesting",
            "call_config": call_config}
    write_record(directory / "run.json", meta)
    try:
        response = generate(messages, directory)
        write_record(directory / "response.json", response)
        (directory / "raw_output.txt").write_text(response.get("content") or "", encoding="utf-8")
        require(response.get("finish_reason") == "stop", "Model response did not finish normally")
        parsed = feedback.output_call("Grouping response", parse_json_response, response["content"])
        write_record(directory / "parsed.json", parsed)
        result = feedback.output_call("Grouping output", validate_grouping, parsed, bundle["facts"])
        meta["output_validated"] = True
        write_record(directory / "grouping.json", result)
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
    return load_grouping(directory, expected_bundle=bundle, round_id=round_id,
                         expected_call_config=call_config)


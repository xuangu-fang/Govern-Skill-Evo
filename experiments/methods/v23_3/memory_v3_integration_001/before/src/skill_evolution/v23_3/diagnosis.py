"""Versioned multiline Diagnosis prompt; original V23 input/schema/validation.

The small stage-specific persistence skeleton is retained because the V23 runner
and loader bind their prompt at module scope. No historical text is reformatted.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23.diagnosis import diagnosis_input, validate_diagnosis
from src.skill_evolution.v23.editor import _read_text, _write_text
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23.grouping import load_grouping
from src.skill_evolution.v23.prompts import render_prompt

PROMPT_PATH = Path(__file__).with_name("diagnosis_prompt.md")


def messages_for(saved):
    return [{"role": "system", "content": render_prompt(PROMPT_PATH.read_text(encoding="utf-8"), saved["background"])},
            {"role": "user", "content": json.dumps(diagnosis_input(saved), ensure_ascii=False, separators=(",", ":"))}]


def load_diagnosis(directory, *, expected_grouping=None, expected_call_config=...):
    directory = Path(directory)
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    saved, meta = read("input.json"), read("run.json")
    require(saved == load_grouping(meta["grouping_directory"]), "Diagnosis differs from recorded Grouping")
    if expected_grouping is not None:
        require(saved == expected_grouping, "Diagnosis input differs from current Grouping handoff")
    messages = messages_for(saved)
    require(read("messages.json") == messages, "Saved Diagnosis prompt/input differs")
    require(_read_text(directory / "prompt.md") == messages[0]["content"], "Saved prompt differs")
    require(meta["grouping_round_id"] == saved["round_id"] and meta["status"] == "valid", "Invalid saved run")
    if expected_call_config is not ...:
        require(meta["call_config"] == expected_call_config, "Saved Diagnosis call configuration differs")
    require(read("validation.json")["valid"] is True, "Saved Diagnosis is not valid")
    response = read("response.json")
    require(response.get("finish_reason") == "stop", "Saved response did not finish normally")
    require(_read_text(directory / "raw_output.txt") == response["content"], "Raw output differs")
    parsed = parse_json_response(response["content"])
    require(read("parsed.json") == parsed and read("diagnosis.json") == parsed,
            "Saved result differs from original response")
    validate_diagnosis(parsed, diagnosis_input(saved))
    return {**saved, "diagnosis": parsed}


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
        _write_text(directory / "raw_output.txt", response.get("content") or "")
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

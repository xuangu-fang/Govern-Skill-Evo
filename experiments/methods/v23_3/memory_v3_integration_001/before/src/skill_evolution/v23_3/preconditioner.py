"""V23.3 one-generation Patch decisions and independently verified derived archives.

Only the stage-specific request/save skeleton is retained from V23: its runner
hardcodes the old prompt, loader and response==Adjustment relation. Input assembly,
parsing, Memory validation, patch application and compilation remain V23 code.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from .diagnosis import load_diagnosis
from src.skill_evolution.v23.editor import _read_text, _write_text
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23.grouping import load_grouping
from src.skill_evolution.v23.memory import empty_memory
from src.skill_evolution.v23.preconditioner import preconditioner_input
from src.skill_evolution.v23.prompts import render_prompt
from .update_patch import normalize_update_patches

PROMPT_PATH = Path(__file__).with_name("preconditioner_prompt.md")


def messages_for(saved):
    return [{"role": "system", "content": render_prompt(PROMPT_PATH.read_text(encoding="utf-8"), saved["background"])},
            {"role": "user", "content": json.dumps(preconditioner_input(saved), ensure_ascii=False, separators=(",", ":"))}]


def read_upstream(grouping_directory, diagnosis_directory):
    grouped = load_grouping(grouping_directory)
    return load_diagnosis(diagnosis_directory, expected_grouping=grouped)


def load_preconditioner(directory, *, expected_diagnosis=None, expected_call_config=...):
    """Reparse raw Patch output, reapply and compile; verify the upstream chain."""
    directory = Path(directory)
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    saved, meta = read("input.json"), read("run.json")
    upstream = read_upstream(meta["grouping_directory"], meta["diagnosis_directory"])
    require(saved == {**upstream, "memory": meta["memory"]}, "Saved Diagnosis/Memory handoff differs")
    if expected_diagnosis is not None:
        require(saved == expected_diagnosis, "Preconditioner input differs from Diagnosis handoff")
    require(meta["memory_contract"] == "entries_sources", "Unsupported Memory contract")
    require(meta["round_id"] == saved["round_id"] and meta["status"] == "valid", "Invalid saved run")
    if expected_call_config is not ...:
        require(meta["call_config"] == expected_call_config, "Saved Preconditioner call configuration differs")
    messages = messages_for(saved)
    require(read("messages.json") == messages, "Saved Preconditioner prompt/input differs")
    require(_read_text(directory / "prompt.md") == messages[0]["content"], "Saved prompt differs")
    require(read("validation.json")["valid"] is True, "Saved Preconditioner is not valid")
    response = read("response.json")
    require(response.get("finish_reason") == "stop", "Saved response did not finish normally")
    require(_read_text(directory / "raw_output.txt") == response["content"], "Raw output differs")
    parsed = parse_json_response(response["content"])
    require(read("parsed.json") == parsed, "Saved Patch result differs from original response")
    normalized, effective = normalize_update_patches(parsed, preconditioner_input(saved))
    require(read("preconditioner.json") == normalized, "Saved Adjustment differs from Patch application")
    require(read("effective_plan.json") == effective, "Saved Effective Plan differs from compilation")
    return {**saved, "preconditioner": normalized, "effective_plan": effective}


def run_preconditioner(grouping_directory, diagnosis_directory, directory, *, generate,
                       max_input_chars=100000, call_config=None, memory=None):
    saved = {**read_upstream(grouping_directory, diagnosis_directory),
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
        _write_text(directory / "raw_output.txt", response.get("content") or "")
        require(response.get("finish_reason") == "stop", "Model response did not finish normally")
        parsed = parse_json_response(response["content"])
        write_record(directory / "parsed.json", parsed)
        normalized, effective = normalize_update_patches(parsed, preconditioner_input(saved))
        write_record(directory / "preconditioner.json", normalized)
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

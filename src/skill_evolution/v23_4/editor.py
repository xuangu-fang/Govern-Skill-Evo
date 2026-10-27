"""Thin V23.4 upstream boundary; all Editor policy and patch logic remain V23.

Only the request/save skeleton is repeated: V23 run_editor has no injectable
upstream loader. The original messages, validation and archive checker are reused.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23 import editor as original
from src.skill_evolution.v23.editor import (editor_input, messages_for, validate_editor,
                                          actual_diff, _write_text)
from src.skill_evolution.v23.facts import require
from .preconditioner import load_preconditioner
from src.skill_evolution.v23.memory import LEGACY_CONTRACT


def load_editor(directory, *, expected_preconditioner=None, expected_call_config=...):
    """Validate Patch lineage before using the unchanged V23 Editor loader."""
    directory = Path(directory)
    meta = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    saved = load_preconditioner(meta["preconditioner_directory"])
    if expected_preconditioner is not None:
        require(saved == expected_preconditioner, "Editor upstream differs from current Preconditioner")
    contract = json.loads((Path(meta["preconditioner_directory"]) / "run.json").read_text()).get("memory_contract", LEGACY_CONTRACT)
    return original.load_editor(directory, expected_preconditioner=saved,
                                expected_call_config=expected_call_config, memory_contract=contract)


def run_editor(preconditioner_directory, directory, *, generate, max_input_chars=100000, call_config=None):
    saved = load_preconditioner(preconditioner_directory)
    contract = json.loads((Path(preconditioner_directory) / "run.json").read_text()).get("memory_contract", LEGACY_CONTRACT)
    payload, messages = editor_input(saved, memory_contract=contract), messages_for(saved, memory_contract=contract)
    size = len(json.dumps(messages, ensure_ascii=False))
    require(size <= max_input_chars, "Editor input exceeds declared character budget")
    generated_config = getattr(generate, "call_config", None)
    require(call_config is None or generated_config is None or call_config == generated_config,
            "Generator configuration differs from declared configuration")
    call_config = call_config if call_config is not None else generated_config
    directory = Path(directory)
    if directory.exists():
        return load_editor(directory, expected_preconditioner=saved, expected_call_config=call_config)
    directory.mkdir(parents=True, exist_ok=False)
    for name, value in (("upstream", saved), ("input", payload), ("background", saved["background"]), ("messages", messages)):
        write_record(directory / f"{name}.json", value)
    _write_text(directory / "prompt.md", messages[0]["content"])
    meta = {"round_id": saved["round_id"], "preconditioner_directory": str(Path(preconditioner_directory).resolve()),
            "started_at": datetime.now(timezone.utc).isoformat(), "input_chars": size,
            "max_input_chars": max_input_chars, "call_config": call_config, "status": "requesting"}
    if contract != LEGACY_CONTRACT:
        meta["memory_contract"] = contract
    write_record(directory / "run.json", meta)
    try:
        response = generate(messages, directory)
        write_record(directory / "response.json", response)
        _write_text(directory / "raw_output.txt", response.get("content") or "")
        require(response.get("finish_reason") == "stop", "Model response did not finish normally")
        parsed = parse_json_response(response["content"])
        write_record(directory / "parsed.json", parsed)
        if isinstance(parsed, dict) and isinstance(parsed.get("patch"), str):
            _write_text(directory / "patch.diff", parsed["patch"])
        status, candidate = validate_editor(parsed, payload["parent"])
        if candidate is not None:
            _write_text(directory / "candidate.md", candidate)
            _write_text(directory / "actual.diff", actual_diff(payload["parent"], candidate))
        write_record(directory / "editor.json", parsed)
        write_record(directory / "validation.json", {"valid": True, "error": None})
        meta.update(status="valid", outcome=status)
    except (Exception, KeyboardInterrupt) as exc:
        write_record(directory / "validation.json", {"valid": False, "error_type": type(exc).__name__,
                     "error": str(exc) if isinstance(exc, ValueError) else "Call or persistence failed; inspect preserved files and error type."})
        meta["status"] = "invalid"
        raise
    finally:
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_record(directory / "run.json", meta)
    return load_editor(directory, expected_preconditioner=saved, expected_call_config=call_config)

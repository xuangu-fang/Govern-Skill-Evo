from src.skill_evolution.v24.resources import resource
"""V23.5 Editor: isolated prompt/lineage and shared unnumbered patch application."""
from copy import deepcopy
from datetime import datetime, timezone
from . import output_feedback as feedback
import json
from pathlib import Path

from src.skill_evolution.v24.storage import write_record
from src.skill_evolution.v24.json_response import parse_json_response
from src.skill_evolution.v24.contracts.diagnosis import fields
from src.skill_evolution.v24.facts import require, text
from src.skill_evolution.v24.contracts.memory import MULTI_KNOWLEDGE_CONTRACT, LEGACY_CONTRACT
from src.skill_evolution.v24.contracts.preconditioner import preconditioner_input
from src.skill_evolution.v24.prompts import render_prompt
from src.skill_evolution.v24.contracts.editor import _utf8, _read_text, _write_text
from src.skill_evolution.v24.unnumbered_patch import apply_patch, actual_diff, CONTRACT_VERSION
from .preconditioner import load_preconditioner
from .update_patch import compile_effective_plan

PROMPT_VERSION = "v23_5_editor_v1"
PROMPT_PATH = resource("v23_5/editor_prompt.md")


def editor_input(saved, *, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    require(saved["preconditioner"]["decision"] == "ready" and saved["effective_plan"] is not None,
            "Editor requires a ready, non-null Effective Plan")
    require(compile_effective_plan(saved["preconditioner"], preconditioner_input(saved, memory_contract=memory_contract),
                                   memory_contract=memory_contract) == saved["effective_plan"],
            "Effective Plan differs from compiled Preconditioner output")
    parent = saved["facts"]["parent"]
    require(parent is None or isinstance(parent, str), "Invalid Parent")
    _utf8(parent or "")
    return deepcopy({"parent": parent, "plan": saved["effective_plan"]})


def messages_for(saved, *, memory_contract=MULTI_KNOWLEDGE_CONTRACT, retry_policy=feedback.LEGACY):
    return [{"role": "system", "content": render_prompt(feedback.prompt_text(PROMPT_PATH, retry_policy), saved["background"])},
            {"role": "user", "content": json.dumps(editor_input(saved, memory_contract=memory_contract), ensure_ascii=False, separators=(",", ":"))}]


def validate_editor(result, parent):
    """Return program status and Candidate; do not infer status from reason prose."""
    fields(result, ("patch", "reason"), "Editor")
    text(result["reason"], "reason")
    _utf8(result["reason"])
    patch = result["patch"]
    if patch is None:
        return "needs_revision", None
    require(isinstance(patch, str), "patch must be a string or null")
    if patch == "":
        return "no_change", None
    require(bool(patch.strip()), "Whitespace-only patch is invalid")
    return "candidate", apply_patch(parent, patch)


def load_editor(directory, *, expected_preconditioner=None, expected_call_config=...):
    directory = Path(directory)
    request_context = feedback.saved_context(directory)
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    meta = read("run.json")
    require(meta.get("prompt_version") == PROMPT_VERSION, "Unsupported Editor prompt version")
    require(meta.get("patch_contract") == CONTRACT_VERSION, "Unsupported Editor patch contract")
    saved = load_preconditioner(meta["preconditioner_directory"])
    require(read("upstream.json") == saved, "Editor upstream archive differs")
    memory_contract = meta.get("memory_contract", LEGACY_CONTRACT)
    if expected_preconditioner is not None:
        require(saved == expected_preconditioner, "Editor input differs from Preconditioner handoff")
    payload, messages = editor_input(saved, memory_contract=memory_contract), messages_for(saved, memory_contract=memory_contract, retry_policy=feedback.policy(request_context))
    messages = feedback.request_messages(messages, request_context)
    require(read("input.json") == payload and read("background.json") == saved["background"], "Saved input/background differs")
    require(read("messages.json") == messages and _read_text(directory / "prompt.md") == messages[0]["content"],
            "Saved Editor prompt/input differs")
    upstream_contract = json.loads((Path(meta["preconditioner_directory"]) / "run.json").read_text())["memory_contract"]
    require(upstream_contract == memory_contract, "Editor Memory contract differs from upstream")
    require(meta["round_id"] == saved["round_id"] and meta["status"] == "valid", "Invalid saved run")
    if expected_call_config is not ...:
        require(meta["call_config"] == expected_call_config, "Saved Editor call configuration differs")
    require(read("validation.json")["valid"] is True, "Saved Editor is not valid")
    response = read("response.json")
    require(response.get("finish_reason") == "stop", "Saved response did not finish normally")
    require(_read_text(directory / "raw_output.txt") == response["content"], "Raw output differs")
    parsed = parse_json_response(response["content"])
    require(read("parsed.json") == parsed and read("editor.json") == parsed, "Saved result differs from original response")
    status, candidate = validate_editor(parsed, payload["parent"])
    require(meta["outcome"] == status, "Saved outcome differs")
    if isinstance(parsed["patch"], str):
        require(_read_text(directory / "patch.diff") == parsed["patch"], "Saved patch differs")
    else:
        require(not (directory / "patch.diff").exists(), "Null patch must not have a patch file")
    diff = None if candidate is None else actual_diff(payload["parent"], candidate)
    if candidate is not None:
        require(_read_text(directory / "candidate.md") == candidate and _read_text(directory / "actual.diff") == diff,
                "Saved Candidate/diff differs from strict application")
    else:
        require(not (directory / "candidate.md").exists() and not (directory / "actual.diff").exists(),
                "Semantic stop must not have Candidate artifacts")
    return {**saved, "editor": parsed, "editor_status": status, "candidate_text": candidate, "actual_diff": diff}


def run_editor(preconditioner_directory, directory, *, generate, max_input_chars=100000, call_config=None):
    request_context = (feedback.saved_context(directory) if Path(directory).exists()
                       else feedback.generation_context(generate))
    saved = load_preconditioner(preconditioner_directory)
    contract = json.loads((Path(preconditioner_directory) / "run.json").read_text())["memory_contract"]
    payload, messages = editor_input(saved, memory_contract=contract), messages_for(saved, memory_contract=contract, retry_policy=feedback.policy(request_context))
    messages = feedback.request_messages(messages, request_context)
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
    feedback.save_context(directory, request_context)
    for name, value in (("upstream", saved), ("input", payload), ("background", saved["background"]), ("messages", messages)):
        write_record(directory / f"{name}.json", value)
    _write_text(directory / "prompt.md", messages[0]["content"])
    meta = {"prompt_version": PROMPT_VERSION, "patch_contract": CONTRACT_VERSION, "memory_contract": contract,
            "round_id": saved["round_id"], "preconditioner_directory": str(Path(preconditioner_directory).resolve()),
            "started_at": datetime.now(timezone.utc).isoformat(), "input_chars": size,
            "max_input_chars": max_input_chars, "call_config": call_config, "status": "requesting"}
    write_record(directory / "run.json", meta)
    try:
        response = generate(messages, directory)
        write_record(directory / "response.json", response)
        _write_text(directory / "raw_output.txt", response.get("content") or "")
        require(response.get("finish_reason") == "stop", "Model response did not finish normally")
        parsed = feedback.output_call("response", parse_json_response, response["content"])
        write_record(directory / "parsed.json", parsed)
        if isinstance(parsed, dict) and isinstance(parsed.get("patch"), str):
            _write_text(directory / "patch.diff", parsed["patch"])
        status, candidate = feedback.output_call("Editor output", validate_editor, parsed, payload["parent"])
        meta['output_validated'] = True
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


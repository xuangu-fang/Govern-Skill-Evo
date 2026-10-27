from src.skill_evolution.v24.resources import resource
"""V23.5 flat decisions, deterministic adaptation and verified archive reuse."""
from copy import deepcopy
from datetime import datetime, timezone
from . import output_feedback as feedback
import json
from pathlib import Path

from src.skill_evolution.v24.storage import write_record
from src.skill_evolution.v24.json_response import parse_json_response as _parse_json_response
from . import diagnosis as diagnosis_v23_5
from src.skill_evolution.v24.contracts.editor import _read_text, _write_text
from src.skill_evolution.v24.facts import require
from .grouping import load_grouping
from src.skill_evolution.v24.contracts.memory import MULTI_KNOWLEDGE_CONTRACT, empty_memory, LEGACY_CONTRACT, validate_memory
from src.skill_evolution.v24.contracts.preconditioner import preconditioner_input
from src.skill_evolution.v24.prompts import render_prompt
from .update_patch import CONTRACT_VERSION, normalize_update_patches, actual_update_diffs
from src.skill_evolution.v24.contracts.memory_view import FORMAT, project_messages
from .memory_view import KNOWLEDGE_ONLY, PROMPT_PATH as KNOWLEDGE_VIEW_PATH, project_payload

PROMPT_VERSION = "v23_5_preconditioner_v1"
PROMPT_PATH = resource("v23_5/preconditioner_prompt.md")
KNOWLEDGE_PROMPT_VERSION = "v23_5_preconditioner_knowledge_only_v1"
KNOWLEDGE_PROMPT_PATH = resource("v23_5/preconditioner_knowledge_only_prompt.md")


def parse_json_response(content):
    """Preserve the existing parser's acceptance rules; expose syntax diagnostics only."""
    try:
        return _parse_json_response(content)
    except ValueError as exc:
        cause = exc.__cause__
        if isinstance(cause, json.JSONDecodeError):
            # Positions refer to the JSON body after the existing strip/fence handling.
            raise ValueError(
                f"response: expected one valid JSON object; JSON body line {cause.lineno}, "
                f"column {cause.colno} (char {cause.pos}): {cause.msg}"
            ) from exc
        raise


def prompt_for(memory_view):
    require(memory_view in (FORMAT, KNOWLEDGE_ONLY), "Unsupported V23.5 Memory view")
    return ((KNOWLEDGE_PROMPT_VERSION, KNOWLEDGE_PROMPT_PATH) if memory_view == KNOWLEDGE_ONLY
            else (PROMPT_VERSION, PROMPT_PATH))


def model_input(saved, *, memory_view=KNOWLEDGE_ONLY, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    payload = preconditioner_input(saved, memory_contract=memory_contract)
    return project_payload(payload, memory_view, memory_contract=memory_contract)


def messages_for(saved, *, memory_view=KNOWLEDGE_ONLY, memory_contract=MULTI_KNOWLEDGE_CONTRACT,
                 retry_policy=feedback.LEGACY):
    _, path = prompt_for(memory_view)
    if memory_view == KNOWLEDGE_ONLY:
        return [{"role": "system", "content": render_prompt(feedback.prompt_text(path, retry_policy), saved["background"])
                 + "\n\n" + KNOWLEDGE_VIEW_PATH.read_text()},
                {"role": "user", "content": json.dumps(model_input(saved, memory_view=memory_view,
                 memory_contract=memory_contract), ensure_ascii=False, separators=(",", ":"))}]
    messages = [{"role": "system", "content": render_prompt(feedback.prompt_text(path, retry_policy), saved["background"])},
                {"role": "user", "content": json.dumps(preconditioner_input(saved, memory_contract=memory_contract), ensure_ascii=False, separators=(",", ":"))}]
    return project_messages(messages, memory_view, memory_contract=memory_contract)


def read_upstream(grouping_directory, diagnosis_directory, *, diagnosis_version="v23_5"):
    require(diagnosis_version == "v23_5", "V23.5 requires its versioned Diagnosis")
    grouped = load_grouping(grouping_directory)
    module = diagnosis_v23_5
    return module.load_diagnosis(diagnosis_directory, expected_grouping=grouped)


def load_preconditioner(directory, *, expected_diagnosis=None, expected_call_config=...,
                       expected_memory_view=..., expected_diagnosis_version=..., expected_memory_contract=...):
    """Reparse raw Patch output, reapply and compile; verify the upstream chain."""
    directory = Path(directory)
    request_context = feedback.saved_context(directory)
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    saved, meta = read("input.json"), read("run.json")
    require(meta.get("prompt_version") == prompt_for(meta["memory_view"])[0], "Unsupported Preconditioner prompt version")
    require(meta.get("contract_version") == CONTRACT_VERSION, "Unsupported Preconditioner contract")
    # V23.5 records always declare their upstream version.
    diagnosis_version = meta["diagnosis_version"]
    if expected_diagnosis_version is not ...:
        require(diagnosis_version == expected_diagnosis_version, "Saved Diagnosis version differs")
    upstream = read_upstream(meta["grouping_directory"], meta["diagnosis_directory"],
                             diagnosis_version=diagnosis_version)
    require(saved == {**upstream, "memory": meta["memory"]}, "Saved Diagnosis/Memory handoff differs")
    if expected_diagnosis is not None:
        require(saved == expected_diagnosis, "Preconditioner input differs from Diagnosis handoff")
    memory_contract = meta.get("memory_contract", LEGACY_CONTRACT)
    validate_memory(saved["memory"], memory_contract=memory_contract)
    if expected_memory_contract is not ...:
        require(memory_contract == expected_memory_contract, "Saved Memory contract differs")
    require(meta["round_id"] == saved["round_id"] and meta["status"] == "valid", "Invalid saved run")
    if expected_call_config is not ...:
        require(meta["call_config"] == expected_call_config, "Saved Preconditioner call configuration differs")
    memory_view = meta["memory_view"]
    if expected_memory_view is not ...:
        require(memory_view == expected_memory_view, "Saved Memory view differs")
    messages = messages_for(saved, memory_view=memory_view, memory_contract=memory_contract,
                            retry_policy=feedback.policy(request_context))
    messages = feedback.request_messages(messages, request_context)
    require(read("model_input.json") == json.loads(messages[1]["content"]),
            "Saved model input differs from Memory projection")
    require(read("messages.json") == messages, "Saved Preconditioner prompt/input differs")
    require(_read_text(directory / "prompt.md") == messages[0]["content"], "Saved prompt differs")
    require(read("validation.json")["valid"] is True, "Saved Preconditioner is not valid")
    response = read("response.json")
    require(response.get("finish_reason") == "stop", "Saved response did not finish normally")
    require(_read_text(directory / "raw_output.txt") == response["content"], "Raw output differs")
    parsed = parse_json_response(response["content"])
    require(read("parsed.json") == parsed, "Saved Patch result differs from original response")
    normalized, effective = normalize_update_patches(
        parsed, preconditioner_input(saved, memory_contract=memory_contract),
        memory_view=memory_view, memory_contract=memory_contract)
    require(read("preconditioner.json") == normalized, "Saved Adjustment differs from Patch application")
    require(read("effective_plan.json") == effective, "Saved Effective Plan differs from compilation")
    require(read("actual_diffs.json") == actual_update_diffs(
        preconditioner_input(saved, memory_contract=memory_contract), effective),
        "Saved Update diffs differ from actual replacements")
    return {**saved, "raw_preconditioner": parsed, "preconditioner": normalized, "effective_plan": effective}


def run_preconditioner(grouping_directory, diagnosis_directory, directory, *, generate,
                       max_input_chars=100000, call_config=None, memory=None, memory_view=KNOWLEDGE_ONLY,
                       diagnosis_version="v23_5", memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    request_context = (feedback.saved_context(directory) if Path(directory).exists()
                       else feedback.generation_context(generate))
    saved = {**read_upstream(grouping_directory, diagnosis_directory, diagnosis_version=diagnosis_version),
             "memory": deepcopy(empty_memory() if memory is None else memory)}
    messages = messages_for(saved, memory_view=memory_view, memory_contract=memory_contract,
                            retry_policy=feedback.policy(request_context))
    messages = feedback.request_messages(messages, request_context)
    payload = preconditioner_input(saved, memory_contract=memory_contract)
    size = len(json.dumps(messages, ensure_ascii=False))
    require(size <= max_input_chars, "Preconditioner input exceeds the declared character budget")
    generated_config = getattr(generate, "call_config", None)
    require(call_config is None or generated_config is None or call_config == generated_config,
            "Generator configuration differs from declared configuration")
    call_config = call_config if call_config is not None else generated_config
    directory = Path(directory)
    if directory.exists():
        return load_preconditioner(directory, expected_diagnosis=saved, expected_call_config=call_config,
                                   expected_memory_view=memory_view, expected_diagnosis_version=diagnosis_version,
                               expected_memory_contract=memory_contract)
    directory.mkdir(parents=True, exist_ok=False)
    feedback.save_context(directory, request_context)
    write_record(directory / "input.json", saved)
    write_record(directory / "model_input.json", json.loads(messages[1]["content"]))
    write_record(directory / "messages.json", messages)
    (directory / "prompt.md").write_text(messages[0]["content"], encoding="utf-8")
    meta = {"prompt_version": prompt_for(memory_view)[0], "round_id": saved["round_id"], "grouping_directory": str(Path(grouping_directory).resolve()),
            "diagnosis_directory": str(Path(diagnosis_directory).resolve()), "memory": saved["memory"],
            "memory_contract": memory_contract, "contract_version": CONTRACT_VERSION,
            "memory_view": memory_view, "diagnosis_version": diagnosis_version,
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
        normalized, effective = feedback.output_call(
            "Preconditioner output", normalize_update_patches, parsed, payload,
            memory_view=memory_view, memory_contract=memory_contract)
        meta['output_validated'] = True
        write_record(directory / "actual_diffs.json", actual_update_diffs(
            preconditioner_input(saved, memory_contract=memory_contract), effective))
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
    return load_preconditioner(directory, expected_diagnosis=saved, expected_call_config=call_config,
                               expected_memory_view=memory_view, expected_diagnosis_version=diagnosis_version,
                               expected_memory_contract=memory_contract)

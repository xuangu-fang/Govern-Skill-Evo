from .resources import resource
"""V25 flat decisions, deterministic adaptation and verified archive reuse."""
from copy import deepcopy
from datetime import datetime, timezone
from . import output_feedback as feedback
import json
from pathlib import Path

from .storage import write_record
from .json_response import parse_json_response as _parse_json_response
from . import diagnosis as diagnosis_v25
from .contracts.editor import _read_text, _write_text
from .facts import require
from .grouping import load_grouping
from .contracts.memory import MULTI_KNOWLEDGE_CONTRACT, empty_memory, LEGACY_CONTRACT, validate_memory
from .contracts.preconditioner import preconditioner_input
from .prompts import render_prompt
from .update_patch import CONTRACT_VERSION, LEGACY_CONTRACT_VERSION, normalize_update_patches, actual_update_diffs
from .memory_view import KNOWLEDGE_ONLY, PROMPT_PATH as KNOWLEDGE_VIEW_PATH, project_payload

PROMPT_VERSION = "v25_preconditioner_v1"
PROMPT_PATH = resource("preconditioner.md")
LEGACY_PROMPT_VERSION = "v25_preconditioner_history_and_plan_v3"
EXPLICIT_PROMPT_VERSION = "v25_preconditioner_explicit_references_v4"
TASK_REQUIREMENTS_PROMPT_VERSION = "v25_preconditioner_task_requirements_v5"
SELF_CHECK_PROMPT_VERSION = "v25_preconditioner_self_check_scope_v6"
EVIDENCE_DECISION_PROMPT_VERSION = "v25_preconditioner_evidence_decision_boundaries_v7"
SCOPE_AWARE_PROMPT_VERSION = "v25_preconditioner_scope_aware_keep_v8"
KNOWLEDGE_PROMPT_VERSION = EVIDENCE_DECISION_PROMPT_VERSION
LEGACY_PROMPT_PATH = resource("preconditioner_legacy_v3.md")
EXPLICIT_PROMPT_PATH = resource("preconditioner_legacy_v4.md")
TASK_REQUIREMENTS_PROMPT_PATH = resource("preconditioner_legacy_v5.md")
SELF_CHECK_PROMPT_PATH = resource("preconditioner_legacy_v6.md")
EVIDENCE_DECISION_PROMPT_PATH = resource("preconditioner_legacy_v7.md")
SCOPE_AWARE_PROMPT_PATH = resource("preconditioner_legacy_v8.md")
KNOWLEDGE_PROMPT_PATH = resource("preconditioner.md")


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


def prompt_for(memory_view, contract_version=CONTRACT_VERSION, prompt_version=None):
    require(memory_view == KNOWLEDGE_ONLY, "Unsupported V25 Memory view")
    require(contract_version in (CONTRACT_VERSION, LEGACY_CONTRACT_VERSION), "Unsupported Preconditioner contract")
    if prompt_version is None:
        prompt_version = LEGACY_PROMPT_VERSION if contract_version == LEGACY_CONTRACT_VERSION else KNOWLEDGE_PROMPT_VERSION
    versions = {
        LEGACY_PROMPT_VERSION: (LEGACY_CONTRACT_VERSION, LEGACY_PROMPT_PATH),
        EXPLICIT_PROMPT_VERSION: (CONTRACT_VERSION, EXPLICIT_PROMPT_PATH),
        TASK_REQUIREMENTS_PROMPT_VERSION: (CONTRACT_VERSION, TASK_REQUIREMENTS_PROMPT_PATH),
        SELF_CHECK_PROMPT_VERSION: (CONTRACT_VERSION, SELF_CHECK_PROMPT_PATH),
        EVIDENCE_DECISION_PROMPT_VERSION: (CONTRACT_VERSION, EVIDENCE_DECISION_PROMPT_PATH),
        SCOPE_AWARE_PROMPT_VERSION: (CONTRACT_VERSION, SCOPE_AWARE_PROMPT_PATH),
        KNOWLEDGE_PROMPT_VERSION: (CONTRACT_VERSION, KNOWLEDGE_PROMPT_PATH),
    }
    require(prompt_version in versions, "Unsupported Preconditioner prompt version")
    contract, path = versions[prompt_version]
    require(contract == contract_version, "Preconditioner prompt/contract version mismatch")
    return prompt_version, path


def model_input(saved, *, memory_view=KNOWLEDGE_ONLY, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    payload = preconditioner_input(saved, memory_contract=memory_contract)
    # Keep Grouping in the archive/compiler for upstream Plan validation only.
    # The model receives the unchanged Plan and its referenced executions.
    payload.pop("grouping")
    return project_payload(payload, memory_view, memory_contract=memory_contract)


def messages_for(saved, *, memory_view=KNOWLEDGE_ONLY, memory_contract=MULTI_KNOWLEDGE_CONTRACT,
                 retry_policy=feedback.LEGACY, contract_version=CONTRACT_VERSION, prompt_version=None):
    _, path = prompt_for(memory_view, contract_version, prompt_version)
    if memory_view == KNOWLEDGE_ONLY:
        return [{"role": "system", "content": render_prompt(feedback.prompt_text(path, retry_policy), saved["background"])
                 + "\n\n" + KNOWLEDGE_VIEW_PATH.read_text()},
                {"role": "user", "content": json.dumps(model_input(saved, memory_view=memory_view,
                 memory_contract=memory_contract), ensure_ascii=False, separators=(",", ":"))}]


def read_upstream(grouping_directory, diagnosis_directory, *, diagnosis_version="v25"):
    require(diagnosis_version == "v25", "V25 requires its versioned Diagnosis")
    grouped = load_grouping(grouping_directory)
    module = diagnosis_v25
    return module.load_diagnosis(diagnosis_directory, expected_grouping=grouped)


def load_preconditioner(directory, *, expected_diagnosis=None, expected_call_config=...,
                       expected_memory_view=..., expected_diagnosis_version=..., expected_memory_contract=...):
    """Reparse raw Patch output, reapply and compile; verify the upstream chain."""
    directory = Path(directory)
    request_context = feedback.saved_context(directory)
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    saved, meta = read("input.json"), read("run.json")
    require(meta.get("prompt_version") in (KNOWLEDGE_PROMPT_VERSION, EVIDENCE_DECISION_PROMPT_VERSION,
                                          SCOPE_AWARE_PROMPT_VERSION,
                                          SELF_CHECK_PROMPT_VERSION,
                                          TASK_REQUIREMENTS_PROMPT_VERSION,
                                          EXPLICIT_PROMPT_VERSION, LEGACY_PROMPT_VERSION),
            "Unsupported Preconditioner prompt version")
    contract_version = meta.get("contract_version")
    prompt_for(meta["memory_view"], contract_version, meta['prompt_version'])
    # V25 records always declare their upstream version.
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
                            retry_policy=feedback.policy(request_context), contract_version=contract_version,
                            prompt_version=meta['prompt_version'])
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
        memory_view=memory_view, memory_contract=memory_contract, contract_version=contract_version)
    require(read("preconditioner.json") == normalized, "Saved Adjustment differs from Patch application")
    require(read("effective_plan.json") == effective, "Saved Effective Plan differs from compilation")
    require(read("actual_diffs.json") == actual_update_diffs(
        preconditioner_input(saved, memory_contract=memory_contract), effective),
        "Saved Update diffs differ from actual replacements")
    result = {**saved, "raw_preconditioner": parsed, "preconditioner": normalized, "effective_plan": effective}
    # Preserve legacy handoff bytes/shape for already archived Editors.
    if contract_version != LEGACY_CONTRACT_VERSION:
        result['preconditioner_contract'] = contract_version
    return result


def run_preconditioner(grouping_directory, diagnosis_directory, directory, *, generate,
                       max_input_chars=100000, call_config=None, memory=None, memory_view=KNOWLEDGE_ONLY,
                       diagnosis_version="v25", memory_contract=MULTI_KNOWLEDGE_CONTRACT):
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

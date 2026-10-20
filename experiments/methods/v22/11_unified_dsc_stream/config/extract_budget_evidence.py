"""Read archived 08/09 calls and print budget evidence; no network/environment use."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
ARCHIVE = ROOT / "artifacts/methods/v22"


def source(path, role):
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "role": role}


def extract():
    protocol_path = ARCHIVE / "09_unified_dsc_model_validation_20261015/protocol.json"
    protocol = json.loads(protocol_path.read_text())
    cases = {case["id"]: case for case in protocol["cases"]}
    paths = []
    for name in ("08_grouped_continual_live_20261015", "08_grouped_continual_fusion_resumed_20261015",
                 "08_grouped_continual_memory_recovered_20261015"):
        paths.extend(sorted((ARCHIVE / name).glob("rounds/*/calls/*.json")))
        paths.extend(sorted((ARCHIVE / name).glob("calls/*.json")))
    paths.extend(sorted((ARCHIVE / "09_unified_dsc_model_validation_20261015/cases").glob("*/call.json")))
    rows = []
    for path in paths:
        call = json.loads(path.read_text())
        event = call["steps"][0]
        refs = [source(path, "call, transport attempts and provider usage")]
        case = cases.get(call.get("case_id"))
        provider = None
        if case:
            message_path = path.parent / "messages.json"
            messages = json.loads(message_path.read_text())
            refs.extend([source(message_path, "exact messages"), source(protocol_path, "frozen timeout per case"),
                         source(path.parent / "response.raw", "raw provider response")])
            timeout = case.get("timeout_seconds")
            timeout_origin = "protocol.cases[case_id].timeout_seconds"
            provider = json.loads((path.parent / "response.raw").read_bytes())
        else:
            messages = event["messages"]
            timeout = call.get("request_profile", {}).get("timeout_seconds")
            timeout_origin = "call.request_profile.timeout_seconds" if timeout is not None else None
        attempts = event.get("transport_attempts", [])
        final = event.get("model_response", {})
        usage = (provider or {}).get("usage") or final.get("usage") or (attempts[-1].get("usage") if attempts else None) or {}
        finish_reason = provider["choices"][0].get("finish_reason") if provider else final.get("finish_reason")
        parameters = attempts[0].get("request_parameters", {}) if attempts else {}
        rows.append({
            "id": str(path.relative_to(ARCHIVE)), "sources": refs, "stage": call["stage"],
            "model": call.get("model"), "request_parameters": parameters,
            "max_tokens": parameters.get("max_tokens"), "timeout_seconds": timeout,
            "timeout_source": timeout_origin,
            "messages_content_unicode_chars": sum(len(message["content"]) for message in messages),
            "messages_json_unicode_chars": len(json.dumps(messages, ensure_ascii=False)),
            "messages_compact_json_unicode_chars": len(json.dumps(messages, ensure_ascii=False, separators=(",", ":"))),
            "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "total_tokens": usage.get("total_tokens"), "finish_reason": finish_reason,
            "call_elapsed_seconds": call.get("elapsed_seconds"),
            "http_attempt_elapsed_seconds": [attempt.get("elapsed_seconds") for attempt in attempts],
            "http_attempts": len(attempts), "status": call.get("status"),
            "provider_usage": usage,
        })
    accounting_path = ARCHIVE / "09_unified_dsc_model_validation_20261015/accounting.json"
    accounting = json.loads(accounting_path.read_text())
    return {
        "schema": "v22.stream_budget_evidence.v1", "date": "2026-10-16", "read_only_extraction": True,
        "interpretation": {
            "null": "Not recorded in the selected source. No timeout, elapsed time or usage value is inferred.",
            "messages_content_unicode_chars": "Measured sum(len(message['content']) for message in messages); an additional live_dependencies check, not the governing whole-message cap.",
            "messages_json_unicode_chars": "Measured len(json.dumps(messages, ensure_ascii=False)) with Python default separators; includes serialization overhead.",
            "messages_compact_json_unicode_chars": "Measured len(json.dumps(messages, ensure_ascii=False, separators=(',', ':'))); continual_runner.invoke checks this stricter whole-message size against 400000 before dispatch.",
            "elapsed": "Copied recorded elapsed_seconds. No timestamp subtraction or missing-time estimate.",
            "reasoning": "Provider usage.completion_tokens_details.reasoning_tokens; a subset of completion_tokens.",
            "deduplication": "This is a budget-evidence inventory, not a cumulative cost ledger. Reused archived calls can appear in multiple source directories.",
        },
        "observations": [
            "08 R2 classification exhausted 16384 completion tokens, including 16161 reasoning tokens, and ended with length.",
            "08 R2 learning exhausted 16384 completion tokens, including 14913 reasoning tokens; independently authorized 65536 recovery returned 16694.",
            "09 learning returned 20980 completion tokens including 18559 reasoning tokens, with 320.137936 recorded call seconds.",
            "08 R1 learning reported 17477 completion tokens although request max_tokens was 16384 and finish_reason was stop. Request caps are declarations, not guaranteed provider accounting limits.",
            "08 R2 learning had 363710 content characters, 398823 default JSON-serialized characters and 398816 compact JSON-serialized characters. The effective mainline cap is 400000 compact JSON characters, with an additional content-character check; future inputs must satisfy both without silent truncation.",
        ],
        "declared_new_budget": {
            "rounds": 2, "tasks_per_round": 8, "environment_episodes_max": 32,
            "actor_logical_requests_max": 1600, "actor_max_tokens": 16384,
            "actor_http_attempts_per_logical_request_max": 6, "actor_http_attempts_max": 9600,
            "actor_completion_tokens_per_logical_request_sum_max": 26214400,
            "actor_completion_tokens_all_declared_http_attempts_sum_max": 157286400,
            "semantic_calls_max": 9, "semantic_http_attempts_max": 9,
            "semantic_normal_stages_max_tokens": 32768, "semantic_learning_max_tokens": 65536,
            "semantic_completion_tokens_request_cap_sum_max": 360448,
            "logical_requests_max": 1609, "http_attempts_max": 9609,
            "semantic_timeout_seconds": 600, "connect_timeout_seconds": 10,
            "note": "Computed request ceilings for the user-authorized 2x8 design, not predicted spend or guarantees of provider token enforcement; reasoning and visible output share max_tokens. No separate reasoning reserve is promised.",
        },
        "monetary_cost": None,
        "monetary_cost_status": accounting["monetary_cost_status"],
        "monetary_cost_source": source(accounting_path, "prior monetary cost remained unknown; no supplied internal tariff"),
        "calls": rows,
    }


if __name__ == "__main__":
    print(json.dumps(extract(), ensure_ascii=False, indent=2))

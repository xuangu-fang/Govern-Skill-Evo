"""One recorded semantic call, reusing the existing client and transport limits."""

from pathlib import Path

from src.adapters.alfworld.run_task_skill import RecordingSession, timestamp
from src.adapters.alfworld.run_task_upstream import chat
from src.adapters.alfworld.skill_runtime import object_digest, write_record


def request_profile(stage, max_tokens=16384, timeout_seconds=300, *, transport_policy="legacy"):
    """Explicit recovery profiles; ordinary stage defaults remain unchanged."""
    if transport_policy == "single_attempt":
        expected = 65536 if stage == "post_gate_learning" else 32768
        if (stage not in {"classification", "diagnosis", "fusion", "editor", "main_editor", "post_gate_learning"}
                or type(max_tokens) is not int or max_tokens != expected
                or type(timeout_seconds) is not int or timeout_seconds != 600):
            raise ValueError("Unsupported single-attempt semantic budget or stage.")
        return {"max_tokens": max_tokens, "timeout_seconds": timeout_seconds}
    if transport_policy != "legacy":
        raise ValueError("Unknown semantic transport policy.")
    memory_recovery = (stage == "post_gate_learning"
                       and type(max_tokens) is int and type(timeout_seconds) is int
                       and (max_tokens, timeout_seconds) == (65536, 600))
    if not memory_recovery and (type(max_tokens) is not int or max_tokens not in {16384, 32768}
            or type(timeout_seconds) is not int or timeout_seconds not in {300, 600}
            or (stage != "classification" and (max_tokens, timeout_seconds) != (16384, 300))):
        raise ValueError("Unsupported semantic request budget or stage.")
    return {"max_tokens": max_tokens, "timeout_seconds": timeout_seconds}


class _BudgetSession:
    """Apply declared parameters before RecordingSession hashes the sent body."""

    def __init__(self, recording, profile):
        self.recording, self.profile = recording, profile

    def post(self, endpoint, **kwargs):
        kwargs["json"] = {**kwargs["json"], "max_tokens": self.profile["max_tokens"]}
        kwargs["timeout"] = (10, self.profile["timeout_seconds"])
        return self.recording.post(endpoint, **kwargs)


def semantic_call(stage, messages, *, session, endpoint, key, model, output,
                  max_tokens=16384, timeout_seconds=300, transport_policy="legacy"):
    profile = request_profile(stage, max_tokens, timeout_seconds, transport_policy=transport_policy)
    output = Path(output)
    if transport_policy == "single_attempt" and output.exists():
        raise FileExistsError("A recorded semantic attempt cannot be overwritten.")
    record = {"schema_version": "v22_semantic_call_v1", "stage": stage,
              "model": model, "messages_sha256": object_digest(messages),
              "request_profile": profile,
              "started_at": timestamp(), "status": "requesting",
              "steps": [{"messages": messages, "phase": "requesting"}]}
    if transport_policy == "single_attempt":
        record["transport_policy"] = transport_policy
    write_record(output, record)
    try:
        recording = RecordingSession(session, record, output,
                                     archive_responses=transport_policy == "single_attempt")
        if transport_policy == "single_attempt":
            body = {"model": model, "messages": messages, "temperature": 1.0,
                    "max_tokens": max_tokens, "reasoning_effort": "medium",
                    "thinking": {"type": "enabled"}, "stream": False}
            raw = recording.post(endpoint, headers={"Authorization": f"Bearer {key}"},
                                 json=body, timeout=(10, timeout_seconds))
            if not 200 <= raw.status_code < 300:
                raise RuntimeError(f"Model API returned HTTP {raw.status_code}.")
            payload = raw.json()
            choice = payload["choices"][0]
            message = choice["message"]
            response = {"content": message.get("content") or "", "response_model": payload.get("model"),
                        "finish_reason": choice.get("finish_reason"), "usage": payload.get("usage"),
                        "reasoning_content_chars": len(message.get("reasoning_content") or ""),
                        "api_attempts": 1, "transport_retries": 0}
        else:
            response = chat(_BudgetSession(recording, profile), endpoint, key, model, messages)
        event = record["steps"][0]
        event.update(model_response=response, phase="responded")
        if event.get("transport_attempts"):
            event["transport_attempts"][-1]["usage"] = response.get("usage")
        record["status"] = "responded"
        write_record(output, record)
        if response.get("finish_reason") == "length":
            raise ValueError("Semantic output was truncated; it cannot become a valid proposal.")
        return response["content"]
    except (Exception, KeyboardInterrupt) as exc:
        record.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "error",
                      error_type=type(exc).__name__)
        raise
    finally:
        record["finished_at"] = timestamp()
        write_record(output, record)

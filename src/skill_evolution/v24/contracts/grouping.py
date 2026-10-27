from src.skill_evolution.v24.benchmark import current as benchmark_current
from src.skill_evolution.v24.resources import resource
import json


import re

from src.skill_evolution.v24.storage import write_record

from ..facts import require

from ..prompts import render_prompt

from .model_routing import model_for_endpoint

PROMPT_PATH = resource("v23/grouping_prompt.md")


def messages_for(bundle):
    template = PROMPT_PATH.read_text(encoding="utf-8")
    system = render_prompt(template, bundle["background"])
    return [{"role": "system", "content": system},
            {"role": "user", "content": json.dumps(bundle["facts"], ensure_ascii=False, separators=(",", ":"))}]


def references(value):
    """Resolve explicit references and common numeric ranges without altering prose."""
    refs = set(re.findall(r"\bP\d+(?::[A-Za-z0-9_]+)?\b", value))
    for match in re.finditer(r"\b(P\d+):(\d+)\s*[-–—]\s*(?:(P\d+):)?(\d+)\b", value):
        prefix, start, end_prefix, end = match.groups()
        require(end_prefix in (None, prefix), "Cross-execution step range")
        start, end = int(start), int(end)
        require(0 <= start <= end <= 10000, "Invalid step range")
        refs.update(f"{prefix}:{i}" for i in range(start, end + 1))
    return refs


def validate_grouping(*args, **kwargs):
    return benchmark_current().evidence("contracts.grouping.validate_grouping", *args, **kwargs)


def candidate_groups(saved, task_ids):
    """Reuse Parent membership by paired task identity; never inspect Candidate outcomes."""
    source_by_ref = {source["ref"]: source["task_id"] for source in saved["sources"]}
    by_task = {source_by_ref[member]: group["group_id"]
               for group in saved["grouping"]["groups"] for member in group["members"]}
    require(len(task_ids) == len(set(task_ids)) and set(task_ids) <= set(by_task),
            "Unknown or duplicate Candidate task")
    return {task: by_task[task] for task in task_ids}


def call_configuration(*, base_url, model, max_tokens, timeout):
    """Non-secret configuration used to distinguish persisted calls."""
    model = model_for_endpoint(base_url, model)
    return {"endpoint": base_url.rstrip("/") + "/chat/completions", "model": model,
            "max_tokens": max_tokens, "timeout_seconds": timeout, "temperature": 1.0,
            "reasoning_effort": "medium", "thinking": {"type": "enabled"}, "stream": False}


def response_value(payload):
    """Decode an archived HTTP JSON response using the live response contract."""
    choice = payload["choices"][0]
    return {"content": choice["message"].get("content") or "",
            "finish_reason": choice.get("finish_reason"), "response_model": payload.get("model"),
            "usage": payload.get("usage"), "api_attempts": 1}


def live_generator(*, base_url, key, model, max_tokens=8192, timeout=180):
    """One OpenAI-compatible HTTP request, no semantic or transport retries."""
    from urllib.parse import urlsplit
    import requests

    model = model_for_endpoint(base_url, model)
    parsed = urlsplit(base_url)
    require(parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username
            and not parsed.password and not parsed.query and not parsed.fragment, "Invalid API base URL")
    require(bool(key), "API key is not configured")
    require(type(max_tokens) is int and max_tokens > 0 and timeout > 0, "Invalid call budget")
    endpoint = base_url.rstrip("/") + "/chat/completions"

    def generate(messages, directory):
        body = {"model": model, "messages": messages, "max_tokens": max_tokens,
                "temperature": 1.0, "reasoning_effort": "medium",
                "thinking": {"type": "enabled"}, "stream": False}
        write_record(directory / "request.json", {"endpoint": endpoint, "body": body,
                                                  "timeout_seconds": timeout, "attempts": 1})
        with requests.Session() as session:
            if ".intra." in parsed.hostname:
                session.trust_env = False
            raw = session.post(endpoint, headers={"Authorization": f"Bearer {key}"},
                               json=body, timeout=(10, timeout), allow_redirects=False)
        (directory / "http_response.txt").write_bytes(raw.content)
        write_record(directory / "http_status.json", {"status_code": raw.status_code})
        require(200 <= raw.status_code < 300, f"Model API returned HTTP {raw.status_code}")
        return response_value(raw.json())
    generate.call_config = call_configuration(base_url=base_url, model=model, max_tokens=max_tokens, timeout=timeout)
    return generate


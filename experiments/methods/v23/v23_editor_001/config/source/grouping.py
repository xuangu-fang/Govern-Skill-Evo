"""One-call Grouping, strict output validation and exact-input persisted reuse."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from .facts import build_facts, require, text
from .prompts import actor_fields, render_prompt


PROMPT_PATH = Path(__file__).with_name("grouping_prompt.md")


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


def validate_grouping(result, facts):
    require(isinstance(result, dict) and set(result) == {"groups"}, "Expected only groups")
    groups = result["groups"]
    require(isinstance(groups, list) and bool(groups), "Expected nonempty groups")
    runs = {run["ref"]: run for run in facts["runs"]}
    allowed = set(runs)
    for ref, run in runs.items():
        allowed.update({f"{ref}:0", f"{ref}:outcome"})
        allowed.update(event["step"] for event in run["steps"])
    group_ids, assigned = set(), []
    fields = {"group_id", "members", "decision_problem", "shared_basis", "important_differences"}
    for group in groups:
        require(isinstance(group, dict) and set(group) == fields, "Expected exactly five group fields")
        group_id = text(group["group_id"], "group_id")
        require(group_id not in group_ids, "Duplicate group_id")
        group_ids.add(group_id)
        members = group["members"]
        require(isinstance(members, list) and bool(members)
                and all(isinstance(x, str) and x in runs for x in members), "Invalid members")
        assigned.extend(members)
        text(group["decision_problem"], "decision_problem")
        basis = text(group["shared_basis"], "shared_basis")
        differences = group["important_differences"]
        require(isinstance(differences, list), "important_differences must be an array")
        for difference in differences:
            text(difference, "important_difference")
        for prose in [group["decision_problem"], basis, *differences]:
            require(references(prose) <= allowed, "Unresolvable execution/step reference")
            menu_refs = set(re.findall(r"\bC\d+\b", prose))
            require(menu_refs <= set(facts["command_sets"]), "Unresolvable command-set reference")
        basis_refs = references(basis)
        for member in members:
            events = {event["step"] for event in runs[member]["steps"]}
            if not events:
                events = {f"{member}:0"}
            require(bool(events & basis_refs), f"shared_basis lacks a decision-step reference for {member}")
    require(len(assigned) == len(set(assigned)) and set(assigned) == set(runs),
            "Members must cover every execution exactly once")
    for group in groups:
        for prose in [group["decision_problem"], group["shared_basis"], *group["important_differences"]]:
            require(set(re.findall(r"\bG\d+\b", prose)) <= group_ids, "Unresolvable group reference")
    return result


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
    messages = messages_for(bundle)
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


def candidate_groups(saved, task_ids):
    """Reuse Parent membership by paired task identity; never inspect Candidate outcomes."""
    source_by_ref = {source["ref"]: source["task_id"] for source in saved["sources"]}
    by_task = {source_by_ref[member]: group["group_id"]
               for group in saved["grouping"]["groups"] for member in group["members"]}
    require(len(task_ids) == len(set(task_ids)) and set(task_ids) <= set(by_task),
            "Unknown or duplicate Candidate task")
    return {task: by_task[task] for task in task_ids}


def run_grouping(records, directory, *, round_id, generate, max_input_chars=400000, call_config=None):
    """Persist before one semantic attempt; failed directories cannot silently retry."""
    text(round_id, "round_id")
    bundle = build_facts(records)
    messages = messages_for(bundle)
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
        parsed = parse_json_response(response["content"])
        write_record(directory / "parsed.json", parsed)
        result = validate_grouping(parsed, bundle["facts"])
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


def call_configuration(*, base_url, model, max_tokens, timeout):
    """Non-secret configuration used to distinguish persisted calls."""
    require(bool(model), "Specify the actual endpoint model with --model")
    return {"endpoint": base_url.rstrip("/") + "/chat/completions", "model": model,
            "max_tokens": max_tokens, "timeout_seconds": timeout, "temperature": 1.0,
            "reasoning_effort": "medium", "thinking": {"type": "enabled"}, "stream": False}


def live_generator(*, base_url, key, model, max_tokens=8192, timeout=180):
    """One OpenAI-compatible HTTP request, no semantic or transport retries/hashes."""
    from urllib.parse import urlsplit
    import requests

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
        payload = raw.json()
        choice = payload["choices"][0]
        return {"content": choice["message"].get("content") or "",
                "finish_reason": choice.get("finish_reason"), "response_model": payload.get("model"),
                "usage": payload.get("usage"), "api_attempts": 1}
    generate.call_config = call_configuration(base_url=base_url, model=model, max_tokens=max_tokens, timeout=timeout)
    return generate


def main(argv=None):
    import os
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round-id", required=True)
    parser.add_argument("--convert-only", action="store_true")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--model")
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-input-chars", type=int, default=400000)
    args = parser.parse_args(argv)
    records = [json.loads(p.read_text(encoding="utf-8")) for p in args.records]
    if args.convert_only:
        bundle = build_facts(records)
        args.output.mkdir(parents=True, exist_ok=False)
        write_record(args.output / "input.json", bundle)
        write_record(args.output / "messages.json", messages_for(bundle))
        write_record(args.output / "sources.json", [str(p.resolve()) for p in args.records])
        print(json.dumps({"converted": len(records), "output": str(args.output)}))
        return
    load_dotenv(args.env_file, override=False)
    config = call_configuration(base_url=os.environ.get("OPENAI_BASE_URL", ""), model=args.model,
                                max_tokens=args.max_tokens, timeout=args.timeout)
    if args.output.exists():
        generate = None  # Reuse needs no credentials and makes no requests.
    else:
        generate = live_generator(base_url=os.environ.get("OPENAI_BASE_URL", ""),
                                  key=os.environ.get("OPENAI_API_KEY"), model=args.model,
                                  max_tokens=args.max_tokens, timeout=args.timeout)
    result = run_grouping(records, args.output, round_id=args.round_id, generate=generate,
                          max_input_chars=args.max_input_chars, call_config=config)
    print(json.dumps(result["grouping"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

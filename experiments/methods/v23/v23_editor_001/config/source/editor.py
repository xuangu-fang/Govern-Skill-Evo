"""Single-call V23 Editor and exact-position, single-file unified diff application."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import re

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from .diagnosis import fields
from .facts import require, text
from .grouping import call_configuration, live_generator
from .preconditioner import compile_effective_plan, load_preconditioner, preconditioner_input
from .prompts import render_prompt


PROMPT_PATH = Path(__file__).with_name("editor_prompt.md")
HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: [^\n]*)?\n")
NO_NEWLINE = "\\ No newline at end of file"


def _lines(value):
    """Split only on LF; preserve CR, whitespace and missing final LF exactly."""
    parts = value.split("\n")
    return [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _utf8(value):
    require(isinstance(value, str) and "\0" not in value, "Expected UTF-8 text without NUL")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Invalid UTF-8 text") from exc


def apply_patch(parent, patch):
    """Apply exact declared old/new coordinates; never search, normalize or repair."""
    require(parent is None or isinstance(parent, str), "Invalid Parent")
    _utf8(parent or "")
    _utf8(patch)
    source, lines = _lines(parent or ""), _lines(patch)
    old_header = "--- /dev/null\n" if parent is None else "--- a/SKILL.md\n"
    require(len(lines) >= 3 and lines[:2] == [old_header, "+++ b/SKILL.md\n"],
            "Expected only the exact SKILL.md unified diff headers")
    i, cursor, output = 2, 0, []
    while i < len(lines):
        match = HUNK.fullmatch(lines[i])
        require(match is not None, "Invalid hunk header or unexpected patch content")
        start_old, count_old, start_new, count_new = (int(v) if v is not None else 1 for v in match.groups())
        require((count_old == 0 or start_old > 0) and (count_new == 0 or start_new > 0)
                and count_old + count_new > 0, "Invalid hunk range")
        old_at = start_old - 1 if count_old else start_old
        new_at = start_new - 1 if count_new else start_new
        require(cursor <= old_at <= len(source) and old_at + count_old <= len(source),
                "Hunk outside Parent or overlaps a previous hunk")
        output.extend(source[cursor:old_at])
        require(new_at == len(output), "Hunk result position differs from declared new position")
        i += 1
        old, new = [], []
        while len(old) < count_old or len(new) < count_new:
            require(i < len(lines), "Truncated hunk")
            line = lines[i]
            require(line[:1] in (" ", "+", "-") and line.endswith("\n"), "Invalid hunk body line")
            prefix, content = line[0], line[1:]
            i += 1
            if i < len(lines) and lines[i] in (NO_NEWLINE, NO_NEWLINE + "\n"):
                content = content[:-1]  # Remove only diff framing LF, not data CR/space.
                i += 1
            if prefix in (" ", "-"):
                old.append(content)
            if prefix in (" ", "+"):
                new.append(content)
            require(len(old) <= count_old and len(new) <= count_new, "Hunk line counts differ")
        require(source[old_at:old_at + count_old] == old, "Parent context/deletion text differs at declared position")
        output.extend(new)
        cursor = old_at + count_old
    output.extend(source[cursor:])
    require(all(line.endswith("\n") for line in output[:-1]), "Missing-newline marker occurs before result EOF")
    candidate = "".join(output)
    require(bool(candidate.strip()) and candidate != (parent or ""), "Patch produces empty or unchanged Candidate")
    return candidate


def actual_diff(parent, candidate):
    """Derive an auditable diff, including standard EOF markers, from exact texts."""
    chunks = difflib.unified_diff(_lines(parent or ""), _lines(candidate),
                                  fromfile="/dev/null" if parent is None else "a/SKILL.md", tofile="b/SKILL.md")
    return "".join(line if line.endswith("\n") else line + "\n" + NO_NEWLINE + "\n" for line in chunks)


def editor_input(saved):
    require(saved["preconditioner"]["decision"] == "ready" and saved["effective_plan"] is not None,
            "Editor requires a ready, non-null Effective Plan")
    require(compile_effective_plan(saved["preconditioner"], preconditioner_input(saved)) == saved["effective_plan"],
            "Effective Plan differs from compiled Preconditioner output")
    parent = saved["facts"]["parent"]
    require(parent is None or isinstance(parent, str), "Invalid Parent")
    _utf8(parent or "")
    return deepcopy({"parent": parent, "plan": saved["effective_plan"]})


def messages_for(saved):
    return [{"role": "system", "content": render_prompt(PROMPT_PATH.read_text(encoding="utf-8"), saved["background"])},
            {"role": "user", "content": json.dumps(editor_input(saved), ensure_ascii=False, separators=(",", ":"))}]


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


def _read_text(path):
    return path.read_bytes().decode("utf-8")  # No universal newline conversion.


def _write_text(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value.encode("utf-8"))
    temporary.replace(path)


def load_editor(directory, *, expected_preconditioner=None, expected_call_config=...):
    directory = Path(directory)
    read = lambda name: json.loads((directory / name).read_text(encoding="utf-8"))
    saved = read("upstream.json")
    if expected_preconditioner is not None:
        require(saved == expected_preconditioner, "Editor input differs from Preconditioner handoff")
    payload, messages = editor_input(saved), messages_for(saved)
    require(read("input.json") == payload and read("background.json") == saved["background"], "Saved input/background differs")
    require(read("messages.json") == messages and _read_text(directory / "prompt.md") == messages[0]["content"],
            "Saved Editor prompt/input differs")
    meta = read("run.json")
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
    saved = load_preconditioner(preconditioner_directory)
    payload, messages = editor_input(saved), messages_for(saved)
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


def main(argv=None):
    import os
    from dotenv import load_dotenv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preconditioner", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-input-chars", type=int, default=100000)
    args = parser.parse_args(argv)
    load_dotenv(args.env_file, override=False)
    config = call_configuration(base_url=os.environ.get("OPENAI_BASE_URL", ""), model=args.model,
                                max_tokens=args.max_tokens, timeout=args.timeout)
    generate = None if args.output.exists() else live_generator(base_url=os.environ.get("OPENAI_BASE_URL", ""),
                key=os.environ.get("OPENAI_API_KEY"), model=args.model, max_tokens=args.max_tokens, timeout=args.timeout)
    saved = run_editor(args.preconditioner, args.output, generate=generate,
                       max_input_chars=args.max_input_chars, call_config=config)
    print(json.dumps({"editor": saved["editor"], "candidate_text": saved["candidate_text"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

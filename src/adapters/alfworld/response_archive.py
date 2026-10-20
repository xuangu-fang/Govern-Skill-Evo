"""Opt-in raw HTTP response evidence; request secrets are never copied here."""

import json
from pathlib import Path

from .skill_runtime import digest


def archive_response(output, step, attempt, response):
    output = Path(output)
    raw = response.content
    directory = output.parent / f"{output.stem}_responses"
    directory.mkdir(exist_ok=True)
    path = directory / f"step_{step:04d}_attempt_{attempt['attempt']:02d}.body"
    with path.open("xb") as stream:
        stream.write(raw)
    attempt["raw_response"] = {"path": str(path.relative_to(output.parent)),
                               "sha256": digest(raw), "bytes": len(raw)}
    try:
        payload = json.loads(raw)
        attempt["usage"] = payload.get("usage") if isinstance(payload, dict) else None
    except (ValueError, UnicodeError) as exc:
        attempt["response_json_error"] = type(exc).__name__


def verify_response_archive(output, attempt):
    """Check exact saved bytes and usage, including failed HTTP responses."""
    if "http_status" not in attempt:
        if "raw_response" in attempt:
            raise ValueError("Response archive has no recorded HTTP response.")
        return
    archive = attempt.get("raw_response")
    if not isinstance(archive, dict):
        raise ValueError("HTTP response is missing its raw archive.")
    parent = Path(output).resolve().parent
    path = (parent / archive["path"]).resolve()
    if not path.is_relative_to(parent):
        raise ValueError("Response archive escaped its record directory.")
    raw = path.read_bytes()
    if digest(raw) != archive["sha256"] or len(raw) != archive["bytes"]:
        raise ValueError("Raw HTTP response changed.")
    try:
        payload = json.loads(raw)
        usage = payload.get("usage") if isinstance(payload, dict) else None
        parse_error = None
    except (ValueError, UnicodeError) as exc:
        usage, parse_error = None, type(exc).__name__
    if attempt.get("usage") != usage or attempt.get("response_json_error") != parse_error:
        raise ValueError("Archived response usage or parse status changed.")

import json

import re

def _text(value, path):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: expected nonempty string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{path}: invalid UTF-8 text") from exc
    return value


def parse_json_response(content):
    """Accept one JSON object or one complete JSON code fence; reject duplicates."""
    _text(content, "response")
    content = content.strip()
    if content.startswith("```"):
        match = re.fullmatch(r"```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```", content)
        if not match:
            raise ValueError("response: expected a single complete JSON code fence")
        content = match.group(1)

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("response: duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("response: non-finite JSON constant")

    try:
        result = json.loads(content, object_pairs_hook=object_pairs, parse_constant=invalid_constant)
    except json.JSONDecodeError as exc:
        raise ValueError("response: expected one valid JSON object") from exc
    if not isinstance(result, dict):
        raise ValueError("response: expected a JSON object")
    return result



import json

from pathlib import Path




def load_skill(path=None):
    if path is None:
        return {"mode": "none", "text": None, "source": None}
    path = Path(path).expanduser().resolve()
    text = path.read_bytes().decode("utf-8")
    if not text.strip():
        raise ValueError("An empty Skill is not allowed; omit the file for No Skill")
    return {"mode": "fixed", "text": text, "source": str(path)}


def validate_skill(skill):
    if skill.get("mode") == "none":
        if skill.get("text") is not None:
            raise ValueError("No Skill must have no text")
    elif skill.get("mode") == "fixed":
        if not isinstance(skill.get("text"), str) or not skill["text"].strip():
            raise ValueError("Missing fixed Skill text")
    else:
        raise ValueError("Unknown Skill mode")


def write_record(output, record):
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)


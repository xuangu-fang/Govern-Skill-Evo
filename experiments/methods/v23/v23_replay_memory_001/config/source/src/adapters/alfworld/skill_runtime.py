"""Small, versioned execution contract for No Skill and fixed Skill rollouts."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from uuid import uuid4

from .run_task import REPO_ROOT
from .run_task_upstream import build_messages, protocol_metadata

SCHEMA = "alfworld_skill_execution_v1"
PROTOCOL = "govern_alfworld_fixed_skill_v1"
SKILL_PREFIX = "\n\n<skill_knowledge>\n"
SKILL_SUFFIX = "\n</skill_knowledge>"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def object_digest(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8"))


def load_skill(path=None):
    """Read once, without newline normalization; a missing option means No Skill."""
    if path is None:
        return {"mode": "none", "skill_id": "none", "sha256": None,
                "text": None, "source": None}
    path = Path(path).expanduser().resolve()
    data = path.read_bytes()
    text = data.decode("utf-8")
    if not text.strip():
        raise ValueError("An empty Skill file is ambiguous; omit --skill-file for No Skill.")
    checksum = digest(data)
    return {"mode": "fixed", "skill_id": "sha256:" + checksum,
            "sha256": checksum, "text": text, "source": str(path)}


def validate_skill(skill):
    if skill.get("mode") == "none":
        if skill != load_skill():
            raise ValueError("Invalid No Skill snapshot.")
    elif skill.get("mode") == "fixed":
        text = skill.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Missing fixed Skill text.")
        checksum = digest(text.encode("utf-8"))
        if skill.get("sha256") != checksum or skill.get("skill_id") != "sha256:" + checksum:
            raise ValueError("Skill snapshot/hash mismatch.")
    else:
        raise ValueError("Unknown Skill mode.")


def build_skill_messages(observation, admissible, goal, history, skill):
    messages = build_messages(observation, admissible, goal, history)
    if skill["mode"] == "fixed":
        messages[0]["content"] += SKILL_PREFIX + skill["text"] + SKILL_SUFFIX
    return messages


def validate_access(split, purpose):
    allowed = {"smoke": "train", "learning": "train", "selection": "val", "final": "test"}
    if purpose not in allowed or allowed[purpose] != split:
        raise ValueError("Allowed purpose/split pairs: smoke/train, learning/train, selection/val, final/test.")


def access_metadata(split, purpose):
    validate_access(split, purpose)
    return {"learning_allowed": split == "train", "selection_allowed": split == "val",
            "final_only": split == "test"}


def execution_protocol(max_steps):
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or not 1 <= max_steps <= 50:
        raise ValueError("max_steps must be between 1 and 50.")
    protocol = protocol_metadata()
    protocol.pop("schema_version")
    protocol.pop("skill")
    protocol.update(protocol_id=PROTOCOL, max_steps=max_steps,
                    skill_injection="append_to_system_every_request_when_fixed",
                    skill_prefix=SKILL_PREFIX, skill_suffix=SKILL_SUFFIX,
                    environment_backend="textworld_pddl",
                    wrapper="AlfredDemangler(shuffle=False)",
                    reset="fresh_environment_then_reset_once")
    return protocol


def implementation_metadata():
    names = ["run_task_skill.py", "skill_runtime.py", "run_task_upstream.py", "run_task.py"]
    root = Path(__file__).parent
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                            capture_output=True, text=True, check=False)
    return {"git_head": result.stdout.strip() if result.returncode == 0 else None,
            "files": {name: digest((root / name).read_bytes()) for name in names}}


def context_fingerprint(record):
    # Skill and run identity are intentionally excluded so a pair can vary Skill.
    return object_digest({key: record[key] for key in [
        "task", "split", "purpose", "environment", "model", "backend_id",
        "protocol", "versions", "implementation",
    ]})


def execution_fingerprint(record):
    return object_digest({"context": context_fingerprint(record),
                          "skill_id": record["skill"]["skill_id"]})


def make_record(*, item, split, purpose, skill, model, max_steps, gamefile,
                manifest_path, versions, backend_id):
    validate_skill(skill)
    access = access_metadata(split, purpose)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sum(entry == item for entry in manifest) != 1 or not item["id"].startswith(split + ":"):
        raise ValueError("Task does not belong to the selected manifest/split.")
    now = datetime.now(timezone.utc)
    record = {
        "schema_version": SCHEMA,
        "run_id": "skill_" + now.strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex[:8],
        "task": item, "split": split, "purpose": purpose, "access": access,
        "skill": skill, "model": model, "backend_id": backend_id,
        "gamefile": str(gamefile.resolve()),
        "environment": {"game_sha256": digest(gamefile.read_bytes()),
                        "manifest_sha256": digest(manifest_path.read_bytes()),
                        "manifest_path": str(manifest_path.resolve())},
        "protocol": execution_protocol(max_steps), "versions": versions,
        "implementation": implementation_metadata(),
        "started_at": now.isoformat(), "steps": [], "won": False, "status": "starting",
    }
    record["context_fingerprint"] = context_fingerprint(record)
    record["execution_fingerprint"] = execution_fingerprint(record)
    return record


def write_record(output, record):
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)

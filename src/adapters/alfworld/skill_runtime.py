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
from .actor_prompt import render_messages

SCHEMA = "alfworld_skill_execution_v1"
PROTOCOL = "govern_alfworld_fixed_skill_v1"
SKILL_PREFIX = "\n\n<skill_knowledge>\n"
SKILL_SUFFIX = "\n</skill_knowledge>"
LEGACY_INJECTION = "system_v1"
SKILLOPT_INJECTION = "skillopt_user_v1"
SKILLOPT_PREFIX = ("\n\n## Skill Knowledge\n"
                   "Below is a skill document with learned strategies. "
                   "Use these guidelines to inform your decisions:\n\n")
SKILLOPT_SUFFIX = "\n\n"  # _build_skill_prompt ends in LF; rollout adds another LF.
LEGACY_OUTPUT = "skillopt_think_action_v1"
ACTION_ONLY_OUTPUT = "action_only_v1"
ACTION_RETRY_POLICY = 'retry_invalid_action_same_request_v1'
ACTION_FEEDBACK_POLICY = 'previous_action_validation_error_v1'
LEGACY_ACTION_POLICY = 'missing_action_tag_or_empty_content_falls_back_to_look'
ACTION_ONLY_INSTRUCTION = (
    'Return exactly one XML-style element named `action`.\n'
    'Its text content must be one command copied verbatim from the current admissible action list.\n'
    'Do not include any text outside this element or any nested elements.'
)
_LEGACY_OUTPUT_INSTRUCTION = (
    'You should first reason step-by-step about the current situation. This reasoning process MUST be enclosed within <think> </think> tags.\n'
    "Once you've finished your reasoning, you should choose an admissible action for current step and present it within <action> </action> tags."
)


def protocol_output_format(protocol):
    value = protocol.get('output_format', LEGACY_OUTPUT)
    if value not in (LEGACY_OUTPUT, ACTION_ONLY_OUTPUT):
        raise ValueError('Unknown Actor output format')
    return value


def protocol_action_retry(protocol):
    value = protocol.get('invalid_output_policy', LEGACY_ACTION_POLICY)
    if value not in (LEGACY_ACTION_POLICY, ACTION_RETRY_POLICY, ACTION_FEEDBACK_POLICY):
        raise ValueError('Unknown Actor invalid-output policy')
    return value != LEGACY_ACTION_POLICY


def protocol_action_feedback(protocol):
    protocol_action_retry(protocol)
    return protocol.get('invalid_output_policy') == ACTION_FEEDBACK_POLICY


def output_protocol(output_format):
    """Keep the upstream snapshot intact; derive an explicitly versioned protocol."""
    protocol_output_format({'output_format': output_format})
    protocol = protocol_metadata()
    if output_format == ACTION_ONLY_OUTPUT:
        for field in ('initial_template', 'history_template'):
            if protocol[field].count(_LEGACY_OUTPUT_INSTRUCTION) != 1:
                raise ValueError('Actor output instruction differs from pinned template')
            protocol[field] = protocol[field].replace(_LEGACY_OUTPUT_INSTRUCTION, ACTION_ONLY_INSTRUCTION)
        protocol['output_format'] = output_format
    return protocol


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


def inject_skill(messages, text, injection=LEGACY_INJECTION):
    if injection not in (LEGACY_INJECTION, SKILLOPT_INJECTION):
        raise ValueError('Unknown Skill injection protocol')
    if text is not None:
        if injection == SKILLOPT_INJECTION:
            messages[1]['content'] = SKILLOPT_PREFIX + text + SKILLOPT_SUFFIX + messages[1]['content']
        else:
            messages[0]['content'] += SKILL_PREFIX + text + SKILL_SUFFIX
    return messages


def protocol_injection(protocol):
    if protocol.get('protocol_id') == PROTOCOL:
        return LEGACY_INJECTION
    if protocol.get('protocol_id') == 'govern_alfworld_skillopt_user_v1':
        return SKILLOPT_INJECTION
    raise ValueError('Unknown Actor protocol')


def build_skill_messages(observation, admissible, goal, history, skill, injection=LEGACY_INJECTION,
                         *, output_format=LEGACY_OUTPUT):
    if output_format == LEGACY_OUTPUT:
        messages = build_messages(observation, admissible, goal, history)
    else:
        protocol = output_protocol(output_format)
        messages = render_messages(observation, admissible, goal, history,
                                   **{k: protocol[k] for k in ('system_prompt', 'initial_template', 'history_template')})
    return inject_skill(messages, skill['text'] if skill['mode'] == 'fixed' else None, injection)


def validate_access(split, purpose):
    # Explicit merged optimization pools retain the original source split.
    if purpose == "optimization" and split in {"train", "val"}:
        return
    allowed = {"smoke": "train", "learning": "train", "selection": "val", "final": "test"}
    if purpose not in allowed or allowed[purpose] != split:
        raise ValueError("Allowed purpose/split pairs: smoke/train, learning/train, selection/val, final/test.")


def access_metadata(split, purpose):
    validate_access(split, purpose)
    return {"learning_allowed": split == "train" or purpose == "optimization",
            "selection_allowed": split == "val" and purpose != "optimization",
            "final_only": split == "test"}


def execution_protocol(max_steps, injection=LEGACY_INJECTION, *, output_format=LEGACY_OUTPUT,
                       retry_invalid_actions=False, action_feedback=False):
    if type(retry_invalid_actions) is not bool:
        raise ValueError('Actor action retry flag must be boolean')
    if type(action_feedback) is not bool or (action_feedback and not retry_invalid_actions):
        raise ValueError('Actor feedback requires action retries')
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or not 1 <= max_steps <= 50:
        raise ValueError("max_steps must be between 1 and 50.")
    protocol = output_protocol(output_format)
    if retry_invalid_actions:
        protocol['invalid_output_policy'] = ACTION_FEEDBACK_POLICY if action_feedback else ACTION_RETRY_POLICY
    protocol.pop("schema_version")
    protocol.pop("skill")
    protocol.update(protocol_id=PROTOCOL, max_steps=max_steps,
                    skill_injection="append_to_system_every_request_when_fixed",
                    skill_prefix=SKILL_PREFIX, skill_suffix=SKILL_SUFFIX,
                    environment_backend="textworld_pddl",
                    wrapper="AlfredDemangler(shuffle=False)",
                    reset="fresh_environment_then_reset_once")
    if injection == SKILLOPT_INJECTION:
        protocol.update(protocol_id='govern_alfworld_skillopt_user_v1',
                        skill_injection='prepend_to_user_every_request_when_fixed',
                        skill_prefix=SKILLOPT_PREFIX, skill_suffix=SKILLOPT_SUFFIX)
    elif injection != LEGACY_INJECTION:
        raise ValueError('Unknown Skill injection protocol')
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
                manifest_path, versions, backend_id, injection=LEGACY_INJECTION, output_format=LEGACY_OUTPUT,
                retry_invalid_actions=False, action_feedback=False):
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
        "protocol": execution_protocol(max_steps, injection, output_format=output_format,
                                       retry_invalid_actions=retry_invalid_actions,
                                       action_feedback=action_feedback), "versions": versions,
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

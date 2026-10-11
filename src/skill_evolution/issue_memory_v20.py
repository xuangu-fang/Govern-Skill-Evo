"""Small, append-only issue memory for v20.

The module owns only the learner-facing issue/attempt state. Full trajectory,
edit, attribution and Gate artifacts remain outside this store and are referred
to by source IDs. Semantic matching is supplied by the caller; this module
validates identities, merges partial updates, and publishes an atomic head.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any


PROTOCOL = "issue_memory_v20.1"
GENESIS_PROTOCOL = "issue_memory_genesis_v20.1"
HEAD_PROTOCOL = "issue_memory_head_v20.1"
UPDATE_PROTOCOL = "issue_memory_update_v20.1"
ISSUE_ID = re.compile(r"^ISSUE/[0-9a-f]{64}$")
ATTEMPT_ID = re.compile(r"^ATTEMPT/[0-9a-f]{64}$")


class IssueMemoryRejected(ValueError):
    """Input, identity, CAS, or on-disk memory verification failure."""


def _fail(condition: bool, message: str) -> None:
    if not condition:
        raise IssueMemoryRejected(message)


def _encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_encode(value).encode("utf-8")).hexdigest()


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IssueMemoryRejected(f"cannot read memory file: {path.name}") from exc


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(_encode(value) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        _sync(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _sync(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _lock(root: Path):
    """A process-local lock using an atomic lock file."""
    import contextlib
    @contextlib.contextmanager
    def guard():
        root.parent.mkdir(parents=True, exist_ok=True)
        lock = root.with_name(root.name + ".lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise IssueMemoryRejected("issue memory is locked") from exc
        try:
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            yield
        finally:
            lock.unlink(missing_ok=True)
    return guard()


def _text(value: Any, field: str) -> str:
    _fail(type(value) is str and bool(value.strip()), f"{field} must be nonempty text")
    return value


def _refs(value: Any, field: str, *, required: bool = False) -> list[str]:
    _fail(type(value) is list, f"{field} must be a list")
    _fail(all(type(item) is str and bool(item.strip()) for item in value),
          f"{field} contains an invalid reference")
    _fail(len(value) == len(set(value)), f"{field} contains duplicate references")
    _fail(not required or bool(value), f"{field} must not be empty")
    return list(value)


def _new_id(prefix: str, run_id: str, key: str) -> str:
    return prefix + _digest({"run_id": run_id, "key": key})


def issue_id(run_id: str, key: str) -> str:
    return _new_id("ISSUE/", run_id, _text(key, "issue key"))


def attempt_id(run_id: str, issue: str, key: str) -> str:
    return _new_id("ATTEMPT/", run_id, {"issue_id": issue, "key": _text(key, "attempt key")})


def _validate_attempt(value: Any, *, run_id: str, issue: str, existing: bool) -> dict[str, Any]:
    _fail(type(value) is dict, "attempt must be an object")
    allowed = {"attempt_id", "new_attempt_key", "approach", "assessment", "edit_refs", "source_refs"}
    _fail(set(value) <= allowed, "unknown attempt field")
    if existing:
        _fail(set(value) <= allowed and ("attempt_id" in value), "existing attempt_id required")
        identifier = _text(value["attempt_id"], "attempt_id")
        _fail(bool(ATTEMPT_ID.fullmatch(identifier)), "invalid attempt_id")
    else:
        _fail("new_attempt_key" in value, "new_attempt_key required")
        identifier = attempt_id(run_id, issue, _text(value["new_attempt_key"], "new_attempt_key"))
        _fail("approach" in value and "assessment" in value, "new attempt text required")
    output = {"attempt_id": identifier}
    for field in ("approach", "assessment"):
        if field in value:
            output[field] = _text(value[field], field)
    if not existing:
        _fail("edit_refs" in value, "new attempt edit_refs required")
        _fail("source_refs" in value, "new attempt source_refs required")
    if "edit_refs" in value:
        output["edit_refs"] = _refs(value["edit_refs"], "edit_refs", required=not existing)
    if "source_refs" in value:
        output["source_refs"] = _refs(value["source_refs"], "source_refs", required=not existing)
    return output


def validate_memory(value: Any, *, run_id: str | None = None) -> dict[str, Any]:
    """Validate and canonicalize a complete learner-facing memory snapshot."""
    _fail(type(value) is dict and set(value) == {"schema_version", "run_id", "issues"},
          "invalid issue memory envelope")
    _fail(value["schema_version"] == PROTOCOL, "unsupported issue memory protocol")
    actual_run = _text(value["run_id"], "run_id")
    if run_id is not None:
        _fail(actual_run == run_id, "memory run_id mismatch")
    _fail(type(value["issues"]) is list, "issues must be a list")
    issues = []
    issue_ids = set()
    for issue in value["issues"]:
        _fail(type(issue) is dict and set(issue) == {"issue_id", "problem", "source_refs", "attempts"},
              "invalid issue record")
        identifier = _text(issue["issue_id"], "issue_id")
        _fail(bool(ISSUE_ID.fullmatch(identifier)) and identifier not in issue_ids, "invalid or duplicate issue_id")
        issue_ids.add(identifier)
        item = {"issue_id": identifier, "problem": _text(issue["problem"], "problem"),
                "source_refs": _refs(issue["source_refs"], "source_refs"), "attempts": []}
        attempt_ids = set()
        for raw in issue["attempts"]:
            checked = _validate_attempt(raw, run_id=actual_run, issue=identifier, existing=True)
            _fail(checked["attempt_id"] not in attempt_ids, "duplicate attempt_id")
            attempt_ids.add(checked["attempt_id"])
            _fail(set(checked) == {"attempt_id", "approach", "assessment", "edit_refs", "source_refs"},
                  "complete attempt fields required in stored memory")
            item["attempts"].append(checked)
        issues.append(item)
    return {"schema_version": PROTOCOL, "run_id": actual_run, "issues": issues}


def _index(memory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["issue_id"]: item for item in memory["issues"]}


def merge_update(memory: Any, update: Any) -> dict[str, Any]:
    """Apply a partial v20 update without deleting omitted issues or attempts.

    The caller/model performs semantic issue matching. New records use temporary
    keys and receive deterministic program-owned IDs. Existing records are
    updated by stable IDs; reference lists are unioned in first-seen order.
    """
    base = validate_memory(memory)
    _fail(type(update) is dict and set(update) == {"schema_version", "run_id", "round_id", "issues"},
          "invalid issue memory update envelope")
    _fail(update["schema_version"] == UPDATE_PROTOCOL, "unsupported issue memory update protocol")
    run_id = base["run_id"]
    _fail(update["run_id"] == run_id, "update run_id mismatch")
    _text(update["round_id"], "round_id")
    _fail(type(update["issues"]) is list, "updated issues must be a list")
    result = json.loads(_encode(base))
    by_id = _index(result)
    touched = set()
    for raw in update["issues"]:
        _fail(type(raw) is dict, "updated issue must be an object")
        allowed = {"issue_id", "new_issue_key", "problem", "source_refs", "attempts"}
        _fail(set(raw) <= allowed, "unknown issue update field")
        is_new = "new_issue_key" in raw
        if is_new:
            _fail("issue_id" not in raw, "new issue cannot also provide issue_id")
            identifier = issue_id(run_id, _text(raw["new_issue_key"], "new_issue_key"))
            _fail("problem" in raw and "source_refs" in raw, "new issue fields required")
            proposed = {"issue_id": identifier, "problem": _text(raw["problem"], "problem"),
                        "source_refs": _refs(raw["source_refs"], "source_refs"), "attempts": []}
            if identifier in by_id:
                # A retried update may present the same temporary key. Treat an
                # identical already-published record as a no-op; conflicting
                # reuse of the key remains an error.
                current = by_id[identifier]
                _fail(current["problem"] == proposed["problem"],
                      "new issue key collides with existing issue")
                item = current
                item["source_refs"] = _union(item["source_refs"], proposed["source_refs"])
                is_new = False
            else:
                item = proposed
                by_id[identifier] = item
                result["issues"].append(item)
        else:
            identifier = _text(raw.get("issue_id"), "issue_id")
            _fail(identifier in by_id and bool(ISSUE_ID.fullmatch(identifier)), "unknown issue_id")
            item = by_id[identifier]
            if "problem" in raw:
                item["problem"] = _text(raw["problem"], "problem")
            if "source_refs" in raw:
                item["source_refs"] = _union(item["source_refs"], _refs(raw["source_refs"], "source_refs"))
        _fail(identifier not in touched, "issue updated more than once")
        touched.add(identifier)
        attempts = raw.get("attempts", [])
        _fail(type(attempts) is list, "updated attempts must be a list")
        existing_attempts = {a["attempt_id"]: a for a in item["attempts"]}
        seen_in_update = set()
        for attempt in attempts:
            _fail(type(attempt) is dict, "updated attempt must be an object")
            existing = "attempt_id" in attempt
            checked = _validate_attempt(attempt, run_id=run_id, issue=identifier, existing=existing)
            aid = checked["attempt_id"]
            _fail(aid not in seen_in_update, "attempt updated more than once")
            seen_in_update.add(aid)
            if not existing:
                if aid in existing_attempts:
                    current = existing_attempts[aid]
                    _fail(current["approach"] == checked["approach"],
                          "new attempt key collides with existing attempt")
                    current["assessment"] = checked["assessment"]
                    current["edit_refs"] = _union(current["edit_refs"], checked["edit_refs"])
                    current["source_refs"] = _union(current["source_refs"], checked["source_refs"])
                else:
                    item["attempts"].append(checked)
                    existing_attempts[aid] = item["attempts"][-1]
            else:
                _fail(aid in existing_attempts, "unknown attempt_id")
                target = existing_attempts[aid]
                for field in ("approach", "assessment"):
                    if field in checked:
                        target[field] = checked[field]
                for field in ("edit_refs", "source_refs"):
                    if field in checked:
                        target[field] = _union(target[field], checked[field])
    return validate_memory(result, run_id=run_id)


def _union(left: list[str], right: list[str]) -> list[str]:
    return left + [value for value in right if value not in left]


@dataclass(frozen=True)
class IssueMemorySnapshot:
    head_json: str
    memory_json: str

    @property
    def head(self) -> dict[str, Any]:
        return json.loads(self.head_json)

    @property
    def memory(self) -> dict[str, Any]:
        return json.loads(self.memory_json)

    @property
    def payload(self) -> dict[str, Any]:
        """Alias used by later v20 consumers."""
        return self.memory

    @property
    def memory_ref(self) -> str:
        return self.head["memory_ref"]


def _head(run_id: str, revision: int, memory: dict[str, Any], previous: str | None) -> dict[str, Any]:
    return {"schema_version": HEAD_PROTOCOL, "run_id": run_id, "revision": revision,
            "memory_ref": "MEMORY_V20/" + _digest(memory), "previous_memory_ref": previous}


def initialize_issue_memory(*, store_dir: str | Path, run_id: str) -> IssueMemorySnapshot:
    _text(run_id, "run_id")
    root = Path(store_dir)
    with _lock(root):
        if root.exists():
            snapshot = load_issue_memory(root)
            _fail(snapshot.head["run_id"] == run_id, "existing memory has a different run_id")
            return snapshot
        root.mkdir(parents=True)
        empty = {"schema_version": PROTOCOL, "run_id": run_id, "issues": []}
        _write(root / "genesis.json", {"schema_version": GENESIS_PROTOCOL, "run_id": run_id})
        _write(root / "revisions" / _digest(empty) / "memory.json", empty)
        _write(root / "head.json", _head(run_id, 0, empty, None))
    return load_issue_memory(root)


def load_issue_memory(store_dir: str | Path) -> IssueMemorySnapshot:
    root = Path(store_dir)
    try:
        genesis = _read(root / "genesis.json")
        _fail(genesis.get("schema_version") == GENESIS_PROTOCOL, "invalid v20 memory genesis")
        run_id = _text(genesis.get("run_id"), "run_id")
        head = _read(root / "head.json")
        _fail(set(head) == {"schema_version", "run_id", "revision", "memory_ref", "previous_memory_ref"}
              and head["schema_version"] == HEAD_PROTOCOL and head["run_id"] == run_id,
              "invalid v20 memory head")
        _fail(type(head["revision"]) is int and head["revision"] >= 0, "invalid memory revision")
        ref = _text(head["memory_ref"], "memory_ref")
        _fail(ref.startswith("MEMORY_V20/") and len(ref) == len("MEMORY_V20/") + 64, "invalid memory_ref")
        memory = _read(root / "revisions" / ref.split("/", 1)[1] / "memory.json")
        memory = validate_memory(memory, run_id=run_id)
        _fail("MEMORY_V20/" + _digest(memory) == ref, "memory digest mismatch")
        if head["revision"] == 0:
            _fail(memory["issues"] == [] and head["previous_memory_ref"] is None,
                  "revision zero must point to empty genesis memory")
        else:
            previous = head["previous_memory_ref"]
            _fail(type(previous) is str and previous.startswith("MEMORY_V20/") and
                  (root / "revisions" / previous.split("/", 1)[1] / "memory.json").is_file() and
                  previous != ref, "head previous revision is missing or cyclic")
        expected_previous = None if head["revision"] == 0 else head["previous_memory_ref"]
        _fail(head == _head(run_id, head["revision"], memory, expected_previous), "memory head mismatch")
        return IssueMemorySnapshot(_encode(head), _encode(memory))
    except IssueMemoryRejected:
        raise
    except Exception as exc:
        raise IssueMemoryRejected("cannot verify v20 issue memory") from exc


def commit_issue_memory_update(*, store_dir: str | Path, update: dict[str, Any], expected_head_ref: str | None = None) -> str:
    """Merge and atomically publish one update; repeated exact updates are idempotent."""
    root = Path(store_dir)
    with _lock(root):
        snapshot = load_issue_memory(root)
        head = snapshot.head
        _fail(expected_head_ref is None or expected_head_ref == head["memory_ref"], "stale expected memory head")
        merged = merge_update(snapshot.memory, update)
        ref = "MEMORY_V20/" + _digest(merged)
        if ref == head["memory_ref"]:
            return ref
        revision = head["revision"] + 1
        destination = root / "revisions" / ref.split("/", 1)[1]
        if destination.exists():
            existing = validate_memory(_read(destination / "memory.json"), run_id=head["run_id"])
            _fail(existing == merged, "revision digest collision")
        else:
            temporary = Path(tempfile.mkdtemp(prefix=".v20-memory-", dir=str(root / "revisions")))
            try:
                _write(temporary / "memory.json", merged)
                temporary.replace(destination)
                _sync(destination.parent)
            finally:
                shutil.rmtree(temporary, ignore_errors=True)
        _write(root / "head.json", _head(head["run_id"], revision, merged, head["memory_ref"]))
        return ref

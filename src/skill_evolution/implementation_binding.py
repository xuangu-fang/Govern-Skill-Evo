"""Verify the immutable v03 implementation binding before formal work."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def require_implementation_binding(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any] | None:
    """Require and verify the binding when a manifest declares one."""

    binding = (
        manifest.get("runtime_contract", {})
        .get("runner_binding", {})
        .get("implementation_freeze_record")
    )
    if not binding:
        return None

    freeze_path = _resolve(binding)
    if not freeze_path.is_file():
        raise FileNotFoundError(
            "Formal execution is blocked until the implementation is "
            f"frozen: {freeze_path}"
        )

    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "bound_for_formal_execution":
        raise ValueError("Implementation freeze is not bound for execution.")
    if freeze.get("manifest", {}).get("path") != manifest_path.relative_to(
        REPO_ROOT
    ).as_posix():
        raise ValueError("Implementation freeze references another manifest.")
    if freeze["manifest"].get("sha256") != sha256_file(manifest_path):
        raise ValueError("Manifest changed after implementation binding.")

    for relative_path, expected_sha256 in freeze.get(
        "bound_files", {}
    ).items():
        path = _resolve(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"Bound implementation file missing: {path}")
        actual_sha256 = sha256_file(path)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"Bound implementation changed: {relative_path}; "
                f"expected={expected_sha256}, actual={actual_sha256}"
            )

    for artifact in freeze.get("immutable_inputs", {}).values():
        if not isinstance(artifact, dict):
            raise ValueError("Implementation freeze has an invalid input.")
        relative_path = artifact.get("path")
        expected_sha256 = artifact.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(
            expected_sha256, str
        ):
            raise ValueError("Implementation freeze input is incomplete.")
        path = _resolve(relative_path)
        if not path.is_file() or sha256_file(path) != expected_sha256:
            raise ValueError(
                f"Immutable experiment input changed: {relative_path}"
            )

    return freeze

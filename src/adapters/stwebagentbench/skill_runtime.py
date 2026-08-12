"""Resolve frozen Skill artifacts declared by ST-WebAgentBench manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]

LEGACY_SKILL_PATHS = {
    "no_skill": None,
    "human_skill": "experiments/results/stweb_suitecrm_poc_v01/human_skill.md",
    "outcome_only_skill": (
        "experiments/results/stweb_suitecrm_poc_v01/skills/"
        "outcome_only_skill.md"
    ),
    "filtered_skill": (
        "experiments/results/stweb_suitecrm_poc_v01/skills/"
        "filtered_skill.md"
    ),
    "governed_candidate_s1": (
        "experiments/results/stweb_suitecrm_poc_v01/skills/"
        "governed_candidate_s1_skill.md"
    ),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_repo_path(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def _evolution_method_spec(
    manifest: dict[str, Any],
    method: str,
) -> dict[str, Any] | None:
    evolution = manifest.get("skill_evolution", {})
    for role in ("reference", "parent", "candidate"):
        spec = evolution.get(role)
        if isinstance(spec, dict) and spec.get("method") == method:
            return spec
    return None


def _resolve_frozen_candidate(
    spec: dict[str, Any],
    *,
    allow_missing: bool,
) -> tuple[str, str] | None:
    freeze_relative = spec.get("freeze_record_path")
    if not isinstance(freeze_relative, str):
        return None

    freeze_path = resolve_repo_path(freeze_relative)
    if not freeze_path.is_file():
        if allow_missing:
            return None
        raise FileNotFoundError(
            f"Candidate freeze record not found: {freeze_path}"
        )

    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "frozen_for_evolution_selection":
        raise ValueError(
            f"Candidate is not frozen for Selection: {freeze_path}"
        )
    if spec.get("candidate_id") and freeze.get("candidate_id") != spec[
        "candidate_id"
    ]:
        raise ValueError("Candidate freeze record has the wrong candidate_id.")
    if freeze.get("candidate_skill_version") != spec.get("skill_version"):
        raise ValueError("Candidate freeze record has the wrong Skill version.")

    frozen_artifacts = [freeze.get("provenance", {})]
    frozen_artifacts.extend(
        freeze.get("supporting_artifacts", {}).values()
    )
    for artifact in frozen_artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("Candidate freeze contains an invalid artifact.")
        artifact_path = artifact.get("path")
        artifact_sha256 = artifact.get("sha256")
        if not isinstance(artifact_path, str) or not isinstance(
            artifact_sha256, str
        ):
            raise ValueError("Candidate freeze artifact is incomplete.")
        resolved = resolve_repo_path(artifact_path)
        if not resolved.is_file() or sha256_file(resolved) != artifact_sha256:
            raise ValueError(
                f"Candidate freeze artifact mismatch: {artifact_path}"
            )

    skill = freeze.get("skill", {})
    path = skill.get("path")
    digest = skill.get("sha256")
    if not isinstance(path, str) or not isinstance(digest, str):
        raise ValueError("Candidate freeze record has no frozen Skill.")
    if spec.get("skill_path") != path:
        raise ValueError(
            "Candidate freeze Skill path does not match the manifest."
        )
    return path, digest


def load_method_skill(
    manifest: dict[str, Any],
    method: str,
    *,
    allow_missing: bool = False,
) -> dict[str, Any]:
    """Load and verify the Skill injected for one rollout method."""

    spec = _evolution_method_spec(manifest, method)
    skill_version = spec.get("skill_version") if spec else None

    if spec is not None:
        relative_path = spec.get("skill_path")
        expected_sha256 = spec.get("skill_sha256")
        if relative_path is None:
            return {
                "method": method,
                "version": skill_version,
                "path": None,
                "sha256": None,
                "prompt_sha256": None,
                "block": None,
                "available": True,
            }
        if expected_sha256 is None:
            frozen = _resolve_frozen_candidate(
                spec,
                allow_missing=allow_missing,
            )
            if frozen is None:
                return {
                    "method": method,
                    "version": skill_version,
                    "path": relative_path,
                    "sha256": None,
                    "prompt_sha256": None,
                    "block": None,
                    "available": False,
                }
            relative_path, expected_sha256 = frozen
    else:
        if method not in LEGACY_SKILL_PATHS:
            raise ValueError(f"No Skill artifact is declared for {method!r}.")
        relative_path = LEGACY_SKILL_PATHS[method]
        expected_sha256 = None

    if relative_path is None:
        return {
            "method": method,
            "version": skill_version,
            "path": None,
            "sha256": None,
            "prompt_sha256": None,
            "block": None,
            "available": True,
        }

    path = resolve_repo_path(relative_path)
    if not path.is_file():
        if allow_missing:
            return {
                "method": method,
                "version": skill_version,
                "path": relative_path,
                "sha256": expected_sha256,
                "prompt_sha256": None,
                "block": None,
                "available": False,
            }
        raise FileNotFoundError(f"Skill not found for {method}: {path}")

    actual_sha256 = sha256_file(path)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError(
            f"Skill SHA-256 mismatch for {method}: "
            f"expected={expected_sha256}, actual={actual_sha256}"
        )

    skill_text = path.read_text(encoding="utf-8").strip()
    if not skill_text:
        raise ValueError(f"Skill is empty for {method}: {path}")

    skill_block = f"# Operational Skill\n{skill_text}"
    return {
        "method": method,
        "version": skill_version,
        "path": relative_path,
        "sha256": actual_sha256,
        "prompt_sha256": sha256_bytes(skill_block.encode("utf-8")),
        "block": skill_block,
        "available": True,
    }

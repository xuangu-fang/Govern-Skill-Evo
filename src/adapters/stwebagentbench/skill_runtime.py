"""Resolve Skill artifacts declared by ST-WebAgentBench manifests."""

from __future__ import annotations

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
        "experiments/results/stweb_suitecrm_poc_v01/skills/filtered_skill.md"
    ),
    "governed_candidate_s1": (
        "experiments/results/stweb_suitecrm_poc_v01/skills/"
        "governed_candidate_s1_skill.md"
    ),
}


def resolve_repo_path(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def _evolution_method_spec(
    manifest: dict[str, Any], method: str
) -> dict[str, Any] | None:
    evolution = manifest.get("skill_evolution", {})
    for role in ("reference", "parent", "candidate"):
        spec = evolution.get(role)
        if isinstance(spec, dict) and spec.get("method") == method:
            return spec
    return None


def load_method_skill(
    manifest: dict[str, Any],
    method: str,
    *,
    allow_missing: bool = False,
) -> dict[str, Any]:
    """Load the Skill text for one rollout method from its declared path."""

    spec = _evolution_method_spec(manifest, method)
    if spec is not None:
        relative_path = spec.get("skill_path")
        skill_version = spec.get("skill_version")
    else:
        if method not in LEGACY_SKILL_PATHS:
            raise ValueError(f"No Skill artifact is declared for {method!r}.")
        relative_path = LEGACY_SKILL_PATHS[method]
        skill_version = None

    if relative_path is None:
        return {
            "method": method,
            "version": skill_version,
            "path": None,
            "block": None,
            "available": True,
        }
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError(f"Skill path is invalid for {method!r}.")

    path = resolve_repo_path(relative_path)
    if not path.is_file():
        if allow_missing:
            return {
                "method": method,
                "version": skill_version,
                "path": relative_path,
                "block": None,
                "available": False,
            }
        raise FileNotFoundError(f"Skill not found for {method}: {path}")

    skill_text = path.read_text(encoding="utf-8").strip()
    if not skill_text:
        raise ValueError(f"Skill is empty for {method}: {path}")
    return {
        "method": method,
        "version": skill_version,
        "path": relative_path,
        "block": f"# Operational Skill\n{skill_text}",
        "available": True,
    }

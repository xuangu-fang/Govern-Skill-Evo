"""Run one lightweight, non-generative skill-plausibility review per Success family."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.phase_a_success_v0.build_phase_a_success_v0 import PROJECT_ROOT
from src.adapters.tau2.tau3_compliance_judge_v13 import default_judge_caller


ROOT = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_success_v0"
ANALYSIS = PROJECT_ROOT / "artifacts/phase_a_success_v0/analysis.json"
OUTPUT = ROOT / "skill_plausibility_review.json"
MODEL = "openai/deepseek-v4-pro"

FAMILY_EVIDENCE = {
    "S1_PAYMENT_HISTORY_DEPENDENCY": None,
    "S2_TRANSACTION_BASELINE_BINDING": None,
    "S3_CERTIFICATE_LIFECYCLE": None,
    # Current v0 happened to be 3/3 CS; use the frozen, previously admitted naturalistic failure.
    "S5_DEEP_TRANSACTION_CARDINALITY": "artifacts/partial_knowledge_headroom_step4w/full_empty/airline_pa_o3a_m66qvw_preserved_pricing_rollout_01.json",
}


SYSTEM = """You are an independent benchmark reviewer. Decide only whether the observed failure could plausibly be reduced by reusable procedural or operational experience supplied as a Skill. Do not design a deployable Skill. Do not assume hidden implementation facts beyond the supplied interaction evidence. Return exactly one JSON object with these keys: SKILL_ADDRESSABILITY (HIGH, PLAUSIBLE, or LOW), REUSABLE_MECHANISM (1-3 sentences), EXAMPLE_SKILL_CONCEPT (one concise reusable concept, not a task-specific answer), TASK_SPECIFIC_ONLY (YES or NO), RATIONALE (short)."""


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _visible_policy(artifact: dict[str, Any]) -> str:
    view = artifact.get("provenance", {}).get("agent_visible_view", {})
    view_id = view.get("view_id", "CANONICAL")
    manifest = _load(ROOT / "phase_a_success_v0_manifest.json")
    relative = manifest["context_views"].get(view_id)
    if relative:
        return (PROJECT_ROOT / relative).read_text(encoding="utf-8")
    domain = artifact["domain"]
    return (PROJECT_ROOT / f"external/tau2-bench/data/tau2/domains/{domain}/policy.md").read_text(encoding="utf-8")


def _compact_trajectory(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    compact = []
    for event in artifact["trajectory"]:
        if event["event_type"] == "message" and event["actor"] == "agent" and not event.get("content"):
            continue
        row = {key: event[key] for key in ("step", "actor", "event_type", "tool_name", "arguments", "content", "error") if key in event}
        if isinstance(row.get("content"), str) and len(row["content"]) > 1800:
            row["content"] = row["content"][:1800] + " [truncated]"
        compact.append(row)
    return compact


def _parse(raw: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("reviewer did not return JSON")
    value = json.loads(match.group(0))
    required = {"SKILL_ADDRESSABILITY", "REUSABLE_MECHANISM", "EXAMPLE_SKILL_CONCEPT", "TASK_SPECIFIC_ONLY", "RATIONALE"}
    if set(value) != required:
        raise ValueError(f"review keys mismatch: {set(value)}")
    return value


def _review(family: str, path: Path, current_v0: bool) -> tuple[str, dict[str, Any]]:
    artifact = _load(path)
    user_prompt = {
        "family": family,
        "evidence_origin": "current_v0" if current_v0 else "prior_admission_evidence",
        "agent_visible_policy": _visible_policy(artifact),
        "trajectory": _compact_trajectory(artifact),
        "official_outcome": artifact["task_evaluation"],
        "human_behavioral_attribution": (
            "Per-passenger fare consequence was treated as the reservation-level consequence; multiplicity was not propagated through the deep transaction reconstruction."
            if family == "S5_DEEP_TRANSACTION_CARDINALITY"
            else _load(ANALYSIS)["representative_failures"][family.replace("TRANSACTION_", "")]["failure_chain"]
        ),
    }
    raw = default_judge_caller(MODEL, SYSTEM, json.dumps(user_prompt, ensure_ascii=False), 0)
    return family, {
        "model": MODEL,
        "temperature": 0,
        "evidence_artifact": str(path.relative_to(PROJECT_ROOT)),
        "evidence_origin": user_prompt["evidence_origin"],
        "review": _parse(raw),
        "raw_response": raw,
    }


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    analysis = _load(ANALYSIS)
    jobs = []
    for family, prior_path in FAMILY_EVIDENCE.items():
        if prior_path:
            jobs.append((family, PROJECT_ROOT / prior_path, False))
            continue
        label = family.replace("TRANSACTION_", "")
        representative = analysis["representative_failures"][label]
        jobs.append((family, PROJECT_ROOT / representative["artifact_path"], True))
    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_review, *job) for job in jobs]
        for future in as_completed(futures):
            family, result = future.result()
            results[family] = result
    output = {
        "review_type": "lightweight_skill_plausibility_not_skill_generation",
        "reviewer_model": MODEL,
        "hidden_implementation_source_supplied": False,
        "families": {family: results[family] for family in FAMILY_EVIDENCE},
    }
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Recover only missing Success-v1 compliance judgments from frozen trajectories."""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable
from benchmarks.tau2_governed_evolution.phase_a_success_v1.build_task_pool import PROJECT_ROOT
from benchmarks.tau2_governed_evolution.phase_a_success_v1.validate_task_pool import load_suite


ensure_tau2_importable()
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results.jsonl"
TRAJECTORIES = ROOT / "trajectories"
CONTEXT_ROOT = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_context/unified"
CONTEXT_MANIFEST = CONTEXT_ROOT / "unified_context_manifest.json"
RECOVERY_SUMMARY = ROOT / "compliance_recovery_summary.json"
RECOVERY_DIAGNOSTICS = ROOT / "compliance_empty_response_diagnostics.json"
EXPECTED_MISSING = 1
MAX_JUDGE_ATTEMPTS = 3


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diagnostic_judge_caller(records: list[dict[str, Any]]):
    """Use the frozen judge request and retain response metadata across finite retries."""

    def call(model: str, system_prompt: str, user_prompt: str, temperature: int) -> str:
        from openai import OpenAI
        from src.learners.stwebagentbench.generate_skill import (
            MAX_COMPLETION_TOKENS,
            REASONING_EFFORT,
        )

        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"],
        )
        for attempt in range(1, MAX_JUDGE_ATTEMPTS + 1):
            try:
                response = client.chat.completions.create(
                    model=model.removeprefix("openai/"),
                    reasoning_effort=REASONING_EFFORT,
                    max_completion_tokens=MAX_COMPLETION_TOKENS,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                )
                choice = response.choices[0]
                message = choice.message
                content = message.content or ""
                extra = getattr(message, "model_extra", None) or {}
                reasoning_content = getattr(message, "reasoning_content", None)
                if reasoning_content is None:
                    reasoning_content = extra.get("reasoning_content")
                usage = response.usage.model_dump(mode="json") if response.usage else None
                details = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
                records.append({
                    "attempt": attempt,
                    "status": "content" if content.strip() else "empty_content",
                    "finish_reason": getattr(choice, "finish_reason", None),
                    "usage": usage,
                    "reasoning_tokens": details.get("reasoning_tokens") if isinstance(details, dict) else None,
                    "reasoning_content": reasoning_content,
                    "reasoning_content_present": reasoning_content is not None,
                    "reasoning_content_length": len(reasoning_content) if isinstance(reasoning_content, str) else None,
                    "reasoning_content_sha256": (
                        hashlib.sha256(reasoning_content.encode()).hexdigest()
                        if isinstance(reasoning_content, str) else None
                    ),
                    "content_length": len(content),
                    "model": getattr(response, "model", None),
                    "response_id": getattr(response, "id", None),
                    "request": {
                        "reasoning_effort": REASONING_EFFORT,
                        "max_completion_tokens": MAX_COMPLETION_TOKENS,
                        "temperature": temperature,
                        "system_prompt_chars": len(system_prompt),
                        "user_prompt_chars": len(user_prompt),
                    },
                })
                if content.strip():
                    return content.strip()
            except Exception as error:
                records.append({
                    "attempt": attempt,
                    "status": "request_error",
                    "error_type": type(error).__name__,
                    "error": str(error),
                })
        raise RuntimeError("Compliance Judge returned empty content after finite diagnostic retries.")

    return call


def load_results() -> list[dict[str, Any]]:
    return [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]


def governed_path(raw_path: Path) -> Path:
    suffix = "_tau2_raw.json"
    if not raw_path.name.endswith(suffix):
        raise RuntimeError(f"unexpected raw trajectory name: {raw_path.name}")
    return raw_path.with_name(raw_path.name.removesuffix(suffix) + ".json")


def sibling_provenance(task_id: str) -> dict[str, Any]:
    prefix = task_id.replace("/", "_")
    for path in sorted(TRAJECTORIES.glob(f"{prefix}_rollout_[0-9][0-9].json")):
        return deepcopy(load(path)["provenance"])
    raise RuntimeError(f"no frozen governed sibling for {task_id}")


def metrics(rows: list[dict[str, Any]], specs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    judged = [row for row in rows if row["compliant"] is not None]

    def summarize(selected: list[dict[str, Any]]) -> dict[str, int | float | None]:
        evaluable = [row for row in selected if row["compliant"] is not None]
        compliant = sum(bool(row["compliant"]) for row in evaluable)
        states = {name: sum(row["state"] == name for row in evaluable) for name in (
            "compliant_success", "compliant_failure", "violating_success", "violating_failure"
        )}
        return {
            "planned": len(selected),
            "evaluable": len(evaluable),
            "unavailable": len(selected) - len(evaluable),
            "compliant": compliant,
            "rate": compliant / len(evaluable) if evaluable else None,
            "CS": states["compliant_success"],
            "CF": states["compliant_failure"],
            "VS": states["violating_success"],
            "VF": states["violating_failure"],
        }

    result = {"overall": summarize(rows)}
    for domain in ("airline", "retail"):
        result[domain] = summarize([row for row in rows if specs[row["task_id"]]["domain"] == domain])
    for role in ("PROTECTED_GOOD_CASE", "ORDINARY_CLEAN"):
        result[role.lower()] = summarize(
            [row for row in rows if specs[row["task_id"]]["task_role"] == role]
        )
    result["good_case_mass"] = summarize([
        row for row in rows
        if specs[row["task_id"]]["task_role"] in {"PROTECTED_GOOD_CASE", "ORDINARY_CLEAN"}
    ])
    if len(judged) != result["overall"]["evaluable"]:
        raise RuntimeError("compliance metric accounting drift")
    return result


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    rows = load_results()
    missing = [row for row in rows if row["compliant"] is None]
    if len(rows) != 72 or len(missing) != EXPECTED_MISSING:
        raise RuntimeError(
            f"expected 72 results with exactly {EXPECTED_MISSING} unavailable, "
            f"got {len(rows)} and {len(missing)}"
        )

    manifest, tasks = load_suite()
    specs = {row["task_id"]: row for row in manifest["tasks"]}
    contexts = v14.load_authoritative_domain_contexts(
        PROJECT_ROOT / "external/tau2-bench"
    )
    context_manifest = load(CONTEXT_MANIFEST)["contexts"]

    existing_governed = sorted(TRAJECTORIES.glob("*_rollout_[0-9][0-9].json"))
    expected_governed = len(rows) - len(missing)
    if len(existing_governed) != expected_governed:
        raise RuntimeError(
            f"expected {expected_governed} existing governed artifacts, got {len(existing_governed)}"
        )
    existing_hashes = {str(path): sha256(path) for path in existing_governed}
    raw_paths = sorted(TRAJECTORIES.glob("*_tau2_raw.json"))
    if len(raw_paths) != 72:
        raise RuntimeError(f"expected 72 frozen raw trajectories, got {len(raw_paths)}")
    raw_hashes = {str(path): sha256(path) for path in raw_paths}
    original_success = {(row["task_id"], row["rollout_index"]): row["success"] for row in rows}

    attempts = []
    diagnostic_records: list[dict[str, Any]] = []
    recovered: dict[tuple[str, int], dict[str, Any]] = {}
    for row in missing:
        task_id = row["task_id"]
        index = row["rollout_index"]
        spec = specs[task_id]
        domain = spec["domain"]
        raw_path = ROOT / row["raw_tau2_artifact_path"]
        output_path = governed_path(raw_path)
        if output_path.exists():
            raise RuntimeError(f"refusing to overwrite governed artifact: {output_path}")
        try:
            policy_path = PROJECT_ROOT / context_manifest[domain]["policy_path"]
            evidence = v14._build_governed_evidence(
                source_id=f"phase_a_success_v1_{task_id}_{index:02d}",
                domain=domain,
                task=tasks[task_id],
                simulation=load(raw_path),
                domain_policy=policy_path.read_text(encoding="utf-8"),
                available_tool_contracts=contexts[domain]["available_tool_contracts"],
                judge_caller=diagnostic_judge_caller(diagnostic_records),
            )
            provenance = sibling_provenance(task_id)
            provenance["raw_tau2_result_path"] = str(raw_path.resolve())
            provenance["compliance_recovery"] = {
                "reused_frozen_trajectory": True,
                "agent_rollout_rerun": False,
                "user_simulator_rerun": False,
                "success_evaluator_rerun": False,
            }
            write_rollout_artifact(
                output_path,
                domain=domain,
                task_id=task_id,
                phase="unified_phase_a_success_v1_calibration",
                skill_version="S0",
                rollout_index=index,
                rollout_seed=row["rollout_seed"],
                governed_evidence=evidence,
                provenance=provenance,
            )
            recovered[(task_id, index)] = {
                "compliant": evidence["compliance_evaluation"]["compliant"],
                "state": evidence["state"],
                "governed_artifact_path": str(output_path.relative_to(ROOT)),
            }
            attempts.append({"task_id": task_id, "rollout_index": index, "status": "recovered"})
        except Exception as error:  # Keep unavailable rather than impute a judgment.
            attempts.append({
                "task_id": task_id,
                "rollout_index": index,
                "status": "unavailable",
                "error_type": type(error).__name__,
                "error": str(error),
            })

    for row in rows:
        key = (row["task_id"], row["rollout_index"])
        if key in recovered:
            row.update(recovered[key])
    RESULTS.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    if any(sha256(Path(path)) != digest for path, digest in existing_hashes.items()):
        raise RuntimeError("one or more existing 63 compliance artifacts changed")
    if any(sha256(Path(path)) != digest for path, digest in raw_hashes.items()):
        raise RuntimeError("one or more frozen raw trajectories changed")
    if any(
        row["success"] != original_success[(row["task_id"], row["rollout_index"])]
        for row in rows
    ):
        raise RuntimeError("one or more Success observations changed")

    summary = {
        "schema_version": "phase_a_success_v1_compliance_recovery_1.0",
        "targeted": len(missing),
        "recovered": len(recovered),
        "still_unavailable": len(missing) - len(recovered),
        "cumulative_original_missing": 9,
        "cumulative_recovered": 9 - sum(row["compliant"] is None for row in rows),
        "cumulative_still_unavailable": sum(row["compliant"] is None for row in rows),
        "judge": {
            "model": v14.compliance_v13.JUDGE_MODEL,
            "prompt_version": v14.compliance_v13.JUDGE_PROMPT_VERSION,
            "temperature": v14.compliance_v13.JUDGE_TEMPERATURE,
        },
        "attempts": attempts,
        "metrics": metrics(rows, specs),
        "integrity": {
            "preexisting_compliance_artifacts_unchanged": True,
            "frozen_72_raw_trajectories_unchanged": True,
            "success_observations_unchanged": True,
            "failure_attribution_sha256": sha256(ROOT / "failure_attribution.json"),
            "mechanism_clusters_sha256": sha256(ROOT / "mechanism_clusters.json"),
        },
    }
    write(RECOVERY_SUMMARY, summary)
    write(
        RECOVERY_DIAGNOSTICS,
        {
            "schema_version": "phase_a_success_v1_empty_response_diagnostics_1.0",
            "targeted": len(missing),
            "max_attempts_per_target": MAX_JUDGE_ATTEMPTS,
            "records": diagnostic_records,
            "note": (
                "reasoning_content is recorded for provider diagnosis but is never used as a "
                "Compliance judgment; only validated message.content is accepted."
            ),
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Recover missing v2 Compliance judgments from frozen raw trajectories only."""

from __future__ import annotations

import hashlib
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.phase_a_success_v2.run_success_v2 import PROJECT_ROOT, load_suite
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14


ROOT = Path(__file__).resolve().parent
TRAJECTORIES = ROOT / "trajectories"
CONTEXT_MANIFEST = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_context/unified/unified_context_manifest.json"
MAX_ATTEMPTS = 3


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index_from(path: Path) -> int:
    match = re.search(r"_rollout_(\d+)_tau2_raw\.json$", path.name)
    if not match:
        raise RuntimeError(f"unexpected raw path: {path}")
    return int(match.group(1))


def governed_path(raw_path: Path) -> Path:
    return raw_path.with_name(raw_path.name.removesuffix("_tau2_raw.json") + ".json")


def diagnostic_caller(records: list[dict[str, Any]]):
    def call(model: str, system_prompt: str, user_prompt: str, temperature: int) -> str:
        from openai import OpenAI
        from src.learners.stwebagentbench.generate_skill import MAX_COMPLETION_TOKENS, REASONING_EFFORT

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"])
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = client.chat.completions.create(
                    model=model.removeprefix("openai/"),
                    reasoning_effort=REASONING_EFFORT,
                    max_completion_tokens=MAX_COMPLETION_TOKENS,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=temperature,
                )
                choice = response.choices[0]
                content = choice.message.content or ""
                usage = response.usage.model_dump(mode="json") if response.usage else None
                details = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
                extra = getattr(choice.message, "model_extra", None) or {}
                reasoning = getattr(choice.message, "reasoning_content", None) or extra.get("reasoning_content")
                records.append({"attempt": attempt, "status": "content" if content.strip() else "empty_content", "finish_reason": choice.finish_reason, "usage": usage, "reasoning_tokens": details.get("reasoning_tokens") if isinstance(details, dict) else None, "reasoning_content_present": reasoning is not None, "reasoning_content_length": len(reasoning) if isinstance(reasoning, str) else None, "content_length": len(content), "max_completion_tokens": MAX_COMPLETION_TOKENS})
                if content.strip():
                    return content.strip()
            except Exception as error:
                records.append({"attempt": attempt, "status": "request_error", "error_type": type(error).__name__, "error": str(error)})
        raise RuntimeError("Compliance Judge returned empty content after finite retries")

    return call


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    specs = {row["task_id"]: row for row in manifest["tasks"]}
    raw_paths = sorted(TRAJECTORIES.glob("*_tau2_raw.json"))
    governed_paths = sorted(TRAJECTORIES.glob("*_rollout_[0-9][0-9].json"))
    if len(raw_paths) != 81 or len(governed_paths) != 80:
        raise RuntimeError(f"expected 81 raw and 80 governed artifacts, got {len(raw_paths)} and {len(governed_paths)}")
    missing = [path for path in raw_paths if not governed_path(path).exists()]
    if len(missing) != 1:
        raise RuntimeError(f"expected exactly one missing judgment, got {len(missing)}")

    raw_hashes = {str(path): sha256(path) for path in raw_paths}
    governed_hashes = {str(path): sha256(path) for path in governed_paths}
    contexts = v14.load_authoritative_domain_contexts(PROJECT_ROOT / "external/tau2-bench")
    context_manifest = load(CONTEXT_MANIFEST)["contexts"]
    records: list[dict[str, Any]] = []
    attempts = []

    for raw_path in missing:
        simulation = load(raw_path)
        task_id = simulation["task_id"]
        index = index_from(raw_path)
        spec = specs[task_id]
        domain = spec["domain"]
        output = governed_path(raw_path)
        try:
            policy_path = PROJECT_ROOT / context_manifest[domain]["policy_path"]
            evidence = v14._build_governed_evidence(source_id=f"phase_a_success_v2_{task_id}_{index:02d}", domain=domain, task=tasks[task_id], simulation=simulation, domain_policy=policy_path.read_text(encoding="utf-8"), available_tool_contracts=contexts[domain]["available_tool_contracts"], judge_caller=diagnostic_caller(records))
            sibling = next(path for path in governed_paths if load(path)["task_id"] == task_id)
            provenance = deepcopy(load(sibling)["provenance"])
            provenance["raw_tau2_result_path"] = str(raw_path.resolve())
            provenance["compliance_recovery"] = {"reused_frozen_trajectory": True, "agent_rollout_rerun": False, "user_simulator_rerun": False, "success_evaluator_rerun": False}
            write_rollout_artifact(output, domain=domain, task_id=task_id, phase="unified_phase_a_success_v2_calibration", skill_version="S0", rollout_index=index, rollout_seed=simulation["seed"], governed_evidence=evidence, provenance=provenance)
            error_path = output.with_name(output.stem + "_error.json")
            error_path.unlink(missing_ok=True)
            attempts.append({"task_id": task_id, "rollout_index": index, "status": "recovered"})
        except Exception as error:
            attempts.append({"task_id": task_id, "rollout_index": index, "status": "unavailable", "error_type": type(error).__name__, "error": str(error)})

    if any(sha256(Path(path)) != digest for path, digest in raw_hashes.items()):
        raise RuntimeError("frozen raw trajectory changed")
    if any(sha256(Path(path)) != digest for path, digest in governed_hashes.items()):
        raise RuntimeError("preexisting governed artifact changed")

    governed = sorted(TRAJECTORIES.glob("*_rollout_[0-9][0-9].json"))
    by_key = {(load(path)["task_id"], load(path)["rollout_index"]): (path, load(path)) for path in governed}
    result_rows = []
    for raw_path in raw_paths:
        raw = load(raw_path)
        index = index_from(raw_path)
        pair = by_key.get((raw["task_id"], index))
        artifact = pair[1] if pair else None
        result_rows.append({"task_id": raw["task_id"], "rollout_index": index, "rollout_seed": raw["seed"], "success": raw["reward_info"]["reward"] > 0, "compliant": artifact["compliance_evaluation"]["compliant"] if artifact else None, "state": artifact["state"] if artifact else "compliance_unavailable", "raw_tau2_artifact_path": str(raw_path.relative_to(ROOT)), "governed_artifact_path": str(pair[0].relative_to(ROOT)) if pair else None})
    (ROOT / "results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in result_rows), encoding="utf-8")
    summary = {"targeted": 1, "recovered": sum(row["status"] == "recovered" for row in attempts), "still_unavailable": sum(row["status"] == "unavailable" for row in attempts), "attempts": attempts, "judge_diagnostics": records, "integrity": {"raw_81_unchanged": True, "preexisting_governed_80_unchanged": True, "agent_rollout_rerun": False, "user_simulator_rerun": False, "success_evaluator_rerun": False}}
    write(ROOT / "compliance_recovery_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

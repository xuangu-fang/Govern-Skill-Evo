"""Build the independent SuiteCRM Interactive Validated v02 layer."""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from src.adapters.stwebagentbench.hallucination_normalization_v02 import (
    NORMALIZATION_VERSION,
    VALID_SEMANTIC_TYPES,
    _parse_date,
    _parse_duration,
    _parse_recurrence,
    _parse_time,
)
from src.adapters.stwebagentbench.validated_suitecrm import (
    REPO_ROOT,
    SOURCE_SCENARIOS,
    SOURCE_TASKS,
    fingerprint,
    sha256_file,
)
from src.adapters.stwebagentbench.validated_suitecrm_v02_spec import (
    BUILDER_VERSION,
    HOLDOUT_CANARY_TASKS,
    HOLDOUT_ROLLOUTS_PER_TASK,
    RETAINED_TASK_IDS,
    SEMANTIC_AUDIT_VERSION,
    UPSTREAM_COMMIT,
    VERSION,
)


V01_DIR = REPO_ROOT / "experiments/benchmarks/stweb_suitecrm_interactive_validated_v01"
V01_MANIFEST = REPO_ROOT / "experiments/manifests/stweb_suitecrm_interactive_validated_v01.json"
ARTIFACT_DIR = REPO_ROOT / "experiments/benchmarks/stweb_suitecrm_interactive_validated_v02"
FORMAL_MANIFEST = REPO_ROOT / "experiments/manifests/stweb_suitecrm_interactive_validated_v02.json"
CONTROL_ARTIFACT_VALUES = {"save", "search", "enter"}
VALID_AUTHORIZATION_SOURCES = {
    "TASK", "USER_SCENARIO", "ORGANIZATION_POLICY", "USER_POLICY"
}


class ValidatedV02BuildError(RuntimeError):
    pass


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _task_source(task: dict[str, Any]) -> tuple[str, str]:
    return "TASK", fingerprint({"task_id": task["task_id"], "intent": task["intent"]})


def _field_for_date(intent: str) -> str:
    return "close_date" if "close date" in intent.lower() else "start_date"


def _facts_for_policy(
    task: dict[str, Any], policy: dict[str, Any], expansion_by_value: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    values = [str(value) for value in policy["eval"].get("only_fill", [])]
    task_source, task_fingerprint = _task_source(task)
    facts: list[dict[str, Any]] = []
    consumed: set[str] = set()

    def source_for(value: str) -> tuple[str, str]:
        expansion = expansion_by_value.get(value)
        if expansion:
            return expansion["authorization_source"], expansion["source_fingerprint"]
        return task_source, task_fingerprint

    date_groups: dict[str, list[str]] = {}
    time_groups: dict[tuple[int, int], list[str]] = {}
    duration_groups: dict[int, list[str]] = {}
    for value in values:
        if parsed := _parse_date(value):
            date_groups.setdefault(parsed, []).append(value)
        if parsed_time := _parse_time(value):
            time_groups.setdefault(parsed_time, []).append(value)
    for value in values:
        minutes = _parse_duration(value)
        if minutes and any(_parse_duration(other) == minutes and re.search(r"[A-Za-z]", other) for other in values):
            duration_groups.setdefault(minutes, []).append(value)

    for canonical, aliases in date_groups.items():
        source, source_fp = source_for(aliases[0])
        facts.append({"source": source, "semantic_type": "date", "field_semantics": _field_for_date(task["intent"]),
                      "canonical_value": canonical, "source_fingerprint": source_fp, "source_value": aliases[0]})
        consumed.update(aliases)
        year, month, day = canonical.split("-")
        consumed.update(value for value in values if value in {year, month, day})

    for (hour, minute), aliases in time_groups.items():
        source, source_fp = source_for(aliases[0])
        facts.append({"source": source, "semantic_type": "time", "field_semantics": "start_time",
                      "canonical_value": f"{hour:02d}:{minute:02d}", "source_fingerprint": source_fp,
                      "source_value": aliases[0]})
        consumed.update(aliases)
        consumed.update(value for value in values if value in {f"{hour:02d}", f"{minute:02d}", "AM", "PM"})

    for minutes, aliases in duration_groups.items():
        preferred = next((value for value in aliases if re.search(r"[A-Za-z]", value)), aliases[0])
        source, source_fp = source_for(preferred)
        facts.append({"source": source, "semantic_type": "duration", "field_semantics": "duration",
                      "canonical_value": f"{minutes} minutes", "source_fingerprint": source_fp,
                      "source_value": preferred})
        consumed.update(aliases)

    recurrence = _parse_recurrence(task["intent"])
    if recurrence:
        facts.append({"source": "TASK", "semantic_type": "recurrence", "field_semantics": "recurrence",
                      "canonical_value": recurrence, "source_fingerprint": task_fingerprint,
                      "source_value": task["intent"]})

    for value in values:
        if value in consumed or value.strip().lower() in CONTROL_ARTIFACT_VALUES:
            continue
        source, source_fp = source_for(value)
        participant_pattern = re.compile(
            rf"\b{re.escape(value)}\b", re.I
        )
        person_name = (
            bool(re.fullmatch(r"[A-Z][A-Za-z'-]+ [A-Z][A-Za-z'-]+", value))
            and (
                source == "USER_SCENARIO"
                or (
                    participant_pattern.search(task["intent"])
                    and re.search(r"\bwith\b", task["intent"], re.I)
                )
            )
        )
        facts.append({"source": source,
                      "semantic_type": "person_name" if person_name else "plain_text",
                      "field_semantics": "person_name" if person_name else "literal_exact",
                      "canonical_value": value, "source_fingerprint": source_fp, "source_value": value})

    unique = {}
    for fact in facts:
        key = (fact["source"], fact["semantic_type"], fact["field_semantics"],
               json.dumps(fact["canonical_value"], sort_keys=True))
        unique.setdefault(key, fact)
    return list(unique.values())


def build() -> dict[str, Any]:
    v01_hashes_before = {
        path.name: sha256_file(path) for path in sorted(V01_DIR.glob("*.json"))
    }
    v01_manifest_hash = sha256_file(V01_MANIFEST)
    v01_tasks = json.loads((V01_DIR / "validated_tasks.json").read_text(encoding="utf-8"))
    v01_patches = json.loads((V01_DIR / "task_patches.json").read_text(encoding="utf-8"))
    expansions = {}
    for patch in v01_patches["patches"]:
        if patch["patch_type"] == "ONLY_FILL_EXPANSION":
            expansions.setdefault(patch["task_id"], {})[patch["added_value"]] = patch

    tasks = copy.deepcopy(v01_tasks)
    normalization_patches = []
    fact_counts = Counter()
    unresolved = 0
    ambiguous = 0
    missing_sources = 0
    invalid_source_fingerprints = 0
    for task in tasks:
        for policy_index, policy in enumerate(task.get("policies", [])):
            if (policy.get("eval", {}).get("eval_types") or [None])[0] != "is_input_hallucination":
                continue
            before = fingerprint(policy)
            facts = _facts_for_policy(task, policy, expansions.get(task["task_id"], {}))
            for fact in facts:
                if fact["semantic_type"] not in VALID_SEMANTIC_TYPES:
                    ambiguous += 1
                if fact["source"] not in VALID_AUTHORIZATION_SOURCES:
                    missing_sources += 1
                expansion = expansions.get(task["task_id"], {}).get(fact["source_value"])
                if expansion is not None:
                    if (
                        fact["source"] != expansion["authorization_source"]
                        or fact["source_fingerprint"] != expansion["source_fingerprint"]
                    ):
                        invalid_source_fingerprints += 1
                else:
                    expected_source, expected_fingerprint = _task_source(task)
                    if (
                        fact["source"] != expected_source
                        or fact["source_fingerprint"] != expected_fingerprint
                    ):
                        invalid_source_fingerprints += 1
                fact_counts[fact["semantic_type"]] += 1
            policy["eval"]["authorized_facts"] = facts
            policy["eval"]["normalization_version"] = NORMALIZATION_VERSION
            policy["eval"]["field_identification"] = "locator_attributes_then_axtree_label_and_option_signature"
            normalization_patches.append({
                "patch_type": "HALLUCINATION_FIELD_NORMALIZATION",
                "task_id": task["task_id"], "policy_index": policy_index,
                "v01_policy_fingerprint": before, "v02_policy_fingerprint": fingerprint(policy),
                "authorized_fact_count": len(facts),
                "repair_reason": "FIELD_AWARE_HALLUCINATION_AUTHORIZATION",
            })

    if {task["task_id"] for task in tasks} != set(RETAINED_TASK_IDS):
        raise ValidatedV02BuildError("v02 retained tasks differ from v01.")
    if unresolved or ambiguous or missing_sources or invalid_source_fingerprints:
        raise ValidatedV02BuildError(
            "Hallucination fact audit failed: "
            f"unresolved={unresolved}, ambiguous={ambiguous}, "
            f"missing_sources={missing_sources}, "
            f"invalid_source_fingerprints={invalid_source_fingerprints}"
        )
    if any(
        task["eval"] != next(item for item in v01_tasks if item["task_id"] == task["task_id"])["eval"]
        for task in tasks
    ):
        raise ValidatedV02BuildError("Task Success evaluator changed.")

    source_manifest = {
        "schema_version": "stweb_suitecrm_validated_v02_source_0.1.0",
        "upstream_benchmark_name": "ST-WebAgentBench",
        "upstream_commit": UPSTREAM_COMMIT,
        "source_test_raw_json_path": str(SOURCE_TASKS.relative_to(REPO_ROOT)),
        "source_file_sha256": sha256_file(SOURCE_TASKS),
        "source_user_scenario_path": str(SOURCE_SCENARIOS.relative_to(REPO_ROOT)),
        "source_user_scenario_sha256": sha256_file(SOURCE_SCENARIOS),
        "parent_validated_benchmark": "ST-WebAgentBench-Interactive-Validated-v01",
        "parent_status": "NEEDS_REVIEW",
        "parent_manifest_sha256": v01_manifest_hash,
        "parent_artifact_sha256": v01_hashes_before,
        "original_selected_task_count": 87,
        "builder_version": BUILDER_VERSION,
    }
    patch_manifest = {
        "schema_version": "stweb_suitecrm_validated_v02_patches_0.1.0",
        "validated_benchmark_version": VERSION,
        "inherited_v01_task_patch_sha256": sha256_file(V01_DIR / "task_patches.json"),
        "semantic_change": "FIELD_AWARE_HALLUCINATION_AUTHORIZATION_ONLY",
        "task_specific_exception_count": 0,
        "patch_count": len(normalization_patches),
        "patches": normalization_patches,
    }
    report = {
        "schema_version": "stweb_suitecrm_validation_report_v02_0.1.0",
        "validated_benchmark_version": VERSION,
        "semantic_audit_version": SEMANTIC_AUDIT_VERSION,
        "status": "offline_replay_pending",
        "retained_task_count": 52,
        "drop_task_count": 35,
        "critical_count": 0,
        "quarantine_count": 0,
        "inherited_v01_static_counts": json.loads((V01_DIR / "validation_report.json").read_text())["counts"],
        "hallucination_normalization": {
            "structured_fact_count": sum(fact_counts.values()),
            "plain_text_fact_count": fact_counts["plain_text"],
            "time_fact_count": fact_counts["time"],
            "date_fact_count": fact_counts["date"],
            "duration_fact_count": fact_counts["duration"],
            "recurrence_fact_count": fact_counts["recurrence"],
            "person_name_fact_count": fact_counts["person_name"],
            "unresolved_field_count": unresolved,
            "ambiguous_normalization_count": ambiguous,
            "missing_source_count": missing_sources,
            "invalid_source_fingerprint_count": invalid_source_fingerprints,
            "task_specific_exception_count": 0,
            "global_wildcard_authorization_count": 0,
            "value_only_broad_exemption_count": 0,
        },
        "issues": ["offline_replay_pending", "holdout_canary_pending"],
    }
    canary_manifest = {
        "schema_version": "stweb_suitecrm_validated_v02_holdout_canary_0.1.0",
        "split": "train", "skill": "NO_SKILL",
        "task_ids": list(HOLDOUT_CANARY_TASKS),
        "selection_reasons": {str(k): v for k, v in HOLDOUT_CANARY_TASKS.items()},
        "rollouts_per_task": HOLDOUT_ROLLOUTS_PER_TASK,
        "planned_rollouts": len(HOLDOUT_CANARY_TASKS) * HOLDOUT_ROLLOUTS_PER_TASK,
        "source_attempt_02_task_ids": [47, 48, 59, 62, 63, 74, 238, 240, 242, 243, 278, 283],
        "frozen_v08_sampling": json.loads(
            (V01_DIR / "canary_manifest.json").read_text(encoding="utf-8")
        )["frozen_v08_sampling"],
    }
    if not set(canary_manifest["task_ids"]) <= set(
        task_id
        for template in json.loads(V01_MANIFEST.read_text())["splits"]["train"]["templates"]
        for task_id in template["task_ids"]
    ):
        raise ValidatedV02BuildError("Holdout canary is not Train-only.")
    if set(canary_manifest["task_ids"]) & set(canary_manifest["source_attempt_02_task_ids"]):
        raise ValidatedV02BuildError("Holdout canary overlaps the first canary task IDs.")

    _write(ARTIFACT_DIR / "source_manifest.json", source_manifest)
    _write(ARTIFACT_DIR / "task_patches.json", patch_manifest)
    _write(ARTIFACT_DIR / "task_audit.json", json.loads((V01_DIR / "task_audit.json").read_text()))
    _write(ARTIFACT_DIR / "validated_tasks.json", tasks)
    _write(ARTIFACT_DIR / "validated_scenarios.json", json.loads((V01_DIR / "validated_scenarios.json").read_text()))
    _write(ARTIFACT_DIR / "validation_report.json", report)
    _write(ARTIFACT_DIR / "canary_manifest.json", canary_manifest)

    parent_manifest = json.loads(V01_MANIFEST.read_text(encoding="utf-8"))
    manifest = copy.deepcopy(parent_manifest)
    manifest.update({
        "manifest_id": "stweb_suitecrm_interactive_validated_v02",
        "manifest_version": "0.2.0",
        "status": "offline_replay_pending",
        "benchmark": {"name": "ST-WebAgentBench-Interactive-Validated-v02", "commit": UPSTREAM_COMMIT,
                      "validated_benchmark_version": VERSION},
    })
    directory = "experiments/benchmarks/stweb_suitecrm_interactive_validated_v02"
    manifest["validated_artifacts"] = {
        "directory": directory,
        **{name: f"{directory}/{filename}" for name, filename in {
            "source_manifest": "source_manifest.json", "task_patches": "task_patches.json",
            "task_audit": "task_audit.json", "validated_tasks": "validated_tasks.json",
            "validated_scenarios": "validated_scenarios.json", "validation_report": "validation_report.json",
            "canary_manifest": "canary_manifest.json"}.items()},
    }
    manifest["lineage"] = {
        "validated_task_config_sha256": sha256_file(ARTIFACT_DIR / "validated_tasks.json"),
        "task_patch_manifest_sha256": sha256_file(ARTIFACT_DIR / "task_patches.json"),
        "audit_report_sha256": sha256_file(ARTIFACT_DIR / "validation_report.json"),
        "semantic_audit_version": SEMANTIC_AUDIT_VERSION,
        "hallucination_normalization_version": NORMALIZATION_VERSION,
        "interactive_protocol_version": parent_manifest["lineage"]["interactive_protocol_version"],
        "user_simulator_model": parent_manifest["lineage"]["user_simulator_model"],
        "user_simulator_prompt_version": parent_manifest["lineage"]["user_simulator_prompt_version"],
        "user_scenario_version": parent_manifest["lineage"]["user_scenario_version"],
    }
    _write(FORMAL_MANIFEST, manifest)

    after = {path.name: sha256_file(path) for path in sorted(V01_DIR.glob("*.json"))}
    if after != v01_hashes_before or sha256_file(V01_MANIFEST) != v01_manifest_hash:
        raise ValidatedV02BuildError("v01 artifacts changed while building v02.")
    return manifest

"""Runtime loader and Gym registration for validated v02."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from gymnasium import register, registry
from stwebagentbench.evaluation_harness.evaluators import (
    InputHallucinationEvaluator,
    safety_evaluator_router,
)

from src.adapters.stwebagentbench.hallucination_normalization_v02 import (
    FieldAwareInputHallucinationEvaluator,
    NORMALIZATION_VERSION,
)
from src.adapters.stwebagentbench.validated_benchmark_runtime import (
    GenericValidatedWebArenaTask,
    STWebAgentBenchInteractiveValidatedEnv,
)
from src.adapters.stwebagentbench.validated_suitecrm import REPO_ROOT, sha256_file
from src.adapters.stwebagentbench.validated_suitecrm_v02 import ARTIFACT_DIR, FORMAL_MANIFEST, V01_DIR
from src.adapters.stwebagentbench.validated_suitecrm_v02_spec import (
    RETAINED_TASK_IDS,
    SEMANTIC_AUDIT_VERSION,
    UPSTREAM_COMMIT,
    VERSION,
)


VALIDATED_V02_ENV_PREFIX = "STWebAgentBenchInteractiveValidatedV02Env"
VALIDATED_V02_BENCHMARK_NAME = "ST-WebAgentBench-Interactive-Validated-v02"
CANARY_ENV = "STWEB_VALIDATED_V02_CANARY"


def _manifest() -> dict[str, Any]:
    payload = json.loads(FORMAL_MANIFEST.read_text(encoding="utf-8"))
    allowed = payload.get("status") == "ready" or (
        payload.get("status") == "canary_ready" and os.environ.get(CANARY_ENV) == "1"
    )
    if not allowed:
        raise RuntimeError("Validated v02 benchmark is not ready for this execution mode.")
    expected = {
        "validated_task_config_sha256": sha256_file(ARTIFACT_DIR / "validated_tasks.json"),
        "task_patch_manifest_sha256": sha256_file(ARTIFACT_DIR / "task_patches.json"),
        "audit_report_sha256": sha256_file(ARTIFACT_DIR / "validation_report.json"),
    }
    if any(payload["lineage"].get(key) != value for key, value in expected.items()):
        raise RuntimeError("Validated v02 artifact lineage mismatch.")
    return payload


def validated_v02_metadata() -> dict[str, str]:
    lineage = _manifest()["lineage"]
    return {
        "benchmark_variant": "ST-WebAgentBench-Interactive-Validated",
        "validated_benchmark_name": VALIDATED_V02_BENCHMARK_NAME,
        "validated_benchmark_version": VERSION,
        "upstream_benchmark_commit": UPSTREAM_COMMIT,
        "validated_task_config_sha256": lineage["validated_task_config_sha256"],
        "task_patch_manifest_sha256": lineage["task_patch_manifest_sha256"],
        "semantic_audit_version": SEMANTIC_AUDIT_VERSION,
        "hallucination_normalization_version": NORMALIZATION_VERSION,
        "interactive_protocol_version": lineage["interactive_protocol_version"],
        "user_simulator_model": lineage["user_simulator_model"],
        "user_simulator_prompt_version": lineage["user_simulator_prompt_version"],
        "user_scenario_version": lineage["user_scenario_version"],
    }


def _load(path: Path, task_id: int) -> dict[str, Any]:
    matches = [task for task in json.loads(path.read_text(encoding="utf-8")) if task["task_id"] == task_id]
    if len(matches) != 1:
        raise RuntimeError(f"Validated task missing or duplicated: {task_id}")
    return copy.deepcopy(matches[0])


def _substitute_urls(task: dict[str, Any], urls: dict[str, str]) -> dict[str, Any]:
    serialized = json.dumps(task, ensure_ascii=False)
    for pattern, key in {
        "__IPA_HOME__": "ipa_home", "__SUITECRM__": "suitecrm", "__GITLAB__": "gitlab",
        "__REDDIT__": "reddit", "__SHOPPING__": "shopping", "__SHOPPING_ADMIN__": "shopping_admin",
        "__WIKIPEDIA__": "wikipedia", "__MAP__": "map",
    }.items():
        serialized = serialized.replace(pattern, urls[key])
    return json.loads(serialized)


class GenericValidatedV02WebArenaTask(GenericValidatedWebArenaTask):
    def __init__(self, seed: int, task_id: int | None = None, intent_template_id=None, **kwargs):
        super().__init__(seed=seed, task_id=task_id, intent_template_id=intent_template_id, **kwargs)
        if task_id not in RETAINED_TASK_IDS:
            raise ValueError(f"Task {task_id} is not retained by {VERSION}.")
        self.v01_config = _substitute_urls(
            _load(V01_DIR / "validated_tasks.json", task_id), self.webarena_instance.urls
        )
        self.task_configs = [
            _substitute_urls(
                _load(ARTIFACT_DIR / "validated_tasks.json", task_id), self.webarena_instance.urls
            )
        ]
        self.v01_config_file: str | None = None

    def setup(self, page: Any):
        goal, info = super().setup(page)
        self.safety_evaluator.evaluators = [
            FieldAwareInputHallucinationEvaluator(evaluator.params)
            if isinstance(evaluator, InputHallucinationEvaluator)
            else evaluator
            for evaluator in self.safety_evaluator.evaluators
        ]
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as handle:
            json.dump(self.v01_config, handle)
            handle.flush()
            self.v01_config_file = handle.name
        self.v01_safety_evaluator = safety_evaluator_router(self.v01_config_file)
        return goal, info

    def validate(self, page, chat_messages, trajectory):
        result = super().validate(page, chat_messages, trajectory)
        score, safety_score, reports, done, message, partial_info = result
        _, v01_reports = self.v01_safety_evaluator(
            trajectory=trajectory, config_file=self.v01_config_file, page=page, client=None
        )
        partial_info["evaluator_v01_v02_diff"] = {
            "v01_compliance": not any(report.get("violated") for report in v01_reports),
            "v02_compliance": not any(report.get("violated") for report in reports),
            "v01_violations": [report for report in v01_reports if report.get("violated")],
            "v02_violations": [report for report in reports if report.get("violated")],
        }
        return score, safety_score, reports, done, message, partial_info

    def teardown(self):
        super().teardown()
        if self.v01_config_file:
            try:
                os.remove(self.v01_config_file)
            except OSError:
                pass


class STWebAgentBenchInteractiveValidatedV02Env(STWebAgentBenchInteractiveValidatedEnv):
    def __init__(self, *args, **kwargs):
        kwargs["user_scenario_path"] = ARTIFACT_DIR / "validated_scenarios.json"
        super().__init__(*args, **kwargs)


def _entrypoint(*args, **kwargs):
    return STWebAgentBenchInteractiveValidatedV02Env(
        GenericValidatedV02WebArenaTask, *args, **kwargs
    )


def ensure_validated_v02_environments_registered() -> tuple[str, ...]:
    _manifest()
    ids = []
    for task_id in RETAINED_TASK_IDS:
        gym_id = f"browsergym/{VALIDATED_V02_ENV_PREFIX}.{task_id}"
        if gym_id not in registry:
            register(id=gym_id, order_enforce=False, disable_env_checker=True,
                     entry_point=_entrypoint, nondeterministic=True,
                     kwargs={"task_kwargs": {"task_id": task_id}})
        ids.append(gym_id)
    return tuple(ids)


def validate_v02_trajectory_lineage(trajectory: dict[str, Any]) -> None:
    expected = validated_v02_metadata()
    run = trajectory.get("run", {})
    mismatches = {key: {"expected": value, "actual": run.get(key)} for key, value in expected.items()
                  if run.get(key) != value}
    if trajectory.get("task", {}).get("task_id") not in RETAINED_TASK_IDS:
        mismatches["task_id"] = {"expected": "retained", "actual": trajectory.get("task", {}).get("task_id")}
    if mismatches:
        raise ValueError(f"Validated v02 trajectory lineage mismatch: {mismatches}")

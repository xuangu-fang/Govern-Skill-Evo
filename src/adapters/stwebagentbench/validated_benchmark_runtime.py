"""Runtime loader and Gym registration for the validated benchmark overlay."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from gymnasium import register, registry

from stwebagentbench.browser_env.interactive_env import InteractiveBrowserEnv
from browsergym.stwebagentbench.task import GenericWebArenaTask

from src.adapters.stwebagentbench.validated_suitecrm import (
    ARTIFACT_DIR,
    FORMAL_MANIFEST,
    REPO_ROOT,
    sha256_file,
)
from src.adapters.stwebagentbench.validated_suitecrm_spec import (
    RETAINED_TASK_IDS,
    SEMANTIC_AUDIT_VERSION,
    UPSTREAM_COMMIT,
    VERSION,
)


VALIDATED_ENV_PREFIX = "STWebAgentBenchInteractiveValidatedEnv"
VALIDATED_BENCHMARK_NAME = "ST-WebAgentBench-Interactive-Validated"
CANARY_RETRY_AUTHORIZATION_ENV = "STWEB_VALIDATED_CANARY_RETRY_AUTHORIZATION"
CANARY_RETRY_ATTEMPT = "attempt_02"
CANARY_RETRY_ONLY_ISSUE = (
    "Canary incomplete: repeated Agent API endpoint connection failures."
)


def _retry_authorized(payload: dict[str, Any]) -> bool:
    authorization_value = os.environ.get(CANARY_RETRY_AUTHORIZATION_ENV)
    if not authorization_value:
        return False
    authorization_path = Path(authorization_value).resolve()
    expected_path = (
        REPO_ROOT
        / "artifacts/stweb_suitecrm_interactive_validated_v01/canary"
        / CANARY_RETRY_ATTEMPT
        / "retry_authorization.json"
    ).resolve()
    if authorization_path != expected_path or not authorization_path.is_file():
        return False
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    report = json.loads(
        (ARTIFACT_DIR / "validation_report.json").read_text(encoding="utf-8")
    )
    return (
        payload.get("status") == "needs_review"
        and report.get("status") == "needs_review"
        and report.get("canary_issues") == [CANARY_RETRY_ONLY_ISSUE]
        and authorization.get("status") == "authorized"
        and authorization.get("attempt_id") == CANARY_RETRY_ATTEMPT
        and authorization.get("lineage", {}).get(
            "validated_task_config_sha256"
        )
        == sha256_file(ARTIFACT_DIR / "validated_tasks.json")
        and authorization.get("lineage", {}).get(
            "task_patch_manifest_sha256"
        )
        == sha256_file(ARTIFACT_DIR / "task_patches.json")
        and authorization.get("lineage", {}).get("semantic_audit_version")
        == SEMANTIC_AUDIT_VERSION
    )


def _manifest() -> dict[str, Any]:
    payload = json.loads(FORMAL_MANIFEST.read_text(encoding="utf-8"))
    if payload.get("status") != "ready" and not _retry_authorized(payload):
        raise RuntimeError("Validated benchmark manifest is not ready.")
    lineage = payload["lineage"]
    expected = {
        "validated_task_config_sha256": sha256_file(ARTIFACT_DIR / "validated_tasks.json"),
        "task_patch_manifest_sha256": sha256_file(ARTIFACT_DIR / "task_patches.json"),
        "audit_report_sha256": sha256_file(ARTIFACT_DIR / "validation_report.json"),
    }
    if any(lineage.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Validated benchmark artifact lineage mismatch.")
    return payload


def validated_metadata() -> dict[str, str]:
    lineage = _manifest()["lineage"]
    return {
        "benchmark_variant": VALIDATED_BENCHMARK_NAME,
        "validated_benchmark_version": VERSION,
        "upstream_benchmark_commit": UPSTREAM_COMMIT,
        "validated_task_config_sha256": lineage["validated_task_config_sha256"],
        "task_patch_manifest_sha256": lineage["task_patch_manifest_sha256"],
        "semantic_audit_version": SEMANTIC_AUDIT_VERSION,
        "interactive_protocol_version": lineage["interactive_protocol_version"],
        "user_simulator_model": lineage["user_simulator_model"],
        "user_simulator_prompt_version": lineage["user_simulator_prompt_version"],
        "user_scenario_version": lineage["user_scenario_version"],
    }


def _load_validated_task(task_id: int) -> dict[str, Any]:
    if task_id not in RETAINED_TASK_IDS:
        raise ValueError(f"Task {task_id} is not retained by {VERSION}.")
    tasks = json.loads((ARTIFACT_DIR / "validated_tasks.json").read_text(encoding="utf-8"))
    matches = [task for task in tasks if int(task["task_id"]) == task_id]
    if len(matches) != 1:
        raise RuntimeError(f"Validated task config is missing or duplicated: {task_id}")
    return matches[0]


class GenericValidatedWebArenaTask(GenericWebArenaTask):
    """Native task loader using repaired config plus an original shadow evaluator."""

    def __init__(
        self,
        seed: int,
        task_id: int | None = None,
        intent_template_id: int | None = None,
        **kwargs: Any,
    ) -> None:
        if task_id is None or intent_template_id is not None:
            raise ValueError("Validated environments require one retained task_id.")
        super().__init__(seed=seed, task_id=task_id, **kwargs)
        self.original_config = copy.deepcopy(self.task_configs[0])
        config = copy.deepcopy(_load_validated_task(task_id))
        serialized = json.dumps(config, ensure_ascii=False)
        for pattern, url_key in {
            "__IPA_HOME__": "ipa_home",
            "__SUITECRM__": "suitecrm",
            "__GITLAB__": "gitlab",
            "__REDDIT__": "reddit",
            "__SHOPPING__": "shopping",
            "__SHOPPING_ADMIN__": "shopping_admin",
            "__WIKIPEDIA__": "wikipedia",
            "__MAP__": "map",
        }.items():
            serialized = serialized.replace(pattern, self.webarena_instance.urls[url_key])
        self.task_configs = [json.loads(serialized)]
        self.original_config_file: str | None = None

    def setup(self, page: Any) -> tuple[str, dict]:
        goal, info = super().setup(page)
        from stwebagentbench.evaluation_harness.evaluators import (
            evaluator_router,
            safety_evaluator_router,
        )

        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as handle:
            json.dump(self.original_config, handle)
            handle.flush()
            self.original_config_file = handle.name
        self.original_evaluator = evaluator_router(self.original_config_file)
        self.original_safety_evaluator = safety_evaluator_router(
            self.original_config_file
        )
        return goal, info

    def validate(
        self, page: Any, chat_messages: list[str], trajectory: list[Any]
    ) -> tuple[float, float, list, bool, str, dict]:
        result = super().validate(page, chat_messages, trajectory)
        score, safety_score, reports, done, message, partial_info = result
        original_task_success = self.original_evaluator(
            trajectory=trajectory,
            config_file=self.original_config_file,
            page=page,
            client=None,
        )
        original_safety_score, original_reports = self.original_safety_evaluator(
            trajectory=trajectory,
            config_file=self.original_config_file,
            page=page,
            client=None,
        )
        partial_info = {
            **partial_info,
            "evaluator_shadow_diff": {
                "original_task_success": float(original_task_success),
                "validated_task_success": float(score),
                "original_compliance": not any(
                    report.get("violated") is True for report in original_reports
                ),
                "validated_compliance": not any(
                    report.get("violated") is True for report in reports
                ),
                "original_violations": [
                    report for report in original_reports if report.get("violated") is True
                ],
                "validated_violations": [
                    report for report in reports if report.get("violated") is True
                ],
            },
        }
        return score, safety_score, reports, done, message, partial_info

    def teardown(self) -> None:
        super().teardown()
        if self.original_config_file:
            try:
                os.remove(self.original_config_file)
            except OSError:
                pass


class STWebAgentBenchInteractiveValidatedEnv(InteractiveBrowserEnv):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault(
            "user_scenario_path",
            ARTIFACT_DIR / "validated_scenarios.json",
        )
        super().__init__(*args, **kwargs)


def _entrypoint(*args: Any, **kwargs: Any) -> STWebAgentBenchInteractiveValidatedEnv:
    return STWebAgentBenchInteractiveValidatedEnv(
        GenericValidatedWebArenaTask, *args, **kwargs
    )


def ensure_validated_environments_registered() -> tuple[str, ...]:
    _manifest()
    ids = []
    for task_id in RETAINED_TASK_IDS:
        gym_id = f"browsergym/{VALIDATED_ENV_PREFIX}.{task_id}"
        if gym_id not in registry:
            register(
                id=gym_id,
                order_enforce=False,
                disable_env_checker=True,
                entry_point=_entrypoint,
                nondeterministic=True,
                kwargs={"task_kwargs": {"task_id": task_id}},
            )
        ids.append(gym_id)
    return tuple(ids)


def validate_validated_trajectory_lineage(trajectory: dict[str, Any]) -> None:
    expected = validated_metadata()
    run = trajectory.get("run", {})
    mismatches = {
        key: {"expected": value, "actual": run.get(key)}
        for key, value in expected.items()
        if run.get(key) != value
    }
    task_id = trajectory.get("task", {}).get("task_id")
    if task_id not in RETAINED_TASK_IDS:
        mismatches["task_id"] = {"expected": "retained task", "actual": task_id}
    if mismatches:
        raise ValueError(f"Validated trajectory lineage mismatch: {mismatches}")

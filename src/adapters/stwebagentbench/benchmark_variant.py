"""Select the original or interactive ST-WebAgentBench environment."""

from __future__ import annotations

import os


ORIGINAL_VARIANT = "original"
INTERACTIVE_VARIANT = "interactive"
INTERACTIVE_VALIDATED_VARIANT = "interactive_validated"
INTERACTIVE_VALIDATED_V02_VARIANT = "interactive_validated_v02"
VARIANT_ENV = "STWEB_BENCHMARK_VARIANT"
USER_SIMULATOR_MODEL = "openai/gpt-5.6-luna"
INTERACTIVE_PROTOCOL_VERSION = "stweb-interactive-v2"
USER_SIMULATOR_PROMPT_VERSION = "stweb-interactive-user-v6"
USER_SCENARIO_VERSION = "suitecrm-v03-all-v4"


def benchmark_variant() -> str:
    value = os.environ.get(VARIANT_ENV, ORIGINAL_VARIANT).strip().lower()
    if value not in {
        ORIGINAL_VARIANT,
        INTERACTIVE_VARIANT,
        INTERACTIVE_VALIDATED_VARIANT,
        INTERACTIVE_VALIDATED_V02_VARIANT,
    }:
        raise ValueError(
            f"{VARIANT_ENV} must be 'original', 'interactive', or "
            f"'interactive_validated', or 'interactive_validated_v02', got {value!r}"
        )
    return value


def benchmark_environment_id(task_id: int) -> str:
    if benchmark_variant() == INTERACTIVE_VALIDATED_V02_VARIANT:
        from src.adapters.stwebagentbench.validated_benchmark_v02_runtime import (
            VALIDATED_V02_ENV_PREFIX,
            ensure_validated_v02_environments_registered,
        )
        registered = ensure_validated_v02_environments_registered()
        environment_id = f"browsergym/{VALIDATED_V02_ENV_PREFIX}.{task_id}"
        if environment_id not in registered:
            raise ValueError(f"Task {task_id} is not retained by validated v02.")
        return environment_id
    if benchmark_variant() == INTERACTIVE_VALIDATED_VARIANT:
        from src.adapters.stwebagentbench.validated_benchmark_runtime import (
            VALIDATED_ENV_PREFIX,
            ensure_validated_environments_registered,
        )

        registered = ensure_validated_environments_registered()
        environment_id = f"browsergym/{VALIDATED_ENV_PREFIX}.{task_id}"
        if environment_id not in registered:
            raise ValueError(f"Task {task_id} is not retained by the validated variant.")
        return environment_id
    prefix = (
        "STWebAgentBenchInteractiveEnv"
        if benchmark_variant() == INTERACTIVE_VARIANT
        else "STWebAgentBenchEnv"
    )
    return f"browsergym/{prefix}.{task_id}"


def benchmark_artifact_group(formal: bool) -> str:
    base = "raw" if formal else "smoke"
    if benchmark_variant() == INTERACTIVE_VARIANT:
        return f"{base}_interactive_v2"
    if benchmark_variant() == INTERACTIVE_VALIDATED_VARIANT:
        return f"{base}_interactive_validated_v01"
    if benchmark_variant() == INTERACTIVE_VALIDATED_V02_VARIANT:
        return f"{base}_interactive_validated_v02"
    return base


def benchmark_variant_metadata() -> dict[str, str]:
    if benchmark_variant() == INTERACTIVE_VALIDATED_V02_VARIANT:
        from src.adapters.stwebagentbench.validated_benchmark_v02_runtime import (
            validated_v02_metadata,
        )
        return validated_v02_metadata()
    if benchmark_variant() == INTERACTIVE_VALIDATED_VARIANT:
        from src.adapters.stwebagentbench.validated_benchmark_runtime import (
            validated_metadata,
        )

        return validated_metadata()
    if benchmark_variant() != INTERACTIVE_VARIANT:
        return {}
    return {
        "benchmark_variant": "ST-WebAgentBench-Interactive",
        "interactive_protocol_version": INTERACTIVE_PROTOCOL_VERSION,
        "user_simulator_model": USER_SIMULATOR_MODEL,
        "user_simulator_prompt_version": USER_SIMULATOR_PROMPT_VERSION,
        "user_scenario_version": USER_SCENARIO_VERSION,
    }

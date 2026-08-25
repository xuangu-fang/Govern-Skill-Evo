"""Select the original or interactive ST-WebAgentBench environment."""

from __future__ import annotations

import os


ORIGINAL_VARIANT = "original"
INTERACTIVE_VARIANT = "interactive"
VARIANT_ENV = "STWEB_BENCHMARK_VARIANT"
USER_SIMULATOR_MODEL = "openai/gpt-5.6-luna"
INTERACTIVE_PROTOCOL_VERSION = "stweb-interactive-v2"
USER_SIMULATOR_PROMPT_VERSION = "stweb-interactive-user-v6"
USER_SCENARIO_VERSION = "suitecrm-v03-all-v4"


def benchmark_variant() -> str:
    value = os.environ.get(VARIANT_ENV, ORIGINAL_VARIANT).strip().lower()
    if value not in {ORIGINAL_VARIANT, INTERACTIVE_VARIANT}:
        raise ValueError(
            f"{VARIANT_ENV} must be 'original' or 'interactive', got {value!r}"
        )
    return value


def benchmark_environment_id(task_id: int) -> str:
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
    return base


def benchmark_variant_metadata() -> dict[str, str]:
    if benchmark_variant() != INTERACTIVE_VARIANT:
        return {}
    return {
        "benchmark_variant": "ST-WebAgentBench-Interactive",
        "interactive_protocol_version": INTERACTIVE_PROTOCOL_VERSION,
        "user_simulator_model": USER_SIMULATOR_MODEL,
        "user_simulator_prompt_version": USER_SIMULATOR_PROMPT_VERSION,
        "user_scenario_version": USER_SCENARIO_VERSION,
    }

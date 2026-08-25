"""Frozen specification for ST-WebAgentBench SuiteCRM validated v02."""

from src.adapters.stwebagentbench.validated_suitecrm_spec import (  # noqa: F401
    DROP_TASK_IDS,
    RETAINED_TASK_IDS,
    SELECTION_TASK_IDS,
    TEST_TASK_IDS,
    TRAIN_BATCHES,
    TRAIN_TASK_IDS,
    UPSTREAM_COMMIT,
)


VERSION = "stweb-suitecrm-interactive-validated-v02"
BUILDER_VERSION = "stweb-suitecrm-validated-builder-v02"
SEMANTIC_AUDIT_VERSION = "stweb-suitecrm-semantic-audit-v02"

HOLDOUT_CANARY_TASKS = {
    49: "polarity-repaired account create; text and dropdown",
    60: "only_fill-repaired task create; date/time and UserScenario",
    61: "relatively untouched create-flow control",
    64: "polarity plus only_fill repaired lead update",
    75: "task-authorized ordinary phone text update",
    258: "difficulty export control",
    260: "held-out meeting date/time/duration and policy dropdown",
    262: "held-out recurrence plus UserScenario interaction",
    263: "held-out case create plus UserScenario parameters",
    270: "import mapping, file parameter, and dropdown",
}
HOLDOUT_ROLLOUTS_PER_TASK = 3

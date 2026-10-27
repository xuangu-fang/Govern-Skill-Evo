"""Explicit V23.5 method baseline; unsupported views never fall back silently."""
from copy import deepcopy
from src.skill_evolution.v23 import gate, memory
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23_3.memory_view import FORMAT as MEMORY_V3
from src.skill_evolution.shared.unnumbered_patch import CONTRACT_VERSION as PATCH_CONTRACT
from . import diagnosis, preconditioner, editor, replay
from .update_patch import CONTRACT_VERSION

from .memory_view import KNOWLEDGE_ONLY
from .output_feedback import POLICY, LEGACY
from .knowledge_review import POLICY as KNOWLEDGE_REVIEW


def method_config(memory_view=KNOWLEDGE_ONLY, *, retry_policy=POLICY, knowledge_review=False):
    require(memory_view in (MEMORY_V3, KNOWLEDGE_ONLY), "Unsupported V23.5 Memory view")
    require(retry_policy in (POLICY, LEGACY), "Unsupported output retry policy")
    knowledge_only = memory_view == KNOWLEDGE_ONLY
    result = {
        "version": "v23_5_campaign_v1",
        "grouping": "v23",
        "editor": editor.PROMPT_VERSION,
        "patch_contract": PATCH_CONTRACT,
        "gate": gate.RULE,
        "diagnosis_version": diagnosis.PROMPT_VERSION,
        "preconditioner_contract": CONTRACT_VERSION,
        "preconditioner_prompt": preconditioner.prompt_for(memory_view)[0],
        "memory_contract": memory.MULTI_KNOWLEDGE_CONTRACT,
        "memory_view": memory_view,
        "replay_input_view": replay.KNOWLEDGE_INPUT_VIEW if knowledge_only else replay.INPUT_VIEW,
        "replay_prompt_version": replay.KNOWLEDGE_PROMPT_VERSION if knowledge_only else replay.LEARNING_PROMPT_VERSION,
        "replay_boundary": replay.ADAPTER_VERSION,
        "memory_publication": "validated_replay_after_accept_or_retain_next_round",
        "semantic_resampling": False,
    }
    if retry_policy == POLICY:
        result['retry_policy'] = POLICY
    if knowledge_review:
        require(memory_view == KNOWLEDGE_ONLY, 'Knowledge review requires Knowledge Only')
        result['knowledge_review'] = KNOWLEDGE_REVIEW
        result['memory_publication'] = 'fact_screen_and_optional_repair_before_memory_commit'
    return result


def validate_method(value):
    require(isinstance(value, dict), "Missing V23.5 method freeze")
    require(value.get('knowledge_review') in (None, KNOWLEDGE_REVIEW), 'Unsupported Knowledge review policy')
    expected = method_config(value.get("memory_view"), retry_policy=value.get('retry_policy', LEGACY),
                             knowledge_review=value.get('knowledge_review') is not None)
    require(value == expected, "Unsupported or missing V23.5 method freeze")


def baseline_config(base, *, memory_view=KNOWLEDGE_ONLY, retry_policy=POLICY):
    """Prepare a NEW campaign configuration, retaining tasks and runtime parameters.

    This never modifies a saved campaign or relaxes its freeze. The caller supplies
    the new output directory to evolution.initialize/run_campaign.
    """
    result = deepcopy(base)
    result['method'] = method_config(memory_view, retry_policy=retry_policy)
    from .evolution import validate_config
    validate_config(result)
    return result

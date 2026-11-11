"""V24 verified baseline. Contract IDs retain their original semantic versions."""
from copy import deepcopy
from .facts import require
from . import diagnosis, preconditioner, editor, replay
from .contracts import memory, gate
from .memory_view import KNOWLEDGE_ONLY
from .output_feedback import POLICY
from .knowledge_review import POLICY as KNOWLEDGE_REVIEW
from .update_patch import CONTRACT_VERSION
from src.skill_evolution.v24.unnumbered_patch import CONTRACT_VERSION as PATCH_CONTRACT


REVIEW_DISABLED = 'disabled_v1'


def method_config(knowledge_review=KNOWLEDGE_REVIEW):
    require(knowledge_review in (KNOWLEDGE_REVIEW, REVIEW_DISABLED), 'Unsupported knowledge review policy')
    return {
        'version': 'v24_campaign_v1',
        'grouping': 'v23',
        'editor': editor.PROMPT_VERSION,
        'patch_contract': PATCH_CONTRACT,
        'gate': gate.RULE,
        'diagnosis_version': diagnosis.PROMPT_VERSION,
        'preconditioner_contract': CONTRACT_VERSION,
        'preconditioner_prompt': preconditioner.KNOWLEDGE_PROMPT_VERSION,
        'memory_contract': memory.MULTI_KNOWLEDGE_CONTRACT,
        'memory_view': KNOWLEDGE_ONLY,
        'replay_input_view': replay.KNOWLEDGE_INPUT_VIEW,
        'replay_prompt_version': replay.KNOWLEDGE_PROMPT_VERSION,
        'replay_boundary': replay.ADAPTER_VERSION,
        'memory_publication': ('replay_validated_before_commit' if knowledge_review == REVIEW_DISABLED
                               else 'fact_screen_and_optional_repair_before_memory_commit'),
        'semantic_resampling': False,
        'retry_policy': POLICY,
        'knowledge_review': knowledge_review,
    }


def validate_method(value):
    require(isinstance(value, dict), 'Unsupported or missing V24 method freeze')
    require(value == method_config(value.get('knowledge_review')), 'Unsupported or missing V24 method freeze')


def review_enabled(config):
    return config['method']['knowledge_review'] == KNOWLEDGE_REVIEW


def baseline_config(base, *, benchmark):
    """Compile a new effective config; no existing campaign is modified."""
    result = deepcopy(base)
    result['method'] = method_config()
    result['benchmark'] = deepcopy(benchmark.identity)
    if result.get('initial_skill'):
        result['initial_skill'] = {k: result['initial_skill'][k] for k in ('source', 'text')}
    from .benchmark import using_benchmark
    from .evolution import validate_config
    with using_benchmark(benchmark):
        validate_config(result)
    return result

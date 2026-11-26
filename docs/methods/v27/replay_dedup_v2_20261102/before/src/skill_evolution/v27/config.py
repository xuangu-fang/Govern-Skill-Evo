"""V27 configuration with inherited input guards; construction never starts a run."""
import math
from .benchmark import current
from .facts import require
from .contracts import memory, gate
from .update_patch import CONTRACT_VERSION
from .unnumbered_patch import CONTRACT_VERSION as PATCH_CONTRACT
from .memory_view import KNOWLEDGE_ONLY
from .output_feedback import POLICY
from .modules import REVIEW_POLICY
from .transport import validate_call
from .benchmarks.lmb import prompting, protocol as p
from .benchmarks.lmb.protocol import MODEL_INPUT_VIEW
from .training import MERGED_POOL


REVIEW_DISABLED = 'disabled_v1'


def method_config(knowledge_review=REVIEW_DISABLED):
    require(knowledge_review == REVIEW_DISABLED, 'Unsupported knowledge review policy')
    return {'version': 'v27_campaign_v1', 'prompts': dict(prompting.PROMPT_VERSIONS),
            'preconditioner_contract': CONTRACT_VERSION, 'patch_contract': PATCH_CONTRACT,
            'memory_contract': memory.MULTI_KNOWLEDGE_CONTRACT, 'memory_view': KNOWLEDGE_ONLY,
            'replay_input_view': p.INPUT_VIEW, 'model_input_view': MODEL_INPUT_VIEW, 'gate_rule': gate.RULE,
            'retry_policy': POLICY, 'knowledge_review': knowledge_review,
            'semantic_resampling': False, 'memory_publication': (
                'replay_validated_before_commit' if knowledge_review == REVIEW_DISABLED else 'review_before_commit')}


def validate_config(config):
    required = {'method', 'benchmark', 'actor', 'gate_metric', 'optimization_splits', 'batches',
                'initial_skill', 'max_attempts', 'continue_no_change', 'max_input_chars',
                'max_message_utf8_bytes', 'module_calls'}
    require(isinstance(config, dict) and required <= set(config) <= required | {'epoch_schedule', 'retry_delay_seconds', 'optimization_pool', 'actor_task_output_limits'},
            'Missing or unknown Campaign configuration fields')
    require(config['method'] == method_config(config['method'].get('knowledge_review')), 'Unsupported V27 method freeze')
    adapter = current(); adapter._bound()
    pool = config.get('optimization_pool')
    require(pool in (None, MERGED_POOL) and pool == getattr(adapter.dataset, 'optimization_pool', None),
            'Configured optimization pool differs from the bound dataset view')
    require(config['benchmark'] == adapter.identity, 'Benchmark identity differs')
    require(config['actor'] == adapter.transport.metadata(), 'Actor configuration differs')
    limits = config.get('actor_task_output_limits', {})
    require(isinstance(limits, dict) and all(isinstance(t, str) and type(n) is int and n > 0
            for t, n in limits.items()), 'Invalid task output limits')
    require(limits == getattr(adapter, 'task_output_limits', {}), 'Task output limits differ from bound Actor')
    require(config['gate_metric'] == adapter.gate_metric == p.EM_GATE, 'Explicit matching Gate metric required')
    splits = config['optimization_splits']
    require(isinstance(splits, list) and splits and len(splits) == len(set(splits))
            and set(splits) <= {'train', 'validation'}, 'Declare optimization splits; Test is forbidden')
    batches = config['batches']
    require(isinstance(batches, list) and batches and all(isinstance(b, list) and b for b in batches), 'Missing batches')
    ids = []
    for batch in batches:
        require(all(isinstance(t, str) and t in adapter.dataset.rows for t in batch), 'Unknown task ID')
        require(len(batch) == len(set(batch)), 'Duplicate task within batch')
        actual = {adapter.dataset.case(t).metadata['split'] for t in batch}
        require(len(actual) == 1 and actual <= set(splits), 'Batch must use one declared optimization split')
        ids.extend(batch)
    require(set(limits) <= set(ids), 'Task output limit outside optimization batches')
    if pool == MERGED_POOL:
        require(splits == ['train'] and set(ids) == set(adapter.dataset.splits['train']),
                'Merged optimization must cover all 53 tasks as train; no separate validation pool')
    require(config.get('epoch_schedule') is None, 'LMB uses one pass, no epoch overrides')
    require(len(ids) == len(set(ids)), 'Repeated optimization tasks')
    require(config['continue_no_change'] is True, 'LMB continues all frozen batches')
    if pool == MERGED_POOL:
        require(batches == adapter.dataset.batches(), 'LMB requires fixed ordered 10/10/10/10/10/3 batches')
    initial = config['initial_skill']
    if initial is not None:
        p.fields(initial, ('source', 'text'), 'Initial Skill')
        require(isinstance(initial['text'], str) and bool(initial['text'].strip()), 'Initial Skill must be nonempty')
        require(initial['source'] is None or isinstance(initial['source'], str), 'Invalid Skill provenance')
    if pool == MERGED_POOL:
        from .training import RESOURCES
        require(initial is not None and initial['text'] == (RESOURCES/'initial.md').read_text(), 'Use native initial Skill')
    delay = config.get('retry_delay_seconds', 0)
    require(type(delay) in (int, float) and math.isfinite(delay) and delay >= 0, 'Invalid retry delay')
    require(type(config['max_attempts']) is int and 1 <= config['max_attempts'] <= 6, 'Method total attempts must be 1..6')
    require(type(config['continue_no_change']) is bool, 'Explicit no-change policy required')
    for key in ('max_input_chars', 'max_message_utf8_bytes'):
        require(type(config[key]) is int and config[key] > 0, 'Explicit input capacity required')
    require(isinstance(config['module_calls'], dict) and set(config['module_calls']) == set(prompting.PROMPT_VERSIONS),
            'Declare call configuration for all five modules')
    for name, value in config['module_calls'].items():
        prompting.render(name, p.background(config['actor']))  # Reject protocol drift before any Actor call.
        validate_call(value)
        expected = 16384 if name in ('grouping','editor') else 32768
        require(value['max_tokens'] == expected, 'Wrong method output budget')
        require(value['model'] == p.ACTOR['model'] and value['endpoint'] == p.ACTOR['endpoint']
                and value['temperature'] == 1.0 and value.get('reasoning_effort') == 'medium'
                and value.get('thinking') == {'type':'enabled'}, 'Method model configuration differs')
    return config


def campaign_config(adapter, *, max_input_chars=4000000, max_message_utf8_bytes=6000000,
                    context_window_tokens=None):
    """Build an explicit configuration without initializing a campaign or credentials."""
    from .training import RESOURCES
    calls={name:{'endpoint':p.ACTOR['endpoint'],'model':p.ACTOR['model'],
                 'max_tokens':16384 if name in ('grouping','editor') else 32768,
                 'timeout_seconds':300,'temperature':1.0,'reasoning_effort':'medium','thinking':{'type':'enabled'}}
           for name in prompting.PROMPT_VERSIONS}
    if context_window_tokens is not None:
        for value in calls.values():value['context_window_tokens']=context_window_tokens
    return {'method':method_config(),'benchmark':adapter.identity,'actor':adapter.transport.metadata(),
            'gate_metric':p.EM_GATE,'optimization_splits':['train'],'optimization_pool':MERGED_POOL,
            'batches':adapter.dataset.batches(),'initial_skill':{'source':str(RESOURCES/'initial.md'),'text':(RESOURCES/'initial.md').read_text()},
            'max_attempts':6,'continue_no_change':True,'retry_delay_seconds':2.0,
            'max_input_chars':max_input_chars,'max_message_utf8_bytes':max_message_utf8_bytes,'module_calls':calls}

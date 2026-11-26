"""Explicit V26 Campaign configuration; no experiment defaults are selected."""
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
from .benchmarks.officeqa import prompting, protocol as p
from .benchmarks.officeqa.input_view import FORMAT as MODEL_INPUT_VIEW
from .training import MERGED_POOL


REVIEW_DISABLED = 'disabled_v1'


def method_config(knowledge_review=REVIEW_POLICY):
    require(knowledge_review in (REVIEW_POLICY, REVIEW_DISABLED), 'Unsupported knowledge review policy')
    return {'version': 'v26_campaign_v1', 'prompts': dict(prompting.PROMPT_VERSIONS),
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
    require(config['method'] == method_config(config['method'].get('knowledge_review')), 'Unsupported V26 method freeze')
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
                'Merged optimization must cover all 74 tasks as train; no separate validation pool')
    schedule = config.get('epoch_schedule')
    if schedule is None:
        require(len(ids) == len(set(ids)), 'Repeated tasks require an explicit epoch schedule')
    else:
        p.fields(schedule, ('epochs', 'round_epochs', 'batch_size'), 'Epoch schedule')
        epochs, rounds, size = schedule['epochs'], schedule['round_epochs'], schedule['batch_size']
        require(type(epochs) is int and epochs > 0 and type(size) is int and size > 0, 'Invalid epoch budget')
        require(isinstance(rounds, list) and len(rounds) == len(batches) and all(type(e) is int for e in rounds)
                and rounds == sorted(rounds) and set(rounds) == set(range(1, epochs+1)), 'Invalid round epoch mapping')
        require(all(len(b) <= size for b in batches), 'Epoch batch exceeds budget')
        for epoch in range(1, epochs+1):
            tasks = [t for e, batch in zip(rounds, batches) if e == epoch for t in batch]
            require(len(tasks) == len(set(tasks)) and set(tasks) == set(ids), 'Each epoch must cover the same task pool once')
    initial = config['initial_skill']
    if initial is not None:
        p.fields(initial, ('source', 'text'), 'Initial Skill')
        require(isinstance(initial['text'], str) and bool(initial['text'].strip()), 'Initial Skill must be nonempty')
        require(initial['source'] is None or isinstance(initial['source'], str), 'Invalid Skill provenance')
    delay = config.get('retry_delay_seconds', 0)
    require(type(delay) in (int, float) and math.isfinite(delay) and delay >= 0, 'Invalid retry delay')
    require(type(config['max_attempts']) is int and 1 <= config['max_attempts'] <= 6, 'Method total attempts must be 1..6')
    require(type(config['continue_no_change']) is bool, 'Explicit no-change policy required')
    for key in ('max_input_chars', 'max_message_utf8_bytes'):
        require(type(config[key]) is int and config[key] > 0, 'Explicit input capacity required')
    require(isinstance(config['module_calls'], dict) and set(config['module_calls']) == set(prompting.PROMPT_VERSIONS),
            'Declare call configuration for all seven modules')
    for value in config['module_calls'].values(): validate_call(value)
    return config

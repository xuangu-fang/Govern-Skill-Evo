"""Frozen single-pass SearchQA configuration; building it never starts execution."""
from copy import deepcopy
import math

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts import memory, gate
from src.skill_evolution.v27.update_patch import CONTRACT_VERSION
from src.skill_evolution.v27.unnumbered_patch import CONTRACT_VERSION as PATCH_CONTRACT
from src.skill_evolution.v27.memory_view import KNOWLEDGE_ONLY
from src.skill_evolution.v27.transport import validate_call
from .output_feedback import POLICY
from . import profiles
from .benchmarks.searchqa import protocol as p, prompting, replay_input_view
from .benchmarks.searchqa.dataset import SearchQADataset

REVIEW_DISABLED = 'disabled_v1'
MERGED_POOL = 'v28_searchqa_train600_v1'


def module_budget(name, batch_size):
    if batch_size == 30:
        return {'grouping': 32768, 'diagnosis': 65536, 'preconditioner': 65536,
                'editor': 16384, 'replay': 65536}[name]
    return 16384 if name in ('grouping', 'editor') else 32768


def method_config(profile=profiles.V28):
    return {'version': profiles.check(profile), 'prompts': profiles.prompt_versions(profile),
            'preconditioner_contract': CONTRACT_VERSION, 'patch_contract': PATCH_CONTRACT,
            'memory_contract': memory.MULTI_KNOWLEDGE_CONTRACT, 'memory_view': KNOWLEDGE_ONLY,
            'replay_input_view': replay_input_view.INPUT_VIEW, 'model_input_view': p.MODEL_INPUT_VIEW,
            'gate_rule': gate.RULE, 'retry_policy': POLICY, 'knowledge_review': REVIEW_DISABLED,
            'semantic_resampling': False, 'memory_publication': 'replay_validated_before_commit'}


def validate_config(config):
    p.fields(config, ('method', 'benchmark', 'actor', 'gate_metric', 'optimization_splits', 'optimization_pool',
                     'batches', 'initial_skill', 'max_attempts', 'continue_no_change', 'max_input_chars',
                     'max_message_utf8_bytes', 'module_calls', 'retry_delay_seconds'), 'Campaign configuration')
    adapter = current(); adapter._bound()
    p.require(p.equal(config['method'], method_config(adapter.profile)), 'Unsupported SearchQA method profile')
    p.require(config['benchmark'] == adapter.identity and config['gate_metric'] == p.GATE_PROFILE,
              'Benchmark/Gate identity differs')
    p.require(p.equal(config['actor'], adapter.actor_adapter._actor), 'Actor configuration differs')
    p.require(config['optimization_splits'] == ['train'], 'Only merged training pool may optimize')
    dataset = adapter.dataset
    batch_size = getattr(dataset, 'batch_size', 15)
    if adapter.profile == profiles.V28_1:
        p.require(batch_size == 30 and not adapter.actor_adapter.verify_hashes,
                  'v28.1 requires batch30 and plain archives')
    p.require(config['optimization_pool'] == getattr(dataset, 'optimization_pool', None), 'Optimization pool differs')
    batches = config['batches']
    p.require(isinstance(batches, list) and batches and all(isinstance(b, list) and b for b in batches), 'Missing batches')
    ids = [t for batch in batches for t in batch]
    p.require(all(isinstance(t, str) and t in dataset.rows for t in ids) and len(ids) == len(set(ids)),
              'Unknown or repeated optimization tasks')
    p.require(all(dataset.case(t).metadata['split'] == 'train' for t in ids), 'Test is isolated from optimization')
    p.require(batches == dataset.batches and ids == dataset.splits['train'], 'Frozen full-pass schedule differs')
    if isinstance(dataset, SearchQADataset):
        p.require(config['optimization_pool'] == MERGED_POOL and len(batches) == 600 // batch_size and
                  all(len(b) == batch_size for b in batches), 'SearchQA full-pass batch profile differs')
    p.require(config['continue_no_change'] is True, 'Continue all frozen batches after no-change')
    p.require(type(config['max_attempts']) is int and config['max_attempts'] == 6, 'Method attempts must total six')
    p.require(type(config['retry_delay_seconds']) in (int, float) and
              math.isfinite(config['retry_delay_seconds']) and config['retry_delay_seconds'] == 2.0,
              'Method retry delay must be 2 seconds times attempt number')
    initial = config['initial_skill']
    p.fields(initial, ('source', 'text'), 'Initial Skill')
    p.nonempty_text(initial['text'], 'Explicit initial Skill')
    p.require(initial['source'] is None or isinstance(initial['source'], str), 'Invalid initial Skill provenance')
    for key in ('max_input_chars', 'max_message_utf8_bytes'):
        p.require(type(config[key]) is int and config[key] > 0, 'Explicit input capacity required')
    p.fields(config['module_calls'], prompting.PROMPT_VERSIONS, 'Module calls')
    for name, value in config['module_calls'].items():
        prompting.render(name, p.background(config['actor']))
        validate_call(value)
        expected = module_budget(name, batch_size)
        p.require(value['max_tokens'] == expected and value['model'] == p.ACTOR['model'] and
                  value['endpoint'] == p.ACTOR['endpoint'] and value['temperature'] == 1.0 and
                  value.get('reasoning_effort') == 'medium' and value.get('thinking') == {'type': 'enabled'} and
                  value['timeout_seconds'] == (600 if batch_size == 30 else 300) and value.get('token_limit_field', 'max_tokens') == 'max_tokens',
                  'Method model configuration differs')
    return config


def campaign_config(adapter, *, initial_skill, max_input_chars=4000000,
                    max_message_utf8_bytes=6000000, context_window_tokens=None):
    """Require an explicit Skill choice; token capacity is never inferred."""
    batch_size = getattr(adapter.dataset, 'batch_size', 15)
    calls = {name: {'endpoint': p.ACTOR['endpoint'], 'model': p.ACTOR['model'],
                   'max_tokens': module_budget(name, batch_size),
                   'timeout_seconds': 600 if batch_size == 30 else 300, 'temperature': 1.0, 'reasoning_effort': 'medium',
                   'thinking': {'type': 'enabled'}} for name in prompting.PROMPT_VERSIONS}
    if context_window_tokens is not None:
        for value in calls.values():
            value['context_window_tokens'] = context_window_tokens
    return {'method': method_config(adapter.profile), 'benchmark': adapter.identity, 'actor': deepcopy(adapter.actor_adapter._actor),
            'gate_metric': p.GATE_PROFILE, 'optimization_splits': ['train'],
            'optimization_pool': getattr(adapter.dataset, 'optimization_pool', None),
            'batches': deepcopy(adapter.dataset.batches), 'initial_skill': deepcopy(initial_skill),
            'max_attempts': 6, 'continue_no_change': True, 'retry_delay_seconds': 2.0,
            'max_input_chars': max_input_chars, 'max_message_utf8_bytes': max_message_utf8_bytes,
            'module_calls': calls}

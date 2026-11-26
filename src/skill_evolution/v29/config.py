"""DocVQA single-pass schedule; method output budgets remain explicitly unset."""
from copy import deepcopy
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v27.update_patch import CONTRACT_VERSION
from src.skill_evolution.v27.unnumbered_patch import CONTRACT_VERSION as PATCH_CONTRACT
from src.skill_evolution.v27.transport import validate_call
from .benchmarks.docvqa import protocol as p, prompting, replay_input_view
from .benchmarks.docvqa.dataset import DocVQADataset
from .output_feedback import POLICY

REVIEW_DISABLED = 'disabled_v1'


def method_config(adapter=None):
    return {'version': getattr(adapter, 'method_version', 'v29_campaign_v1'),
            'prompts': dict(getattr(adapter, 'prompt_versions', prompting.PROMPT_VERSIONS)),
            'preconditioner_contract': CONTRACT_VERSION, 'patch_contract': PATCH_CONTRACT,
            'memory_contract': memory.MULTI_KNOWLEDGE_CONTRACT, 'memory_view': 'memory_knowledge_only_v1',
            'replay_input_view': replay_input_view.INPUT_VIEW, 'model_input_view': p.MODEL_INPUT_VIEW,
            'retry_policy': POLICY, 'knowledge_review': REVIEW_DISABLED,
            'semantic_resampling': False, 'memory_publication': 'replay_validated_before_commit'}


def pending_calls():
    return {name: {'endpoint': p.ACTOR['endpoint'], 'model': p.ACTOR['model'],
                   'max_tokens': None, 'timeout_seconds': None, 'temperature': 1.0,
                   'reasoning_effort': 'medium', 'thinking': {'type': 'enabled'}}
            for name in prompting.PROMPT_VERSIONS}


def campaign_config(adapter, *, module_calls=None):
    return {'method': method_config(adapter), 'actor': p.actor_config(), 'revision': p.REVISION,
            'gate_metric': p.GATE_PROFILE, 'optimization_pool': adapter.dataset.optimization_pool,
            'batches': deepcopy(adapter.dataset.batches), 'initial_skill': p.initial_skill(),
            'max_attempts': 6, 'continue_no_change': True, 'retry_delay_seconds': 2.0,
            'max_input_chars': 4000000, 'max_message_utf8_bytes': 6000000,
            'module_calls': deepcopy(pending_calls() if module_calls is None else module_calls)}


def validate_config(config, *, executable=False):
    p.fields(config, ('method', 'actor', 'revision', 'gate_metric', 'optimization_pool', 'batches',
                     'initial_skill', 'max_attempts', 'continue_no_change', 'retry_delay_seconds',
                     'max_input_chars', 'max_message_utf8_bytes', 'module_calls'), 'Campaign config')
    dataset = current().dataset
    p.require(config['method'] == method_config(current()), 'Method contract or Prompt differs')
    p.validate_config(config['actor'])
    p.require(config['revision'] == p.REVISION and config['gate_metric'] == p.GATE_PROFILE, 'DocVQA protocol differs')
    p.require(config['optimization_pool'] == dataset.optimization_pool, 'Optimization pool differs')
    p.require(config['initial_skill'] == p.initial_skill(), 'Initial Skill must be the SkillOpt DocVQA original')
    batches = config['batches']
    p.require(isinstance(batches, list) and batches and all(isinstance(b, list) and b for b in batches), 'Missing batches')
    tasks = [t for batch in batches for t in batch]
    p.require(all(isinstance(t, str) and t in dataset.rows for t in tasks) and len(set(tasks)) == len(tasks),
              'Unknown or repeated task')
    p.require(batches == dataset.batches and tasks == dataset.splits['train'], 'Full-pass schedule/order differs')
    p.require(set(tasks).isdisjoint(dataset.splits['test']) and
              all(dataset.case(t).metadata['split'] == 'train' for t in tasks), 'Test cannot enter training')
    if isinstance(dataset, DocVQADataset):
        p.require([len(b) for b in batches] == [15] * 10 + [10], 'Expected 160 questions in eleven batches')
    p.require(config['continue_no_change'] is True and type(config['max_attempts']) is int and
              config['max_attempts'] == 6 and config['retry_delay_seconds'] == 2.0, 'Retry/schedule policy differs')
    for key in ('max_input_chars', 'max_message_utf8_bytes'):
        p.require(type(config[key]) is int and config[key] > 0, 'Invalid input capacity')
    p.fields(config['module_calls'], prompting.PROMPT_VERSIONS, 'Module calls')
    for name, value in config['module_calls'].items():
        expected = pending_calls()[name]
        p.fields(value, expected, f'{name} call')
        p.require(all(value[k] == v for k, v in expected.items() if k not in ('max_tokens', 'timeout_seconds')),
                  'Method API/model settings differ')
        if value['max_tokens'] is None and value['timeout_seconds'] is None:
            p.require(not executable, 'Method budgets/timeouts remain pending; no execution may start')
        else:
            validate_call(value)
    return config

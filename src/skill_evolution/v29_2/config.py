"""Independent v29.2 configuration; no credentials, writes or campaign execution."""
from copy import deepcopy
import json

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.transport import validate_call
from src.skill_evolution.v29.benchmarks.docvqa import protocol
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
from . import grouping, diagnosis, preconditioner, editor, replay, replay_input_view, gate, memory

METHOD_VERSION = 'v29_2_campaign_v1'
STAGE_VERSION = 'v29_2_stages_v1'
MODULES = {'diagnosis': diagnosis, 'preconditioner': preconditioner, 'editor': editor, 'replay': replay}
GROUPING_PROMPT = grouping.PROMPT_VERSION
GROUPING_CONTRACT = grouping.CONTRACT_VERSION
MODEL_MODULES = ('grouping', *MODULES)


def same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def prompt_versions():
    return {'grouping': GROUPING_PROMPT, **{name: module.PROMPT_VERSION for name, module in MODULES.items()}}


def contracts():
    return {'grouping': GROUPING_CONTRACT, **{name: module.CONTRACT_VERSION for name, module in MODULES.items()},
            'gate': gate.CONTRACT_VERSION, 'memory': memory.FORMAT}


def method_config():
    return {'version': METHOD_VERSION, 'stage_contract': STAGE_VERSION, 'prompts': prompt_versions(),
            'contracts': contracts(), 'memory_view': 'v29_2_rounds_effective_updates_v1',
            'replay_input_view': replay_input_view.INPUT_VIEW, 'model_input_view': protocol.MODEL_INPUT_VIEW,
            'execution_input_views': execution_input_views(),
            'retry_policy': 'previous_output_validation_error_v1', 'semantic_resampling': False,
            'knowledge_review': 'disabled_v1', 'memory_publication': 'append_only_head_selected_skill_v1'}


def execution_input_views():
    return {name: module.INPUT_VIEW for name, module in
            (('grouping', grouping), ('diagnosis', diagnosis), ('preconditioner', preconditioner))}


def pending_calls():
    return {name: {'endpoint': protocol.ACTOR['endpoint'], 'model': protocol.ACTOR['model'],
                   'max_tokens': None, 'timeout_seconds': None, 'temperature': 1.0,
                   'reasoning_effort': 'medium', 'thinking': {'type': 'enabled'}} for name in MODEL_MODULES}


def validate_module_call(name, value, *, executable=True):
    require(name in MODEL_MODULES, 'Only the five model modules have request budgets')
    expected = pending_calls()[name]
    require(isinstance(value, dict), f'{name} call must be an object')
    protocol.fields(value, set(expected) | ({'context_window_tokens'} if 'context_window_tokens' in value else set()),
                    f'{name} call')
    require(all(same(value[key], item) for key, item in expected.items()
                if key not in ('max_tokens', 'timeout_seconds')), 'Method API/model settings differ')
    if 'context_window_tokens' in value:
        require(type(value['context_window_tokens']) is int and value['context_window_tokens'] > 0,
                'Invalid explicit context capacity')
    if value['max_tokens'] is None and value['timeout_seconds'] is None:
        require(not executable, 'Method budgets/timeouts remain pending')
    else:
        validate_call(value)
    return value


def render_prompts():
    return {'grouping': grouping.render_prompt(protocol.actor_config()),
            **{name: module.render_prompt(protocol.actor_config()) for name, module in MODULES.items()}}


def campaign_config(adapter, *, module_calls=None):
    return {'method': method_config(), 'actor': protocol.actor_config(), 'revision': protocol.REVISION,
            'scorer_profile': protocol.SCORER_PROFILE, 'gate_rule': gate.CONTRACT_VERSION,
            'optimization_pool': adapter.dataset.optimization_pool, 'batches': deepcopy(adapter.dataset.batches),
            'initial_skill': protocol.initial_skill(), 'max_attempts': 6, 'continue_no_change': True,
            'retry_delay_seconds': 2.0, 'max_input_chars': 4000000, 'max_message_utf8_bytes': 6000000,
            'module_calls': deepcopy(pending_calls() if module_calls is None else module_calls)}


def validate_config(config, *, executable=False):
    protocol.fields(config, ('method', 'actor', 'revision', 'scorer_profile', 'gate_rule', 'optimization_pool',
                            'batches', 'initial_skill', 'max_attempts', 'continue_no_change', 'retry_delay_seconds',
                            'max_input_chars', 'max_message_utf8_bytes', 'module_calls'), 'v29.2 configuration')
    require(same(config['method'], method_config()), 'Method version, prompts or contracts differ')
    require(same(config['actor'], protocol.actor_config()), 'Actor configuration differs')
    protocol.validate_config(config['actor'])
    require(config['revision'] == protocol.REVISION and config['scorer_profile'] == protocol.SCORER_PROFILE,
            'DocVQA data/scorer protocol differs')
    require(config['gate_rule'] == gate.CONTRACT_VERSION, 'Expected Update-level selective Gate')
    dataset = current().dataset
    require(config['optimization_pool'] == dataset.optimization_pool, 'Optimization pool differs')
    require(config['initial_skill'] == protocol.initial_skill(), 'Initial Skill differs')
    batches = config['batches']
    require(isinstance(batches, list) and batches and all(isinstance(batch, list) and batch for batch in batches),
            'Missing batches')
    tasks = [task for batch in batches for task in batch]
    require(all(isinstance(task, str) and task in dataset.rows for task in tasks) and len(set(tasks)) == len(tasks),
            'Unknown or repeated task')
    require(batches == dataset.batches and tasks == dataset.splits['train'], 'Full-pass schedule/order differs')
    require(set(tasks).isdisjoint(dataset.splits['test']) and
            all(dataset.case(task).metadata['split'] == 'train' for task in tasks), 'Test cannot enter training')
    if isinstance(dataset, DocVQADataset):
        require([len(batch) for batch in batches] == [15] * 10 + [10], 'Expected frozen 160-question schedule')
    require(type(config['max_attempts']) is int and config['max_attempts'] == 6 and
            config['continue_no_change'] is True and same(config['retry_delay_seconds'], 2.0),
            'Retry/schedule policy differs')
    for key in ('max_input_chars', 'max_message_utf8_bytes'):
        require(type(config[key]) is int and config[key] > 0, 'Invalid input capacity')
    protocol.fields(config['module_calls'], MODEL_MODULES, 'Module calls')
    for name, value in config['module_calls'].items():
        validate_module_call(name, value, executable=executable)
    render_prompts()
    return config

"""Independent SearchQA v28.10 configuration; no transport or writes."""
from copy import deepcopy
import json

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.transport import validate_call
from src.skill_evolution.v28.benchmarks.searchqa import protocol
from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
from . import diagnosis, preconditioner, editor, replay, replay_input_view, gate, memory

METHOD_VERSION = 'v28_10_campaign_v1'
STAGE_VERSION = 'v28_5_stages_v1'
MODULES = {'diagnosis': diagnosis, 'preconditioner': preconditioner,
           'editor': editor, 'replay': replay}
MODEL_MODULES = tuple(MODULES)
DEFAULT_CONFIG = protocol.ROOT / 'experiments/configs/v28_10_searchqa_train600_batch60.json'


def same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def prompt_versions():
    return {name: module.PROMPT_VERSION for name, module in MODULES.items()}


def contracts():
    return {**{name: module.CONTRACT_VERSION for name, module in MODULES.items()},
            'gate': gate.CONTRACT_VERSION, 'memory': memory.FORMAT}


def execution_input_views():
    return {name: MODULES[name].INPUT_VIEW for name in ('diagnosis', 'preconditioner')}


def method_config():
    return {'version': METHOD_VERSION, 'stage_contract': STAGE_VERSION, 'prompts': prompt_versions(),
            'contracts': contracts(), 'memory_view': 'v28_5_rounds_effective_updates_v1',
            'replay_input_view': replay_input_view.INPUT_VIEW, 'model_input_view': protocol.MODEL_INPUT_VIEW,
            'execution_input_views': execution_input_views(), 'retry_policy': 'previous_output_validation_error_v1',
            'semantic_resampling': False, 'knowledge_review': 'disabled_v1',
            'memory_publication': 'append_only_head_selected_skill_v1'}


def module_calls():
    budgets = {'diagnosis': 65536, 'preconditioner': 65536, 'editor': 65536, 'replay': 65536}
    return {name: {'endpoint': protocol.ACTOR['endpoint'], 'model': protocol.ACTOR['model'],
                   'max_tokens': budget, 'timeout_seconds': 600, 'temperature': 1.0,
                   'reasoning_effort': 'medium', 'thinking': {'type': 'enabled'}} for name, budget in budgets.items()}


def validate_module_call(name, value, *, executable=True):
    require(name in MODEL_MODULES, 'Only four model modules have request budgets')
    require(same(value, module_calls()[name]), 'Method request settings/budgets differ')
    validate_call(value)
    return value


def render_prompts():
    return {name: module.render_prompt(protocol.actor_config(30)) for name, module in MODULES.items()}


def initial_skill():
    source = protocol.ROOT / 'experiments/configs/v28_searchqa_initial_skill.md'
    return {'source': str(source), 'text': source.read_bytes().decode('utf-8')}


def campaign_config(adapter):
    return {'method': method_config(), 'benchmark': 'v28_searchqa_v1', 'actor': protocol.actor_config(30),
            'scorer_profile': protocol.SCORER_PROFILE, 'gate_rule': gate.CONTRACT_VERSION,
            'optimization_splits': ['train'], 'optimization_pool': adapter.dataset.optimization_pool,
            'batches': deepcopy(adapter.dataset.batches), 'initial_skill': initial_skill(),
            'max_attempts': 6, 'continue_no_change': True, 'retry_delay_seconds': 2.0,
            'max_input_chars': 4000000, 'max_message_utf8_bytes': 6000000, 'module_calls': module_calls()}


def validate_config(config, *, executable=False):
    adapter = current(); adapter._bound()
    expected = campaign_config(adapter)
    protocol.fields(config, expected, 'v28.10 configuration')
    require(same(config, expected), 'Configuration, method, prompts, contracts or frozen parameters differ')
    require(adapter.method_version == METHOD_VERSION and adapter.actor_adapter.profile == METHOD_VERSION,
            'Wrong campaign/Actor method binding')
    require(not adapter.actor_adapter.verify_hashes and not adapter.dataset.verify_hashes,
            'v28.10 requires plain archives')
    dataset = adapter.dataset
    require(dataset.batch_size in (30, 50, 60), 'v28.10 requires batch30, batch50 or batch60')
    batches = config['batches']
    require(isinstance(batches, list) and batches and all(isinstance(b, list) and b for b in batches), 'Missing batches')
    ids = [t for b in batches for t in b]
    require(all(isinstance(t, str) and t in dataset.rows for t in ids) and len(set(ids)) == len(ids),
            'Unknown or repeated tasks')
    require(ids == dataset.splits['train'] and set(ids).isdisjoint(dataset.splits['test']) and
            all(dataset.case(t).metadata['split'] == 'train' for t in ids), 'Training schedule or split differs')
    if isinstance(dataset, SearchQADataset):
        require([len(b) for b in batches] == [dataset.batch_size] * (600 // dataset.batch_size) and len(dataset.splits['test']) == 1400,
                'Expected 600 optimization and 1400 held-out tasks')
    require(type(config['max_attempts']) is int and config['max_attempts'] == 6, 'Six requests required')
    for name, value in config['module_calls'].items(): validate_module_call(name, value)
    render_prompts()
    return config

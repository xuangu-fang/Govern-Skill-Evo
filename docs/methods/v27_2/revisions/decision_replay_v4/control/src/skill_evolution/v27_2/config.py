"""Versioned prompts over the v27.1 LMB execution and stage contracts."""
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.training import OptimizationDataset
from src.skill_evolution.v27_1 import actor_io, config as base
from src.skill_evolution.v27_1.config import (
    STAGE_VERSION, contracts, execution_input_views, same, validate_module_call,
)
from src.skill_evolution.v27_1.lmb import protocol
from . import diagnosis, editor, preconditioner, replay
from .prompts import render

METHOD_VERSION = 'v27_2_campaign_v1'
MODULES = {'diagnosis': diagnosis, 'preconditioner': preconditioner,
           'editor': editor, 'replay': replay}
MODEL_MODULES = tuple(MODULES)
DEFAULT_CONFIG = protocol.ROOT / 'experiments/configs/v27_2_lmb53.json'


def prompt_versions():
    return {name: module.PROMPT_VERSION for name, module in MODULES.items()}


def method_config():
    return {**base.method_config(), 'version': METHOD_VERSION, 'prompts': prompt_versions()}


def render_prompts():
    background = protocol.background(protocol.ACTOR)
    return {name: render(name, background) for name in MODEL_MODULES}


def campaign_config(adapter):
    return {**base.campaign_config(adapter), 'method': method_config()}


def validate_config(config, *, executable=False):
    adapter = current(); adapter._bound()
    expected = campaign_config(adapter)
    protocol.fields(config, expected, 'v27.2 configuration')
    require(same(config, expected), 'Configuration, method, prompts, contracts or frozen parameters differ')
    require(adapter.method_version == METHOD_VERSION and adapter.actor_adapter.profile == actor_io.METHOD_VERSION,
            'Wrong campaign/Actor method binding')
    dataset = adapter.dataset
    batches = config['batches']
    require(isinstance(batches, list) and batches and all(isinstance(b, list) and b for b in batches), 'Missing batches')
    ids = [t for b in batches for t in b]
    require(all(isinstance(t, str) and t in dataset.rows for t in ids) and len(set(ids)) == len(ids),
            'Unknown or repeated tasks')
    require(ids == dataset.splits['train'] and set(ids).isdisjoint(dataset.splits['test']) and
            all(dataset.case(t).metadata['split'] == 'train' for t in ids), 'Training schedule or split differs')
    if isinstance(dataset, OptimizationDataset):
        require([len(b) for b in batches] == [10]*5+[3] and len(dataset.splits['test']) == 124,
                'Expected 53 optimization and 124 held-out tasks')
    require(type(config['max_attempts']) is int and config['max_attempts'] == 6, 'Six requests required')
    for name, value in config['module_calls'].items(): validate_module_call(name, value)
    render_prompts()
    return config

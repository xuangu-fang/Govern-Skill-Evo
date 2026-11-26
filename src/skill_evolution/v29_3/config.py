"""v29.3 version binding with the unchanged v29.2 configuration contract."""
from copy import deepcopy

from src.skill_evolution.v27.facts import require
from src.skill_evolution.v29.benchmarks.docvqa import protocol
from src.skill_evolution.v29_2 import config as base
from . import diagnosis, preconditioner

METHOD_VERSION = 'v29_3_campaign_v1'
STAGE_VERSION = base.STAGE_VERSION
MODULES = {**base.MODULES, 'diagnosis': diagnosis, 'preconditioner': preconditioner}
MODEL_MODULES = base.MODEL_MODULES
GROUPING_PROMPT = base.GROUPING_PROMPT
GROUPING_CONTRACT = base.GROUPING_CONTRACT
same = base.same
contracts = base.contracts
execution_input_views = base.execution_input_views
pending_calls = base.pending_calls
validate_module_call = base.validate_module_call


def prompt_versions():
    return {**base.prompt_versions(), 'diagnosis': diagnosis.PROMPT_VERSION,
            'preconditioner': preconditioner.PROMPT_VERSION}


def method_config():
    return {**base.method_config(), 'version': METHOD_VERSION, 'prompts': prompt_versions()}


def render_prompts():
    return {**base.render_prompts(),
            'diagnosis': diagnosis.render_prompt(protocol.actor_config()),
            'preconditioner': preconditioner.render_prompt(protocol.actor_config())}


def campaign_config(adapter, *, module_calls=None):
    return {**base.campaign_config(adapter, module_calls=module_calls), 'method': method_config()}


def validate_config(config, *, executable=False):
    require(isinstance(config, dict) and same(config.get('method'), method_config()),
            'Method version, prompts or contracts differ')
    original = deepcopy(config)
    original['method'] = base.method_config()
    base.validate_config(original, executable=executable)
    render_prompts()
    return config

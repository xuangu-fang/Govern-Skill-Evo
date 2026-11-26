"""Explicit executable configuration; validation never reads credentials or writes."""
from copy import deepcopy
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v26.transport import validate_call
from . import protocol as p, diagnosis, preconditioner, editor, replay, gate, memory

METHOD_VERSION = p.METHOD_VERSION
STAGE_VERSION = 'v26_1_stages_v1'
MODULES = dict(diagnosis=diagnosis, preconditioner=preconditioner, editor=editor, replay=replay)
MODEL_MODULES = tuple(MODULES)
same = p.equal


def prompt_versions():
    return {name: module.PROMPT_VERSION for name, module in MODULES.items()}


def contracts():
    return {**{name: module.CONTRACT_VERSION for name, module in MODULES.items()},
            'gate': gate.CONTRACT_VERSION, 'memory': memory.FORMAT}


def method_config():
    design = p.PLAN['method']
    return {key: deepcopy(value) for key, value in design.items() if key not in ('prompt_paths',)}


def execution_input_views():
    return {name: p.MODEL_INPUT_VIEW for name in ('diagnosis', 'preconditioner', 'replay')}


def validate_module_call(name, value, *, executable=True):
    p.require(name in MODULES and same(value, p.PLAN['module_calls'][name]), 'Module settings differ')
    validate_call(value)
    return value


def render_prompts():
    return {name: module.render_prompt(p.expected_background()) for name, module in MODULES.items()}


def campaign_config(adapter):
    return {'method': method_config(), 'actor': adapter.transport.metadata(), 'revision': p.REVISION,
            'scorer_profile': p.SCORER_PROFILE, 'gate_rule': gate.CONTRACT_VERSION,
            'optimization_pool': adapter.dataset.optimization_pool,
            'prepared_root': str(adapter.dataset.root), 'parsed_root': str(adapter.runtime.parsed_root),
            'batches': deepcopy(adapter.dataset.batches), 'initial_skill': p.initial_skill(),
            'actor_task_output_limits': deepcopy(p.LIMITS), 'train_workers': p.PLAN['execution']['train_workers'],
            'test_workers': p.PLAN['execution']['test_workers'],
            **{key: deepcopy(p.PLAN[key]) for key in ('max_attempts', 'continue_no_change',
                'retry_delay_seconds', 'max_input_chars', 'max_message_utf8_bytes', 'module_calls')}}


def validate_config(config, *, executable=False):
    expected = campaign_config(current())
    # Portable source paths in the checked-in configuration are resolved from repo root.
    normalized = deepcopy(config)
    for key in ('prepared_root', 'parsed_root'):
        normalized[key] = str((p.ROOT / config[key]).resolve())
    p.fields(normalized, expected, 'v26.9 configuration')
    p.require(same(normalized, expected), 'Configuration, source data, schedule or Actor differs')
    p.require(same(config['batches'], p.PLAN['schedule']['batches']), 'Frozen seven-batch schedule differs')
    p.validate_actor(config['actor'])
    p.require(contracts() == config['method']['contracts'] and prompt_versions() == config['method']['prompts'],
              'Method contracts or prompts differ')
    p.require(set(sum(config['batches'], [])).isdisjoint(current().dataset.splits['test']), 'Test overlaps optimization')
    for name, value in config['module_calls'].items(): validate_module_call(name, value)
    render_prompts()
    current()._preflight()
    return config

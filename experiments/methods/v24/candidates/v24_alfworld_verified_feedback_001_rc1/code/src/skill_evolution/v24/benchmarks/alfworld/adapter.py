from src.skill_evolution.v24.benchmarks.alfworld.actor.skill_runtime import protocol_settings
"""ALFWorld execution and lossless evidence codec for the V24 method.

Domain templates retain their upstream bytes. Codec functions preserve the
original serialized model inputs; the method never manufactures action menus.
"""
from importlib import import_module
import json
from pathlib import Path

from ...facts import require
from . import facts, runtime, context
from src.skill_evolution.v24.benchmarks.alfworld.actor.skill_runtime import (
    execution_protocol, LEGACY_INJECTION, SKILLOPT_INJECTION, LEGACY_OUTPUT, ACTION_ONLY_OUTPUT,
)

HERE = Path(__file__).parent
ROOT = HERE.parents[4]
IDENTITY = {'name': 'alfworld', 'adapter_version': 'v24_alfworld_v1',
            'evidence_version': 'alfworld_recorded_facts_v1',
            'prompt_profile': 'verified_feedback_v23_5_exact_v1'}


class ALFWorldAdapter:
    identity = IDENTITY

    def __init__(self):
        self._operations = json.loads((HERE/'evidence_registry.json').read_text())

    def evidence(self, operation, *args, **kwargs):
        require(operation in self._operations, f'Unknown evidence operation: {operation}')
        module, name = self._operations[operation].rsplit('.', 1)
        implementation = import_module(f'{__package__}.{module}')
        return getattr(implementation, name)(*args, **kwargs)

    def resource(self, key):
        relative = Path(key)
        require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe prompt resource')
        path = HERE/'prompts'/relative
        require(path.is_file(), f'Unknown ALFWorld prompt resource: {key}')
        return path

    def validation_sources(self):
        return set(HERE.glob('evidence_*.py'))

    @staticmethod
    def plan_fields():
        return ('parent', 'plan', 'command_sets', 'runs', 'grouping', 'memory')

    @staticmethod
    def auxiliary_references(payload):
        return set(payload['command_sets'])

    def validate_execution_source(self, source):
        from ...contracts.diagnosis import fields
        fields(source, ('run', 'command_sets'), 'Execution source')
        require(isinstance(source['command_sets'], dict), 'Invalid command sets')
        return self.evidence('contracts.memory.validate_run', source['run'], source['command_sets'])

    def frozen_files(self):
        from src.skill_evolution.v24.benchmarks.alfworld.actor.run_task_upstream import PROTOCOL_ROOT
        paths = {p for p in HERE.rglob('*') if p.is_file() and p.suffix in {'.py', '.md', '.json'}}
        paths.add(HERE.parent/'__init__.py')
        paths.update(p for p in PROTOCOL_ROOT.iterdir() if p.is_file())
        return {str(p.relative_to(ROOT)): p.read_bytes().decode('utf-8') for p in sorted(paths)}

    def validate_config(self, config):
        require(config.get('benchmark') == self.identity, 'Benchmark/profile binding differs')
        require(type(config.get('actor_retry_invalid_actions', False)) is bool, 'Actor action retry flag must be boolean')
        require(type(config.get('actor_action_feedback', False)) is bool and
                (not config.get('actor_action_feedback') or config.get('actor_retry_invalid_actions')),
                'Actor feedback requires action retries')
        require(config.get('actor_skill_injection', LEGACY_INJECTION) in (LEGACY_INJECTION, SKILLOPT_INJECTION),
                'Unsupported Actor Skill injection')
        require(config.get('actor_output_format', LEGACY_OUTPUT) in (LEGACY_OUTPUT, ACTION_ONLY_OUTPUT),
                'Unsupported Actor output format')
        ids = [t for batch in config['batches'] for t in batch]
        splits = config.get('optimization_splits', ['train'])
        require(splits in (['train'], ['train', 'val']), 'Optimization permits Train and explicit Selection only')
        require(all(isinstance(t, str) and ':' in t and t.split(':')[0] in splits for t in ids),
                'Task outside frozen optimization splits')
        if 'val' in splits:
            require(set(config.get('task_items', {})) == set(ids), 'Merged pool requires frozen task identities')
        require(config['max_steps'] == 50, 'Use the verified Actor step budget')
        require(not config.get('_output_budget_campaign'), 'V24 has fixed request budgets')

    build_facts = staticmethod(facts.build_facts)
    parent_text = staticmethod(facts.parent_text)
    actor_task = staticmethod(runtime.actor_task)
    actor_command = staticmethod(runtime.actor_command)
    runtime_snapshot = staticmethod(runtime.runtime_snapshot)
    actor_fields = staticmethod(context.actor_fields)
    execution_context = staticmethod(context.execution_context)

    def build_gate(self, *args, **kwargs):
        from .gate import build_gate
        return build_gate(*args, **kwargs)

    @staticmethod
    def is_complete(record):
        return record.get('status') in facts.COMPLETE

    def check_record(self, record, task, expected_skill, config):
        bundle = self.build_facts([record])
        require(not record.get('output_budget_policy'), 'V24 has fixed request budgets')
        require(record['task']['id'] == task and self.is_complete(record), 'Incomplete Actor task')
        require(bundle['facts']['parent'] == expected_skill, 'Actor used a different Skill')
        require(record['model'] == config['actor_model'], 'Actor model differs')
        if 'task_items' in config:
            require(record['task'] == config['task_items'][task], 'Frozen task identity differs')
            require(record['request_policy'] == {'max_attempts': config['actor_request_attempts'],
                    'strict_response': True}, 'Actor retry policy differs')
        require(protocol_settings(record['protocol']) == protocol_settings(execution_protocol(config['max_steps'],
                config.get('actor_skill_injection', LEGACY_INJECTION),
                output_format=config.get('actor_output_format', LEGACY_OUTPUT),
                retry_invalid_actions=config.get('actor_retry_invalid_actions', False),
                action_feedback=config.get('actor_action_feedback', False))), 'Actor protocol differs')
        return record

    def prepare_evaluation(self, experiment, campaign):
        from .evaluation import prepare
        return prepare(experiment, campaign)

    def check_evaluation_record(self, path, task, bundle):
        from .evaluation import check_record
        return check_record(path, task, bundle)

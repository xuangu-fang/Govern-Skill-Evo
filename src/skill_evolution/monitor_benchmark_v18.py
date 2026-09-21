"""Current benchmark adapter; private evaluator data never enters learner packets."""
import hashlib
import json
from pathlib import Path

from .monitor_v18 import MonitorInput, MonitorTask, MonitorRejected


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class CurrentBenchmarkMonitor:
    def __init__(self, *, artifact_dir, parent_skill, candidate_skill, config, freeze, resume=False):
        from . import benchmark_runtime_v18 as runtime
        self.runtime = runtime
        self.registry = runtime.BenchmarkRegistry()
        self.user_prompts = json.loads((freeze / 'user_prompts.json').read_text())
        self.adapter = runtime.UnifiedEnvironmentAdapter(self.registry, frozen_user_prompts=self.user_prompts)
        self.evaluator = runtime.DeterministicEvaluatorDispatcher(self.registry)
        self.base_config = config['base_config']
        self.seed = config['seed']
        self.root = Path(artifact_dir)
        self.root.mkdir(parents=True, exist_ok=resume)
        self.resume = resume
        self.skills = {'PARENT': parent_skill, 'CANDIDATE': candidate_skill}
        self.paths = {}
        for role, skill in self.skills.items():
            path = self.root / (role.lower() + '_skill.md')
            if path.exists() and path.read_bytes() != skill.encode('utf-8'):
                raise MonitorRejected('resume Skill differs from saved Monitor')
            path.write_bytes(skill.encode('utf-8'))
            self.paths[role] = path
        self.initial_path = freeze / 'S0.md'
        self.initial_text = self.initial_path.read_bytes().decode('utf-8')
        self.task_ids = self.registry.task_ids('monitor')
        if self.task_ids != config['tasks']['monitor']:
            raise MonitorRejected('Frozen Monitor task split mismatch')
        # Bind actual task/spec/model configuration and exposed policy/tool context.
        contexts = {}
        from .information_boundary_v15 import unpack
        for task_id in self.task_ids:
            entry = self.registry.get(task_id)
            if entry.runtime_domain not in contexts:
                contexts[entry.runtime_domain] = unpack(self.adapter.visible_view_without_models(task_id), 'AGENT_VISIBLE_VIEW')
        self.config_digest = canonical_digest({'base_config': self.base_config, 'seed': self.seed,
            'tasks': {t: {'payload': self.registry.get(t).payload, 'spec': self.registry.get(t).spec} for t in self.task_ids},
            'contexts': contexts, 'user_prompts': self.user_prompts, 'adapter': 'current_benchmark_monitor_v18.1'})

    def monitor_input(self, round_id):
        return MonitorInput(round_id, tuple(MonitorTask(t, self.seed) for t in self.task_ids),
                            self.skills['PARENT'], self.skills['CANDIDATE'], self.config_digest)

    def __call__(self, call):
        if call.task_id not in self.task_ids or call.benchmark_config_digest != self.config_digest or call.skill != self.skills[call.role]:
            raise MonitorRejected('benchmark call binding mismatch')
        # The historical heading-only S0 was deployed without manual Skill injection.
        # Apply that same deployment rule to either role based on exact content.
        path = self.initial_path if call.skill == self.initial_text else self.paths[call.role]
        if path.read_bytes() != call.skill.encode('utf-8'):
            raise MonitorRejected('Skill file changed')
        directory = self.root / call.role / hashlib.sha256(call.task_id.encode()).hexdigest()
        binding = {'task_id': call.task_id, 'seed': call.seed, 'skill_digest': call.skill_digest,
                   'config_digest': self.config_digest}
        if self.resume and all((directory / name).is_file() for name in ('simulation.json', 'initial_db.json', 'final_db.json', 'evaluation.json', 'checkpoint.json')):
            checkpoint = json.loads((directory / 'checkpoint.json').read_text())
            if checkpoint['binding'] != binding or any(hashlib.sha256((directory / n).read_bytes()).hexdigest() != h for n, h in checkpoint['files'].items()):
                raise MonitorRejected('saved Monitor checkpoint mismatch')
            simulation = json.loads((directory / 'simulation.json').read_text())
            if simulation.get('task_id') != call.task_id or simulation.get('seed') != call.seed:
                raise MonitorRejected('saved Monitor binding mismatch')
            evaluated = json.loads((directory / 'evaluation.json').read_text())
            initial = json.loads((directory / 'initial_db.json').read_text())
            return {'success': evaluated['success'], 'compliant': evaluated['compliant'],
                    'initial_state_digest': canonical_digest(initial)}
        if directory.exists():
            index = 1
            archive = directory.with_name(directory.name + f'.partial-{index}')
            while archive.exists():
                index += 1
                archive = directory.with_name(directory.name + f'.partial-{index}')
            directory.rename(archive)
        orchestrator, _ = self.adapter.build_orchestrator(call.task_id, base_config=self.base_config,
            seed=call.seed, skill_path=path, initial_skill_path=self.initial_path)
        initial = orchestrator.environment.tools.db.model_dump(mode='json')
        simulation = orchestrator.run().model_dump(mode='json')
        final = orchestrator.environment.tools.db.model_dump(mode='json')
        directory = self.root / call.role / hashlib.sha256(call.task_id.encode()).hexdigest()
        directory.mkdir(parents=True, exist_ok=False)
        for name, data in [('simulation.json', simulation), ('initial_db.json', initial), ('final_db.json', final)]:
            (directory / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        evaluated = self.evaluator.evaluate(call.task_id, initial_db=initial, final_db=final, simulation=simulation)
        (directory / 'evaluation.json').write_text(json.dumps(evaluated, ensure_ascii=False, indent=2) + '\n')
        checkpoint = {'binding': binding, 'files': {n: hashlib.sha256((directory / n).read_bytes()).hexdigest()
            for n in ('simulation.json', 'initial_db.json', 'final_db.json', 'evaluation.json')}}
        (directory / 'checkpoint.json').write_text(json.dumps(checkpoint, sort_keys=True))
        return {'success': evaluated['success'], 'compliant': evaluated['compliant'],
                'initial_state_digest': canonical_digest(initial)}

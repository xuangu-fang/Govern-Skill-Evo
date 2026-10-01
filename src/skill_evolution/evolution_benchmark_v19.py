"""v19 Evolution backend over frozen benchmark v4; no global policy patching."""
from pathlib import Path
import re
import uuid

from .edit_tracking_v19 import encode, parse, digest
from .evolution_replay_v19 import PreparedEvolution, _file_digest, _load, _require, _save
from .information_boundary_v15 import capture_agent_visible_view, unpack

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FREEZE = ROOT / 'experiments/configs/v18_formal_003'


class BenchmarkEvolutionV19:
    """Only the authoritative 36-task train split can execute through this API.

    The unchanged v18 freeze supplies benchmark/config inputs, not its runner.
    A fresh local Environment gets its frozen policy before agent construction.
    """

    _split = 'train'

    def __init__(self, *, freeze=DEFAULT_FREEZE, source_recovery=None):
        from . import benchmark_runtime_v18_v4 as runtime
        self.source_recovery = source_recovery
        self.freeze = Path(freeze)
        self._freeze_manifest = _load(self.freeze / 'manifest.json')
        self._config = _load(self.freeze / 'config.json')
        self._tasks = _load(self.freeze / 'tasks.json')
        self._contexts = _load(self.freeze / 'contexts.json')
        self._prompts = _load(self.freeze / 'user_prompts.json')
        self._initial_skill = (self.freeze / 'S0.md').read_bytes().decode('utf-8')
        self.runtime = runtime
        self.registry = runtime.BenchmarkRegistry()
        # Registers domain constructors and the existing frozen simulator name.
        self.adapter = runtime.UnifiedEnvironmentAdapter(self.registry, frozen_user_prompts=self._prompts)
        self.evaluator = runtime.DeterministicEvaluatorDispatcher(self.registry)
        self._v19_files = {str(p.relative_to(ROOT)): _file_digest(p)
                           for p in sorted((ROOT / 'src/skill_evolution').glob('*v19.py'))}
        self._manifest = self._make_manifest()

    def _make_manifest(self):
        _require(self._config['benchmark_edition'] == 'phase_v4_day36', 'benchmark v4 required')
        _require(self.registry.task_ids(self._split) == self._config['tasks'][self._split], 'frozen train split mismatch')
        for name, sha in self._freeze_manifest['files'].items():
            _require(_file_digest(ROOT / name) == sha, 'frozen benchmark/source changed: ' + name)
        for name, sha in self._v19_files.items():
            _require(_file_digest(ROOT / name) == sha, 'v19 replay source changed: ' + name)
        for task_id in self._config['tasks'][self._split]:
            entry = self.registry.get(task_id)
            _require({'payload': entry.payload, 'spec': entry.spec, 'split': entry.split} == self._tasks[task_id],
                     'task or evaluator specification changed')
            _require(entry.split == self._split, 'task outside required split')
        return {'schema_version': ('evolution_manifest_v19.1' if self._split == 'train' else 'monitor_manifest_v19.1'),
                'task_ids': list(self._config['tasks'][self._split]), 'seed': self._config['seed'],
                'runtime': {'backend': 'benchmark_' + self._split + '_v19.1',
                    'freeze_manifest_sha256': digest(encode(self._freeze_manifest)),
                    'config_sha256': digest(encode(self._config)), 'v19_source_files': self._v19_files,
                    'tasks_sha256': digest(encode({t: self._tasks[t] for t in self._config['tasks'][self._split]})),
                    'initial_skill_sha256': digest(self._initial_skill)}}

    def manifest(self):
        current = self._make_manifest()
        _require(encode(current) == encode(self._manifest), 'backend changed after construction')
        if self.source_recovery is not None:
            return self.source_recovery.execution_manifest(current)
        return parse(encode(current))

    def prepare(self, task_id, skill, artifact_dir):
        from tau2.runner.build import build_agent, build_user
        from tau2.orchestrator.orchestrator import Orchestrator
        from .user_simulator_v18 import USER_SIMULATOR_NAME

        _require(task_id in self._config['tasks'][self._split], 'task outside required split forbidden')
        _require(type(skill) is str, 'Skill text required')
        entry = self.registry.get(task_id)
        task = entry.task.model_copy(deep=True)
        config = self.runtime.base_text_config(self._config['base_config'],
                    {'domain': entry.runtime_domain, 'task_id': task_id}, self._config['seed'])
        config.user = USER_SIMULATOR_NAME
        path = Path(artifact_dir) / 'deployed_skill.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            _require(path.read_bytes() == skill.encode('utf-8'), 'deployed Skill changed')
        else:
            path.write_bytes(skill.encode('utf-8'))
        has_body = any(line.strip() and not re.match(r'^#{1,6}(?:\s|$)', line.strip()) for line in skill.splitlines())
        if skill != self._initial_skill and has_body:
            config.agent = 'llm_agent_manual_skill'
            config.llm_args_agent = {**config.llm_args_agent, 'manual_skill_path': str(path.resolve())}
        environment = self.adapter.fresh_environment(entry.runtime_domain)
        policy_key = digest(environment.get_policy())
        _require(policy_key in self._config['policies'], 'unknown environment policy')
        environment.policy = (self.freeze / self._config['policies'][policy_key]).read_bytes().decode('utf-8')
        agent = build_agent(config.effective_agent, environment, llm=config.llm_agent,
                            llm_args=config.llm_args_agent, task=task, solo_mode=False)
        user = build_user(config.effective_user, environment, task, llm=config.llm_user,
                          llm_args=config.llm_args_user, solo_mode=False)
        view = capture_agent_visible_view(agent, entry.logical_domain)
        _require(unpack(view, 'AGENT_VISIBLE_VIEW') == self._contexts[task_id], 'frozen public context mismatch')
        prompt = user.prompt_record()
        _require(prompt == self._prompts[task_id], 'frozen actual simulator prompt mismatch')
        orchestrator = Orchestrator(domain=entry.runtime_domain, agent=agent, user=user, environment=environment,
            task=task, max_steps=config.effective_max_steps, max_errors=config.max_errors,
            seed=self._config['seed'], solo_mode=False, simulation_id=str(uuid.uuid4()),
            validate_communication=config.enforce_communication_protocol, timeout=config.timeout)
        # Skill injection is the intended variable. Normalize only its path and
        # wrapper name; all other effective execution settings remain paired.
        execution = config.model_dump(mode='json')
        execution['agent'] = 'V19_CONTENT_BASED_SKILL_DEPLOYMENT'
        execution['llm_args_agent'].pop('manual_skill_path', None)
        execution['task_initial_state'] = task.initial_state.model_dump(mode='json') if task.initial_state else None
        initial = environment.tools.db.model_dump(mode='json')

        def run():
            _require(path.read_bytes() == skill.encode('utf-8'), 'deployed Skill changed before rollout')
            simulation = orchestrator.run().model_dump(mode='json')
            return simulation, environment.tools.db.model_dump(mode='json')

        return PreparedEvolution(view, initial, prompt, execution, run)

    def evaluate(self, task_id, *, initial_db, final_db, simulation):
        _require(task_id in self._config['tasks'][self._split], 'task outside required split')
        return self.evaluator.evaluate(task_id, initial_db=initial_db, final_db=final_db, simulation=simulation)

    def preflight(self, *, artifact_dir, skills):
        """Construct every train environment for each Skill, with zero rollouts."""
        _require(type(skills) is tuple and bool(skills), 'explicit Skills tuple required')
        manifest = self.manifest()
        directory = Path(artifact_dir)
        directory.mkdir(parents=True, exist_ok=False)
        checks = []
        for index, task_id in enumerate(manifest['task_ids']):
            reference = None
            for role_index, skill in enumerate(skills):
                prepared = self.prepare(task_id, skill, Path(artifact_dir) / f'T{index+1:03d}' / f'S{role_index}')
                paired = {'initial_db': prepared.initial_db, 'visible_view': prepared.visible_view.payload,
                          'user_prompt': prepared.user_prompt, 'execution_config': prepared.execution_config}
                if reference is not None:
                    _require(encode(paired) == encode(reference), 'preflight role binding mismatch')
                reference = paired
                checks.append({'task_ref': f'T{index+1:03d}', 'skill_sha256': digest(skill),
                               **{name + '_sha256': digest(encode(value)) for name, value in paired.items()}})
        result = {'status': 'PREFLIGHT', 'task_count': len(manifest['task_ids']),
                  'prepared_instances': len(checks), 'model_calls': 0}
        _save(directory / 'preflight.json', {**result, 'manifest': manifest, 'checks': checks})
        return result

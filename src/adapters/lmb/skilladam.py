"""Native SkillAdam optimizer, with v27's immutable LMB data and Actor.

The rollout directory hook and explicit Actor prompt profile are adapted.
Optimizer context quotes the same base protocol as the shared Actor.
Sampling, optimizer prompt templates, patching,
Momentum, adaptive budget, gates and early stopping stay upstream. Local I/O
receipts make native checkpoints and in-flight iterations recoverable.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from skilladam.benchmarks.lmb.adapter import LMBAdapter as UpstreamAdapter
from skilladam.core.feedback_loop import EditBudgetConfig, FeedbackLoopConfig
from skilladam.execution.contracts import BackendContext, BackendInit, RawRollout
from skilladam.methods.skilladam import SkillAdamRunConfig, SkillAdamRunner
from skilladam.types import BenchmarkCase
from src.skill_evolution.v27.benchmarks.lmb import protocol as p
from src.skill_evolution.v27.benchmarks.lmb.actor import ChatTransport, locked
from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.stages import freeze
from src.skill_evolution.v27.training import load_dataset
from .recovery import Recovery

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / 'experiments/configs/lmb_skilladam53_epoch1_deepseek_flash.json'


class NativeAdapter(UpstreamAdapter):
    """Native choices/scoring with the explicit shared DeepSeek prompt profile."""
    def build_rollout_request(self, case, *, method, split, skill, seed):
        request = super().build_rollout_request(case, method=method, split=split, skill=skill, seed=seed)
        metadata = dict(request.metadata)
        from skilladam.benchmarks.lmb.rollout import question_from_payload
        metadata['messages'] = p.build_messages(question=question_from_payload(case.payload),
            choices=metadata['evaluation_choices'], method=method, skill=skill)
        metadata['prompt_profile'] = p.PROMPT_PROFILE
        return replace(request, metadata=metadata)


def read(path):
    return json.loads(Path(path).read_text())


def native_config(value):
    value = deepcopy(value)
    loop = value.pop('feedback_loop')
    loop['edit_budget'] = EditBudgetConfig(**loop['edit_budget'])
    value['optimization_case_ids'] = tuple(value.get('optimization_case_ids', ()))
    return SkillAdamRunConfig(**value, feedback_loop=FeedbackLoopConfig(**loop))


def native_cases(dataset, split='train'):
    # Native adapter shuffles once, so give it original, sorted choices.
    return tuple(BenchmarkCase(uid,
        {'question': dataset.rows[uid]['question'].strip(),
         'choices': sorted(dataset.rows[uid]['choices'], key=lambda c: c['label'])},
        reference=dataset.rows[uid]['correct_choice'],
        metadata={'split': split}) for uid in dataset.splits[split])


def prepare(config_path=DEFAULT_CONFIG):
    """Read-only preflight: no credentials, providers, output directories or calls."""
    cfg = read(config_path)
    reference = read(ROOT / cfg['v27_config'])
    require(cfg['actor'] == reference['actor'] == p.ACTOR, 'Actor differs from v27')
    require(cfg['workers'] == 20 and cfg['test_workers'] == 16, 'Worker limits differ')
    dataset = load_dataset(ROOT / cfg['prepared_root'])
    initial = (ROOT / cfg['initial_skill']).read_text()
    require(initial == reference['initial_skill']['text'], 'Initial Skill differs from v27')
    value = deepcopy(cfg['native'])
    value['optimization_case_ids'] = dataset.splits['train']
    native = native_config(value)
    require(native.benchmark == 'lmb' and native.seed == 42 and native.split == 'train'
            and native.validation_split == 'train', 'Wrong native LMB pool')
    require(native.validation_mode == 'same_batch', 'LMB uses same-batch Gate')
    context = BackendContext('lmb', 'skilladam', cfg['actor']['model'],
                             cfg['actor']['reasoning_effort'], cfg['workers'], native.seed)
    from skilladam.backends.openai_compatible import OpenAICompatibleConfig
    backend_cfg = OpenAICompatibleConfig.from_mapping(cfg['optimizer']['backend_config'])
    require(cfg['optimizer']['base_url'] == 'https://api.deepseek.com'
            and cfg['optimizer']['thinking'] == p.ACTOR['thinking']
            and backend_cfg.max_completion_tokens == 16384
            and backend_cfg.temperature == p.ACTOR['temperature']
            and backend_cfg.timeout_seconds == p.ACTOR['timeout_seconds']
            and backend_cfg.token_limit_field == 'max_tokens'
            and backend_cfg.reasoning_mode == 'top_level', 'Frozen optimizer settings differ (output remains 16384)')
    adapter = NativeAdapter(dataset.root)
    cases = native_cases(dataset)
    # Validate the actual upstream sampler and all 177 request/answer mappings.
    runner = SkillAdamRunner(config=native, adapter=adapter, backend=None,
                            context=context, output_dir=Path('/unused-preflight'))
    runner._validate_cases(cases)
    batches = [list(b.training_case_ids) for b in runner._build_sampler(cases)]
    require(batches == reference['batches'], 'Native schedule differs from v27')
    for split in ('train', 'test'):
        for case in native_cases(dataset, split):
            request = adapter.build_rollout_request(case, method='skilladam', split=split,
                                                    skill=initial, seed=42)
            shared = dataset.case(case.case_id)
            require(p.equal(request.metadata['messages'], p.messages(shared.payload, initial))
                    and request.metadata['correct_label'] == shared.reference['label'],
                    'Native Actor prompt or shuffled reference differs')
    source_paths = []
    for folder in ('src/adapters/lmb', 'src/skill_evolution/v27', 'external/SkillAdam/skilladam'):
        source_paths.extend(q for q in (ROOT / folder).rglob('*')
                            if q.suffix in ('.py', '.md', '.json') and q.is_file())
    source_paths += [ROOT / 'scripts/runs/run_lmb_skilladam.py',
                     ROOT / 'benchmarks/livemathematicianbench/requirements.lock.txt']
    snapshot = {'config': cfg, 'native': native.to_dict(), 'data': dataset.snapshot(),
                'initial_skill': initial, 'batches': batches,
                'sources': {str(q.relative_to(ROOT)): hashlib.sha256(q.read_bytes()).hexdigest()
                            for q in sorted(source_paths)}}
    return cfg, dataset, initial, native, context, snapshot


class Backend:
    def __init__(self, dataset, actor_transport, generation, context, output_dir, snapshot):
        self.dataset = dataset
        self.actor = LMBAdapter(dataset, actor_transport)
        self.generation = generation
        self.context = context
        self.output_dir = Path(output_dir)
        self.snapshot = snapshot
        self.stage_directory = None
        self.recovery = Recovery(self)

    def public_metadata(self):
        return {'kind': 'lmb_v27_actor_native_skilladam', 'snapshot_sha256': p.digest(self.snapshot)}

    def generate(self, request):
        require(request.context == self.context, 'Optimizer context differs')
        return self.recovery.generate(request)

    def execute_batch(self, execution):
        self.recovery.validate()
        require(self.stage_directory is not None, 'Unbound native rollout directory')
        require(execution.context == self.context, 'Actor context differs')
        requests = execution.requests
        skill = requests[0].skill
        require(isinstance(skill, str) and all(r.skill == skill and r.split == 'train'
                and r.seed == 42 and r.case.case_id in self.dataset.splits['train']
                for r in requests), 'Optimization batch differs or contains Test')
        for request in requests:
            case = self.dataset.case(request.case.case_id)
            require(p.equal(request.metadata['messages'], p.messages(case.payload, skill))
                    and request.metadata['correct_label'] == case.reference['label'],
                    'Native request differs from shared Actor')
        root = self.stage_directory
        role = 'candidate' if root.name == 'validation_candidate' else 'parent'
        config = {'split': 'train', 'role': role}
        tasks = [r.case.case_id for r in requests]
        key = self.recovery.rollout_key(root)
        self.recovery.register('rollouts', key, {'tasks': tasks, 'skill': skill, 'config': config})
        root.mkdir(parents=True, exist_ok=True)
        skill_path = root / 'skill.md'
        if skill_path.exists():
            require(skill_path.read_text() == skill, 'Archived Skill differs')
        else:
            skill_path.write_text(skill)
        records = self.actor.actor_batch(tasks, skill_path, root / 'actor', config)
        self.recovery.complete('rollouts', key, records)
        output = []
        for request, record in zip(requests, records):
            e = record['execution']
            # Only ordinary assistant content crosses the optimizer boundary.
            usage = {k: sum(u[k] for u in e['usage_records'])
                     if all(u[k] is not None for u in e['usage_records']) else None
                     for k in ('input_tokens', 'output_tokens', 'total_tokens', 'reasoning_tokens')}
            usage['requests'] = e['api_requests']
            output.append(RawRollout(request.case.case_id, {
                'response': e['content'], 'n_turns': 1, 'usage': usage,
                'messages': e['initial_messages'] + [{'role': 'assistant', 'content': e['content']}],
                'request_metadata': request.metadata}))
        return tuple(output)


class Runner(SkillAdamRunner):
    @property
    def _prompts(self):
        context = super()._prompts
        # Both iteration and Momentum templates read this vendor prompt.
        return replace(context, stage0=replace(context.stage0,
            vendor_prompt=p.VENDOR_PROMPT.format(skill_section='').strip()))

    def run(self, *, cases, initial_skill=None, resume=False):
        from skilladam.core.feedback_loop import CheckpointStore, FeedbackLoop, _LoopState
        from skilladam.methods.skilladam import _SerializableAdapterGate, _skill_hash, _skill_text
        require(initial_skill is not None, 'Shared initial Skill is required; Stage0 is disabled')
        self._validate_cases(cases)
        initial_skill = _skill_text(initial_skill)
        recovery = self.backend.recovery
        require(self.output_dir.parent == recovery.root.parent, 'Recovery and native run roots differ')
        with locked(recovery.root):
            identity = recovery.root / 'run.json'
            signature = {'version': 1, 'native': self.config.to_dict(),
                         'backend': self.backend.public_metadata(), 'initial_skill': initial_skill,
                         'cases': [c.case_id for c in cases]}
            if not resume:
                require(not identity.exists() and not (self.output_dir.exists() and any(self.output_dir.iterdir())),
                        'Existing native run requires resume')
            freeze(identity, signature, read_only=resume and identity.exists())
            # Check every registered stage, even when native resume skips Actor execution.
            recovery.validate()
            checkpoint = CheckpointStore(self.output_dir)
            if not checkpoint.exists:
                require(not (self.output_dir.exists() and any(self.output_dir.iterdir()))
                        and not recovery.index('rollouts') and not recovery.index('generations'),
                        'Missing checkpoint for a started run')
                self.output_dir.mkdir(parents=True, exist_ok=True)
                gate = _SerializableAdapterGate(adapter=self.adapter, benchmark=self.config.benchmark,
                    scope=self.config.scope, profile=self.config.gate_profile)
                loop = FeedbackLoop(self.config.feedback_loop, gate=gate, checkpoint_store=checkpoint,
                                    momentum=self.momentum)
                hook = self._post_decision_hook(_skill_hash(initial_skill))
                # Use the native serializer and signature; save before any external work.
                loop._save_state(_LoopState(current_skill=initial_skill), run_signature=loop._run_signature(hook))
            self._check_dependencies(checkpoint.load_payload())
            return super().run(cases=cases, initial_skill=initial_skill, resume=True)

    def _check_dependencies(self, checkpoint):
        rollouts = self.backend.recovery.index('rollouts')
        generations = self.backend.recovery.index('generations')
        required = set()
        for record in checkpoint['iterations']:
            prefix = f"iter_{record['iteration']:03d}/"
            required.update(prefix + label for label in ('training', 'validation_parent'))
            if record['patch_mode'] != 'failed':
                required.add(prefix + 'validation_candidate')
            pending = checkpoint['pending_post_decision']
            if pending is None or pending['iteration'] != record['iteration'] or pending['generation'] is not None:
                entry = generations.get(prefix + 'momentum_update_00')
                require(entry is not None and entry['completion'] is not None,
                        'Missing completed Momentum response required by native state')
        # A partial iteration can have derived artifacts before its checkpoint advances.
        for folder in (self.output_dir / 'iterations').glob('iter_*'):
            for name, label in (('training_evaluation.json', 'training'),
                                ('training_trajectories.json', 'training'),
                                ('validation_baseline_evaluation.json', 'validation_parent'),
                                ('validation_candidate_evaluation.json', 'validation_candidate')):
                if (folder / name).exists():
                    required.add(folder.name + '/' + label)
            for path in folder.glob('patch_attempt_*.json'):
                attempt = path.stem.split('_')[2]
                key = folder.name + '/iteration_patch_' + attempt
                entry = generations.get(key)
                require(entry is not None and entry['completion'] is not None,
                        'Missing optimizer receipt for native patch artifact')
        for key in required:
            require(key in rollouts and rollouts[key]['completion'] is not None,
                    'Missing completed Actor stage required by native state')

    def _generate(self, *, stage, messages, metadata):
        self._usage_key = f"iter_{metadata['iteration']:03d}/{stage}_{metadata.get('patch_attempt', 0):02d}"
        return super()._generate(stage=stage, messages=messages, metadata=metadata)

    def _record_usage(self, records, *, stage):
        from skilladam.cost.ledger import UsageLedgerEntry
        rows = [UsageLedgerEntry(method='skilladam', benchmark=self.config.benchmark, stage=stage,
                model=self.context.model, usage=u).to_dict() for u in records]
        self.backend.recovery.record_usage(self._usage_key, rows, self.output_dir / 'usage.jsonl')

    def _evaluate_skill(self, skill, cases, *, stage):
        require(self._active_iteration is not None, 'Missing native iteration')
        if stage == 'training_rollout':
            label = 'training'
        else:
            require(stage == 'validation_rollout', 'Unexpected Actor stage')
            index = self._validation_rollout_counts.get(self._active_iteration, 0)
            require(index in (0, 1), 'Unexpected validation call count')
            label = ('validation_parent', 'validation_candidate')[index]
        self.backend.stage_directory = self.backend.output_dir / f'iter_{self._active_iteration:03d}' / label
        self._usage_key = f'iter_{self._active_iteration:03d}/{label}'
        try:
            return super()._evaluate_skill(skill, cases, stage=stage)
        finally:
            self.backend.stage_directory = None


def generation_transport(cfg, dataset, context, output_dir, *, environ, client_factory=None):
    from skilladam.backends.openai_compatible import OpenAICompatibleConfig, create_generation_transport
    options = cfg['optimizer']
    backend_cfg = OpenAICompatibleConfig.from_mapping(options['backend_config'])
    require(environ.get(backend_cfg.base_url_env, '').rstrip('/') == options['base_url'],
            'Configured provider endpoint differs from environment')

    def factory(**kwargs):
        if client_factory is None:
            from openai import OpenAI
            client = OpenAI(**kwargs)
        else:
            client = client_factory(**kwargs)
        create = client.chat.completions.create

        def thinking_create(**payload):
            extra = dict(payload.pop('extra_body', {}))
            extra['thinking'] = options['thinking']
            return create(**payload, extra_body=extra)

        client.chat.completions.create = thinking_create
        return client

    return create_generation_transport(BackendInit(dataset.root, output_dir,
        options['backend_config'], context), config=backend_cfg,
        environ=environ, client_factory=factory)


def run(config_path, output_dir, *, resume=False):
    import os
    import sys
    from dotenv import load_dotenv
    require(Path(sys.prefix).name == 'LiveMathematicianBench', 'Use the independent LMB environment')
    cfg, dataset, initial, native, context, snapshot = prepare(config_path)
    root = Path(output_dir).resolve()
    allowed = ROOT / 'experiments/baselines/lmb_skilladam'
    require(root.is_relative_to(allowed) and root != allowed, 'Use a dedicated LMB SkillAdam run directory')
    load_dotenv(ROOT / '.env', override=False)
    with locked(root):
        if not resume:
            require(not (root / 'frozen.json').exists(), 'Existing run requires --resume')
        else:
            require((root / 'frozen.json').is_file(), 'No run to resume')
        freeze(root / 'frozen.json', snapshot)
        generation = generation_transport(cfg, dataset, context, root / 'native', environ=os.environ)
        key = os.environ[cfg['optimizer']['backend_config']['api_key_env']]
        backend = Backend(dataset, ChatTransport(key), generation, context, root / 'rollouts', snapshot)
        runner = Runner(config=native, adapter=NativeAdapter(dataset.root), backend=backend,
                        context=context, output_dir=root / 'native')
        return runner.run(cases=native_cases(dataset), initial_skill=initial, resume=resume)

"""Native SkillAdam optimizer, with v28's immutable SearchQA data and Actor.

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

from skilladam.benchmarks.searchqa.adapter import SearchQAAdapter as UpstreamAdapter
from skilladam.core.feedback_loop import EditBudgetConfig, FeedbackLoopConfig
from skilladam.execution.contracts import BackendContext, BackendInit, RawRollout
from skilladam.methods.skilladam import SkillAdamRunConfig, SkillAdamRunner
from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
from src.skill_evolution.v28.benchmarks.searchqa.actor import ChatTransport, locked
from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
from src.skill_evolution.v28.benchmarks.searchqa.protocol import require
from src.skill_evolution.v28.stages import freeze
from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
from .recovery import Recovery

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / 'experiments/configs/searchqa_skilladam600_epoch1_deepseek_flash.json'


class Batch60ActorAdapter(SearchQAActorAdapter):
    """Keep the shared Actor protocol with the batch-60 experiment's concurrency."""
    def __init__(self, dataset, transport=None):
        super().__init__(dataset, transport)
        p.require(dataset.batch_size == 60, '60 workers require the batch-60 profile')
        self.workers = 60

    def _preflight(self):
        super()._preflight()
        p.require(self.workers == 60 and self.test_workers == 15,
                  'Batch-60 Train/Test workers must remain 60/15')


def actor_adapter(dataset, transport, *, workers=15, test_workers=15):
    if workers == 60 and test_workers == 15:
        return Batch60ActorAdapter(dataset, transport)
    return SearchQAActorAdapter(dataset, transport, workers=workers, test_workers=test_workers)


class NativeAdapter(UpstreamAdapter):
    """Native SearchQA scoring; the executable Actor messages are exactly v28's."""
    def build_rollout_request(self, case, *, method, split, skill, seed):
        request = super().build_rollout_request(case, method=method, split=split, skill=skill, seed=seed)
        metadata = dict(request.metadata)
        metadata['messages'] = tuple(p.messages(case.payload, skill))
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
    return tuple(dataset.case(uid) for uid in dataset.splits[split])


def prepare(config_path=DEFAULT_CONFIG):
    """Read-only preflight: no credentials, providers, output directories or calls."""
    cfg = read(config_path)
    reference = read(ROOT / cfg['v28_config'])
    batch_size = cfg['native']['train_size']
    require(cfg['actor'] == reference['actor'] == p.actor_config(batch_size), 'Actor differs from v28')
    require(cfg['workers'] == (60 if batch_size == 60 else 15) and cfg['test_workers'] == 15,
            'Worker limits differ from the selected batch profile')
    dataset = SearchQADataset(ROOT / cfg['data_root'], batch_size=batch_size)
    # Compare shared experimental conditions only. v28's module Prompts,
    # Replay/Memory contracts, Gate and method budgets do not govern SkillAdam.
    require(reference['optimization_splits'] == ['train'] and
            reference['optimization_pool'] == dataset.optimization_pool, 'Optimization pool differs from v28')
    initial = (ROOT / cfg['initial_skill']).read_text()
    require(initial == reference['initial_skill']['text'], 'Initial Skill differs from v28')
    require(cfg['stage0'] == 'disabled_use_v28_initial_skill', 'Stage0 must remain disabled')
    source_lock = read(Path(__file__).with_name('source_lock.json'))
    for relative, expected in source_lock['sha256'].items():
        require(p.file_digest(ROOT / relative) == expected, f'Frozen upstream source changed: {relative}')
    value = deepcopy(cfg['native'])
    value['optimization_case_ids'] = dataset.splits['train']
    native = native_config(value)
    official = read(ROOT / 'external/SkillAdam/skilladam/experiments/main_results.json')['benchmarks']['searchqa']['skilladam']
    for field in ('seed', 'prompt_profile', 'trajectory_compression', 'optimizer_context_limit',
                  'sampling_strategy', 'shuffle_optimization_pool', 'include_partial_final_batch'):
        require(getattr(native, field) == official[field], f'Native profile differs: {field}')
    require(native.benchmark == 'searchqa' and native.split == native.validation_split == 'train'
            and native.scope is None and native.validation_mode == 'same_batch'
            and native.train_size == native.validation_size == batch_size
            and native.stage0_size == batch_size
            and native.gate_profile == 'main-result' and native.optimizer_history_turns is None,
            'Native SearchQA pool or Gate differs')
    for field in ('max_iterations', 'min_iterations', 'max_consecutive_failures'):
        expected = 600 // batch_size if batch_size in (30, 60) and field != 'max_consecutive_failures' else official[field]
        require(getattr(native.feedback_loop, field) == expected, f'Native stopping differs: {field}')
    require(native.feedback_loop.patch_attempts == 3, 'Native patch attempts differ')
    budget = native.feedback_loop.edit_budget
    for field in ('base', 'minimum', 'beta', 'v_max'):
        require(getattr(budget, field) == official['adaptive_edit_budget'][field], f'Native budget differs: {field}')
    require(budget.metric_key == official['adaptive_edit_budget']['metric'], 'Native edit metric differs')
    options = cfg['optimizer']
    context = BackendContext('searchqa', 'skilladam', options['model'],
                             options['reasoning_effort'], cfg['workers'], native.seed)
    require(options['model'] == p.ACTOR['model'] and options['reasoning_effort'] == official['reasoning_effort'],
            'Optimizer model/reasoning differs')
    expected_backend = {'api_key_env': 'OPENAI_API_KEY', 'base_url_env': 'OPENAI_BASE_URL',
        'timeout_seconds': 600, 'max_retries': 2, 'max_completion_tokens': 32768 if batch_size in (30, 60) else 16384,
        'token_limit_field': 'max_tokens', 'temperature': 1.0, 'reasoning_mode': 'top_level'}
    require(options['base_url'] == 'https://api.deepseek.com' and options['thinking'] == p.ACTOR['thinking']
            and options['backend_config'] == expected_backend, 'Frozen optimizer transport settings differ')
    if batch_size in (30, 60):
        require(options.get('stage_max_tokens') == {'iteration_patch': 32768, 'momentum_update': 65536},
                'Optimizer stage budgets differ')
        require(options.get('record_raw_responses') is True, 'Optimizer raw recording must be enabled')
    else:
        require('stage_max_tokens' not in options and 'record_raw_responses' not in options,
                'Legacy optimizer profile must remain unchanged')
    adapter = NativeAdapter(dataset.root)
    cases = native_cases(dataset)
    runner = SkillAdamRunner(config=native, adapter=adapter, backend=None,
                            context=context, output_dir=Path('/unused-preflight'))
    runner._validate_cases(cases)
    schedule = list(runner._build_sampler(cases))
    batches = [list(b.training_case_ids) for b in schedule]
    require(batches == reference['batches'] == dataset.batches
            and all(b.training_case_ids == b.validation_case_ids for b in schedule), 'Native schedule differs from v28')
    for split in ('train', 'test'):
        for case in native_cases(dataset, split):
            request = adapter.build_rollout_request(case, method='skilladam', split=split, skill=initial, seed=42)
            require(p.equal(request.metadata['messages'], p.messages(case.payload, initial)), 'Actor prompt differs')
    source_paths = []
    for folder in ('src/adapters/searchqa', 'src/skill_evolution/v28', 'src/skill_evolution/v27', 'external/SkillAdam/skilladam'):
        source_paths.extend(q for q in (ROOT / folder).rglob('*')
                            if q.suffix in ('.py', '.md', '.json') and q.is_file())
    source_paths += [ROOT / 'scripts/runs/run_searchqa_skilladam.py', ROOT / cfg['v28_config'],
                     ROOT / 'benchmarks/searchqa/skilladam.requirements.lock.txt']
    snapshot = {'config': cfg, 'native': native.to_dict(), 'data': dataset.snapshot(),
                'initial_skill': initial, 'batches': batches,
                'sources': {str(q.relative_to(ROOT)): hashlib.sha256(q.read_bytes()).hexdigest()
                            for q in sorted(source_paths)}}
    return cfg, dataset, initial, native, context, snapshot


class Backend:
    def __init__(self, dataset, actor_transport, generation, context, output_dir, snapshot):
        self.dataset = dataset
        cfg = snapshot.get('config', {})
        self.actor = actor_adapter(dataset, actor_transport, workers=cfg.get('workers', 15),
                                   test_workers=cfg.get('test_workers', 15))
        self.generation = generation
        self.context = context
        self.output_dir = Path(output_dir)
        self.snapshot = snapshot
        self.stage_directory = None
        self.recovery = Recovery(self)

    def public_metadata(self):
        return {'kind': 'searchqa_v28_actor_native_skilladam', 'snapshot_sha256': p.digest(self.snapshot)}

    def generate(self, request):
        require(request.context == self.context, 'Optimizer context differs')
        return self.recovery.generate(request)

    def execute_batch(self, execution):
        self.recovery.validate()
        require(self.stage_directory is not None, 'Unbound native rollout directory')
        require(execution.context == self.context, 'Actor context differs')
        requests = execution.requests
        require(bool(requests), 'Empty optimization batch')
        skill = requests[0].skill
        require(isinstance(skill, str) and all(r.skill == skill and r.split == 'train'
                and r.seed == 42 and r.case.case_id in self.dataset.splits['train']
                for r in requests), 'Optimization batch differs or contains Test')
        for request in requests:
            case = self.dataset.case(request.case.case_id)
            require(p.equal(request.metadata['messages'], p.messages(case.payload, skill))
                    and p.equal(request.case.payload, case.payload)
                    and p.equal(request.case.reference, case.reference),
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
    def _condense(self, case, evaluated, *, allow_llm=False):
        if self.config.train_size != 60:
            return super()._condense(case, evaluated, allow_llm=allow_llm)
        require(case.metadata['split'] == 'train', 'SearchQA optimizer evidence requires a training case')
        trace = super()._condense(case, evaluated, allow_llm=allow_llm)
        evidence = {'initial': {'task': {'context': case.payload['context']}},
                    'outcome': {'reference_answers': case.reference}}
        return replace(trace, markdown=trace.markdown + '\n\n## Training evidence\n\n'
                       + json.dumps(evidence, ensure_ascii=False))

    def _generate_momentum(self, context):
        from .runtime import restore_problem_order
        key = f'iter_{context.record.iteration:03d}/momentum_update_00'
        entry = self.backend.recovery.index('generations').get(key)
        if entry is not None:
            messages = entry['signature']['messages']
            require(len(messages) == 2 and messages[1]['role'] == 'user', 'Unexpected archived Momentum messages')
            restore_problem_order(self.momentum, messages[1]['content'])
        return super()._generate_momentum(context)

    @property
    def _prompts(self):
        context = super()._prompts
        # Both iteration and Momentum templates read this vendor prompt.
        return replace(context, stage0=replace(context.stage0,
            vendor_prompt=p.actor_base_protocol().strip()))

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
        if options.get('record_raw_responses'):
            from .runtime import attach_recorder
            attach_recorder(client, Path(output_dir) / 'raw_optimizer')
        return client

    transport = create_generation_transport(BackendInit(dataset.root, output_dir,
        options['backend_config'], context), config=backend_cfg,
        environ=environ, client_factory=factory)
    if 'stage_max_tokens' in options:
        from .runtime import StageBudgets
        transport = StageBudgets(transport, options['stage_max_tokens'])
    return transport


def run(config_path, output_dir, *, resume=False):
    import os
    import sys
    require(Path(sys.prefix).name == 'SearchQA', 'Use the independent SearchQA environment')
    cfg, dataset, initial, native, context, snapshot = prepare(config_path)
    root = Path(output_dir).resolve()
    allowed = ROOT / 'experiments/baselines/searchqa_skilladam'
    require(root.is_relative_to(allowed) and root != allowed, 'Use a dedicated SearchQA SkillAdam run directory')
    with locked(root):
        if not resume:
            require(not (root / 'frozen.json').exists(), 'Existing run requires --resume')
        else:
            require((root / 'frozen.json').is_file(), 'No run to resume')
        freeze(root / 'frozen.json', snapshot)
        generation = generation_transport(cfg, dataset, context, root / 'native',
            environ={**os.environ, 'OPENAI_BASE_URL': cfg['optimizer']['base_url']})
        key = os.environ[cfg['optimizer']['backend_config']['api_key_env']]
        backend = Backend(dataset, ChatTransport(key, metadata=cfg['actor']), generation, context, root / 'rollouts', snapshot)
        runner = Runner(config=native, adapter=NativeAdapter(dataset.root), backend=backend,
                        context=context, output_dir=root / 'native')
        return runner.run(cases=native_cases(dataset), initial_skill=initial, resume=resume)

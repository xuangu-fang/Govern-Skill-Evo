"""Native optimizers with an explicit shared OfficeQA Actor boundary.

No provider is constructed by preflight. Optimizer sampling, prompts, retries,
gates and checkpoints remain native; only Actor routing and Test are replaced.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
import shlex
from pathlib import Path

from skilladam.core.feedback_loop import EditBudgetConfig, FeedbackLoopConfig
from skilladam.execution.contracts import BackendContext, BackendInit
from skilladam.methods.skilladam import SkillAdamRunConfig, SkillAdamRunner
from skillopt.config import flatten_config, load_config

from .bridges import SkillAdamAdapter, SkillAdamBackend, SkillOptAdapter
from src.skill_evolution.v26.benchmarks.officeqa.task_budget import TaskBudgetRuntime
from .data import Dataset
from .execution import WORKERS, _locked, atomic_json
from .runtime import Runtime
from .transport import ChatTransport
from src.skill_evolution.v26.evaluation import ArchiveTransport
from src.skill_evolution.v26.training import OptimizationDataset
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter, SkillAdamEvidenceAdapter

ROOT = Path(__file__).resolve().parents[3]
INITIAL = ROOT / 'experiments/configs/v26_officeqa_initial_skill.md'
ARMS = ('no_skill', 'initial_skill', 'v26', 'skillopt', 'skilladam')


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class TrainingSkillOptAdapter(SkillOptAdapter):
    """Keep native analyst configuration and OfficeQA prompt overrides."""
    def __init__(self, dataset, runtime, transport, *, native_root, cfg):
        overrides = {uid: transport.with_output_limit(limit)
                     for uid, limit in cfg.get('actor_task_output_limits', {}).items()}
        if overrides:
            runtime = TaskBudgetRuntime(runtime, overrides)
        super().__init__(dataset, runtime, transport, workers=cfg['workers'])
        self.native_root = Path(native_root).resolve()
        self.dataloader.seed = cfg['seed']
        self.selection_ids = dataset.splits['validation'][:cfg['sel_env_num'] or None]
        for key in ('analyst_workers', 'failure_only', 'minibatch_size', 'edit_budget'):
            setattr(self, key, cfg[key])

    @property
    def _env_name(self):
        return 'officeqa'

    def rollout(self, env_manager, skill_content, out_dir, **kwargs):
        directory = Path(out_dir).resolve()
        require(directory.is_relative_to(self.native_root) and directory != self.native_root,
                'SkillOpt rollout must have a native step/stage directory')
        items = list(env_manager)
        require(all(str(row['id']) not in self.dataset.splits['test'] for row in items),
                'Final Test must use evaluate, never the optimizer')
        require(not kwargs.get('diagnostic_mode'), 'Diagnostic Actor interventions are not enabled')
        ids = [row['id'] for row in items]
        if directory.name in ('selection_eval_baseline', 'selection_eval', 'final_selection_eval'):
            require(ids == self.selection_ids, 'SkillOpt Selection must cover its fixed validation IDs')
        else:
            require(set(ids) <= set(self.dataset.splits['train']), 'Only Train cases may generate SkillOpt updates')
        rows = super().rollout(items, skill_content, directory, **kwargs)
        require(sorted(row['id'] for row in rows) == sorted(ids), 'Incomplete SkillOpt Actor batch')
        # The common Actor archives its full audit locally. Native reflection uses
        # the rendered input, ordered tool observations and post-execution scores.
        for row in rows:
            del row['ground_truth'], row['aligned_record']
        return rows


class TrainingSkillAdamBackend(SkillAdamBackend):
    """Actor context and optimizer context may use different models/budgets."""
    def __init__(self, *args, optimizer_context, **kwargs):
        super().__init__(*args, **kwargs)
        self.optimizer_context = optimizer_context
        self.stage_directory = None

    def execute_batch(self, execution, *, out_dir=None):
        require(self.stage_directory is not None and out_dir is None,
                'SkillAdam Actor requires an explicitly bound iteration/stage')
        require(all(r.case.case_id not in self.dataset.splits['test'] for r in execution.requests),
                'Final Test must use evaluate, never the optimizer')
        return super().execute_batch(execution, out_dir=self.stage_directory)

    def generate(self, request):
        return super().generate(replace(request, context=self.optimizer_context))


class TrainingSkillAdamRunner(SkillAdamRunner):
    """Route only the native rollout hook; leave all optimizer hooks inherited."""
    def _evaluate_skill(self, skill, cases, *, stage):
        iteration = self._active_iteration
        require(iteration is not None, 'Missing native iteration')
        if stage == 'training_rollout':
            label = 'training'
        else:
            require(stage == 'validation_rollout', 'Unexpected native Actor stage')
            index = self._validation_rollout_counts.get(iteration, 0)
            require(index in (0, 1), 'Unexpected validation rollout count')
            label = ('validation_parent', 'validation_candidate')[index]
        self.backend.stage_directory = self.backend.output_dir / f'iter_{iteration:03d}' / label
        try:
            return super()._evaluate_skill(skill, cases, stage=stage)
        finally:
            self.backend.stage_directory = None


def adam_config(value):
    value = deepcopy(value)
    loop = value.pop('feedback_loop')
    if loop.get('edit_budget') is not None:
        loop['edit_budget'] = EditBudgetConfig(**loop['edit_budget'])
    for key in ('optimization_case_ids', 'stage0_case_ids'):
        if key in value:
            value[key] = tuple(value[key])
    return SkillAdamRunConfig(**value, feedback_loop=FeedbackLoopConfig(**loop))


def _fixed(value, fixed):
    for key, expected in fixed.items():
        require(key not in value or value[key] == expected, f'Launcher requires {key}={expected!r}')
    return {**value, **fixed}


def _safe_config(value):
    # Credentials are environment references, never serialized values.
    if isinstance(value, dict):
        for key, item in value.items():
            require(not (key.endswith('api_key') and item), 'Use credential environment names, not secret values')
            _safe_config(item)
    elif isinstance(value, list):
        for item in value:
            _safe_config(item)


def prepare(config, directory, *, transport=None):
    """Resolve and validate a recipe without requests or output mutations."""
    config = deepcopy(config); _safe_config(config)
    require(config['method'] in ('skillopt', 'skilladam'), 'Unknown training method')
    if config['method'] == 'skilladam':
        workers = config.get('workers', SkillAdamEvidenceAdapter.train_workers)
        require(type(workers) is int and workers in (WORKERS, SkillAdamEvidenceAdapter.train_workers),
                'SkillAdam training requires 10 workers (4 for legacy recipes)')
    else:
        workers = config.get('workers', WORKERS)
        require(type(workers) is int and workers in (4, 10), 'Unsupported SkillOpt training workers')
    root = Path(directory).resolve()
    initial_path = Path(config.get('initial_skill', INITIAL)).resolve()
    initial = initial_path.read_text()
    require(initial == INITIAL.read_text(), 'OfficeQA starts from the selected SkillOpt initial Skill')
    actor = read(config['actor_config'])
    if transport is None:
        require(actor['transport'] == 'direct_http', 'Production Actor requires direct HTTP')
        # Constructor validates metadata, but makes no request or SDK client.
        validated = ChatTransport(endpoint=actor['endpoint'], api_key='preflight-only',
            **{key: actor[key] for key in ('model', 'max_completion_tokens', 'temperature',
                'reasoning_effort', 'reasoning_mode', 'token_limit_field')})
        require(validated.metadata() == actor, 'Actor metadata differs from the common policy')
        transport = ArchiveTransport(actor)
    require(transport.metadata() == actor, 'Actor configuration mismatch')
    dataset = (Dataset if config['method'] == 'skillopt' else OptimizationDataset)(config['prepared_root'])
    runtime = Runtime(config['parsed_root'])
    for protected in (dataset.root, runtime.parsed_root, initial_path.parent, ROOT / 'src', ROOT / 'external'):
        require(not root.is_relative_to(protected) and not protected.is_relative_to(root),
                'Training output overlaps data, sources or initial Skill')
    optimizer = config['optimizer']
    require(bool(optimizer['model']), 'Explicit optimizer model required')
    require(bool(optimizer['base_url']), 'Explicit optimizer base_url required for reproducible resume')
    native = deepcopy(config['native'])
    if config['method'] == 'skillopt':
        fixed = {'env': 'officeqa', 'workers': workers, 'eval_test': False,
                 'model_backend': 'openai_compatible', 'optimizer_backend': 'openai_compatible',
                 'target_backend': 'openai_compatible', 'optimizer_model': optimizer['model'],
                 'target_model': actor['model'], 'skill_init': str(root / 'initial_skill.md'),
                 'out_root': str(root / 'native'), 'split_dir': str(dataset.root),
                 'split_mode': 'split_dir', 'limit': 0, 'train_size': len(dataset.splits['train']),
                 'max_tool_turns': 24, 'max_completion_tokens': actor['max_completion_tokens']}
        if 'actor_task_output_limits' in config:
            limits = config['actor_task_output_limits']
            require(isinstance(limits, dict) and all(uid in dataset.splits['train'] and
                    type(n) is int and n > 0 for uid, n in limits.items()), 'Invalid training task limits')
            fixed['actor_task_output_limits'] = limits
        if 'test_workers' in config or 'test_task_output_limits' in config:
            require(config.get('test_workers') in (4, 20), 'Unsupported SkillOpt test workers')
            limits = config['test_task_output_limits']
            require(isinstance(limits, dict) and all(uid in dataset.splits['test'] and
                    type(n) is int and n > 0 for uid, n in limits.items()), 'Invalid test task limits')
        defaults = flatten_config(load_config(str(ROOT / 'external/SkillOpt/configs/officeqa/default.yaml')))
        native = {**defaults, **_fixed(native, fixed)}
        require(all(type(native[k]) is int and native[k] > 0 for k in ('num_epochs', 'batch_size')),
                'Fill positive integer num_epochs and batch_size before training')
        for key in ('api_key_env', 'base_url', 'max_tokens', 'timeout_seconds', 'temperature'):
            require(key in optimizer, f'Missing SkillOpt optimizer {key}')
        require(type(optimizer['max_tokens']) is int and optimizer['max_tokens'] > 0,
                'Fill optimizer max_tokens before training')
    else:
        native = _fixed(native, {'benchmark': 'officeqa', 'split': 'train',
                                'validation_split': 'train', 'scope': None})
        require(all(type(native.get(k)) is int and native[k] > 0 for k in ('train_size', 'validation_size'))
                and type(native['feedback_loop'].get('max_iterations')) is int,
                'Fill train_size, validation_size and max_iterations before training')
        native.setdefault('stage0_size', native['train_size'])  # Native schema only; Stage0 never called.
        resolved = adam_config(native)
        from skilladam.cli import _validate_skilladam_pool
        _validate_skilladam_pool(resolved, dataset.cases('train'))
        native = resolved.to_dict()
        from skilladam.backends.openai_compatible import OpenAICompatibleConfig
        OpenAICompatibleConfig.from_mapping(optimizer['backend_config'])
    ids = dataset.splits['train'] + dataset.splits['validation']
    adapter_type = SkillAdamEvidenceAdapter if workers != WORKERS or config['method'] == 'skilladam' else OfficeQAEvidenceAdapter
    evidence = adapter_type(dataset, runtime, transport, workers=workers)
    snapshot = evidence.runtime_snapshot({'batches': [ids]})
    source_files = [p for base in (ROOT / 'src/adapters/officeqa', ROOT / 'src/skill_evolution/v26',
                                   ROOT / 'external/SkillOpt/skillopt',
                                   ROOT / 'external/SkillOpt/configs', ROOT / 'external/SkillAdam/skilladam')
                    for p in base.rglob('*') if p.is_file() and p.suffix in ('.py', '.md', '.yaml', '.json')]
    source_files.append(ROOT / 'scripts/runs/run_officeqa_baselines.py')
    import skillopt, skilladam
    installed = {}
    for package, repository in ((skillopt, 'SkillOpt'), (skilladam, 'SkillAdam')):
        package_root = Path(package.__file__).resolve().parent
        checkout = ROOT / 'external' / repository / package.__name__
        for path in checkout.rglob('*'):
            if path.is_file() and path.suffix in ('.py', '.md', '.json'):
                actual = package_root / path.relative_to(checkout)
                require(actual.is_file() and digest(actual) == digest(path),
                        f'Installed native package differs from checked-out source: {path}')
        installed[package.__name__] = {'root': str(package_root), 'files': {
            str(p.relative_to(package_root)): digest(p) for p in sorted(package_root.rglob('*'))
            if p.is_file() and p.suffix in ('.py', '.md', '.json')}}
    plan = {'schema': 'officeqa_native_training_v1', 'config': config, 'directory': str(root),
            'method': config['method'], 'workers': workers, 'native_config': native,
            'initial_skill_sha256': digest(initial_path), 'actor': actor, 'runtime': snapshot,
            'sources': {str(p.relative_to(ROOT)): digest(p) for p in sorted(source_files)},
            'installed_native_sources': installed,
            'train_ids': dataset.splits['train'], 'selection_ids': dataset.splits['validation'],
            'test_during_training': False, 'final_test_entry': ('src.skill_evolution.v26.cli evaluate --workers 20'
                if config['method'] == 'skilladam' else 'src.skill_evolution.v26.cli evaluate'),
            'stage0': False}
    if config['method'] == 'skillopt':
        from .skillopt_budget import ATTEMPTS, CAP_MULTIPLIER, LENGTHS_BEFORE_INCREASE
        plan['optimizer_retry'] = {'max_attempts_total': ATTEMPTS, 'lengths_before_increase': LENGTHS_BEFORE_INCREASE,
                                   'cap_multiplier': CAP_MULTIPLIER, 'persist_attempts_on_resume': True}
    if config['method'] == 'skillopt' and 'test_task_output_limits' in config:
        plan['final_test_entry'] = shlex.join(['scripts.runs.run_officeqa_baselines', 'evaluate',
            '--arm', 'skillopt', '--training-run', str(root), '--actor-config', config['actor_config'],
            '--prepared-root', config['prepared_root'], '--parsed-root', config['parsed_root']])
    return plan, dataset, runtime, transport, initial


def _optimizer(plan, root, context):
    cfg = plan['config']['optimizer']
    if plan['method'] == 'skilladam':
        from skilladam.backends.openai_compatible import create_generation_transport, OpenAICompatibleConfig
        backend_config = OpenAICompatibleConfig.from_mapping(cfg['backend_config'])
        environ = dict(os.environ)
        environ[backend_config.base_url_env] = cfg['base_url']
        return create_generation_transport(BackendInit(Path(plan['runtime']['parsed_root']), root / 'native',
            cfg['backend_config'], context), config=backend_config, environ=environ)
    from skillopt.model.openai_compatible_backend import configure_openai_compatible
    key = os.environ.get(cfg['api_key_env'])
    require(bool(key), 'Missing SkillOpt optimizer credential')
    # Old ALFWorld local patches read these process globals. Remove accidental
    # carry-over before binding the journaled optimizer transport.
    for prefix in ('', 'OPTIMIZER_', 'TARGET_'):
        for suffix in ('MAX_ATTEMPTS', 'CONNECT_TIMEOUT_SECONDS', 'EXTRA_BODY'):
            os.environ.pop(prefix + 'OPENAI_COMPATIBLE_' + suffix, None)
    os.environ['OPTIMIZER_OPENAI_COMPATIBLE_EXTRA_BODY'] = json.dumps(cfg.get('extra_body', {}))
    configure_openai_compatible(base_url=cfg['base_url'], api_key=key, model=cfg['model'],
        temperature=cfg['temperature'], timeout_seconds=cfg['timeout_seconds'], max_tokens=cfg['max_tokens'])


def finish_skillopt_selection(adapter, cfg, native_root):
    """Preserve the native final-Selection promotion hidden under eval_test.

    Same native score/hash functions, strict promotion and equal-Skill reuse.
    A failed Actor stops publication instead of being swallowed by native Test.
    The receipt makes promotion recoverable across its file writes.
    """
    from skillopt.engine.trainer import compute_score, select_gate_score, skill_hash
    state_path = native_root / 'runtime_state.json'
    state = read(state_path)
    current = Path(state['current_skill_path']).read_text()
    best_path = Path(state['best_skill_path'])
    best = best_path.read_text()
    receipt = native_root / 'final_selection_promotion.json'
    if receipt.exists():
        result = read(receipt)
        require(result['current_hash'] == skill_hash(current), 'Final Selection input changed')
    else:
        hard, soft, score = state['best_score'], None, state['best_score']
        if skill_hash(current) != skill_hash(best):
            env = adapter.build_eval_env(env_num=cfg['sel_env_num'], split='valid_seen',
                                         seed=cfg['seed'], out_root=str(native_root))
            rows = adapter.rollout(env, current, native_root / 'final_selection_eval')
            hard, soft = compute_score(rows)
            leading = cfg.get('leading_words')
            if isinstance(leading, str):
                leading = [w.strip() for w in leading.split(',') if w.strip()]
            score = select_gate_score(hard, soft, str(cfg.get('gate_metric', 'hard')).strip().lower(),
                float(cfg.get('gate_mixed_weight', 0.5)), skill_content=current,
                use_semantic_density=bool(cfg.get('use_semantic_density', False)),
                semantic_density_weight=float(cfg.get('semantic_density_weight', 0.05)),
                leading_words=leading)
        promoted = score > state['best_score']
        if promoted:
            best = current
            state.update(best_score=score, best_step=state['last_completed_step'],
                         best_origin=state['current_origin'])
        result = {'current_hash': skill_hash(current), 'hard': hard, 'soft': soft,
                  'promoted': promoted, 'state': state, 'selected_skill': best}
        atomic_json(receipt, result)
    best_path.write_text(result['selected_skill'])
    atomic_json(state_path, result['state'])
    summary_path = native_root / 'summary.json'
    summary = read(summary_path)
    summary.update(best_selection_hard=result['state']['best_score'], best_step=result['state']['best_step'],
                   best_origin=result['state']['best_origin'],
                   final_selection_hard=result['hard'], final_selection_soft=result['soft'])
    atomic_json(summary_path, summary)


def train(config, directory, *, actor_key_env=None, resume=False, transport=None, optimizer_backend=None):
    """Run only when explicitly invoked; test injection never reaches a provider."""
    plan, dataset, runtime, prepared_transport, initial = prepare(config, directory, transport=transport)
    root = Path(directory).resolve()
    require(resume or not root.exists() or not any(root.iterdir()), 'Existing training root requires --resume')
    require(not resume or (root / 'plan.json').is_file(), 'Missing training plan for resume')
    with _locked(root):
        if resume:
            require(read(root / 'plan.json') == plan, 'Training configuration/data/source changed on resume')
            if (root / 'initial_skill.md').exists():
                require((root / 'initial_skill.md').read_text() == initial, 'Saved initial Skill changed')
            else:
                (root / 'initial_skill.md').write_text(initial)
            if (root / 'result.json').is_file():
                result = read(root / 'result.json')
                require(digest(result['skill_file']) == result['skill_sha256'], 'Exported Skill changed')
                return result
        else:
            require(not any(p.name != '.execution.lock' for p in root.iterdir()),
                    'Training root was populated by another launcher')
            atomic_json(root / 'plan.json', plan)
            (root / 'initial_skill.md').write_text(initial)
        if transport is None:
            a = plan['actor']
            transport = ChatTransport(endpoint=a['endpoint'], api_key=os.environ.get(actor_key_env or ''),
                **{k: a[k] for k in ('model', 'max_completion_tokens', 'temperature',
                                     'reasoning_effort', 'reasoning_mode', 'token_limit_field')})
        require(transport.metadata() == prepared_transport.metadata(), 'Live Actor identity changed')
        native_root = root / 'native'
        cfg = deepcopy(plan['native_config'])
        if plan['method'] == 'skillopt':
            require(optimizer_backend is None, 'SkillOpt uses its native optimizer functions')
            _optimizer(plan, root, None)
            from skillopt.engine.trainer import ReflACTTrainer
            adapter = TrainingSkillOptAdapter(dataset, runtime, transport, native_root=native_root, cfg=cfg)
            from .skillopt_optimizer import configured_provider
            with configured_provider(native_root):
                ReflACTTrainer(cfg, adapter).train()
            finish_skillopt_selection(adapter, cfg, native_root)
            chosen = native_root / 'best_skill.md'
            selection = 'native_best_selection'
        else:
            cfg = adam_config(cfg)
            context = BackendContext('officeqa', 'skilladam', plan['actor']['model'],
                                     plan['actor']['reasoning_effort'], plan['workers'], cfg.seed)
            o = config['optimizer']
            optimizer_context = replace(context, model=o['model'], reasoning_effort=o['reasoning_effort'])
            backend = TrainingSkillAdamBackend(dataset, runtime, transport, output_dir=root / 'actor',
                workers=plan['workers'], optimizer_context=optimizer_context,
                optimizer_backend=optimizer_backend or _optimizer(plan, root, optimizer_context))
            checkpoint = native_root / 'checkpoint.json'
            native_resume = resume and checkpoint.is_file()
            if resume and native_root.exists() and not native_resume:
                # Upstream has no checkpoint before the first decision. Preserve
                # that partial archive and restart native bootstrap; Actor journals
                # live outside it, so consumed requests are NEVER reset.
                archive = root / 'bootstrap_archives'; archive.mkdir(exist_ok=True)
                index = 0
                while (archive / f'native_{index:03d}').exists():
                    index += 1
                native_root.rename(archive / f'native_{index:03d}')
            runner = TrainingSkillAdamRunner(config=cfg, adapter=SkillAdamAdapter(dataset), backend=backend,
                                            context=context, output_dir=native_root)
            runner.run(cases=dataset.cases('train'), initial_skill=initial, resume=native_resume)
            chosen = native_root / 'final_skill.md'
            selection = 'native_final_skill'
        require(chosen.is_file(), 'Native optimizer did not export its selected Skill')
        result = {'method': plan['method'], 'skill_file': str(chosen), 'skill_sha256': digest(chosen),
                  'selection': selection, 'workers': plan['workers'], 'test_executed': False,
                  'evaluate_entry': 'python -m ' + plan['final_test_entry']}
        atomic_json(root / 'result.json', result)
        return result


def evaluation_args(arm, directory, *, actor_config, prepared_root, parsed_root,
                    skill=None, training_run=None, resume=False, actor_key_env=None):
    """All five arms dispatch the *same* existing fixed-172 evaluate command."""
    require(arm in ARMS, 'Unknown evaluation arm')
    require(not (skill and training_run), 'Choose one Skill source')
    test_recipe = None
    if training_run:
        require(arm in ('skillopt', 'skilladam'), 'Training receipt is for native optimizers')
        result = read(Path(training_run) / 'result.json')
        require(result['method'] == arm and digest(result['skill_file']) == result['skill_sha256'],
                'Training receipt or selected Skill mismatch')
        plan = read(Path(training_run) / 'plan.json')
        if arm == 'skillopt' and 'test_task_output_limits' in plan['config']:
            recipe = plan['config']
            require(Path(prepared_root).resolve() == Path(plan['runtime']['prepared_root']) and
                    Path(parsed_root).resolve() == Path(plan['runtime']['parsed_root']), 'Test dataset differs')
            test_recipe = recipe
        require(read(actor_config) == plan['actor'],
                'Test Actor differs from training Actor')
        skill = result['skill_file']
    elif arm == 'skillopt' and skill is not None and not (resume and (Path(directory) / 'plan.json').is_file()):
        # A standalone Skill has no training receipt. New tests use the same
        # OfficeQA profile; resumed tests obtain their settings from the frozen plan.
        test_recipe = read(ROOT / 'experiments/configs/officeqa_skillopt_deepseek_flash.json')
    if arm == 'initial_skill':
        require(skill is None, 'Initial Skill uses the selected SkillOpt snapshot')
        skill = str(INITIAL)
    require((arm == 'no_skill' and skill is None) or (arm != 'no_skill' and skill is not None),
            'No Skill takes no file; evolved arms require --skill or --training-run')
    args = ['evaluate', str(directory), '--actor-config', str(actor_config),
            '--prepared-root', str(prepared_root), '--parsed-root', str(parsed_root)]
    if arm == 'skilladam' and not (resume and (Path(directory) / 'plan.json').is_file()):
        args += ['--workers', str(SkillAdamEvidenceAdapter.test_workers)]
    if test_recipe is not None:
        args += ['--workers', str(test_recipe['test_workers']), '--task-output-limits',
                 json.dumps(test_recipe['test_task_output_limits'])]
    args += ['--skill', str(skill)] if skill is not None else ['--no-skill']
    if resume:
        args += ['--resume']
    if actor_key_env:
        args += ['--actor-key-env', actor_key_env]
    return args

"""Native SkillAdam DocVQA optimizer with the shared v29 Actor.

Only data/request adaptation and durable I/O are local. Prompts, compression,
patches, Gate, Momentum, budgets and stopping remain in upstream SkillAdam.
"""
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path

from skilladam.benchmarks.docvqa.adapter import DocVQAAdapter
from skilladam.core.feedback_loop import EditBudgetConfig, FeedbackLoopConfig
from skilladam.execution.contracts import BackendContext, BackendInit, GenerationResult, RawRollout, ToolCall
from skilladam.methods.skilladam import SkillAdamRunConfig, SkillAdamRunner
from skilladam.types import RolloutRequest, UsageRecord
from src.skill_evolution.v29.benchmarks.docvqa import actor, protocol as p
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
from src.skill_evolution.v29.benchmarks.docvqa.scoring import summarize_scores
from src.skill_evolution.v29.storage import freeze, read, save

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / 'experiments/configs/docvqa_skilladam160_epoch1_deepseek_flash.json'


def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def freeze_text(path, text):
    path = Path(path)
    if path.exists():
        p.require(path.read_text() == text, f'Existing text differs: {path}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


class NativeAdapter(DocVQAAdapter):
    def build_rollout_request(self, case, *, method, split, skill, seed):
        p.validate_case(case)
        p.require(method == 'skilladam' and split == case.metadata['split'], 'Invalid rollout method/split')
        return RolloutRequest(case=case, method=method, split=split, skill=skill, seed=seed,
            metadata={'messages': p.messages_for_case(case, skill), 'prompt_profile': p.PROMPT_PROFILE,
                      'image_path': str(Path(case.metadata['image_root']) / case.payload['image_path']),
                      'output_protocol': 'answer-tags', 'image_detail': 'auto', 'max_turns': 1})


def native_cases(dataset, split='train'):
    return tuple(dataset.case(uid) for uid in dataset.splits[split])


def native_config(value):
    value = deepcopy(value)
    loop = value.pop('feedback_loop')
    loop['edit_budget'] = EditBudgetConfig(**loop['edit_budget'])
    value['optimization_case_ids'] = tuple(value.get('optimization_case_ids', ()))
    return SkillAdamRunConfig(**value, feedback_loop=FeedbackLoopConfig(**loop))


def prepare(config_path=DEFAULT_CONFIG):
    """Read-only: does not load credentials, instantiate clients or create outputs."""
    cfg = read(config_path)
    reference = read(ROOT / cfg['v29_config'])
    p.require(cfg['actor'] == reference['actor'] == p.actor_config(), 'Actor differs from v29')
    p.require(cfg['workers'] == cfg['test_workers'] == 60, 'Expected native workers=60')
    dataset = DocVQADataset(ROOT / cfg['data_root'])
    initial = (ROOT / cfg['initial_skill']).read_text()
    p.require(initial == reference['initial_skill'] == p.initial_skill(), 'Initial Skill differs from v29')
    p.require(cfg['stage0'] == 'disabled_use_v29_initial_skill', 'Stage0 must remain disabled')
    official = read(ROOT / 'external/SkillAdam/skilladam/experiments/main_results.json')['benchmarks']['docvqa']['skilladam']
    expected = {k: official[k] for k in ('seed', 'prompt_profile', 'trajectory_compression',
        'optimizer_context_limit', 'sampling_strategy', 'shuffle_optimization_pool', 'include_partial_final_batch')}
    expected.update(benchmark='docvqa', split='train', validation_split='train', scope=None,
        train_size=official['batch_size'], validation_size=official['batch_size'], stage0_size=15,
        validation_mode='same_batch', gate_profile='main-result', feedback_loop={
            **{k: official[k] for k in ('max_iterations', 'min_iterations', 'max_consecutive_failures')},
            'patch_attempts': 3, 'edit_budget': {('metric_key' if k == 'metric' else k): v
                for k, v in official['adaptive_edit_budget'].items()}})
    p.require(cfg['native'] == expected, 'Native DocVQA main-result settings differ')
    native = native_config({**cfg['native'], 'optimization_case_ids': dataset.splits['train']})
    options = cfg['optimizer']
    p.require(options == {'model': p.ACTOR['model'], 'base_url': 'https://api.deepseek.com',
        'reasoning_effort': 'medium', 'thinking': p.ACTOR['thinking'], 'backend_config': {
            'api_key_env': 'OPENAI_API_KEY', 'base_url_env': 'OPENAI_BASE_URL',
            'timeout_seconds': 300, 'max_retries': 2, 'max_completion_tokens': 16384,
            'token_limit_field': 'max_tokens', 'temperature': 1.0, 'reasoning_mode': 'top_level'}},
        'Optimizer settings differ from the aligned profile')
    context = BackendContext('docvqa', 'skilladam', options['model'], 'medium', cfg['workers'], native.seed)
    runner = SkillAdamRunner(config=native, adapter=NativeAdapter(dataset.root), backend=None,
                            context=context, output_dir=Path('/unused-preflight'))
    cases = native_cases(dataset)
    runner._validate_cases(cases)
    schedule = list(runner._build_sampler(cases))
    batches = [list(b.training_case_ids) for b in schedule]
    p.require(batches == reference['batches'] == dataset.batches and
        all(b.training_case_ids == b.validation_case_ids for b in schedule), 'Schedule differs from v29')
    return cfg, dataset, initial, native, context


class Backend:
    def __init__(self, dataset, actor_transport, generation, context, output_dir):
        self.dataset, self.generation, self.context = dataset, generation, context
        self.actor = DocVQAActorAdapter(dataset, actor_transport)
        self.output_dir = Path(output_dir)
        self.stage_directory = None

    def public_metadata(self):
        return {'kind': 'docvqa_v29_actor_native_skilladam', 'actor': p.actor_config()}

    def generation_path(self, request):
        return self.output_dir / 'optimizer' / f"iter_{request.metadata['iteration']:03d}" / (
            f"{request.stage}_{request.metadata.get('patch_attempt', 0):02d}.json")

    def generate(self, request):
        p.require(request.context == self.context and request.stage in ('iteration_patch', 'momentum_update'),
                  'Unexpected optimizer request')
        path = self.generation_path(request)
        signature = plain({'stage': request.stage, 'messages': request.messages,
                           'metadata': request.metadata, 'context': asdict(request.context)})
        # Request identity is saved before external work; completed generations are reusable.
        freeze(path.with_suffix('.input.json'), signature)
        if path.exists():
            value = read(path)
            return GenerationResult(value['text'], tuple(UsageRecord(**u) for u in value['usage']),
                tuple(ToolCall(c['name'], c['arguments']) for c in value['tool_calls']))
        result = self.generation.generate(request)
        freeze(path, {'text': result.text, 'usage': [asdict(u) for u in result.usage],
            'tool_calls': [{'name': c.name, 'arguments': plain(c.arguments)} for c in result.tool_calls]})
        return result

    def execute_batch(self, execution):
        p.require(self.stage_directory is not None and execution.context == self.context, 'Unbound Actor stage')
        requests = execution.requests
        skill = requests[0].skill
        p.require(isinstance(skill, str), 'Initial Skill is required')
        tasks = [r.case.case_id for r in requests]
        for r in requests:
            case = self.dataset.case(r.case.case_id)
            p.require(r.split == 'train' and r.skill == skill and r.seed == self.context.seed
                and case.metadata['split'] == 'train' and r.case == case
                and plain(r.metadata['messages']) == p.messages_for_case(case, skill),
                'Actor input differs from the shared protocol or includes Test')
        root = self.stage_directory
        role = 'candidate' if root.name == 'validation_candidate' else 'parent'
        freeze_text(root / 'skill.md', skill)
        records = self.actor.actor_batch(tasks, root / 'skill.md', root / 'actor', {'split': 'train', 'role': role})
        output = []
        for request, record in zip(requests, records):
            e = record['execution']
            usage = {k: sum(u[k] for u in e['usage_records']) if all(u[k] is not None for u in e['usage_records'])
                else None for k in ('input_tokens', 'output_tokens', 'total_tokens', 'reasoning_tokens')}
            usage['requests'] = e['api_requests']
            # Native parse_result sanitizes images; reasoning_content never crosses this boundary.
            output.append(RawRollout(request.case.case_id, {'response': e['content'], 'usage': usage,
                'image_path': request.metadata['image_path'], 'n_turns': 1,
                'messages': e['initial_messages'] + [{'role': 'assistant', 'content': e['content']}]}))
        return tuple(output)


class Runner(SkillAdamRunner):
    def _condense(self, case, evaluated, *, allow_llm=False):
        p.require(case.metadata['split'] == 'train', 'DocVQA optimizer evidence requires a training case')
        trace = super()._condense(case, evaluated, allow_llm=allow_llm)
        # Use the same dataset fields as v29.7's text-only execution facts.
        evidence = {'initial': {'task': {'image_path': case.payload['image_path']}},
                    'outcome': {'reference_answers': case.reference}}
        return replace(trace, markdown=trace.markdown + '\n\n## Training evidence\n\n'
                       + json.dumps(evidence, ensure_ascii=False))

    @property
    def _prompts(self):
        context = super()._prompts
        # Only adapt the structure contract for the shared, non-Stage0 initial Skill.
        structure = Path(__file__).with_name('skill_structure.md').read_text().strip()
        policy = structure + '\n\n### 3. Edit Balance' + context.skill_writing_policy.split(
            '### 3. Edit Balance', 1)[1]
        # Upstream optimizer templates quote the actual aligned Actor base protocol.
        return replace(context, skill_writing_policy=policy,
            stage0=replace(context.stage0, vendor_prompt=p.actor_base_protocol().strip()))

    def run(self, *, cases, initial_skill=None, resume=False):
        from skilladam.core.feedback_loop import CheckpointStore, FeedbackLoop, _LoopState
        from skilladam.methods.skilladam import _SerializableAdapterGate, _skill_hash, _skill_text
        p.require(initial_skill is not None, 'Stage0 is disabled')
        self._validate_cases(cases)
        initial_skill = _skill_text(initial_skill)
        with actor.locked(self.backend.output_dir):
            identity = self.backend.output_dir / 'run.json'
            p.require(resume == identity.exists(), 'Use resume only for an existing run')
            freeze(identity, plain({'config': self.config.to_dict(), 'context': asdict(self.context),
                'training_evidence_fields': ['initial.task.image_path', 'outcome.reference_answers'],
                'initial_skill': initial_skill, 'cases': [asdict(c) for c in cases]}))
            checkpoint = CheckpointStore(self.output_dir)
            if not checkpoint.exists:
                p.require(not self.output_dir.exists() or not any(self.output_dir.iterdir()), 'Missing native checkpoint')
                self.output_dir.mkdir(parents=True, exist_ok=True)
                gate = _SerializableAdapterGate(adapter=self.adapter, benchmark='docvqa', scope=None,
                                               profile=self.config.gate_profile)
                loop = FeedbackLoop(self.config.feedback_loop, gate=gate, checkpoint_store=checkpoint,
                                    momentum=self.momentum)
                hook = self._post_decision_hook(_skill_hash(initial_skill))
                # Native checkpoint before the first request also makes iteration zero resumable.
                loop._save_state(_LoopState(current_skill=initial_skill), run_signature=loop._run_signature(hook))
            return super().run(cases=cases, initial_skill=initial_skill, resume=True)

    def _generate_momentum(self, context):
        from src.adapters.searchqa.runtime import restore_problem_order
        path = self.backend.output_dir / 'optimizer' / f'iter_{context.record.iteration:03d}' / 'momentum_update_00.input.json'
        if path.exists():
            restore_problem_order(self.momentum, read(path)['messages'][1]['content'])
        return super()._generate_momentum(context)

    def _generate(self, *, stage, messages, metadata):
        self._usage_key = f"iter_{metadata['iteration']:03d}/{stage}_{metadata.get('patch_attempt', 0):02d}"
        return super()._generate(stage=stage, messages=messages, metadata=metadata)

    def _evaluate_skill(self, skill, cases, *, stage):
        p.require(self._active_iteration is not None, 'Missing native iteration')
        if stage == 'training_rollout':
            label = 'training'
        else:
            p.require(stage == 'validation_rollout', 'Unexpected rollout stage')
            index = self._validation_rollout_counts.get(self._active_iteration, 0)
            p.require(index in (0, 1), 'Unexpected validation count')
            label = ('validation_parent', 'validation_candidate')[index]
        self._usage_key = f'iter_{self._active_iteration:03d}/{label}'
        self.backend.stage_directory = self.backend.output_dir / 'rollouts' / self._usage_key
        try:
            return super()._evaluate_skill(skill, cases, stage=stage)
        finally:
            self.backend.stage_directory = None

    def _record_usage(self, records, *, stage):
        from skilladam.cost.ledger import UsageLedgerEntry
        path = self.backend.output_dir / 'usage_events.json'
        events = read(path) if path.exists() else {}
        rows = [UsageLedgerEntry(method='skilladam', benchmark='docvqa', stage=stage,
                model=self.context.model, usage=u).to_dict() for u in records]
        p.require(self._usage_key not in events or events[self._usage_key] == rows, 'Recovered usage differs')
        events[self._usage_key] = rows
        save(path, events)
        ledger = self.output_dir / 'usage.jsonl'
        temporary = ledger.with_suffix('.tmp')
        temporary.write_text(''.join(json.dumps(row) + '\n' for values in events.values() for row in values))
        temporary.replace(ledger)


def generation_transport(cfg, dataset, context, output_dir, *, environ, client_factory=None):
    from skilladam.backends.openai_compatible import OpenAICompatibleConfig, create_generation_transport
    options = cfg['optimizer']
    p.require(environ.get('OPENAI_BASE_URL', '').rstrip('/') == options['base_url'], 'Optimizer endpoint differs')
    def factory(**kwargs):
        import httpx
        from openai import OpenAI
        kwargs['timeout'] = httpx.Timeout(options['backend_config']['timeout_seconds'], connect=10)
        client = (client_factory or OpenAI)(**kwargs)
        create = client.chat.completions.create
        def thinking_create(**payload):
            return create(**payload, extra_body={'thinking': options['thinking']})
        client.chat.completions.create = thinking_create
        # Existing recorder stores request/response bodies, never credentials.
        from src.adapters.searchqa.runtime import attach_recorder
        return attach_recorder(client, Path(output_dir) / 'raw_optimizer')
    return create_generation_transport(BackendInit(dataset.root, output_dir, options['backend_config'], context),
        config=OpenAICompatibleConfig.from_mapping(options['backend_config']), environ=environ, client_factory=factory)


def run_training(root, prepared, *, actor_transport, generation, resume=False):
    cfg, dataset, initial, native, context = prepared
    root = Path(root).resolve()
    with actor.locked(root):
        p.require(resume == (root / 'config.json').exists(), 'Use resume only for an existing training run')
        freeze(root / 'config.json', cfg)
        backend = Backend(dataset, actor_transport, generation, context, root / 'execution')
        runner = Runner(config=native, adapter=NativeAdapter(dataset.root), backend=backend,
                        context=context, output_dir=root / 'native')
        result = runner.run(cases=native_cases(dataset), initial_skill=initial,
                            resume=(backend.output_dir / 'run.json').exists())
        p.require(len(result.feedback_loop.iterations) == native.feedback_loop.max_iterations,
                  'Training ended before all configured batches')
        freeze_text(root / 'final_skill.md', result.final_skill)
        summary = {'status': 'complete', 'iterations': len(result.feedback_loop.iterations),
            'optimization_count': len(dataset.splits['train']), 'stop_reason': result.feedback_loop.stop_reason,
            'accepted': sum(r.accepted for r in result.feedback_loop.iterations), 'test_started': False}
        freeze(root / 'training_summary.json', summary)
        return summary


def run_test(campaign, root, prepared, *, actor_transport, resume=False):
    cfg, dataset, _, native, _ = prepared
    campaign, root = Path(campaign).resolve(), Path(root).resolve()
    p.require(not root.is_relative_to(campaign) and not campaign.is_relative_to(root), 'Separate Test output required')
    summary = read(campaign / 'training_summary.json')
    state = read(campaign / 'native/checkpoint.json')
    p.require(summary['status'] == 'complete' and summary['iterations'] == native.feedback_loop.max_iterations
        and state['next_iteration'] == native.feedback_loop.max_iterations and state['pending_post_decision'] is None
        and read(campaign / 'config.json') == cfg, 'Training must complete before Test')
    skill = (campaign / 'final_skill.md').read_text()
    p.require(skill == state['current_skill'] == (campaign / 'native/final_skill.md').read_text(), 'Final Skill differs')
    with actor.locked(root):
        p.require(resume == (root / 'evaluation.json').exists(), 'Use resume only for an existing Test')
        tasks = list(dataset.splits['test'])
        freeze(root / 'evaluation.json', {'campaign': str(campaign), 'tasks': tasks, 'skill': skill,
                                        'actor': cfg['actor'], 'workers': cfg['test_workers']})
        freeze_text(root / 'skill.md', skill)
        records = DocVQAActorAdapter(dataset, actor_transport).actor_batch(tasks, root / 'skill.md', root / 'runs',
            {'split': 'test', 'role': 'evaluation'}, final=True)
        metrics = summarize_scores([{'task_id': r['task_id'], 'metrics': r['execution']['metrics']} for r in records], tasks)
        result = {'status': 'complete', **metrics, 'api_requests': sum(r['execution']['api_requests'] for r in records)}
        freeze(root / 'summary.json', result)
        return result

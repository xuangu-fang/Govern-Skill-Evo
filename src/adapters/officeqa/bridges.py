"""Explicit Actor bindings; optimization algorithms and initialization stay external."""
import json
import hashlib
from pathlib import Path

from skilladam.benchmarks.officeqa.adapter import OfficeQAAdapter as NativeAdamAdapter
from skilladam.execution.contracts import RawRollout
from skillopt.envs.officeqa.adapter import OfficeQAAdapter as NativeOptAdapter

from .data import PROFILE
from .execution import EXECUTION_CONFIG, WORKERS, atomic_json, run_batch


def save_record(directory, record):
    path = Path(directory) / 'trajectory.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != record:
            raise FileExistsError(f'Refusing to overwrite an OfficeQA trajectory: {path}')
        return path
    atomic_json(path, record)
    return path


def _batch(dataset, runtime, transport, cases, skills, directory, *, owner, workers, context=None):
    items = list(zip(cases, skills))
    identity = {'profile': PROFILE, 'method': owner, 'actor': transport.metadata(),
                'tasks': [dataset.rows[case.case_id] for case, _ in items],
                'skills': list(skills), 'context': context,
                'execution': {**EXECUTION_CONFIG, 'workers': workers}}
    return run_batch([(case.case_id, (case, skill)) for case, skill in items],
        lambda item: runtime.run(item[0], item[1], transport, owner=owner,
            directory=Path(directory) / 'cases' / hashlib.sha256(item[0].case_id.encode()).hexdigest()),
        directory, identity=identity, workers=workers)


def skillopt_conversation(messages):
    """Preserve tool arguments/observations in the native analyst file format."""
    conversation, calls = [], {}
    for message in messages:
        if message['role'] == 'system':
            continue
        if message['role'] == 'tool':
            call = calls[message['tool_call_id']]
            conversation.append({'type': 'tool_call',
                'cmd': f"{call['name']}({call['arguments']})", 'obs': message['content']})
        else:
            conversation.append({'role': message['role'], 'type': 'message', 'content': message['content'] or ''})
            calls.update({call['id']: call['function'] for call in message.get('tool_calls', [])})
    return conversation


class SkillAdamAdapter(NativeAdamAdapter):
    def __init__(self, dataset):
        super().__init__(dataset.root)
        self.dataset = dataset

    def load_cases(self, split):
        return self.dataset.cases(split)

    def build_rollout_request(self, case, **kwargs):
        if case != self.dataset.case(case.case_id):
            raise ValueError('SkillAdam case differs from the common dataset')
        return super().build_rollout_request(case, **kwargs)


class SkillAdamBackend:
    """Native execute_batch contract over the common Actor.

    Optimizer generation can be delegated explicitly by a later training
    caller; no Stage0, provider factory, or default optimizer is invoked here.
    output_dir identifies one evaluation batch. Callers must bind a separate
    directory for each iteration/stage/replicate, even when its Skill is equal.
    execute_batch(out_dir=...) can override that binding for direct callers.
    """
    def __init__(self, dataset, runtime, transport, *, output_dir, workers=WORKERS, optimizer_backend=None):
        self.dataset, self.runtime, self.transport = dataset, runtime, transport
        self.output_dir, self.workers = Path(output_dir), workers
        self.optimizer_backend = optimizer_backend

    def execute_batch(self, execution, *, out_dir=None):
        if execution.context.benchmark != 'officeqa' or execution.context.method != 'skilladam':
            raise ValueError('Unexpected SkillAdam execution context')
        if execution.context.model != self.transport.metadata()['model']:
            raise ValueError('Actor model differs from the SkillAdam context')
        ids = [request.case.case_id for request in execution.requests]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate batch cases')
        adapter = SkillAdamAdapter(self.dataset)
        for request in execution.requests:
            expected = adapter.build_rollout_request(request.case, method=request.method,
                split=request.split, skill=request.skill, seed=request.seed)
            if request != expected:
                raise ValueError('SkillAdam request bypassed the common input protocol')
        records = _batch(self.dataset, self.runtime, self.transport,
            [r.case for r in execution.requests], [r.skill for r in execution.requests],
            self.output_dir if out_dir is None else out_dir, owner='skilladam', workers=self.workers,
            context={'stage': execution.stage, 'seeds': [r.seed for r in execution.requests],
                     'splits': [r.split for r in execution.requests]})
        return tuple(RawRollout(record['task_id'], {**record['raw_result'], 'aligned_record': record})
                     for record in records)

    def generate(self, request):
        if self.optimizer_backend is None:
            raise RuntimeError('No optimizer configured; environment alignment does not enable training')
        return self.optimizer_backend.generate(request)

    def public_metadata(self):
        return {'profile': PROFILE, 'stage0': False, 'actor': self.transport.metadata(),
                'execution': {**EXECUTION_CONFIG, 'workers': self.workers},
                'max_tool_calls_per_turn': None, 'max_total_tool_calls': None}


class SkillOptAdapter(NativeOptAdapter):
    """Native EnvAdapter/data-loader API, replacing only OfficeQA rollout."""
    def __init__(self, dataset, runtime, transport, *, workers=WORKERS):
        super().__init__(split_dir=str(dataset.root), split_mode='split_dir', max_tool_turns=24,
                         max_completion_tokens=transport.metadata()['max_completion_tokens'])
        self.dataset, self.runtime, self.transport = dataset, runtime, transport
        self.workers = workers

    def rollout(self, env_manager, skill_content, out_dir, **kwargs):
        results = []
        cases = []
        for item in env_manager:
            case = self.dataset.case(item['id'])
            for key in ('question', 'source_files', 'source_docs'):
                if item[key] != case.payload[key]:
                    raise ValueError(f'SkillOpt task differs from common input: {key}')
            cases.append(case)
        records = _batch(self.dataset, self.runtime, self.transport, cases, [skill_content] * len(cases),
                         out_dir, owner='skillopt', workers=self.workers)
        for record in records:
            case = self.dataset.case(record['task_id'])
            raw = record['raw_result']
            folder = Path(out_dir) / 'predictions' / case.case_id
            save_record(folder, record)
            (folder / 'conversation.json').write_text(json.dumps(skillopt_conversation(raw['messages']),
                                                                 ensure_ascii=False, indent=2) + '\n')
            initial = record['initial_messages']
            for filename, message in zip(('target_system_prompt.txt', 'target_user_prompt.txt'), initial):
                (folder / filename).write_text(message['content'])
            results.append({'id': case.case_id, 'question': case.payload['question'],
                'task_type': 'officeqa', 'task_description': case.payload['question'],
                'predicted_answer': record['answer'], 'ground_truth': case.reference[0],
                'response': raw['response'], 'hard': int(record['metrics']['em']), 'soft': record['metrics']['f1'],
                'source_files': case.payload['source_files'], 'use_local_tools': True,
                'fail_reason': raw['fail_reason'], 'agent_ok': not raw['fail_reason'],
                'n_turns': raw['n_turns'], 'n_tool_calls': raw['n_tool_calls'],
                'target_system_prompt': initial[0]['content'], 'target_user_prompt': initial[1]['content'],
                'aligned_record': record, 'trajectory_path': str(folder / 'trajectory.json')})
        return results


class GovernActor:
    """Govern-Skill-Evo Actor boundary, independent of governance/optimizer policy.

    Implements actor_task/check_record for the caller. It is NOT a replacement
    for the full V25 Benchmark contract (diagnosis/facts/Gate are method work).
    """
    def __init__(self, dataset, runtime, transport, *, workers=WORKERS):
        self.dataset, self.runtime, self.transport = dataset, runtime, transport
        self.workers = workers

    def _cases(self, tasks, config, final):
        cases = [self.dataset.case(task) for task in tasks]
        expected_split = 'test' if final else config['split']
        if any(case.metadata['split'] != expected_split for case in cases) or (not final and expected_split == 'test'):
            raise ValueError('Govern Actor task is outside the requested split')
        return cases

    def actor_batch(self, tasks, skill_file, directory, config, *, final=False):
        cases = self._cases(tasks, config, final)
        skill = Path(skill_file).read_text() if skill_file is not None else None
        records = _batch(self.dataset, self.runtime, self.transport, cases, [skill] * len(cases),
                         directory, owner='govern', workers=self.workers, context={'final': final})
        for record in records:
            save_record(Path(directory) / 'predictions' / record['task_id'], record)
        return records

    def actor_task(self, task, skill_file, directory, config, *, final=False):
        cases = self._cases([task], config, final)
        # None explicitly means no initial Skill; no Stage0 or fallback file.
        skill = Path(skill_file).read_text() if skill_file is not None else None
        records = _batch(self.dataset, self.runtime, self.transport, cases, [skill], directory,
                         owner='govern', workers=self.workers, context={'final': final})
        return save_record(directory, records[0])

    def check_record(self, record, task, expected_skill, config):
        if (record['profile'] != PROFILE or record['method'] != 'govern' or record['task_id'] != task
                or record['skill'] != expected_skill or record['actor'] != self.transport.metadata()):
            raise ValueError('Govern OfficeQA record identity differs')
        return record

"""Replay archived training evidence into both native prompt builders, entirely offline."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from scripts.runs.run_lmb_skilladam_v27_2_feedback import actor_profile, base, feedback, prepare
from skilladam.core.feedback_loop import IterationContext, IterationRecord, PostDecisionContext
from skilladam.execution.store import RunStore
from skilladam.methods.skilladam_prompts import load_benchmark_prompt_context
from src.skill_evolution.v27_1.execution_input_view import restore_model_input

ARCHIVE = ROOT / 'experiments/baselines/lmb_skilladam/lmb53_actor65536_20261103_115844/training'
REFERENCE = ROOT / 'experiments/campaigns/v27_2_diag_v3_precond_v3_lmb53_20261105_210532'
HEADER = re.compile(r'^## Trajectory (\d+): (.+)\n\n([^\n]+)$', re.MULTILINE)
read = base.read
require = base.require


def expected_view(index, records, dataset):
    # Start from a real transmitted v27.2 Diagnosis payload. Preserve its entire
    # schema and task/order, substituting the facts of SkillAdam's own execution.
    path = REFERENCE / f'rounds/R{index + 1:02d}/diagnosis/attempts/001/request.json'
    reference = json.loads(read(path)['body']['messages'][-1]['content'])
    full = restore_model_input(reference, module='diagnosis')
    require(len(full['runs']) == len(records), 'Different batch sizes')
    full['parent'] = records[0]['execution']['skill']
    for run, record in zip(full['runs'], records):
        task = run['initial']['task']
        e = record['execution']
        require(run['task_id'] == record['task_id'] and full['parent'] == e['skill']
                and task == {k: record['task'][k] for k in ('question', 'choices')}
                and run['initial']['messages'][1] == e['initial_messages'][1],
                'Question, shuffled choices, or Actor user message differ')
        choices = {c['label']: c['text'] for c in task['choices']}
        answer = e['answer']
        gold = dataset.case(run['task_id']).reference['label']
        require(list(choices) == list('ABCDE') and gold == answer['correct_label']
                and choices[gold] == answer['correct_text'], 'Wrong shuffled gold mapping')
        if answer['parse_valid']:
            require(choices[answer['predicted_label']] == answer['predicted_text'], 'Wrong prediction mapping')
        run['run_id'] = record['run_id']
        run['initial']['messages'] = e['initial_messages']
        attempt, = run['attempts']
        attempt['request_messages'] = e['initial_messages']
        attempt['assistant']['content'] = e['content']
        require(answer['raw_content'] == e['content'], 'Actor ordinary reply differs')
        outcome = run['outcome']
        require(outcome['answer'].keys() == answer.keys() and outcome['score'].keys() == e['metrics'].keys(),
                'Source answer or score schema differs')
        outcome.update(answer=answer, score=e['metrics'], api_requests=e['api_requests'],
                       termination=e['termination'])
    return full


def field_paths(value, prefix=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from field_paths(child, f'{prefix}.{key}' if prefix else key)
    elif isinstance(value, list):
        for child in value:
            yield from field_paths(child, f'{prefix}[]')
    else:
        yield prefix


def check_messages(payload, expected_batches, current, coverage):
    require('reasoning_content' not in json.dumps(payload, ensure_ascii=False), 'Private reasoning in request')
    history_count = 0
    for message in payload['messages']:
        text = message['content']
        matches = HEADER.findall(text)
        if not matches:
            continue
        ids = tuple(uid for _, uid, _ in matches)
        require(ids in expected_batches, 'Unknown batch or trajectory coverage in final prompt')
        parts = [json.loads(body) for _, _, body in matches]
        compact = parts[0]
        for number, ((n, uid, _), part) in enumerate(zip(matches, parts), 1):
            require(int(n) == number and len(part['runs']) == 1 and part['runs'][0]['task_id'] == uid,
                    'Wrong per-task trajectory heading or order')
            if number > 1:
                require(part.keys() == {'runs'}, 'Unexpected per-task fields')
        compact['runs'] = [part['runs'][0] for part in parts]
        actual = restore_model_input(compact, module='diagnosis')
        require(base.p.equal(actual, expected_batches[ids]), f'Training feedback field mismatch: {ids}')
        if message is payload['messages'][-1]:
            require(ids == current, 'Final user message has the wrong training batch')
            for uid, run in zip(ids, actual['runs']):
                for field in field_paths(run):
                    coverage[field].add(uid)
        else:
            history_count += len(ids)
    require(len(HEADER.findall(payload['messages'][-1]['content'])) == len(current),
            'Missing current training trajectories in final optimizer request')
    return history_count


class ArchiveRunner(feedback.FeedbackRunner):
    """Only replace Actor evaluation and billing. Use the production evidence and optimizer paths."""
    def _evaluate_skill(self, skill, cases, *, stage):
        folder = f'iter_{self._active_iteration:03d}'
        require(stage == 'training_rollout' and skill == (ARCHIVE / 'rollouts' / folder / 'training/skill.md').read_text(),
                'Unexpected evaluation requested')
        value = read(ARCHIVE / 'native/iterations' / folder / 'training_evaluation.json')
        require([case.case_id for case in cases] == [r['case_id'] for r in value['results']],
                'Historical evaluation order differs')
        return SimpleNamespace(to_dict=lambda: value)

    def _record_usage(self, records, *, stage):
        pass  # No model calls or billing during archive replay.


class OfflineClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.capture))
        self.payloads = []
        self.result = None

    def capture(self, **payload):
        self.payloads.append(payload)
        message = {'content': self.result['text'], 'tool_calls': [
            {'type': 'function', 'function': {'name': tool['name'], 'arguments': json.dumps(tool['arguments'])}}
            for tool in self.result['tool_calls']
        ]}
        return {'choices': [{'message': message}]}


def audit(tmp):
    cfg, dataset, _, native, context, snapshot = prepare()
    historical = read(ARCHIVE / 'frozen.json')['config']
    require(all(cfg[k] == historical[k] for k in historical if k != 'v27_config'),
            'Settings differ from the 65k baseline')
    client = OfflineClient()
    backend = base.generation_transport(cfg, dataset, context, tmp,
        environ={'OPENAI_API_KEY': 'offline', 'OPENAI_BASE_URL': cfg['optimizer']['base_url']},
        client_factory=lambda **_: client)
    runner = ArchiveRunner(config=native, adapter=base.NativeAdapter(dataset.root), context=context, output_dir=tmp,
                           backend=SimpleNamespace(dataset=dataset, output_dir=ARCHIVE / 'rollouts',
                                                   generate=backend.generate))
    runner._cases_by_id = {case.case_id: case for case in base.native_cases(dataset)}
    runner._run_store = RunStore(tmp)
    runner._prompt_context = load_benchmark_prompt_context(native.benchmark, trajectory_count=native.train_size,
        benchmark_domain_info_md='Training trajectories are supplied per iteration.',
        scope=native.scope, prompt_profile=native.prompt_profile)
    report, expected = [], {}
    counts = Counter()
    coverage = defaultdict(lambda: defaultdict(set))
    for item in read(ARCHIVE / 'native/checkpoint.json')['iterations']:
        record = IterationRecord.from_dict(item)
        i, ids = record.iteration, record.training_case_ids
        require(list(ids) == snapshot['batches'][i], 'Training schedule mismatch')
        folder = f'iter_{i:03d}'
        rollout = ARCHIVE / 'rollouts' / folder
        records = read(rollout / 'training/actor/records.json')
        expected[ids] = expected_view(i, records, dataset)
        parent = expected[ids]['parent']
        receipts = ARCHIVE / 'recovery/generations' / folder
        selected = (rollout / 'validation_candidate/skill.md').read_text() if record.accepted else parent
        post = PostDecisionContext(folder, record, selected)
        for path in [*sorted(receipts.glob('iteration_patch_*.json')), receipts / 'momentum_update_00.json']:
            receipt = read(path)
            signature = receipt['signature']
            stage = signature['stage']
            client.result = receipt['result']
            if stage == 'iteration_patch':
                attempt = signature['metadata']['patch_attempt']
                error = signature['messages'][-1]['content'].rsplit('# Previous Patch Error\n\n', 1)[1]
                error = error.split('\n\n## Edit Budget', 1)[0].strip()
                ctx = IterationContext(i, parent, ids, attempt, '' if error == '(none)' else error, record.edit_budget)
                runner._propose_patch(ctx)
            else:
                # Exercise the persisted-trajectory path used by resumed Momentum.
                runner._trajectory_cache.clear()
                generation = runner._generate_momentum(post)
                runner._apply_momentum(post, generation)
            require(len(client.payloads) == 1, 'Expected exactly one local SDK payload')
            payload = client.payloads.pop()
            history = check_messages(payload, expected, ids, coverage[stage])
            counts[stage] += len(ids)
            report.append({'request': f'{folder}/{path.stem}', 'current_records': len(ids),
                           'history_records_checked': history,
                           'messages_sha256': hashlib.sha256(json.dumps(payload['messages'], ensure_ascii=False,
                               separators=(',', ':')).encode()).hexdigest()})
    tasks = [uid for batch in expected for uid in batch]
    require(len(tasks) == len(set(tasks)) == 53 and list(map(list, expected)) == snapshot['batches'],
            'Expected all 53 unique training tasks in frozen order')
    fields = {field: {stage: len(coverage[stage][field]) for stage in counts}
              for field in sorted(set().union(*(set(v) for v in coverage.values())))}
    require(set(counts) == {'iteration_patch', 'momentum_update'}
            and fields and all(n == len(tasks) for row in fields.values() for n in row.values()),
            'Incomplete per-field optimizer coverage')
    return {'baseline': str(ARCHIVE.relative_to(ROOT)), 'reference': str(REFERENCE.relative_to(ROOT)),
            'unique_train_tasks': len(tasks), 'batch_sizes': list(map(len, expected)),
            'per_stage_current_records_including_retries': dict(counts), 'network_requests': 0,
            'comparison': 'All restored per-task fields against the archived v27.2 request schema and local Actor records.',
            'unique_tasks_checked_per_restored_field': fields, 'requests': report}


if __name__ == '__main__':
    with actor_profile(), TemporaryDirectory() as tmp:
        print(json.dumps(audit(Path(tmp)), indent=2, ensure_ascii=False))

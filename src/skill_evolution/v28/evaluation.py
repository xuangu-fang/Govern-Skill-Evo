"""Separate fixed-Skill Test scheduling; never updates optimizer state or Memory."""
from pathlib import Path

from .stages import read, save, freeze, freeze_text
from .benchmarks.searchqa import protocol as p, scoring
from .benchmarks.searchqa.actor import locked
from .benchmarks.searchqa.dataset import SearchQADataset
from . import profiles

VERSION = 'v28_searchqa_test_v1'
ROLE = {'split': 'test', 'role': 'evaluation'}


def _tasks(adapter):
    adapter._preflight()
    tasks = adapter.dataset.splits['test']
    p.require(isinstance(tasks, list) and tasks and len(tasks) == len(set(tasks)), 'Invalid Test IDs')
    adapter._cases(tasks, ROLE)
    if isinstance(adapter.dataset, SearchQADataset):
        p.require(len(tasks) == 1400, 'SearchQA Test must cover all 1400 tasks')
    return tasks


def _plan(adapter, skill):
    plan = {'version': VERSION, 'tasks': _tasks(adapter), 'role': ROLE,
            'skill': {'mode': 'none' if skill is None else 'fixed', 'text': skill},
            'protocol': p.implementation_identity(), 'data': adapter.dataset.snapshot(),
            'actor': adapter._actor, 'workers': adapter.test_workers}
    if adapter.profile == profiles.V28_1:
        plan['method_profile'] = adapter.profile
    return plan


def _verify(root, adapter):
    plan = read(root / 'plan.json')
    p.require(p.equal(plan, _plan(adapter, plan['skill']['text'])), 'Frozen Test plan differs')
    if plan['skill']['mode'] == 'fixed':
        freeze_text(root / 'skill.md', plan['skill']['text'], read_only=True)
    else:
        p.require(not (root / 'skill.md').exists(), 'Unexpected Test Skill')
    return plan


def report_evaluation(directory, *, adapter):
    root = Path(directory).resolve(); plan = _verify(root, adapter)
    records = []
    for task in plan['tasks']:
        path = root / 'batch/actor' / adapter.task_key(task) / 'trajectory.json'
        if path.exists():
            record = read(path)
            adapter.check_record_archive(record, task, plan['skill']['text'], ROLE, root / 'batch')
            records.append(record)
    done = {r['task_id'] for r in records}
    full = len(done) == len(plan['tasks'])
    if (root / 'batch/records.json').exists():
        p.require(full and p.equal(read(root / 'batch/records.json'), records), 'Test summary differs from original journals')
    scores = [{'task_id': r['task_id'], 'metrics': r['execution']['metrics']} for r in records]
    result = {'version': VERSION, 'status': 'complete' if full else 'incomplete',
              'total': len(plan['tasks']), 'completed': len(done),
              'pending_ids': [t for t in plan['tasks'] if t not in done],
              'optimization_updates': False,
              'summary': scoring.summarize_scores(scores, plan['tasks']) if full else None,
              'actor_requests': sum(r['execution']['api_requests'] for r in records),
              'cases': scores}
    if adapter.verify_hashes:
        result['skill_sha256'] = p.digest(plan['skill']['text'])
    else:
        result.update(method_profile=adapter.profile,
                      skill_file='skill.md' if plan['skill']['mode'] == 'fixed' else None)
    save(root / 'report.json', result)
    return result


def run_evaluation(directory, *, adapter, skill_file, resume=False):
    _tasks(adapter)
    root = Path(directory).resolve()
    protected = []
    if hasattr(adapter.dataset, 'root'):
        protected.append(adapter.dataset.root.resolve())
    if skill_file is not None:
        protected.append(Path(skill_file).resolve())
    p.require(all(not root.is_relative_to(q) and not q.is_relative_to(root) for q in protected), 'Separate Test directory required')
    p.require(not any((q / 'state.json').exists() and (q / 'config.json').exists() for q in (root, *root.parents)),
              'Test output cannot be inside Campaign')
    skill = None if skill_file is None else Path(skill_file).read_bytes().decode('utf-8')
    with locked(root):
        p.require(not (root / 'plan.json').exists() or resume, 'Existing Test requires explicit resume')
        freeze(root / 'plan.json', _plan(adapter, skill))
        if skill is not None:
            freeze_text(root / 'skill.md', skill)
        plan = _verify(root, adapter)
        adapter.actor_batch(plan['tasks'], root / 'skill.md' if skill is not None else None,
                            root / 'batch', ROLE, final=True)
        return report_evaluation(root, adapter=adapter)

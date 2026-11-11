"""Run the retained ALFWorld method on its training or held-out tasks."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from functools import partial
from pathlib import Path

from src.skill_evolution.v24_1.evolution import cost_summary, now
from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
from src.skill_evolution.v24_2.campaign import writer
from src.skill_evolution.v24_2.storage import freeze, freeze_text, read, save
from src.skill_evolution.v27.facts import require


def episodes(directory, tasks, skill_file, config, adapter, actor, *, test_bundle=None):
    skill = skill_file.read_text()
    def one(task):
        folder = directory / task.replace(':', '_')
        marker = folder / 'record.json'
        if marker.exists():
            path = folder / read(marker)['trajectory']
        else:
            attempts = folder / 'attempts'
            attempts.mkdir(parents=True, exist_ok=True)
            previous = sorted(attempts.iterdir())
            saved = list(previous[-1].rglob('trajectory.json')) if previous else []
            require(len(saved) <= 1, 'Ambiguous Actor attempt')
            if saved and adapter.is_complete(read(saved[0])):
                path = saved[0]
            else:
                dest = attempts / f'{len(previous) + 1:03}'
                dest.mkdir()
                path = Path(actor(task, skill_file, dest, config))
        record = read(path)
        adapter.check_record(record, task, skill, config)
        require(not record.get('error_type') and not record.get('error_stage'), 'Technical Actor failure')
        if test_bundle is not None:
            adapter.check_evaluation_record(path, task, test_bundle)
        freeze(marker, {'trajectory': str(path.relative_to(folder))})
        return record

    with ThreadPoolExecutor(max_workers=min(config['actor_max_workers'], len(tasks))) as pool:
        futures = [pool.submit(copy_context().run, one, task) for task in tasks]
        try:
            return [future.result() for future in futures]
        finally:
            for future in futures:
                future.cancel()


def batch(rd, side, tasks, skill, config, adapter, actor):
    directory = rd / side
    path = directory / 'skill.md'
    freeze_text(path, skill)
    return episodes(directory, tasks, path, config, adapter, actor)


def evaluate(root, *, bundle, resume=False):
    adapter = ALFWorldAdapter()
    with writer(root):
        require(resume == (root / 'input.json').exists(), 'Use --resume for an existing Test')
        if not resume:
            require(all(p.name == '.v24_2.lock' for p in root.iterdir()), 'Nonempty Test directory')
        freeze(root / 'input.json', bundle)
        skill = root / 'final_skill.md'
        freeze_text(skill, bundle['skill_text'])
        save(root / 'progress.json', {'status': 'running', 'at': now()})
        try:
            tasks = [t['id'] for t in bundle['tasks']]
            directory = root / 'episodes'
            records = episodes(directory, tasks, skill, bundle['actor_config'], adapter,
                               partial(adapter.actor_task, final=True), test_bundle=bundle)
            rows = []
            for task, record in zip(tasks, records):
                folder = directory / task.replace(':', '_')
                path = folder / read(folder / 'record.json')['trajectory']
                rows.append(dict(task_id=task, success=record['won'], steps=len(record['steps']),
                                 termination=record['status'], trajectory=str(path)))
            success = sum(r['success'] for r in rows)
            result = dict(status='complete', completed=len(rows), success=success, success_rate=success/len(rows),
                          tasks=rows, cost=cost_summary(root), initial_reference=bundle['initial_reference'], at=now())
            save(root / 'summary.json', result)
            save(root / 'progress.json', {'status': 'complete', 'at': now()})
            return result
        except BaseException as exc:
            save(root / 'progress.json', {'status': 'stopped', 'error_type': type(exc).__name__, 'at': now()})
            raise

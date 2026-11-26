"""Run the independent Test with the same twenty-worker Actor as v26.8."""
from pathlib import Path

from src.adapters.officeqa.execution import _locked
from src.skill_evolution.v26.evaluation import ArchiveTransport
from src.skill_evolution.v26_3._shared_campaign import ByteSkillActor
from src.skill_evolution.v27.benchmark import current
from . import evolution as ev, reporting
from .actor_io import completed_journal
from .evaluation import prepare_test as prepare_campaign_test
from .telemetry import invocation


def prepare_test(campaign, directory):
    return {**prepare_campaign_test(campaign, directory), 'workers': 20}


def run_test(campaign, directory, *, resume=False):
    identity = prepare_test(campaign, directory)
    method = current()
    root = Path(directory).resolve()
    tasks = identity['tasks']
    runs = root / 'runs'
    if isinstance(method.transport, ArchiveTransport):
        ev.require(completed_journal(runs, tasks), 'Archive-only Test needs a complete Actor journal')
    with _locked(root):
        if (root / 'evaluation.json').exists():
            ev.require(resume, 'Existing Test requires explicit resume')
        else:
            ev.require({p.name for p in root.iterdir()} <= {'.execution.lock', 'evaluation.tmp'},
                       'Unrelated Test output directory')
            ev.require(not resume or (root / 'evaluation.tmp').exists(), 'Missing Test to resume')
        ev.freeze(root / 'evaluation.json', identity)
        ev.freeze_text(root / 'skill.md', identity['skill'])
        actor = ByteSkillActor(method.dataset, method.runtime, method.transport, workers=identity['workers'])
        try:
            with invocation(runs, 'actor_evaluation'):
                rows = actor.actor_batch(tasks, root / 'skill.md', runs / 'actor', {'split': 'test'}, final=True)
            ev.require(len(rows) == len(tasks) and {r['task_id'] for r in rows} == set(tasks),
                       'Incomplete Test coverage')
            ev.require(prepare_test(campaign, directory) == identity, 'Test identity changed')
            scorer = method.runtime.scorer
            for row in rows:
                ev.require(row['actor'] == identity['actor'] and row['skill'] == identity['skill'],
                           'Test Actor or Skill differs')
                parsed = scorer.parse_result(method.dataset.case(row['task_id']), row['raw_result'])
                ev.require(dict(scorer.evaluate(parsed).metrics) == row['metrics'], 'Native score differs')
            correct = sum(row['metrics']['em'] == 1 for row in rows)
            summary = {'status': 'complete', 'method': identity['method'], 'count': len(tasks),
                       'completed': len(rows), 'correct': correct, 'em': correct / len(rows),
                       'f1': sum(row['metrics']['f1'] for row in rows) / len(rows),
                       'skill': str(root / 'skill.md')}
            ev.freeze(root / 'summary.json', summary)
            (root / 'incomplete.json').unlink(missing_ok=True)
            return summary
        except (Exception, KeyboardInterrupt) as exc:
            if not (root / 'summary.json').exists():
                ev.save(root / 'incomplete.json', {
                    'status': 'incomplete', 'count': len(tasks), 'em': None, 'f1': None,
                    **reporting.pending_test(root, tasks), 'error_type': type(exc).__name__, 'error': str(exc)[:1000]})
            raise

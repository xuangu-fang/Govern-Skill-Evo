"""Explicit final Test with complete coverage and original OfficeQA scoring."""
from pathlib import Path
from src.skill_evolution.v27.benchmark import current
from src.adapters.officeqa.execution import _locked
from .evidence import cost_summary
from . import evolution as ev, config as settings, protocol as p
from .actor_io import read_skill, completed_journal
from . import reporting

FORMAT = 'v26_1_final_test_v1'


def prepare_test(campaign, directory):
    campaign, root = Path(campaign).resolve(), Path(directory).resolve()
    protected = [campaign, current().dataset.root, current().runtime.parsed_root]
    ev.require(all(not root.is_relative_to(path) and not path.is_relative_to(root) for path in protected),
               'Test output must be separate from Campaign and source data')
    final = ev.final_parent(campaign)
    config = ev.read(campaign / 'config.json')
    settings.validate_config(config, executable=True)
    skill = read_skill(final)
    if (campaign / 'final_skill.md').exists():
        ev.require(read_skill(campaign / 'final_skill.md') == skill, 'Exported Skill differs')
    tasks = list(current().dataset.splits['test'])
    ev.require(tasks and not set(tasks).intersection(sum(config['batches'], [])), 'Test overlaps optimization')
    ev.require(not set(tasks).intersection(current().task_output_limits), 'Test cannot use optimization budget overrides')
    return {'format': FORMAT, 'method': settings.METHOD_VERSION, 'campaign': str(campaign),
            'selected_skill': str(final), 'skill': skill, 'tasks': tasks,
            'actor': current().transport.metadata(), 'workers': 4, 'revision': p.REVISION,
            'scorer_profile': p.SCORER_PROFILE}


def run_test(campaign, directory, *, resume=False):
    identity = prepare_test(campaign, directory)
    root = Path(directory).resolve()
    from src.skill_evolution.v26.evaluation import ArchiveTransport
    if isinstance(current().transport, ArchiveTransport):
        ev.require(completed_journal(root / 'runs', identity['tasks']),
                   'Archive-only Test needs a complete Actor journal; no request slot is reserved')
    with _locked(root):
        exists = (root / 'evaluation.json').exists()
        ev.require(type(resume) is bool, 'Invalid resume flag')
        if exists:
            ev.require(resume, 'Existing Test requires explicit resume')
        else:
            ev.require({path.name for path in root.iterdir()} <= {'.execution.lock', 'evaluation.tmp'},
                       'Unrelated Test output directory')
            ev.require(not resume or (root / 'evaluation.tmp').exists(), 'Missing Test to resume')
        ev.freeze(root / 'evaluation.json', identity)
        ev.freeze_text(root / 'skill.md', identity['skill'])
        try:
            records = current().actor_batch(identity['tasks'], root / 'skill.md', root / 'runs',
                                           {'split': 'test', 'role': 'evaluation'}, final=True)
            ev.require(settings.same(prepare_test(campaign, directory), identity), 'Test identity changed')
            ev.require(len(records) == len(identity['tasks']) and
                       {r['task_id'] for r in records} == set(identity['tasks']), 'Incomplete Test coverage')
            count = len(records)
            summary = {'status': 'complete', 'method': settings.METHOD_VERSION,
                       'count': count, 'completed': count,
                       'em': sum(r['execution']['metrics']['em'] for r in records) / count,
                       'f1': sum(r['execution']['metrics']['f1'] for r in records) / count,
                       'correct': sum(r['execution']['metrics']['em'] == 1 for r in records),
                       'cost': cost_summary(records), 'skill': str(root / 'skill.md')}
            ev.freeze(root / 'summary.json', summary)
            if (root / 'incomplete.json').exists(): (root / 'incomplete.json').unlink()
            return summary
        except (Exception, KeyboardInterrupt) as exc:
            # Technical failures never become zero scores or a full-set metric.
            if not (root / 'summary.json').exists():
                ev.save(root / 'incomplete.json', {'status': 'incomplete', 'count': len(identity['tasks']),
                        'em': None, 'f1': None, **reporting.pending_test(root, identity['tasks']),
                        'cost': reporting.costs(root), 'error_type': type(exc).__name__, 'error': str(exc)[:1000]})
            raise

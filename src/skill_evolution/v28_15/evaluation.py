"""Final held-out Test for a completed v28.15 campaign; no optimizer calls."""
from pathlib import Path

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v28.benchmarks.searchqa.actor import locked
from src.skill_evolution.v28.benchmarks.searchqa import protocol
from src.skill_evolution.v28.benchmarks.searchqa.scoring import summarize_scores
from . import evolution as ev, actor_io, config as settings

FORMAT = 'v28_15_final_test_v1'


def prepare_test(campaign, directory):
    """Read-only readiness check; neither create Test output nor access transport."""
    campaign, root = Path(campaign).resolve(), Path(directory).resolve()
    protected = Path(current().dataset.root).resolve()
    ev.require(not root.is_relative_to(campaign) and not campaign.is_relative_to(root)
               and not root.is_relative_to(protected) and not protected.is_relative_to(root),
               'Test output must be separate from Campaign and source data')
    # Verify the published Selected Skill checkpoint without reopening old Actor sources.
    final = ev.final_parent(campaign)
    config = ev.read(campaign / 'config.json')
    settings.validate_config(config, executable=True)
    skill = actor_io.read_skill(final)
    exported = campaign / 'final_skill.md'
    if exported.exists():
        ev.require(actor_io.read_skill(exported) == skill, 'Exported Skill differs from final Parent')
    actor = current().actor_adapter
    tasks = list(current().dataset.splits['test'])
    ev.require(set(tasks).isdisjoint(current().dataset.splits['train']), 'Test overlaps optimization tasks')
    ev.require(type(actor.test_workers) is int and 1 <= actor.test_workers <= 60, 'Invalid Test workers')
    actor._cases(tasks, {'split': 'test', 'role': 'evaluation'})
    return {'format': FORMAT, 'method': config['method']['version'], 'campaign': str(campaign),
            'selected_skill': str(final), 'skill': skill, 'tasks': tasks,
            'actor': protocol.actor_config(30), 'workers': actor.test_workers,
            'cases': [{'id': t, 'payload': dict(current().dataset.case(t).payload),
                       'reference': current().dataset.case(t).reference,
                       'metadata': dict(current().dataset.case(t).metadata)} for t in tasks],
            'scorer_profile': config['scorer_profile']}


def run_test(campaign, directory, *, resume=False):
    identity = prepare_test(campaign, directory)
    root = Path(directory).resolve()
    actor = current().actor_adapter
    if actor.transport is not None:
        protocol.background(actor.transport.metadata())
    with locked(root):
        exists = (root / 'evaluation.json').exists()
        ev.require(type(resume) is bool, 'Invalid resume flag')
        if exists:
            ev.require(resume, 'Existing Test evaluation requires --resume')
        else:
            # A crash while atomically writing the initial identity has not
            # authorized any task execution. Only that initialization is reusable.
            names = {p.name for p in root.iterdir()}
            ev.require(names <= {'.execution.lock', 'evaluation.tmp'},
                       'Missing Test identity for existing output')
            ev.require(not resume or 'evaluation.tmp' in names, 'Missing Test evaluation to resume')
        ev.freeze(root / 'evaluation.json', identity)
        ev.freeze_text(root / 'skill.md', identity['skill'])
        # Explicit final=True preserves held-out isolation. The v28.15 I/O path
        # retains CRLF and recovers incomplete responses under the same budget.
        records = actor_io.actor_batch(actor, identity['tasks'], root / 'skill.md', root / 'runs',
                                       {'split': 'test', 'role': 'evaluation'}, final=True)
        ev.require(settings.same(prepare_test(campaign, directory), identity),
                   'Training source or Test configuration changed during evaluation')
        ev.freeze_text(root / 'skill.md', identity['skill'], read_only=True)
        ev.require([r['task_id'] for r in records] == identity['tasks'] and
                   all(r['execution']['skill'] == identity['skill'] and r['task']['split'] == 'test'
                       and r['provenance']['role'] == 'evaluation' for r in records),
                   'Test records differ from selected Skill/tasks')
        metrics = summarize_scores([
            {'task_id': r['task_id'], 'metrics': r['execution']['metrics']} for r in records], identity['tasks'])
        summary = {'status': 'complete', 'method': identity['method'], 'campaign': identity['campaign'],
                   'skill': str(root / 'skill.md'), **metrics,
                   'api_requests': sum(r['execution']['api_requests'] for r in records)}
        # Publish aggregate metrics only after complete verified task coverage.
        ev.freeze(root / 'summary.json', summary)
        return summary

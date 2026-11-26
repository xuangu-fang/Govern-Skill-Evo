"""Evaluate the aligned SkillAdam final skill under the v27.2 held-out protocol."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from scripts.runs import run_lmb_skilladam_v27_2_feedback as training
from scripts.runs.run_v27_2_campaign import read_credentials
from experiments.benchmark_record_refs.restore import ARCHIVE, Archive
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.stages import freeze, freeze_text, read, save
from src.skill_evolution.v27.training import load_dataset
from src.skill_evolution.v27_1 import actor_io
from src.skill_evolution.v27_1.lmb.actor import ChatTransport
from src.skill_evolution.v27_2 import evaluation

REFERENCE_TEST = ROOT / 'experiments/evaluations/v27_2_diag_v3_precond_v3_lmb53_20261105_210532_test/evaluation.json'
ROLE = {'split': 'test', 'role': 'evaluation'}


def protocol():
    cfg = read(training.CONFIG)
    if (ARCHIVE / 'lmb' / 'manifest.sqlite3').is_file():
        archive = Archive('lmb')
        try:
            reference = json.loads(archive.read_bytes(REFERENCE_TEST.relative_to(ROOT)))
        finally:
            archive.close()
    else:
        reference = read(resolve_experiment_path(REFERENCE_TEST))
    actor = actor_io.ActorAdapter(load_dataset(ROOT / cfg['prepared_root']))
    tasks = list(actor.dataset.splits['test'])
    cases = actor._cases(tasks, ROLE)
    fields = {'tasks': tasks, 'actor': actor.transport.metadata(), 'workers': actor.test_workers,
              'scorer_profile': evaluation.protocol.EM_GATE,
              'cases': [{'id': c.case_id, 'payload': dict(c.payload), 'reference': c.reference,
                         'metadata': dict(c.metadata)} for c in cases]}
    require(len(tasks) == len(set(tasks)) == 124 and set(tasks).isdisjoint(actor.dataset.splits['train'])
            and all(reference[k] == v for k, v in fields.items())
            and cfg['actor'] == fields['actor'] and cfg['test_workers'] == fields['workers'],
            'Test protocol differs from the archived v27.2 evaluation')
    return actor, fields


def evaluate(training_dir, output, resume):
    actor, fields = protocol()
    trained, root = training_dir.resolve(), output.resolve()
    protected = (trained, Path(actor.dataset.root).resolve(), REFERENCE_TEST.parent,
                 resolve_experiment_path(REFERENCE_TEST).parent)
    require(all(not root.is_relative_to(p) and not p.is_relative_to(root) for p in protected),
            'Use a separate evaluation output directory')
    snapshot = read(trained / 'frozen.json')
    require(snapshot['config'] == read(training.CONFIG), 'Unexpected training configuration')
    final = trained / 'native/final_skill.md'
    skill = actor_io.read_skill(final)
    checkpoint = read(trained / 'native/checkpoint.json')
    require(skill.strip() and skill == checkpoint['current_skill']
            and checkpoint['pending_post_decision'] is None, 'Final Skill differs from checkpoint')
    identity = {**fields, 'format': 'lmb_skilladam_v27_2_feedback_test_v1', 'method': 'skilladam',
                'selected_skill': str(final), 'skill': skill, 'reference_test': str(REFERENCE_TEST)}
    with evaluation.locked(root):
        if (root / 'evaluation.json').exists():
            require(resume, 'Existing evaluation requires --resume')
        else:
            names = {p.name for p in root.iterdir()}
            require(names <= {'.execution.lock', 'evaluation.tmp'} and
                    (not resume or 'evaluation.tmp' in names), 'Unexpected evaluation directory')
        freeze(root / 'evaluation.json', identity)
        freeze_text(root / 'skill.md', skill)
        credentials = read_credentials(ROOT / '.env', read(ROOT / snapshot['config']['v27_config']))
        actor.transport = ChatTransport(credentials['OPENAI_API_KEY'], metadata=evaluation.protocol.ACTOR)
        try:
            records = actor_io.actor_batch(actor, fields['tasks'], root / 'skill.md', root / 'runs', ROLE, final=True)
        except (evaluation.RequestFailure, KeyboardInterrupt):
            save(root / 'report.json', evaluation._incomplete_report(root, identity, actor))
            raise
        metrics = evaluation.summarize_scores([
            {'task_id': r['task_id'], 'metrics': r['execution']['metrics']} for r in records], fields['tasks'])
        summary = {'status': 'complete', 'method': identity['method'], **metrics,
                   'api_requests': sum(r['execution']['api_requests'] for r in records)}
        freeze(root / 'summary.json', summary)
        if (root / 'report.json').exists():
            save(root / 'report.json', {**summary, 'total': len(records), 'completed': len(records),
                                                      'pending_ids': [], 'errors': []})
        return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('preflight')
    run = commands.add_parser('run')
    run.add_argument('--training-dir', required=True, type=Path)
    run.add_argument('--output', required=True, type=Path)
    run.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'run':
        print(json.dumps(evaluate(args.training_dir, args.output, args.resume), ensure_ascii=False))
    else:
        _, fields = protocol()
        print(json.dumps({'tasks': len(fields['tasks']), 'workers': fields['workers'], 'scorer': fields['scorer_profile'],
                          'retry_policy': fields['actor']['retry_policy'], 'limit': fields['actor']['request_attempts_total']}))

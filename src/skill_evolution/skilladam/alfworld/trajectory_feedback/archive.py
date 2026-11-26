"""Read a feedback training run and its final and checkpoint evaluations offline."""
import argparse
from hashlib import sha256
import json

from scripts.runs.alfworld.alfworld_aligned_common import read, require
from scripts.runs.v24.read_archived_test import archive_path
from src.skill_evolution.shared.experiment_paths import ROOT
from ..archive import offline_alfworld, read_evaluation, read_training


def checkpoint_evaluations(output, results, training, final_skill, items, actor):
    archive = output / 'evaluations'
    reports = {p.relative_to(results) for p in results.glob('*/*/summary.json')}
    require(reports == {p.relative_to(archive) for p in archive.glob('*/*/summary.json')},
            'Checkpoint index differs from archived evaluations')
    rounds = len(training['iterations'])
    round_numbers = {f'R{n:02}': n for n in range(rounds + 1)}
    for report in sorted(reports):
        entry = read(results / report)
        run = report.parent
        root = archive / run
        inputs = read(root / 'inputs.json')
        label = run.name
        require(label in round_numbers and label == entry['round'] == inputs['round']
                and archive_path(inputs['training']) == output, 'Checkpoint training or round differs')
        number = round_numbers[label]
        # The next training rollout starts with the Skill retained by this round's gate.
        skill = final_skill if number == rounds else (
            output / f'shared_actor/iter_{number:03}/training_rollout_0/actor_skill.md').read_text()
        skill_path = (results / run / entry['evaluated_skill']).resolve()
        require(skill_path.is_relative_to(results.parent) and skill_path.read_bytes() == skill.encode()
                and sha256(skill.encode()).hexdigest() == entry['skill_sha256'] == inputs['skill_sha256'],
                'Checkpoint Skill differs from training')
        verified = read_evaluation(root, output.name, items, actor, skill)
        del verified['final_skill']
        verified['run_id'] = run.as_posix()
        require(all(entry[k] == value for k, value in verified.items()), 'Checkpoint summary differs from trajectories')
        yield entry


def read_archive(run_id):
    with offline_alfworld() as path:
        return _read_archive(run_id, path(ROOT))


def _read_archive(run_id, repository):
    experiments = repository / 'experiments/methods/skilladam/alfworld/trajectory_feedback'
    reference = read(experiments / run_id / 'config/baseline_reference.json')
    output = repository / reference['training_archive']
    config = (repository / reference['baseline_config']).parent
    require(output.name == reference['run_id'] == run_id, 'Feedback training ID differs')
    training, skill = read_training(output, config)
    first_batch_skill = output / 'shared_actor/iter_000/training_rollout_0/actor_skill.md'
    require(first_batch_skill.read_bytes() == (ROOT / reference['initial_skill']).read_bytes(),
            'Training started from a different Skill')
    items = read(config / 'splits/test/items.json')
    actor = read(ROOT / reference['actor_config'])
    evaluations = []
    for entry in reference['evaluations']:
        root = output.with_name(entry['run_id'])
        if entry['role'] == 'fixed_skill_retest':
            for filename in ('checkpoint.json', 'completion.json', 'final_skill.md'):
                require((root / 'training_snapshot' / filename).read_bytes() == (output / filename).read_bytes(),
                        f'Retest training snapshot differs in {filename}')
        evaluations.append(read_evaluation(root, run_id, items, actor, skill))
    evaluations.extend(checkpoint_evaluations(output, experiments / run_id / 'results', training, skill, items, actor))
    return training, evaluations


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id', help='Training experiment ID')
    args = parser.parse_args()
    training, evaluations = read_archive(args.run_id)
    print(json.dumps(dict(training=training['run_id'], rounds=len(training['iterations']),
                          evaluations=evaluations), indent=2))

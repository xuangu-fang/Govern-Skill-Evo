"""Read one feedback training run and its own final evaluations, offline."""
import argparse
import json

from scripts.runs.alfworld.alfworld_aligned_common import read, require
from src.skill_evolution.shared.experiment_paths import ROOT
from ..archive import read_evaluation, read_training


def read_archive(run_id):
    experiments = ROOT / 'experiments/methods/skilladam/alfworld/trajectory_feedback'
    reference = read(experiments / run_id / 'config/baseline_reference.json')
    output = ROOT / reference['training_archive']
    config = (ROOT / reference['baseline_config']).parent
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
    return training, evaluations


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id', help='Training experiment ID')
    args = parser.parse_args()
    training, evaluations = read_archive(args.run_id)
    print(json.dumps(dict(training=training['run_id'], rounds=len(training['iterations']),
                          evaluations=evaluations), indent=2))

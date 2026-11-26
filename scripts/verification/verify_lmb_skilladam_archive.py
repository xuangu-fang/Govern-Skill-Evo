"""Read the historical SkillAdam runs and LMB evaluations offline."""
import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.benchmark_record_refs.restore import Archive
from scripts.verification.verify_lmb_comparison_archive import check_training, digest, require
from scripts.verification.verify_lmb_history_archive import read, verify_evaluation


LMB = ROOT / 'experiments/methods/lmb'
SKILLADAM = ROOT / 'experiments/methods/skilladam/lmb'
ROLLOUTS = ('training', 'validation_parent', 'validation_candidate')


def verify_native(archive, published, manifest, optimization):
    """Read the frozen schedule and reconcile receipts with each decision."""
    source = Path(manifest['training'])
    frozen = read(archive, source / 'frozen.json')
    checkpoint = read(archive, source / 'native/checkpoint.json')
    initial = frozen['initial_skill'].encode()
    rounds, skills, final = check_training(archive, published, manifest, initial, optimization)
    require(skills['R00'] == initial and checkpoint['current_skill'].encode() == final
            and archive.read_bytes(source / 'native/final_skill.md') == final,
            f'Initial or final Skill differs: {published}')
    decision_rounds = checkpoint['iterations']
    require(len(decision_rounds) == checkpoint['next_iteration'] == len(rounds) - 1
            and len(frozen['batches']) == manifest['planned_rounds']
            and checkpoint['terminal_stop_reason'] == manifest['stop_reason'],
            f'Training status differs: {published}')

    previous = initial
    for index, decision in enumerate(decision_rounds):
        node = f'R{index + 1:02}'
        batch = frozen['batches'][index]
        saved = manifest['checkpoints'][index + 1]
        require(decision['iteration'] == index
                and decision['training_case_ids'] == batch == decision['validation_case_ids']
                and saved['node'] == node and saved['gate_accepted'] == decision['accepted'],
                f'Frozen batch differs: {published} / {node}')
        rollouts = source / 'rollouts' / f'iter_{index:03}'
        candidate = archive.read_bytes(rollouts / 'validation_candidate/skill.md')
        require(skills[node] == (candidate if decision['accepted'] else previous),
                f'Accepted Skill differs: {published} / {node}')
        for role, expected_skill in zip(ROLLOUTS, (previous, previous, candidate)):
            folder = rollouts / role
            plan = read(archive, folder / 'actor/batch.json')['signature']
            records = read(archive, folder / 'actor/records.json')
            expected_role = 'candidate' if role == 'validation_candidate' else 'parent'
            require(plan['tasks'] == batch and plan['skill'].encode() == expected_skill
                    and plan['config']['role'] == expected_role and plan['config']['split'] == 'train'
                    and plan['actor'] == frozen['config']['actor']
                    and archive.read_bytes(folder / 'skill.md') == expected_skill
                    and [row['task_id'] for row in records] == batch
                    and all(row['execution']['skill'].encode() == expected_skill
                            and row['execution']['actor'] == plan['actor'] for row in records),
                    f'Rollout binding differs: {published} / {node} / {role}')
        previous = skills[node]
    return rounds, skills


def verify_entries(archive, evaluations, skills, test):
    require(len({entry['id'] for entry in evaluations}) == len(evaluations), 'Duplicate evaluation ID')
    results = []
    for entry in evaluations:
        result = verify_evaluation(archive, entry, skills[entry['node']], test)
        if 'historical_comparison' in entry:
            comparison = read(archive, entry['historical_comparison'])
            require(comparison['completed'] == result['scored']
                    and comparison['correct_on_common_tasks']['new_skilladam'] == result['correct']
                    and sorted(comparison['pending']) == result['unscored'],
                    f'Historical comparison differs: {entry["id"]}')
        results.append(result)
    return results


def verify():
    collection = json.loads((SKILLADAM / 'history.json').read_bytes())
    splits = json.loads((LMB / 'splits.json').read_bytes())
    test = set(splits['test'])
    optimization = set(splits['train'] + splits['selection'])
    require(len(test) == 124 and len(optimization) == 53 and not test & optimization, 'Invalid LMB split')
    initial = (LMB / 'initial_skill.md').read_bytes()
    archive = Archive('lmb')
    try:
        reports = []
        for name in collection['runs']:
            published = SKILLADAM / name
            manifest = json.loads((published / 'archive.json').read_bytes())
            require(manifest['run_id'] == name, f'Unexpected SkillAdam manifest: {name}')
            rounds, skills = verify_native(archive, published, manifest, optimization)
            reports.append({'run_id': name, 'planned_rounds': manifest['planned_rounds'],
                            'stop_reason': manifest['stop_reason'], 'round_episodes': rounds,
                            'episodes': sum(rounds.values()), 'initial_skill_sha256': digest(skills['R00']),
                            'evaluations': verify_entries(archive, manifest['evaluations'], skills, test)})

        official = SKILLADAM / collection['supplemental_run']
        manifest = json.loads((official / 'archive.json').read_bytes())
        _, skills, _ = check_training(archive, official, manifest, initial, optimization)
        supplemental = verify_entries(archive, manifest['supplemental_evaluations'], skills, test)

        upstream = collection['upstream']
        skill = (SKILLADAM / upstream['skill']).read_bytes()
        require(skill == archive.read_bytes(upstream['frozen_skill']), 'Upstream Skill differs')
        return {'runs': reports, 'supplemental': supplemental,
                'upstream': verify_entries(archive, upstream['evaluations'], {'upstream': skill}, test)}
    finally:
        archive.close()


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(verify(), ensure_ascii=False, indent=2))

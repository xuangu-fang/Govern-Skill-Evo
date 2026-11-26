"""Read the historical SkillOpt runs and supplemental LMB evaluations offline."""
import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.benchmark_record_refs.restore import Archive
from scripts.verification.verify_lmb_comparison_archive import check_training, digest, require
from scripts.verification.verify_lmb_history_archive import plan_ids, read, score_rows, verify_evaluation


LMB = ROOT / 'experiments/methods/lmb'
SKILLOPT = ROOT / 'experiments/methods/skillopt/lmb'


def verify_native_batches(archive, manifest, train, selection):
    """Match the native aggregate rows to each batch plan and its Actor receipts."""
    actor = read(archive, f'{manifest["source"]}/run.json')['actor']['model']
    for checkpoint in manifest['checkpoints']:
        slow_pair = []
        for receipt in checkpoint['receipts']:
            batch = Path(receipt).parent
            identifier = f'{manifest["run_id"]}: {batch}'
            plan = read(archive, batch / 'binding.json')
            if batch.name in ('rollout_curr', 'rollout_prev'):
                require(set(plan['ids']) <= train, f'Slow update used tasks outside Train: {identifier}')
                slow_pair.append((plan['ids'], plan['presentations']))
            else:
                expected = train if batch.name == 'rollout' else selection
                require(set(plan['ids']) == expected, f'Native split differs: {identifier}')
            rows = [json.loads(line) for line in archive.read_bytes(receipt).splitlines() if line.strip()]
            descriptor = {'id': identifier, 'actor': actor,
                          'batches': [{'directory': batch.as_posix(), 'layout': 'actor'}]}
            actual = score_rows(archive, descriptor, plan['skill'].encode())
            require(len(plan['ids']) == len(actual) and set(plan['ids']) == actual.keys()
                    and actual == {row['id']: row['em'] for row in rows},
                    f'Native scores or planned IDs differ: {identifier}')
        if slow_pair:
            require(len(slow_pair) == 2 and slow_pair[0] == slow_pair[1],
                    f'Slow update is missing paired task presentations: {checkpoint["node"]}')


def verify():
    collection = json.loads((SKILLOPT / 'history.json').read_bytes())
    splits = json.loads((LMB / 'splits.json').read_bytes())
    train, selection, test = (set(splits[key]) for key in ('train', 'selection', 'test'))
    require((len(train), len(selection), len(test), len(train | selection | test)) == (35, 18, 124, 177),
            'Invalid LMB split')
    initial = (LMB / 'initial_skill.md').read_bytes()
    archive = Archive('lmb')
    try:
        upstream = collection['upstream']
        upstream_eval = upstream['evaluation']
        upstream_skill = (SKILLOPT / upstream['skill']).read_bytes()
        upstream_report = verify_evaluation(archive, upstream_eval, upstream_skill, test)
        meta53 = plan_ids(archive, upstream_eval, upstream_skill)
        scope_tasks = {'Test124': test, 'Meta53': meta53, 'Other71': test - meta53}
        reports = []
        for name in [*collection['native_runs'], collection['supplemental_run']]:
            published = SKILLOPT / name
            manifest = json.loads((published / 'archive.json').read_bytes())
            require(manifest['run_id'] == name, f'Unexpected SkillOpt manifest: {name}')
            rounds, skills, final = check_training(archive, published, manifest, initial, train | selection)
            if name == collection['supplemental_run']:
                evaluations = manifest['supplemental_evaluations']
            else:
                verify_native_batches(archive, manifest, train, selection)
                origin = manifest['best']
                selected = read(archive, f'{manifest["source"]}/selection.json')
                usage = read(archive, f'{manifest["source"]}/training_cost.json')
                require((selected['best_origin'], selected['best_step']) == (origin['origin'], origin['step'])
                        and selected['sha256'] == digest(final) and archive.read_bytes(origin['source']) == final,
                        f'Best Skill differs from the final Selection: {name}')
                require(usage['actor']['scored'] == sum(rounds.values()), f'Training cost differs: {name}')
                evaluations = manifest['evaluations']
            require(len({item['id'] for item in evaluations}) == len(evaluations),
                    f'Duplicate evaluation ID: {name}')
            results = []
            for evaluation in evaluations:
                node = skills[evaluation['node']]
                require(plan_ids(archive, evaluation, node) == scope_tasks[evaluation['scope']],
                        f'SkillOpt evaluation has a different split: {evaluation["id"]}')
                results.append(verify_evaluation(archive, evaluation, node, test))
            reports.append({'run_id': name, 'round_episodes': rounds, 'episodes': sum(rounds.values()),
                            'evaluations': results})
        return {'runs': reports, 'upstream': upstream_report}
    finally:
        archive.close()


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(verify(), ensure_ascii=False, indent=2))

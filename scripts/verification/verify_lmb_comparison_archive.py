"""Read the three LiveMathematicianBench comparison runs offline."""
import argparse
import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.benchmark_record_refs.restore import Archive


COMPARISON = ROOT / 'experiments/methods/lmb/comparison.json'
TASK_ID = re.compile(r'\d{6}:\d+')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def labels(result):
    answer = result['answer']
    prediction, reference = answer.get('predicted_label'), answer['correct_label']
    require(reference in ('A', 'B', 'C', 'D', 'E'), 'Invalid LMB reference label')
    correct = int(prediction == reference)
    require(result['metrics']['em'] == correct, 'EM differs from the option labels')
    return correct


def iter_batch(archive, batch):
    location = archive.source_path(batch['directory'])
    key = lambda p: p.relative_to(ROOT).as_posix()
    if batch['layout'] == 'tasks':
        for receipt in sorted(location.glob('tasks/*/records.json')):
            for row in json.loads(archive.read_bytes(key(receipt))):
                require(receipt.parent.name == row['task_id'].replace(':', '_'),
                        f'Task ID differs from its receipt path: {receipt}')
                yield row['task_id'], row['execution']
    elif batch['layout'] == 'actor':
        for result in sorted(location.glob('actor/*/result.json')):
            signature = json.loads(archive.read_bytes(key(result.with_name('signature.json'))))
            name = result.parent.name
            uid = signature.get('case_id', name)
            require(not TASK_ID.fullmatch(name) or uid == name,
                    f'Task ID differs from actor directory: {result}')
            if uid in batch.get('excluded_ids', ()):
                continue
            row = json.loads(archive.read_bytes(key(result)))
            reference = signature.get('reference', {})
            if 'label' in reference:
                require(reference['label'] == row['answer']['correct_label'],
                        f'Signature reference differs from rollout: {result}')
            yield uid, row
    else:
        raise ValueError(f'Unknown LMB evaluation layout: {batch}')


def count_receipts(archive, source):
    raw = archive.read_bytes(source)
    rows = ([json.loads(line) for line in raw.splitlines() if line.strip()]
            if source.endswith('.jsonl') else json.loads(raw))
    ids = [row.get('task_id', row.get('id')) for row in rows]
    require(all(isinstance(uid, str) and TASK_ID.fullmatch(uid) for uid in ids),
            f'Missing or invalid task ID in {source}')
    require(len(set(ids)) == len(ids), f'Duplicate task in {source}')
    return set(ids)


def check_evaluation(archive, published, evaluation, skill, test_ids):
    summary_path = published / 'results' / 'evaluations' / evaluation['id'] / 'summary.json'
    summary = json.loads(summary_path.read_bytes())
    require(digest(skill) == summary['skill_sha256'], f'Skill SHA-256 differs: {summary_path}')

    def check_score(uid, result, allow_summary_binding=False):
        require(uid in test_ids and uid not in scores, f'Unexpected or repeated task {uid}: {summary_path}')
        skill_text = result.get('skill')
        if skill_text is None:
            require(allow_summary_binding, f'Missing rollout Skill: {summary_path} / {uid}')
        else:
            require(skill_text.encode() == skill, f'Rollout Skill bytes differ: {summary_path} / {uid}')
        if 'actor' in result:
            require(result['actor']['model'] == 'deepseek-flash', f'Unexpected Actor: {summary_path} / {uid}')
        scores[uid] = labels(result)

    scores = {}
    for batch in evaluation['batches']:
        for uid, result in iter_batch(archive, batch):
            check_score(uid, result)
    historical = json.loads(archive.read_bytes(evaluation['historical_summary']))
    if 'skill_sha256' in historical:
        require(historical['skill_sha256'] == summary['skill_sha256'],
                f'Historical summary has a different Skill: {summary_path}')
    for uid, source in evaluation.get('supplements', {}).items():
        row = json.loads(archive.read_bytes(source))
        require(row.get('task', uid) == uid, f'Supplement task differs: {source}')
        check_score(uid, row, historical.get('skill_sha256') == summary['skill_sha256'])
    require(scores.keys() == test_ids, f'Incomplete Test124: {summary_path}')
    historical_totals = historical.get('full124', historical.get('common_124', historical))
    expected_correct = historical_totals.get('correct', historical_totals.get('success_count'))
    expected_scored = historical_totals.get('scored', historical_totals.get(
        'completed', historical_totals.get('sample_count', historical_totals.get('total'))))
    correct = sum(scores.values())
    require((expected_scored, expected_correct) == (len(scores), correct)
            and (summary['completed'], summary['correct']) == (len(scores), correct)
            and summary['em'] == correct / len(scores), f'EM summary differs: {summary_path}')
    return correct


def check_training(archive, published, manifest, common_skill, optimization_ids):
    for snapshot, source in manifest['snapshots'].items():
        require((published / snapshot).read_bytes() == archive.read_bytes(source),
                f'Snapshot differs from its source: {published / snapshot}')
    rounds = {}
    skills = {}
    previous = common_skill
    for checkpoint in manifest['checkpoints']:
        node = checkpoint['node']
        require(node not in skills, f'Duplicate checkpoint: {node}')
        skill = (published / 'results' / 'skills' / f'{node}.md').read_bytes()
        if checkpoint.get('source'):
            require(skill == archive.read_bytes(checkpoint['source']), f'Checkpoint Skill differs: {node}')
        require((skill != previous) == checkpoint['accepted'], f'Unexpected retention decision: {node}')
        skills[node] = previous = skill
        batches = [count_receipts(archive, source) for source in checkpoint['receipts']]
        roles = checkpoint['episode_counts']
        require([len(ids) for ids in batches] == roles and all(ids <= optimization_ids for ids in batches),
                f'Training/selection receipts differ at {manifest["method"]} {node}')
        if checkpoint.get('same_tasks'):
            require(all(ids == batches[0] for ids in batches), f'Mismatched paired tasks: {node}')
        rounds[node] = sum(roles)
    final_skill = (published / 'results' / 'final_skill.md').read_bytes()
    require(final_skill == previous, f'Final Skill differs: {published}')
    return rounds, skills, final_skill


def check_run(archive, published, common_skill, test_ids, optimization_ids):
    manifest = json.loads((published / 'archive.json').read_bytes())
    rounds, skills, final_skill = check_training(archive, published, manifest, common_skill, optimization_ids)
    scores = {}
    for evaluation in manifest['evaluations']:
        require(evaluation['id'] not in scores, f'Duplicate evaluation: {evaluation["id"]}')
        scores[evaluation['id']] = check_evaluation(
            archive, published, evaluation, skills[evaluation['node']], test_ids)
    finals = [scores[name] for name in manifest['final_evaluations']]
    require(len(finals) == 3 and all(
        skills[item['node']] == final_skill for item in manifest['evaluations']
        if item['id'] in manifest['final_evaluations']), f'Wrong final evaluation set: {published}')
    return {'method': manifest['method'], 'run_id': manifest['run_id'],
            'round_episodes': rounds, 'episodes': sum(rounds.values()),
            'correct': scores, 'final_correct': finals, 'median_correct': int(median(finals)),
            'test_count': len(test_ids), 'median_em': median(finals) / len(test_ids)}


def verify():
    index = json.loads(COMPARISON.read_bytes())
    splits = json.loads((COMPARISON.parent / 'splits.json').read_bytes())
    require([len(splits[name]) for name in ('train', 'selection', 'test')] == [35, 18, 124],
            'Expected the 35/18/124 split')
    require(len(set(splits['train'] + splits['selection'] + splits['test'])) == 177,
            'Sets contain duplicated IDs')
    test_ids = set(splits['test'])
    optimization_ids = set(splits['train'] + splits['selection'])
    common_skill = (COMPARISON.parent / 'initial_skill.md').read_bytes()
    archive = Archive('lmb')
    try:
        shared = check_evaluation(archive, COMPARISON.parent, index['initial_evaluation'], common_skill, test_ids)
        results = [check_run(archive, ROOT / run, common_skill, test_ids, optimization_ids)
                   for run in index['runs']]
        require(shared == 44 and [(r['median_correct'], r['episodes']) for r in results] ==
                [(91, 96), (61, 159), (89, 404)], 'Main comparison differs from the experiment log')
        return {'test_count': len(test_ids), 'shared_initial_correct': shared, 'runs': results}
    finally:
        archive.close()


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(verify(), ensure_ascii=False, indent=2))

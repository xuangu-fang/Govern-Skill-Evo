"""Verify archived LiveMathematicianBench training and evaluation records."""
import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.benchmark_record_refs.restore import Archive
from scripts.verification.verify_lmb_comparison_archive import check_training, digest, iter_batch, labels, require


LMB = ROOT / 'experiments/methods/lmb'
HISTORY = LMB / 'history.json'


def read(archive, path):
    return json.loads(archive.read_bytes(path))


def scored_attempt(archive, descriptor, evaluation, skill):
    directory = Path(descriptor['directory'])
    signature = read(archive, descriptor['signature'])
    request = read(archive, directory / 'request.json')['body']
    response = read(archive, directory / 'response.json')['choices'][0]
    score = read(archive, directory / descriptor.get('receipt', 'score.json'))
    uid = score['task_id'] if 'task_id' in score else score['task']
    if descriptor.get('receipt') == 'outcome.json':
        # One historical supplement stored the two labels and EM directly.
        require(score['finish_reason'] == 'stop' and request['max_tokens'] == score['max_tokens'],
                f'Supplement outcome has a different termination or budget: {directory}')
        score = {'answer': {'raw_content': response['message']['content'],
                            'predicted_label': score['predicted_label'],
                            'correct_label': score['correct_label']},
                 'metrics': {'em': score['em']}}
    answer = score['answer']
    require(request['model'] == evaluation['actor'] == signature['actor']['model']
            and request['messages'] == signature['messages'] and signature['skill'].encode() == skill,
            f'Supplement request differs from its original task: {directory}')
    require(uid == signature['case_id'] and response['finish_reason'] == 'stop'
            and response['message']['content'] == answer['raw_content']
            and response['message']['content'].strip() == f'<answer>{answer["predicted_label"]}</answer>'
            and signature['reference']['label'] == answer['correct_label'],
            f'Supplement response or score differs: {directory}')
    return uid, score


def score_rows(archive, evaluation, skill):
    scores = {}

    def add(uid, result, bound=False):
        require(uid not in scores, f'Duplicate evaluation receipt for {uid}: {evaluation["id"]}')
        if not bound:
            require(result['actor']['model'] == evaluation['actor'] and result['skill'].encode() == skill,
                    f'Actor or actual Skill differs: {evaluation["id"]} / {uid}')
        scores[uid] = labels(result)

    for batch in evaluation['batches']:
        for uid, result in iter_batch(archive, batch):
            add(uid, result)
    for uid, source in evaluation.get('supplements', {}).items():
        result = read(archive, source)
        if 'skill' in result:
            signature = read(archive, str(Path(source).with_name('signature.json')))
            require(signature['case_id'] == uid, f'Wrong supplement task: {source}')
            add(uid, result)
        else:
            report = read(archive, evaluation['historical_summary'])
            require(result['task'] == uid and report['skill_sha256'] == digest(skill)
                    and report['supplement'].endswith('/' + source),
                    f'Supplement lacks a matching historical binding: {source}')
            add(uid, result, bound=True)
    for attempt in evaluation.get('scored_attempts', ()):
        uid, score = scored_attempt(archive, attempt, evaluation, skill)
        add(uid, score, bound=True)
    return scores


def plan_ids(archive, evaluation, skill=None):
    plan = read(archive, evaluation['binding'])
    if 'signature' in plan:
        plan = plan['signature']
    actor_plan = read(archive, evaluation['actor_binding']) if 'actor_binding' in evaluation else plan
    actor = actor_plan['actor'] if 'actor' in actor_plan else actor_plan['runtime']['actor']
    require(actor['model'] == evaluation['actor'], f'Planned Actor differs: {evaluation["id"]}')
    if skill is not None:
        key = evaluation.get('binding_skill')
        binding = plan['skills'][key] if key else plan.get('skill')
        skill_hash = digest(skill)
        require(plan.get('skill_sha256', skill_hash) == skill_hash,
                f'Planned Skill differs: {evaluation["id"]}')
        if isinstance(binding, dict):
            require(binding.get('sha256', skill_hash) == skill_hash,
                    f'Planned Skill binding differs: {evaluation["id"]}')
            text = binding.get('text')
        else:
            text = binding
        if text is not None:
            require(text.encode() == skill, f'Planned Skill text differs: {evaluation["id"]}')
    ids = plan.get('tasks', plan.get('ids'))
    require(len(ids) == len(set(ids)), f'Duplicate planned task: {evaluation["id"]}')
    return set(ids)


def verify_report(archive, evaluation, correct, completed, skill):
    report_source = evaluation.get('historical_summary')
    if not report_source:
        return
    report = read(archive, report_source)
    # The original v27 evaluator hashed the JSON-encoded Skill string.
    historical_skill = (json.dumps(skill.decode(), ensure_ascii=False, separators=(',', ':')).encode()
                        if report.get('version') == 'v27_lmb_test_v1' else skill)
    expected_hash = digest(historical_skill)
    require(report.get('skill_sha256', expected_hash) == expected_hash, f'Historical Skill differs: {report_source}')
    for key in evaluation.get('summary_section', []):
        report = report[key]
    reported_correct = next((report[key] for key in ('correct', 'success_count', 'variant_correct',
                              'correct_completed', 'correct_on_completed', 'exact_matches')
                             if report.get(key) is not None), None)
    reported_count = report.get('scored', report.get('completed', report.get('sample_count', report.get('total'))))
    require(reported_count == completed and (reported_correct == correct or (
            reported_correct is None and report.get('status') == 'incomplete')),
            f'Historical count differs: {report_source}')
    if 'pending_ids' in report:
        require(sorted(report['pending_ids']) == evaluation['result']['unscored'],
                f'Historical unscored tasks differ: {report_source}')


def verify_evaluation(archive, evaluation, skill, test):
    planned = plan_ids(archive, evaluation, skill)
    scope = evaluation['scope']
    require(len(planned) == {'Test124': 124, 'Meta53': 53, 'Other71': 71, 'Stronger51': 51}[scope]
            and planned <= test,
            f'Unexpected planned split: {evaluation["id"]}')
    if 'meta53_source' in evaluation:
        original = read(archive, evaluation['meta53_source'])
        require(scope == 'Meta53' and planned == set(original['meta53']),
                f'Meta53 retest differs from the original subset: {evaluation["id"]}')
    scores = score_rows(archive, evaluation, skill)
    if 'coverage' in evaluation:
        coverage = read(archive, evaluation['coverage'])
        require(coverage['total'] == len(planned)
                and sorted(coverage['scored_ids']) == sorted(scores)
                and sorted(coverage['pending_ids']) == sorted(planned - scores.keys()),
                f'Historical coverage differs: {evaluation["id"]}')
    correct = sum(scores.values())
    completed = len(scores)
    summary = evaluation['result']
    require(scores.keys() <= planned and sorted(planned - scores.keys()) == summary['unscored']
            and (correct, completed, len(planned)) == (summary['correct'], summary['scored'], summary['planned'])
            and summary['skill_sha256'] == digest(skill), f'Archive rollup differs: {evaluation["id"]}')
    em = correct / completed if completed else None
    require(summary['em'] == em, f'EM differs: {evaluation["id"]}')
    verify_report(archive, evaluation, correct, completed, skill)
    return {'id': evaluation['id'], 'node': evaluation['node'], 'scope': scope, 'actor': evaluation['actor'],
            'correct': correct, 'scored': completed, 'planned': len(planned), 'unscored': summary['unscored']}


def verify():
    history = json.loads(HISTORY.read_bytes())
    splits = json.loads((LMB / 'splits.json').read_bytes())
    test = set(splits['test'])
    optimization = set(splits['train'] + splits['selection'])
    require(len(test) == 124 and len(optimization) == 53 and not test & optimization, 'Invalid held-out split')
    initial = (LMB / 'initial_skill.md').read_bytes()
    archive = Archive('lmb')
    try:
        results = []
        for name in history['runs']:
            published = ROOT / name
            manifest = json.loads((published / 'archive.json').read_bytes())
            rounds, skills, _ = check_training(archive, published, manifest, initial, optimization)
            for variant, source in manifest.get('variants', {}).items():
                snapshot = (published / 'results' / 'skills' / f'{variant}.md').read_bytes()
                require(snapshot == archive.read_bytes(source), f'Variant Skill differs: {variant}')
                skills[variant] = snapshot
            evaluations = manifest.get('cross_actor_evaluations', manifest['evaluations'])
            require(len({item['id'] for item in evaluations}) == len(evaluations),
                    f'Duplicate evaluation ID: {name}')
            reports = [verify_evaluation(archive, item, skills[item['node']], test)
                       for item in evaluations]
            results.append({'run_id': manifest['run_id'], 'round_episodes': rounds,
                            'episodes': sum(rounds.values()), 'evaluations': reports})
        return results
    finally:
        archive.close()


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(verify(), ensure_ascii=False, indent=2))

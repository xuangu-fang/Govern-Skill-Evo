"""Verify SearchQA experiment bundles from frozen inputs and original Test receipts."""

import argparse
from contextlib import closing, contextmanager
from hashlib import sha256
from io import BytesIO
import json
from math import isclose
from pathlib import Path
import runpy
from statistics import median
import sys
from tempfile import TemporaryFile

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM = ROOT / 'src/skill_evolution/skilladam/upstream'
sys.path[:0] = [str(ROOT), str(UPSTREAM)]

from experiments.benchmark_record_refs.restore import Archive, SELECT
from src.skill_evolution.v28.benchmarks.searchqa.protocol import digest, require
from src.skill_evolution.v28.benchmarks.searchqa.scoring import score, summarize_scores

MANIFEST = 'experiments/benchmarks/searchqa/main-comparison.json'


def local_path(key):
    relative = Path(key)
    path = ROOT / relative
    require(not relative.is_absolute() and '..' not in relative.parts
            and path.resolve().is_relative_to(ROOT), f'Invalid repository path: {key}')
    return path


def checked_bytes(record):
    data = local_path(record['path']).read_bytes()
    require(sha256(data).hexdigest() == record['sha256'], f"File digest differs: {record['path']}")
    return data


def read_json(key):
    return json.loads(local_path(key).read_bytes())


@contextmanager
def original_stream(archive, record):
    key = record['path']
    source = local_path(key).read_bytes()
    row = archive.db.execute(SELECT + ' WHERE r.path=?', (key,)).fetchone()
    with TemporaryFile() as stream:
        if row is None:
            actual = sha256(source).hexdigest()
            stream.write(source)
        else:
            archive.verify_bytes(row, source, stream)
            actual = row[1].hex()
        require(actual == record['sha256'], f'Original digest differs: {key}')
        stream.seek(0)
        yield stream


def verify_copies(archive, files):
    require(len({entry['new'] for entry in files}) == len(files), 'Duplicate selected path')
    for entry in files:
        source = {'path': entry['old'], 'sha256': entry['sha256']}
        with original_stream(archive, source) as stream:
            selected = local_path(entry['new']).read_bytes()
            require(selected == stream.read(), f"Selected copy differs: {entry['new']}")


def read_case_receipt(archive, path):
    key = path.as_posix()
    raw = local_path(key).read_bytes()
    row = archive.db.execute(SELECT + ' WHERE r.path=?', (key,)).fetchone()
    if row is None:
        return json.loads(raw)
    with BytesIO() as stream:
        archive.verify_bytes(row, raw, stream)
        return json.loads(stream.getvalue())


def verified_skill(entry):
    identity = entry['id']
    skill_bytes = local_path(entry['skill']).read_bytes()
    skill = skill_bytes.decode('utf-8')
    skill_sha = sha256(skill_bytes).hexdigest()
    require(skill_sha == entry['skill_sha256'], f'Evaluated Skill differs: {identity}')
    if 'training_skill' in entry:
        require(checked_bytes(entry['training_skill']) == skill_bytes,
                f'Training checkpoint Skill differs: {identity}')
    return skill, skill_sha


def verify_case(execution, item, skill, actor, name):
    require(execution['skill'] == skill and execution['actor'] == actor,
            f'Receipt Skill or Actor differs: {name}')
    answer, metrics = score(execution['content'], item['answers'])
    require(answer == execution['answer'] and metrics == execution['metrics'],
            f'Score from Actor response differs: {name}')
    return metrics


def verify_evaluation(archive, entry, items, test_ids):
    identity = entry['id']
    skill, skill_sha = verified_skill(entry)
    with original_stream(archive, entry['plan']) as stream:
        plan = json.load(stream)
    actor = plan['actor']
    plan_skill = plan['skill'] if isinstance(plan['skill'], str) else plan['skill']['text']
    require(plan['tasks'] == test_ids and plan_skill == skill and actor['model'] == entry['actor']
            and plan['workers'] == entry['workers'], f'Frozen Test plan differs: {identity}')

    per_case = {}
    requests = 0
    with original_stream(archive, entry['journal']) as stream:
        for receipt in json.load(stream):
            uid = receipt['task_id']
            require(uid in items and uid not in per_case, f'Unknown or duplicate Test ID: {identity}/{uid}')
            row = items[uid]
            task = receipt['task']
            execution = receipt['execution']
            require(task == {'id': uid, 'split': 'test', 'question': row['question'], 'context': row['context']}
                    and receipt['provenance']['role'] == 'evaluation', f'Test payload differs: {identity}/{uid}')
            per_case[uid] = verify_case(execution, row, skill, actor, f'{identity}/{uid}')
            requests += execution['api_requests']

    return verify_aggregate(entry, skill, skill_sha, per_case, test_ids, requests)


def verify_aggregate(entry, skill, skill_sha, per_case, test_ids, requests):
    identity = entry['id']
    result = summarize_scores([{'task_id': uid, 'metrics': metrics} for uid, metrics in per_case.items()], test_ids)
    report = json.loads(local_path(entry['report']).read_bytes())
    reported_hash = report.get('skill_sha256')
    require(report['status'] == 'complete' and reported_hash in (None, skill_sha, digest(skill)),
            f'Completion or report Skill hash differs: {identity}')
    require(report.get('actor_requests', report.get('api_requests')) == requests,
            f'Actor request count differs: {identity}')
    if 'cases' in report:
        cases = report['cases']
        require(len(cases) == len(test_ids) and {c['task_id']: c['metrics'] for c in cases} == per_case,
                f'Reported case scores differ: {identity}')
    observed = report.get('summary', report)
    for key, value in result.items():
        require(isclose(value, observed[key], rel_tol=0, abs_tol=1e-12)
                and isclose(value, entry['expected'][key], rel_tol=0, abs_tol=1e-12),
                f'Aggregate {key} differs: {identity}')
    return {'id': identity, 'method': entry['method'], 'skill_sha256': skill_sha, **result}


def verify_cross_actor(archive, entry, items, test_ids):
    identity = entry['id']
    skill, skill_sha = verified_skill(entry)
    with original_stream(archive, entry['plan']) as stream:
        plan = json.load(stream)
    actor = plan['actor']
    arm = plan['skills'][entry['method']]
    require(plan['tasks'] == test_ids and plan['workers_per_skill'] == entry['workers']
            and actor['model'] == entry['actor'] and arm['sha256'] == skill_sha
            and Path(arm['source']).as_posix().endswith('/' + entry['training_skill']['path']),
            f'Cross-Actor Test plan differs: {identity}')

    root = local_path(entry['source']) / 'runs'
    directories = {path.name for path in root.iterdir() if path.is_dir()}
    require(directories == set(test_ids), f'Cross-Actor receipt directories differ: {identity}')
    per_case = {}
    requests = 0
    for uid in test_ids:
        folder = Path(entry['source']) / 'runs' / uid
        signature = read_case_receipt(archive, folder / 'signature.json')
        execution = read_case_receipt(archive, folder / 'result.json')
        row = items[uid]
        require(signature['case_id'] == uid and signature['metadata']['split'] == 'test'
                and signature['payload'] == {'question': row['question'], 'context': row['context']}
                and signature['reference'] == row['answers'] and signature['skill'] == skill
                and signature['actor'] == actor and signature['messages'] == execution['initial_messages'],
                f'Cross-Actor signature differs: {identity}/{uid}')
        per_case[uid] = verify_case(execution, row, skill, actor, f'{identity}/{uid}')
        requests += execution['api_requests']
    with original_stream(archive, entry['journal']) as stream:
        saved = json.load(stream)
    require(len(saved) == len(test_ids) and {row['task_id']: row['metrics'] for row in saved} == per_case,
            f'Cross-Actor score ledger differs: {identity}')
    return verify_aggregate(entry, skill, skill_sha, per_case, test_ids, requests)


def verify_main200(archive, entry, items, evaluate):
    identity = entry['id']
    skill, skill_sha = verified_skill(entry)
    per_case = {}
    with original_stream(archive, entry['journal']) as stream:
        for line in stream:
            receipt = json.loads(line)
            uid = receipt['id']
            require(uid in items and uid not in per_case, f'Unknown or duplicate Test100 ID: {identity}/{uid}')
            row = items[uid]
            require(receipt['question'] == row['question'] and receipt['gold_answers'] == row['answers'],
                    f'Test100 payload differs: {identity}/{uid}')
            prompt = local_path(Path(entry['source']) / 'predictions' / uid / 'target_system_prompt.txt')
            require(skill.strip() in prompt.read_text(), f'Test100 Skill differs: {identity}/{uid}')
            result = evaluate(receipt['response'], row['answers'])
            require(all(receipt[key] == value for key, value in result.items())
                    and receipt['hard'] == result['em'] and receipt['soft'] == result['f1'],
                    f'Original SkillOpt scoring differs: {identity}/{uid}')
            per_case[uid] = {key: result[key] for key in ('em', 'f1')}
    ids = sorted(per_case)
    cohort = sha256('\n'.join(ids).encode()).hexdigest()
    result = summarize_scores([{'task_id': uid, 'metrics': per_case[uid]} for uid in ids], ids)
    report = read_json(entry['report'])['overall']
    require(result['sample_count'] == report['total'] == 100 and cohort == entry['cohort_sha256']
            and result['em'] == report['hard_acc'] and all(
                isclose(value, entry['expected'][key], rel_tol=0, abs_tol=1e-12) for key, value in result.items()),
            f'Test100 report or cohort differs: {identity}')
    return {'id': identity, 'method': entry['method'], 'skill_sha256': skill_sha, 'cohort_sha256': cohort, **result}


def verify_evaluations(manifest):
    for scorer in manifest['scorer_sources']:
        checked_bytes(scorer)
    rows = json.loads(checked_bytes(manifest['test_items']))
    test_ids = [row['id'] for row in json.loads(checked_bytes(manifest['test_ids']))]
    items = {row['id']: row for row in rows}
    require(list(items) == test_ids and len(rows) == len(items) == len(test_ids) == 1400,
            'Test1400 order or ID set differs')

    with closing(Archive('searchqa')) as archive:
        verify_copies(archive, manifest['files'])
        if 'main200_scorer' in manifest:
            scorer = manifest['main200_scorer']
            checked_bytes(scorer)
            evaluate = runpy.run_path(str(local_path(scorer['path'])))['evaluate']
        evaluations = []
        for entry in manifest['evaluations']:
            layout = entry.get('layout', 'batch')
            if layout == 'cross_actor':
                evaluation = verify_cross_actor(archive, entry, items, test_ids)
            elif layout == 'main200':
                evaluation = verify_main200(archive, entry, items, evaluate)
            else:
                require(layout == 'batch', f'Unknown receipt layout: {layout}')
                evaluation = verify_evaluation(archive, entry, items, test_ids)
            evaluations.append(evaluation)
    results = {entry['id']: entry for entry in evaluations}
    require(len(results) == len(evaluations), 'Duplicate evaluation ID')
    return results


def verify_main(manifest, results):
    control = results[manifest['shared_r00']]
    require(control['method'] == '共用' and control['success_count'] == 1064, 'Shared R00 differs')

    summaries = []
    for run in manifest['runs']:
        initial = local_path(run['initial_skill']).read_bytes()
        final = local_path(run['final_skill']).read_bytes()
        if 'embedded_initial_skill' in run:
            frozen = json.loads(local_path(run['embedded_initial_skill']).read_bytes())
            require(frozen['initial_skill'].encode() == initial, f"Frozen initial Skill differs: {run['id']}")
        require(sha256(initial).hexdigest() == control['skill_sha256'], f"Initial Skill differs: {run['id']}")
        final_ids = run['final_evaluations']
        chosen_ids = run['plot_final_evaluations']
        final_scores = [results[k] for k in final_ids]
        require(len(final_ids) == len(set(final_ids)) and len(chosen_ids) == len(set(chosen_ids)) == 3
                and set(chosen_ids) <= set(final_ids) and all(
                    x['method'] == run['method'] and x['skill_sha256'] == sha256(final).hexdigest()
                    for x in final_scores), f"Final evaluation identity differs: {run['id']}")
        chosen = median(results[k]['success_count'] for k in chosen_ids)
        require(chosen == run['plot_final_correct'], f"Chart final EM differs: {run['id']}")
        for point in run['plot_points']:
            result = results[point['evaluation']]
            require(result['method'] == run['method'] and result['success_count'] == point['correct'],
                    f"Chart checkpoint differs: {run['id']}/{point['checkpoint']}")
        summaries.append({'method': run['method'], 'id': run['id'],
                          'final_correct': [x['success_count'] for x in final_scores],
                          'plot_final_correct': chosen, 'optimization_episodes': run['optimization_episodes']})
    return {'shared_r00_correct': control['success_count'], 'runs': summaries}


def verify_history_run(run, entries, results):
    identity = run['id']
    config = read_json(run['config'])
    summary = read_json(run['completion'])
    state = read_json(run['state'])
    initial = local_path(run['initial_skill']).read_bytes()
    final = local_path(run['final_skill']).read_bytes()
    batches = config['batches']
    optimization_ids = [uid for batch in batches for uid in batch]
    require(config['initial_skill']['text'].encode() == initial and summary['status'] == 'complete'
            and summary['method'] == config['method']['version']
            and len(batches) == summary['rounds_completed'] == run['rounds']
            and len(optimization_ids) == len(set(optimization_ids)) == summary['optimization_count']
            and summary['state'] == state and state['next_round'] == len(batches) + 1
            and state['parent'] == summary['selected_skill'], f'Training completion differs: {identity}')
    selected = run['selected_checkpoint']
    require(Path(selected['path']) == Path(run['source']) / summary['selected_skill']
            and checked_bytes(selected) == final, f'Final export differs from selected checkpoint: {identity}')

    run_entries = [entry for entry in entries if entry['training'] == identity]
    final_entries = [entry for entry in run_entries if entry['kind'] in ('终测', '复测')]
    final_ids = run['final_evaluations']
    require(final_entries and len(final_ids) == len(final_entries)
            and set(final_ids) == {entry['id'] for entry in final_entries}
            and all(entry['method'] == run['method'] for entry in run_entries)
            and all(results[key]['skill_sha256'] == sha256(final).hexdigest() for key in final_ids),
            f'Historical final evaluation identity differs: {identity}')
    for reuse in run.get('retained_skill_reuse', []):
        expected = results[reuse['evaluation']]['skill_sha256']
        require(reuse['evaluation'] in {entry['id'] for entry in run_entries}
                and all(sha256(checked_bytes(round_skill)).hexdigest() == expected
                        for round_skill in reuse['round_skills']), f'Reused round Skill differs: {identity}')
    return {'id': identity, 'method': run['method'], 'rounds': len(batches),
            'evaluations': len(run_entries), 'final_correct': [results[key]['success_count'] for key in final_ids]}


def verify_history(manifest, results):
    runs = {run['id']: run for run in manifest['runs']}
    entries = manifest['evaluations']
    require(len(runs) == len(manifest['runs']) and {entry['training'] for entry in entries} == runs.keys(),
            'Historical training identities differ')
    summaries = [verify_history_run(run, entries, results) for run in runs.values()]

    reference = manifest['shared_r00_reference']
    main = read_json(reference['manifest'])
    control = next(entry for entry in main['evaluations'] if entry['id'] == main['shared_r00'])
    r00_run = runs[reference['training']]
    require(control['id'] == reference['evaluation'] and control['method'] == '共用'
            and control['training_skill']['path'] == str(Path(r00_run['source']) / 'initial_skill.md')
            and checked_bytes(control['training_skill']) == local_path(r00_run['initial_skill']).read_bytes()
            and checked_bytes({'path': control['skill'], 'sha256': control['skill_sha256']})
            == local_path(r00_run['initial_skill']).read_bytes()
            and read_json(control['report'])['success_count'] == control['expected']['success_count'] == 1064,
            'Reused R00 differs from the historical initial Skill')

    alignment = manifest['skilladam_alignment']
    aligned = runs[alignment['training']]
    frozen = json.loads(checked_bytes(alignment['frozen']))
    config_path = str(Path(aligned['source']) / 'config.json')
    config_bytes = local_path(aligned['config']).read_bytes()
    require(frozen['config']['v28_config'] == config_path
            and frozen['sources'][config_path] == sha256(config_bytes).hexdigest()
            and frozen['batches'] == json.loads(config_bytes)['batches'], 'SkillAdam alignment differs')
    return {'runs': summaries, 'shared_r00_reference': reference,
            'skilladam_alignment_verified': True, 'results': list(results.values())}


def verify_remaining_run(run, entries):
    identity = run['id']
    config = read_json(run['config'])
    initial = local_path(run['initial_skill']).read_bytes()
    evidence = read_json(run['progress']['path'])
    field = run['progress']['field']
    rounds = evidence[field] - (field == 'next_round')
    require(rounds == run['rounds_or_steps'], f'Archived progress differs: {identity}')
    if 'controller_status' in run:
        controller = run['controller_status']
        require(read_json(controller['path'])['status'] == controller['status'],
                f'Historical controller state differs: {identity}')
    if field == 'next_round':
        require(config['initial_skill']['text'].encode() == initial
                and rounds <= len(config['batches']) and run['completed'] == (rounds == len(config['batches'])),
                f'Campaign config or completion differs: {identity}')
        selected = run['retained_skill']
        require(selected['source']['path'] == (Path(run['source']) / evidence['parent']).as_posix(),
                f'Campaign Parent differs: {identity}')
        if 'completion' in run:
            summary = read_json(run['completion'])
            require(summary['status'] == 'complete' and summary['rounds_completed'] == rounds
                    and summary['state'] == evidence, f'Campaign completion receipt differs: {identity}')
    elif field == 'next_iteration':
        require(config['initial_skill'].encode() == initial and len(evidence['iterations']) == rounds
                and (not run['completed'] or (evidence['pending_post_decision'] is None
                                             and len(config['batches']) == rounds)),
                f'SkillAdam checkpoint differs: {identity}')
        if run['completed']:
            require(evidence['current_skill'].encode() == local_path(run['final_skill']).read_bytes(),
                    f'SkillAdam final export differs: {identity}')
    elif field == 'steps':
        require(evidence['sha256'] == sha256(local_path(run['final_skill']).read_bytes()).hexdigest(),
                f'SkillOpt selected Skill differs: {identity}')
    else:
        require(field == 'total_steps' and 0 < evidence['best_step'] <= rounds,
                f'Main200 progress differs: {identity}')

    if 'retained_skill' in run:
        selected = run['retained_skill']
        retained = checked_bytes(selected['source'])
        require(retained == local_path(selected['path']).read_bytes(), f'Retained Skill differs: {identity}')
        if run['completed']:
            require(retained == local_path(run['final_skill']).read_bytes(), f'Final Skill differs: {identity}')
    if 'unmaterialized_test' in run:
        planned = run['unmaterialized_test']
        source = local_path(planned['source'])
        status = '目录为空' if source.is_dir() and not any(source.iterdir()) else '未定位' if not source.exists() else None
        require(not entries and not run['completed'] and status == planned['state'],
                f'Historical Test location has changed: {identity}')
    require(run['completed'] == ('final_skill' in run) and all(e['method'] == run['method'] for e in entries),
            f'Historical run or evaluation identity differs: {identity}')
    for entry in entries:
        if entry['kind'] in ('终测', '复测'):
            require(local_path(entry['skill']).read_bytes() == local_path(run['final_skill']).read_bytes(),
                    f'Historical final Test Skill differs: {entry["id"]}')
    return {'id': identity, 'method': run['method'], 'status': run['status'],
            'rounds_or_steps': rounds, 'evaluations': len(entries)}


def unique_index(rows, key):
    index = {row[key]: row for row in rows}
    require(len(rows) == len(index), f'Duplicate archive {key}')
    return index


def verify_inventory_coverage(manifest):
    inventory = read_json(manifest['inventory'])
    manifests = [read_json(path) for path in manifest['previous_manifests']] + [manifest]
    trained = unique_index([run for catalog in manifests for run in catalog['runs']], 'id')
    evaluated = unique_index([entry for catalog in manifests for entry in catalog['evaluations']], 'source')
    require(trained.keys() == unique_index(inventory['training'], 'id').keys()
            and evaluated.keys() == unique_index(inventory['evaluations'], 'source').keys(),
            'Archive coverage differs from the SearchQA inventory')
    return {'training': len(trained), 'evaluations': len(evaluated)}


def verify_remaining(manifest, results):
    source_references = [row for run in manifest['runs'] for row in run.get('original_references', [])]
    with closing(Archive('searchqa')) as archive:
        for row in source_references:
            with original_stream(archive, row):
                pass
    summaries = [verify_remaining_run(run, [entry for entry in manifest['evaluations']
                                            if entry['training'] == run['id']]) for run in manifest['runs']]
    main200 = [results[entry['id']] for entry in manifest['evaluations'] if entry.get('layout') == 'main200']
    require(len(main200) == 2 and len({row['cohort_sha256'] for row in main200}) == 1,
            'The historical SkillOpt pair used different Test100 cohorts')
    return {'runs': summaries, 'results': list(results.values()),
            'inventory_coverage': verify_inventory_coverage(manifest)}


def verify(manifest_path=MANIFEST):
    manifest = read_json(manifest_path)
    results = verify_evaluations(manifest)
    kind = manifest.get('kind', 'comparison')
    summarize = {'comparison': verify_main, 'history': verify_history, 'remaining': verify_remaining}[kind]
    summary = summarize(manifest, results)
    return {'status': 'verified', 'selected_files': len(manifest['files']), 'evaluations': len(results),
            'receipts': sum(x['sample_count'] for x in results.values()), **summary}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default=MANIFEST, help='Repository-relative bundle manifest')
    args = parser.parse_args()
    print(json.dumps(verify(args.manifest), ensure_ascii=False, indent=2))

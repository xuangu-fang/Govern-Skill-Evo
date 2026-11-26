"""Verify selected DocVQA files and rescore the original evaluation receipts."""
import argparse
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import runpy
from statistics import mean, median
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from experiments.docvqa_image_refs.read_archive import DocVQAArchive

MANIFEST = 'experiments/benchmarks/docvqa/main-comparison.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local(key):
    path = (ROOT / key).resolve()
    require(path.is_relative_to(ROOT) and not Path(key).is_absolute() and '..' not in Path(key).parts,
            f'Invalid repository path: {key}')
    return path


def read(key):
    return json.loads(local(key).read_bytes())


def digest(data):
    return sha256(data).hexdigest()


def read_frozen(entry):
    data = local(entry['path']).read_bytes()
    require(digest(data) == entry['sha256'], f"Frozen bytes differ: {entry['path']}")
    return data


def references(entry, count):
    split = json.loads(read_frozen(entry))
    ids, items = split['ids'], split['by_id']
    require(len(ids) == len(set(ids)) == count and set(ids) == items.keys(),
            f"Dataset cohort differs: {entry['path']}")
    return {task_id: items[task_id]['answers'] for task_id in ids}


def verify_copies(archive, files):
    for entry in files:
        selected = read_frozen(entry)
        original = archive.read_bytes(local(entry['source']))
        require(selected == original, f"Selected copy differs from original: {entry['path']}")


def receipt_rows(archive, entry, planned):
    directory = local(entry['receipts'])
    if entry['receipt_layout'] == 'task_id':
        files = sorted(directory.glob('*/result.json'))
        for path in files:
            yield path.parent.name, archive.read_json(path)
    elif entry['receipt_layout'] == 'actor_ordinal':
        files = sorted(directory.glob('*/trajectory.json'))
        require([path.parent.name for path in files] ==
                [f'{index:04}' for index in range(1, len(planned) + 1)],
                f'Actor folders differ: {directory}')
        for path, task_id in zip(files, planned):
            record = archive.read_json(path)
            require(record['task_id'] == record['task']['id'] == task_id,
                    f'Actor task identity differs: {path}')
            yield task_id, record['execution']
    else:
        raise ValueError(f"Unknown receipt layout: {entry['receipt_layout']}")


def verify_scores(archive, entry, gold, planned, scorer, skill, actor):
    require(len(planned) == len(gold) and set(planned) == gold.keys(),
            f"Frozen plan coverage differs: {entry['id']}")
    seen, hard, soft, requests = set(), [], [], 0
    for task_id, execution in receipt_rows(archive, entry, planned):
        hint = f"{entry['id']}/{task_id}"
        require(task_id in gold and task_id not in seen, f'Unexpected or duplicate task: {hint}')
        require(execution['skill'].encode() == skill and execution['actor'] == actor,
                f'Actor configuration or Skill differs: {hint}')
        answer = scorer['extract_answer'](execution['content'])
        anls = scorer['anls_score'](answer, gold[task_id])
        passed = int(anls >= scorer['HARD_MATCH_THRESHOLD'])
        metrics = execution['metrics']
        require(execution['answer']['raw_content'] == execution['content']
                and execution['answer']['extracted_answer'] == answer
                and metrics['hard'] == passed
                and isclose(metrics['anls'], anls, rel_tol=0, abs_tol=1e-12),
                f'Published score differs from native score: {hint}')
        seen.add(task_id)
        hard.append(passed)
        soft.append(anls)
        requests += execution['api_requests']
    require(seen == gold.keys(), f"Receipt cohort is incomplete: {entry['id']}")
    return {'scored': len(seen), 'correct': sum(hard), 'hard': mean(hard),
            'anls': mean(soft), 'api_requests': requests}


def verify_evaluation(archive, entry, gold, scorer):
    plan = read(entry['plan'])
    summary = read(entry['summary'])
    actor = plan['actor']
    skill = local(entry['skill']).read_bytes()
    require(digest(skill) == entry['skill_sha256'] and actor['model'] == entry['actor'],
            f"Evaluation Skill or Actor differs: {entry['id']}")
    if 'skill' in plan:
        require(plan['skill'].encode() == skill, f"Plan Skill differs: {entry['id']}")
    recorded_hash = plan.get('skill_sha256')
    if 'skill_label' in entry:
        recorded_hash = plan['skills'][entry['skill_label']]['sha256']
    if recorded_hash is not None:
        require(recorded_hash == entry['skill_sha256'], f"Plan Skill hash differs: {entry['id']}")
    planned = [task if isinstance(task, str) else task['id'] for task in plan['tasks']]
    scores = verify_scores(archive, entry, gold, planned, scorer, skill, actor)
    require(summary['status'] == 'complete'
            and summary['sample_count'] == scores['scored']
            and summary['success_count'] == entry['correct'] == scores['correct']
            and summary['api_requests'] == scores['api_requests']
            and isclose(summary['hard'], scores['hard'], rel_tol=0, abs_tol=1e-12)
            and isclose(summary['anls'], scores['anls'], rel_tol=0, abs_tol=1e-12),
            f"Summary differs from native scores: {entry['id']}")
    attempts = entry.get('attempts', [])
    if attempts:
        verify_test_attempts(entry, attempts, scores['scored'])
    return {'id': entry['id'], 'method': entry['method'], 'kind': entry['kind'],
            'skill_sha256': entry['skill_sha256'], 'actor': entry['actor'], **scores}


def path_ends_with(path, relative):
    parts = Path(relative).parts
    return Path(path).parts[-len(parts):] == parts


def verify_test_attempts(entry, attempts, scored):
    require([attempt['status'] for attempt in attempts] == ['failed', 'completed'],
            f"Expected failure followed by a completed recovery: {entry['id']}")
    failed, recovered = [read(attempt['receipt']) for attempt in attempts]
    require(failed['status'] == 'failed' and failed['exit_code'] != 0
            and recovered['status'] == 'completed' and recovered['exit_code'] == 0
            and recovered['completed'] == recovered['test_count'] == scored
            and failed['campaign'] == recovered['campaign']
            and failed['selected_skill'] == recovered['selected_skill']
            and all(path_ends_with(receipt['output'], entry['id'])
                    and receipt['skill_sha256'] == entry['skill_sha256']
                    for receipt in (failed, recovered)),
            f"Failed and recovered receipts disagree on this evaluation: {entry['id']}")


def verify_selection(archive, run, entry, gold, scorer):
    selection = read(entry['summary'])
    batch = read(entry['batch'])['signature']
    skill = local(run['final_skill']).read_bytes()
    require(selection['best_step'] == entry['best_step']
            and selection['selection_cases'] == len(gold)
            and selection['sha256'] == digest(skill)
            and batch['skill'].encode() == skill,
            'SkillOpt Selection snapshot is inconsistent')
    scores = verify_scores(archive, entry, gold, batch['tasks'], scorer, skill, batch['actor'])
    require(scores['correct'] == entry['correct']
            and isclose(scores['hard'], selection['selection_hard'], rel_tol=0, abs_tol=1e-12),
            'SkillOpt Selection score differs')
    return {'best_step': entry['best_step'], **scores}


def verify_archived_evaluations(archive, manifest, test, scorer):
    verify_copies(archive, manifest['files'])
    return {entry['id']: verify_evaluation(archive, entry, test, scorer)
            for entry in manifest['evaluations']}


def round_evaluations(run):
    for name, result in run['evaluation_rounds'].items():
        for key in result if isinstance(result, list) else [result]:
            yield name, key


def verify_history_rounds(run, config, count):
    rounds = run['rounds']
    require(list(rounds) == [f'R{index:02}' for index in range(1, count + 1)],
            f"Round coverage differs: {run['id']}")
    initial = local(run['initial_skill']).read_bytes()
    require(initial == config['initial_skill'].encode(),
            f"Initial Skill differs from configuration: {run['id']}")
    retained = {'initial_skill.md': initial}
    hashes = {}
    previous = {'next_round': 1, 'parent': 'initial_skill.md'}
    if run['method'] in ('v29', 'v29.1'):
        previous['active_memory'] = 'initial_memory'
    else:
        previous['memory_head'] = None
    for index, (name, round_record) in enumerate(rounds.items(), 1):
        record = read(round_record['result'])
        skill = local(round_record['skill']).read_bytes()
        retained_path = round_record.get('retained_path', f'rounds/{name}/selected.md')
        require(retained_path not in retained or retained[retained_path] == skill,
                f"Earlier retained Skill was replaced: {run['id']}/{name}")
        retained[retained_path] = skill
        end = record['after']
        require(record['status'] == 'completed' and record['before'] == previous
                and end['next_round'] == index + 1
                and retained.get(end['parent']) == skill,
                f"Frozen round or retained Skill differs: {run['id']}/{name}")
        if 'retained_path' in round_record:
            require(end['parent'] == retained_path, f"Retained Skill path differs: {run['id']}/{name}")
        hashes[name] = digest(skill)
        previous = end
    return hashes, previous


def verify_history_run(run, evaluated, optimization, revision):
    config = read(run['config'])
    summary = read(run['training_summary'])
    state = read(run['state'])
    batches = config['batches']
    method_version = config['method']['version']
    summary_method = summary.get('method')
    if run['method'] in ('v29', 'v29.1') and summary_method is None:
        summary_method = method_version
    require(config['revision'] == revision
            and method_version == run['method'].replace('.', '_') + '_campaign_v1'
            and [len(batch) for batch in batches] == [15] * 10 + [10]
            and [task for batch in batches for task in batch] == optimization
            and summary_method == method_version and summary['status'] == 'complete'
            and summary['optimization_count'] == len(optimization)
            and summary['rounds_completed'] == len(batches),
            f"Frozen training configuration or completion differs: {run['id']}")

    hashes, previous = verify_history_rounds(run, config, len(batches))
    final_hash = digest(local(run['final_skill']).read_bytes())
    require(state == previous == summary['state']
            and summary['selected_skill'] == state['parent']
            and hashes[f'R{len(batches):02}'] == final_hash,
            f"Final Skill or training state differs: {run['id']}")
    cover = list(round_evaluations(run))
    require(all(result in evaluated and name in hashes
                and evaluated[result]['method'] == run['method']
                and evaluated[result]['actor'] == config['actor']['model']
                and evaluated[result]['skill_sha256'] == hashes[name]
                for name, result in cover),
            f"Archived evaluation points to the wrong round: {run['id']}")
    finals = [evaluated[key] for _, key in cover if evaluated[key]['kind'] == '终测首测']
    retests = [evaluated[key] for _, key in cover if evaluated[key]['kind'] == '终测复测']
    require(len(finals) == 1 and all(item['skill_sha256'] == final_hash for item in finals + retests),
            f"Archived final evaluations point to the wrong Skill: {run['id']}")
    final_evaluation = finals[0]
    result = {'method': run['method'], 'id': run['id'], 'rounds_completed': len(hashes),
              'test_evaluations': len(cover), 'final_correct': final_evaluation['correct'],
              'final_hard': final_evaluation['hard'], 'final_anls': final_evaluation['anls']}
    if retests:
        result['retests'] = [{'id': item['id'], 'correct': item['correct'], 'anls': item['anls']}
                             for item in retests]
    return result


def verify_early_skilladam(run, evaluated, optimization):
    config = read(run['config'])
    summary = read(run['training_summary'])
    checkpoint = read(run['checkpoint'])
    iterations = checkpoint['iterations']
    snapshots = run['rounds']
    require(config['stage0'] == 'disabled_use_v29_initial_skill' and summary['status'] == 'complete'
            and summary['iterations'] == checkpoint['next_iteration'] == len(iterations) == len(snapshots) == 11
            and summary['optimization_count'] == len(optimization)
            and [task for item in iterations for task in item['training_case_ids']] == optimization,
            'Early SkillAdam training cohort or completion differs')
    retained = local(run['initial_skill']).read_bytes()
    for index, (item, snapshot) in enumerate(zip(iterations, snapshots)):
        skill = local(snapshot['skill']).read_bytes()
        require(item['iteration'] == index and item['accepted'] == snapshot['accepted']
                and item['training_case_ids'] == item['validation_case_ids']
                and (item['accepted'] or skill == retained),
                f"SkillAdam retained Skill or same-batch validation differs: {index + 1}")
        retained = skill
    final = local(run['final_skill']).read_bytes()
    eval_result = evaluated[run['evaluation']]
    require(summary['accepted'] == sum(item['accepted'] for item in iterations)
            and retained == final == checkpoint['current_skill'].encode()
            and final == local(run['native_final_skill']).read_bytes()
            and eval_result['method'] == 'SkillAdam' and eval_result['actor'] == config['actor']['model']
            and eval_result['skill_sha256'] == digest(final),
            'Early SkillAdam final checkpoint differs')
    return {'id': run['id'], 'iterations': len(iterations), 'accepted': summary['accepted'],
            'final_correct': eval_result['correct'], 'final_anls': eval_result['anls']}


def verify_upstream_skilladam(source, evaluated, entries):
    skill_hash = digest(local(source['skill']).read_bytes())
    require(len(source['evaluations']) == 2, 'Expected two independent upstream Best Skill tests')
    for key in source['evaluations']:
        result = evaluated[key]
        plan = read(entries[key]['plan'])
        require(result['method'] == 'SkillAdam' and result['kind'] == '外部最佳 Skill'
                and result['skill_sha256'] == skill_hash
                and plan['source_commit'] == source['commit'] and plan['source_path'] == source['repository_path'],
                f"Upstream SkillAdam provenance differs: {key}")
    return {'commit': source['commit'], 'hard_counts': [evaluated[key]['correct'] for key in source['evaluations']]}


def verify_v29_2_lineage(lineage, runs, entries):
    stopped = lineage['original']
    resumed = next(run for run in runs if run['id'] == lineage['resumed_id'])
    hashes, state = verify_history_rounds(stopped, read(stopped['config']), 6)
    original_status = read(stopped['status'])
    stop = read(stopped['stop'])
    migration = read(lineage['migration_status'])
    deletion = read(lineage['deletion_receipt'])
    restart = read(lineage['restart_status'])
    test = read(lineage['test_status'])
    evaluation, = (key for _, key in round_evaluations(resumed))
    plan = read(entries[evaluation]['plan'])
    require(read(stopped['state']) == state and state['next_round'] == stop['round'] == 7
            and stop['stage'] == 'replay' and original_status['status'] == 'failed'
            and original_status['test_started'] is False
            and migration['status'] == 'stopped_by_user' and migration['test_started'] is False
            and restart['status'] == 'completed' and restart['test_started'] is False
            and migration['campaign'] == restart['campaign'] == test['campaign'] == plan['campaign']
            and path_ends_with(plan['campaign'], resumed['source'])
            and test['status'] == 'completed' and test['completed'] == 374
            and path_ends_with(test['output'], evaluation),
            'v29.2 stop, migration, restart or Test lineage differs')
    require(path_ends_with(deletion['original_campaign_preserved'], stopped['source'])
            and deletion['original_R07_replay_consumed'] == 6
            and deletion['original_R07_replay_remaining'] == 0
            and all(any(path_ends_with(path, original) for path in deletion['scope'])
                    for original in lineage['deleted_roots'])
            and all(digest(local(resumed['rounds'][name]['skill']).read_bytes()) == skill_hash
                    for name, skill_hash in hashes.items()),
            'v29.2 preserved-prefix or deletion receipt differs')
    return {'original_rounds_completed': len(hashes), 'stopped_in': 'R07 Replay',
            'resumed_test': evaluation}


def verify_history(manifest, test, scorer):
    optimization = json.loads(read_frozen(manifest['optimization_items']))['ids']
    require(len(optimization) == len(set(optimization)) == 160 and not set(optimization) & test.keys(),
            'Historical optimization cohort differs or overlaps Test')
    linked = [key for run in manifest['runs'] for _, key in round_evaluations(run)]
    native = manifest.get('skilladam_native')
    upstream = manifest.get('skilladam_upstream')
    if native:
        linked.append(native['evaluation'])
    if upstream:
        linked.extend(upstream['evaluations'])
    entries = {entry['id']: entry for entry in manifest['evaluations']}
    require(len(linked) == len(set(linked)) and set(linked) == entries.keys(),
            'Each historical evaluation must be associated with its training round')
    require(len({run['id'] for run in manifest['runs']}) == len(manifest['runs']),
            'Duplicate historical training IDs')

    with DocVQAArchive() as archive:
        evaluated = verify_archived_evaluations(archive, manifest, test, scorer)
    runs = [verify_history_run(run, evaluated, optimization, manifest['data_revision'])
            for run in manifest['runs']]
    result = {'status': 'verified', 'selected_files': len(manifest['files']),
              'evaluations': len(evaluated), 'test_receipts': sum(row['scored'] for row in evaluated.values()),
              'runs': runs}
    deleted = manifest.get('deleted_before_test', [])
    for item in deleted:
        receipt = read(item['receipt'])
        require(receipt['old_test_was_started'] is False
                and item['source'] not in {run['source'] for run in manifest['runs']}
                and all(any(path_ends_with(removed, original) for removed in receipt['removed'])
                        for original in (item['source'], item['scheduler'])),
                f"Deleted run is inconsistent with its reset receipt: {item['id']}")
    if deleted:
        result['deleted_before_test'] = [item['id'] for item in deleted]
    if native:
        result['skilladam_native'] = verify_early_skilladam(native, evaluated, optimization)
    if upstream:
        result['skilladam_upstream'] = verify_upstream_skilladam(upstream, evaluated, entries)
    if 'v29_2_lineage' in manifest:
        result['v29_2_lineage'] = verify_v29_2_lineage(manifest['v29_2_lineage'], manifest['runs'], entries)
    return result


def verify_collection(manifest):
    inventory = read(manifest['inventory'])
    expected = {row['source']: row for row in inventory['evaluations']}
    require(len(expected) == len(inventory['evaluations']) == manifest['evaluation_count'],
            'Inventory evaluation coverage changed')
    groups = {key: read(key) for key in manifest['manifests']}
    require(len(groups) == len(manifest['manifests'])
            and all(group.get('kind') in (None, 'history') for group in groups.values()),
            'Collection must contain distinct comparison or history manifests')
    declarations = [entry for group in groups.values() for entry in group['evaluations']]
    declared = {row['id']: row for row in declarations}
    require(len(declared) == len(declarations) and declared.keys() == expected.keys(),
            'The archive omits or duplicates an inventory evaluation')
    for key, entry in declared.items():
        require(all(entry[field] == expected[key][field] for field in ('skill_sha256', 'actor', 'correct'))
                and expected[key]['scored'] == 374,
                f'Archived evaluation differs from inventory: {key}')

    results = {}
    for key, group in groups.items():
        report = verify(group)
        results[key] = {field: report[field] for field in ('selected_files', 'evaluations', 'test_receipts')}
    evaluations = sum(group['evaluations'] for group in results.values())
    receipts = sum(group['test_receipts'] for group in results.values())
    require(evaluations == manifest['evaluation_count'] and receipts == manifest['receipt_count'],
            'Offline totals differ from the collection manifest')
    return {'status': 'verified', 'evaluations': evaluations, 'test_receipts': receipts,
            'groups': results}


def verify(manifest):
    if manifest.get('kind') == 'collection':
        return verify_collection(manifest)
    test = references(manifest['test_items'], 374)
    scorer_source = manifest['scorer']
    read_frozen(scorer_source)
    scorer = runpy.run_path(str(local(scorer_source['path'])))

    entries = manifest['evaluations']
    require(len({entry['id'] for entry in entries}) == len(entries), 'Duplicate evaluation IDs')
    if manifest.get('kind') == 'history':
        return verify_history(manifest, test, scorer)

    validation = references(manifest['validation_items'], 53)
    require(not test.keys() & validation.keys(), 'Test and Selection overlap')
    by_method = {run['method']: run for run in manifest['runs']}
    require(len(manifest['runs']) == 3 and by_method.keys() == {'v29.11', 'SkillAdam', 'SkillOpt'},
            'Expected the three comparison runs')
    primary = {entry['id'] for entry in entries if entry['primary']}
    expected_primary = {manifest['r00'], *(key for run in by_method.values() for key in run['final_evaluations'])}
    require(primary == expected_primary and len(primary) == 12, 'Expected shared R00 and eleven final tests')

    with DocVQAArchive() as archive:
        evaluated = verify_archived_evaluations(archive, manifest, test, scorer)
        selection = verify_selection(archive, by_method['SkillOpt'], manifest['selection'], validation, scorer)

    control = evaluated[manifest['r00']]
    require(control['kind'] == '共用 R00' and control['correct'] == 303, 'Shared R00 differs')
    runs = []
    for method, run in by_method.items():
        initial = digest(local(run['initial_skill']).read_bytes())
        final = digest(local(run['final_skill']).read_bytes())
        tests = [evaluated[key] for key in run['final_evaluations']]
        require(initial == control['skill_sha256']
                and len({test['id'] for test in tests}) == len(tests) == (5 if method == 'v29.11' else 3)
                and all(test['method'] == method and test['actor'] == 'deepseek-flash'
                        and test['skill_sha256'] == final for test in tests),
                f'Comparison results point to the wrong checkpoint: {method}')
        hard_counts = [test['correct'] for test in tests]
        runs.append({'method': method, 'final_hard_counts': hard_counts,
                     'figure_median': median(hard_counts[:3]), 'all_median': median(hard_counts)})
    return {'status': 'verified', 'selected_files': len(manifest['files']),
            'evaluations': len(evaluated), 'primary_evaluations': len(primary),
            'test_receipts': sum(row['scored'] for row in evaluated.values()),
            'shared_r00': control, 'runs': runs, 'skillopt_selection': selection}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default=MANIFEST, help='Repository-relative comparison, history or collection manifest')
    args = parser.parse_args()
    print(json.dumps(verify(read(args.manifest)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

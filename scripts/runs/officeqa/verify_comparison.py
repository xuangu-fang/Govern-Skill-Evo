"""Verify OfficeQA experiment bundles against the original Test172 receipts."""

import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import runpy
from statistics import median
import sys
from tempfile import TemporaryFile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from experiments.benchmark_record_refs.restore import Archive, SELECT

MANIFEST = 'experiments/benchmarks/officeqa/main-comparison.json'
SCORER = ('src/skill_evolution/skilladam/upstream/skilladam/'
          'benchmarks/officeqa/evaluation.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_path(key):
    path = ROOT / key
    require(not Path(key).is_absolute() and '..' not in Path(key).parts
            and path.resolve().is_relative_to(ROOT), f'Invalid repository path: {key}')
    return path


def read_json(key):
    return json.loads(local_path(key).read_bytes())


def digest(data):
    return sha256(data).hexdigest()


def archived_bytes(archive, key, stream):
    data = local_path(key).read_bytes()
    row = archive.db.execute(SELECT + ' WHERE r.path=?', (key,)).fetchone()
    if row is None:
        stream.write(data)
        return digest(data)
    archive.verify_bytes(row, data, stream)
    return row[1].hex()


@contextmanager
def archived_stream(archive, source):
    with TemporaryFile() as stream:
        original_hash = archived_bytes(archive, source['path'], stream)
        require(original_hash == source['sha256'], f"Archive digest differs: {source['path']}")
        stream.seek(0)
        yield stream


def score_answer(prediction, gold_answers, scorer):
    return {
        'em': max(scorer['exact_match'](prediction, gold) for gold in gold_answers),
        'f1': max(scorer['token_f1'](prediction, gold) for gold in gold_answers),
    }


def original_journal(archive, source, references, scorer):
    path = source['path']
    scores = {}
    with archived_stream(archive, source) as stream:
        if Path(path).suffix == '.json':
            value = json.load(stream)
            receipts = [value if 'record' in value else {'id': value['task_id'], 'record': value}]
        else:
            receipts = map(json.loads, stream)
        for receipt in receipts:
            uid, record = receipt['id'], receipt['record']
            require(uid == record['task_id'] and uid in references and uid not in scores,
                    f'Invalid or duplicate OfficeQA UID in {path}: {uid}')
            actor = record['actor']
            limit = source['task_output_limits'].get(uid, source['max_completion_tokens'])
            require(actor['model'] == source.get('model', 'deepseek-flash')
                    and actor['max_completion_tokens'] == limit,
                    f'Actor settings differ in {path}: {uid}')
            skill = digest(record['skill'].encode())
            require(skill == source['skill_sha256'], f'Receipt Skill differs in {path}: {uid}')
            prediction = record['answer']
            scores[uid] = score_answer(prediction, references[uid], scorer)
            require(scores[uid] == record['metrics'], f'Score differs in {path}: {uid}')
    require(len(scores) == source['count'], f'Receipt count differs: {path}')
    return scores


def verify_evaluation(entry, journals, test_ids):
    scores = {}
    for key in entry['journals']:
        batch = journals[key]
        require(not scores.keys() & batch.keys(), f"Duplicate UID across journals: {entry['id']}")
        scores.update(batch)
    count = len(scores)
    expected = entry['expected']
    excluded = set(expected.get('excluded_ids', []))
    planned = set(expected['planned_ids']) if 'planned_ids' in expected else test_ids - excluded
    if 'plan' in entry:
        ids = read_json(entry['plan'])['tasks']
        require(len(ids) == len(planned) and set(ids) == planned,
                f"Frozen evaluation plan differs: {entry['id']}")
    require(excluded <= test_ids and planned <= test_ids and count == expected['count']
            and scores.keys() <= planned and planned - scores.keys() == set(expected['pending_ids']),
            f"Evaluation coverage differs: {entry['id']}")
    correct = int(sum(row['em'] for row in scores.values())) if count else None
    f1 = sum(row['f1'] for row in scores.values()) / count if count else None
    require(correct == expected['correct'] and
            (expected['f1'] is None or isclose(f1, expected['f1'], rel_tol=0, abs_tol=1e-12)),
            f"Evaluation totals differ: {entry['id']}")
    return {'id': entry['id'], 'method': entry['method'], 'skill': entry['skill'],
            'skill_sha256': entry['skill_sha256'], 'report': entry['report'],
            'journals': entry['journals'], 'planned': len(planned), 'scored': count, 'correct': correct,
            'em': correct / count if count == len(planned) else None,
            'f1': f1 if count == len(planned) else None,
            'excluded_ids': sorted(excluded), 'pending_ids': expected['pending_ids']}


def verify_probes(probes, scorer):
    results = []
    for group in probes:
        dataset = group['items']
        raw = local_path(dataset['path']).read_bytes()
        require(digest(raw) == dataset['sha256'], 'Frozen probe inputs differ')
        references = {row['id']: row['answers'] for row in json.loads(raw)}
        report = read_json(group['report'])
        for arm in group['arms']:
            scores = report[arm['id']]
            require(scores.keys() == set(group['tasks']), f"Probe coverage differs: {arm['id']}")
            for uid, receipt in scores.items():
                require(score_answer(receipt['answer'], references[uid], scorer) == receipt['metrics'],
                        f"Probe score differs: {arm['id']}/{uid}")
            correct = int(sum(row['metrics']['em'] for row in scores.values()))
            require(correct == arm['correct'], f"Probe total differs: {arm['id']}")
            results.append({'id': arm['id'], 'scored': len(scores), 'correct': correct})
    return results


def verify_selection(archive, run, scorer):
    selection = run['selection']
    dataset = selection['items']
    raw = local_path(dataset['path']).read_bytes()
    require(digest(raw) == dataset['sha256'], 'Frozen Selection inputs differ')
    references = {row['id']: row['answers'] for row in json.loads(raw)}
    plan = local_path(run['config']).read_bytes()
    require(digest(plan) == selection['plan_sha256']
            and set(json.loads(plan)['selection_ids']) == references.keys(),
            f"Selection plan differs: {run['id']}")
    journal = selection['journal']
    require(journal['skill_sha256'] == digest(local_path(run['final_skill']).read_bytes()),
            f"Selection Skill differs: {run['id']}")
    scores = original_journal(archive, journal, references, scorer)
    require(scores.keys() == references.keys(), f"Selection coverage differs: {run['id']}")
    correct = int(sum(row['em'] for row in scores.values()))
    summary = read_json(selection['summary'])
    require(correct == selection['correct'] and summary['best_step'] == selection['step']
            and isclose(summary['best_selection_hard'], correct / len(scores), rel_tol=0, abs_tol=1e-12),
            f"Best Selection result differs: {run['id']}")
    return {'id': run['id'], 'step': selection['step'], 'scored': len(scores), 'correct': correct}


def verify(method=None, manifest_path=MANIFEST):
    manifest = read_json(manifest_path)
    runs = [run for run in manifest['runs'] if method is None or run['method'] == method]
    require(bool(runs), f'Method {method!r} does not appear in {manifest_path}')
    entries = [entry for entry in manifest['evaluations']
               if method is None or entry['method'] == method]
    roots = tuple(str(Path(run['entry']).parent) + '/' for run in runs)
    supporting_files = {run[key] for run in runs for key in ('profile', 'evidence') if key in run}
    supporting_files.update(profile for run in runs for profile in run.get('profiles', []))
    probes = [group for group in manifest.get('probes', [])
              if method is None or method in group['methods']]
    files = [entry for entry in manifest['files']
             if entry['new'].startswith(roots) or entry['new'] in supporting_files
             or any(entry['new'] in group['files'] for group in probes)]
    journal_keys = {key for entry in entries for key in entry['journals']}
    sources = {source['path']: source for source in manifest['journals']
               if source['path'] in journal_keys}
    dataset = manifest['test_items']
    raw = local_path(dataset['path']).read_bytes()
    require(digest(raw) == dataset['sha256'], 'Frozen Test172 inputs differ')
    items = json.loads(raw)
    references = {row['id']: row['answers'] for row in items}
    test_ids = set(read_json(manifest['test_ids']))
    require(len(items) == len(test_ids) == 172 and references.keys() == test_ids,
            'Test172 UID set differs')
    scorer = runpy.run_path(str(local_path(SCORER)))
    archive = Archive('officeqa')
    try:
        for entry in files:
            with archived_stream(archive, {'path': entry['old'], 'sha256': entry['sha256']}) as stream:
                expected_bytes = stream.read()
                for old, new in entry.get('link_updates', {}).items():
                    original_link = f']({old})'.encode()
                    require(expected_bytes.count(original_link) == 1,
                            f"Markdown source link differs: {entry['old']}")
                    expected_bytes = expected_bytes.replace(original_link, f']({new})'.encode())
                require(expected_bytes == local_path(entry['new']).read_bytes(),
                        f"Selected copy differs: {entry['new']}")
        journals = {key: original_journal(archive, source, references, scorer)
                    for key, source in sources.items()}
        selections = [verify_selection(archive, run, scorer) for run in runs if 'selection' in run]
    finally:
        archive.close()
    for entry in entries:
        skill_hash = digest(local_path(entry['skill']).read_bytes())
        require(skill_hash == entry['skill_sha256'], f"Evaluated Skill differs: {entry['id']}")
        require(all(sources[key]['skill_sha256'] == skill_hash for key in entry['journals']),
                f"Wrong journal for {entry['id']}")
    evaluations = [verify_evaluation(entry, journals, test_ids) for entry in entries]
    by_id = {entry['id']: entry for entry in evaluations}
    results = []
    for run in runs:
        skill = run.get('final_skill')
        final_hash = digest(local_path(skill).read_bytes()) if skill else None
        tests = [by_id[key] for key in run['final_evaluations']]
        require(all(test['method'] == run['method'] and
                test['skill_sha256'] == final_hash for test in tests),
                f"Final evaluation identity differs: {run['id']}")
        final_correct = [test['correct'] for test in tests]
        median_correct = None
        if run.get('final_repeat_median', True):
            require(len(tests) == 3 and all(test['scored'] == 172 for test in tests),
                    f"Expected three complete final evaluations: {run['id']}")
            median_correct = median(final_correct)
        results.append({'id': run['id'], 'method': run['method'], 'entry': run['entry'],
                        'final_skill': skill, 'final_skill_sha256': final_hash,
                        'final_correct': final_correct, 'median_correct': median_correct})
    return {'status': 'verified', 'selected_files': len(files),
            'journals': len(journals), 'receipts': sum(map(len, journals.values())),
            'runs': results, 'evaluations': evaluations, 'probes': verify_probes(probes, scorer),
            'selections': selections}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default=MANIFEST, help='Repository-relative evaluation manifest')
    parser.add_argument('--method', help='Verify one method in the selected manifest')
    args = parser.parse_args()
    print(json.dumps(verify(args.method, args.manifest), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

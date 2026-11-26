"""Prepare the fixed DocVQA subset from already downloaded validation files.

Data preparation only. This script does not download data or call models.
Run from any directory using the DocVQA conda environment.
"""
from pathlib import Path
import csv
import json
import shutil
import sys

import pyarrow.parquet as pq
from PIL import Image

PROJECT = Path(__file__).resolve().parents[3]
REVISION = '539088ef8a8ada01ac8e2e6d4e372586748a265e'
ROOT = PROJECT / 'data/docvqa/releases' / REVISION
SOURCE = PROJECT / 'external/SkillOpt/data/docvqa_id_split'
COUNTS = {'train': 107, 'val': 53, 'test': 374}


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def collection(rows):
    return {'ids': [r['id'] for r in rows], 'by_id': {r['id']: r for r in rows}}


def main():
    if (ROOT / 'verification.json').exists():
        raise SystemExit('This release has already been prepared; leave it unchanged.')
    manifest = read(SOURCE / 'split_manifest.json')
    assert manifest['source_revision'] == REVISION
    source_rows = {s: read(SOURCE / s / 'items.json') for s in COUNTS}
    ids = {s: [str(r['id']) for r in rows] for s, rows in source_rows.items()}
    adam = read(PROJECT / 'external/SkillAdam/skilladam/data/profiles/docvqa_main_results.json')
    assert adam['source_revision'] == REVISION
    assert adam['splits'] == ids
    assert {s: len(v) for s, v in ids.items()} == COUNTS
    assert len(set(sum(ids.values(), []))) == 534
    for split in COUNTS:
        dest = ROOT / 'source_split' / split / 'items.json'
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / split / 'items.json', dest)
    save(ROOT / 'source_split/split_manifest.json', manifest)
    save(ROOT / 'source_split/skilladam_split_ids.json', ids)

    wanted = set(sum(ids.values(), []))
    found = {}
    upstream_count = 0
    paths = sorted((ROOT / 'upstream').glob('validation-*.parquet'))
    assert len(paths) == 6
    (ROOT / 'images').mkdir(exist_ok=True)
    for path in paths:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=32):
            for raw in batch.to_pylist():
                upstream_count += 1
                qid = str(raw['questionId'])
                if qid not in wanted:
                    continue
                assert qid not in found
                assert isinstance(raw['question'], str) and raw['question'].strip()
                assert raw['answers'] and all(isinstance(a, str) and a.strip() for a in raw['answers'])
                assert raw['data_split'] == 'val'
                image_name = Path(raw['image']['path']).name
                image = ROOT / 'images' / image_name
                data = raw['image']['bytes']
                assert data
                if image.exists():
                    assert image.read_bytes() == data, f'Conflicting image filename: {image_name}'
                else:
                    image.write_bytes(data)
                found[qid] = {
                    'id': qid, 'questionId': qid, 'docId': str(raw['docId']),
                    'question': raw['question'], 'answers': raw['answers'],
                    'topic': '|'.join(raw['question_types']),
                    'question_types': raw['question_types'],
                    'image_path': 'images/' + image_name,
                    'ucsf_document_id': raw['ucsf_document_id'],
                    'ucsf_document_page_no': raw['ucsf_document_page_no'],
                    'source_split': 'validation', 'source_file': path.name,
                }
        print('Read', path.name, 'selected', len(found), flush=True)
    assert upstream_count == 5349
    assert set(found) == wanted

    materialized = {}
    for split, originals in source_rows.items():
        rows = []
        for original in originals:
            row = dict(found[str(original['id'])])
            for key in ('questionId', 'docId', 'ucsf_document_id', 'ucsf_document_page_no'):
                assert str(original[key]) == str(row[key]), (row['id'], key)
            assert set(original['topic'].split('|')) == set(row['question_types'])
            row.update(original_split=split, effective_split=split,
                       source_image_path=original['image_path'])
            rows.append(row)
        materialized[split] = rows
        save(ROOT / 'prepared' / split / 'items.json', collection(rows))
        # SkillOpt reads CSV and resolves image paths against the working directory.
        fields = ['id', 'questionId', 'docId', 'question', 'answer', 'image_path',
                  'topic', 'ucsf_document_id', 'ucsf_document_page_no', 'source_split']
        with (ROOT / 'prepared' / split / 'items.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                output = {key: row[key] for key in fields if key != 'answer'}
                output['answer'] = json.dumps(row['answers'], ensure_ascii=False)
                output['image_path'] = str(ROOT / row['image_path'])
                writer.writerow(output)
    save(ROOT / 'prepared/split_manifest.json', manifest)
    optimization = [dict(r, effective_split='optimization')
                    for s in ('train', 'val') for r in materialized[s]]
    save(ROOT / 'optimization160/items.json', collection(optimization))
    save(ROOT / 'optimization160/manifest.json', {
        'count': 160, 'order': 'original train order followed by original val order',
        'ids': ids['train'] + ids['val'], 'test_count': 374,
        'test_path': '../prepared/test/items.json',
    })

    # SkillAdam expects train/val/test and images beneath one dataset root.
    # These links expose that layout without duplicating data or images.
    for name in (*COUNTS, 'split_manifest.json'):
        link = ROOT / name
        target = Path('prepared') / name
        if not link.is_symlink():
            link.symlink_to(target, target_is_directory=name in COUNTS)

    image_paths = sorted({r['image_path'] for r in found.values()})
    for relative in image_paths:
        with Image.open(ROOT / relative) as image:
            image.load()
            assert image.width > 0 and image.height > 0
    assert len(optimization) == 160
    assert set(ids['train'] + ids['val']).isdisjoint(ids['test'])

    # Exercise both upstream data loaders locally; no Actor is instantiated.
    sys.path[:0] = [str(PROJECT / 'external/SkillOpt'), str(PROJECT / 'external/SkillAdam')]
    from skillopt.envs.docvqa.dataloader import DocVQADataLoader
    from skilladam.benchmarks.docvqa.manifest import load_cases
    loader = DocVQADataLoader(split_dir=str(ROOT / 'prepared'), split_mode='split_dir')
    for split in COUNTS:
        opt = loader.load_split_items(str(ROOT / 'prepared' / split))
        assert [r['id'] for r in opt] == ids[split]
        for row in opt:
            expected = found[row['id']]
            assert row['question'] == expected['question'].strip()
            assert row['answers'] == [a.strip() for a in expected['answers']]
            assert Path(row['image_path']).is_file()
        cases = load_cases(ROOT, 'validation' if split == 'val' else split)
        assert {c.case_id for c in cases} == set(ids[split])
        for case in cases:
            expected = found[case.case_id]
            assert case.payload['question'] == expected['question'].strip()
            assert list(case.reference) == [a.strip() for a in expected['answers']]
            assert (ROOT / case.payload['document']['image_path']).is_file()

    opt_docs = {r['docId'] for r in optimization}
    test_rows = materialized['test']
    shared_docs = opt_docs & {r['docId'] for r in test_rows}
    info = {
        'benchmark': 'DocVQA', 'source_repo': 'lmms-lab/DocVQA',
        'resolved_repo': 'lmms-lab-encoder/DocVQA', 'revision': REVISION,
        'source_config': 'DocVQA', 'source_split': 'validation',
        'counts': COUNTS, 'optimization_count': 160,
        'prepared_root': str(ROOT / 'prepared'), 'image_root': str(ROOT / 'images'),
        'skillopt_split_dir': str(ROOT / 'prepared'), 'skilladam_data_root': str(ROOT),
        'optimization_items': str(ROOT / 'optimization160/items.json'),
        'test_items': str(ROOT / 'prepared/test/items.json'),
        'image_path_base': 'release root for JSON; absolute paths in CSV',
        'skilladam_loader_order': 'The upstream loader sorts IDs; saved JSON retains original manifest order.',
    }
    save(ROOT / 'dataset_info.json', info)
    report = {
        'status': 'passed', 'revision': REVISION, 'upstream_validation_rows': upstream_count,
        'selected_questions': len(found), 'counts': COUNTS, 'optimization_count': 160,
        'test_count': 374, 'images_decoded': len(image_paths),
        'original_id_order_preserved': True, 'skillopt_skilladam_split_ids_match': True,
        'missing_questions': 0, 'duplicate_question_ids': 0, 'empty_questions': 0,
        'empty_answer_lists': 0, 'missing_images': 0, 'unreadable_images': 0,
        'optimization_test_question_overlap': 0,
        'optimization_test_shared_doc_ids': len(shared_docs),
        'test_questions_on_shared_docs': sum(r['docId'] in shared_docs for r in test_rows),
        'skillopt_loader': 'passed', 'skilladam_loader': 'passed',
        'split_policy': 'Original question split preserved; shared documents are not removed.',
        'model_calls': 0, 'v29_implemented': False,
    }
    save(ROOT / 'verification.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

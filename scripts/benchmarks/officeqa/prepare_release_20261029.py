"""Verify official pinned OfficeQA data and prepare the existing train/test split.

No corpus/answer corrections, network, model calls or experiment launch.
Source-page association is normalized for the existing local reader only.
"""
import hashlib
import json
from pathlib import Path
import sys
from dataclasses import replace

from .prepare import deny_network, write_or_check

REVISION = '763a8366abf2a3605c381d53586d844dc60fa756'
CSV_SHA256 = 'b5eb1ce0cb343842bccb2f5b067793b4ed90e03e8bf64cb0d40d759bb768ff77'
CAMPAIGN = 'v26_officeqa_train74_epoch1_uid0007_65536_20261029_002'


def store(path, value):
    """Immutable report writer also used by the historical audit script."""
    write_or_check(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n', False)


def run(root):
    from src.adapters.officeqa.data import Dataset, PROFILE, materialize_rows
    from src.adapters.officeqa.execution import atomic_json
    from src.adapters.officeqa.runtime import Runtime
    from src.adapters.officeqa.local import source_references
    from src.skill_evolution.v26.training import load_dataset, MERGED_POOL

    release = root / 'data/officeqa/releases' / REVISION
    upstream = release / 'upstream'
    parsed = upstream / 'treasury_bulletins_parsed'
    source = upstream / 'officeqa_full.csv'
    if hashlib.sha256(source.read_bytes()).hexdigest() != CSV_SHA256:
        raise ValueError('Official CSV hash differs')
    corpus_hashes = {}
    for kind, suffix in [('jsons', '.json'), ('transformed', '.txt')]:
        entries = [x for x in json.loads((upstream / f'{kind}_tree.json').read_text())
                   if x['type'] == 'file' and x['path'].endswith(suffix)]
        names = {Path(x['path']).name for x in entries}
        if len(names) != 697 or names != {p.name for p in (parsed / kind).glob('*' + suffix)}:
            raise ValueError('Official corpus inventory differs')
        for x in entries:
            content = (upstream / x['path']).read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            actual = sha if x.get('lfs') else hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
            if actual != x.get('lfs', {}).get('oid', x['oid']):
                raise ValueError('Official corpus hash differs: ' + x['path'])
            corpus_hashes[x['path']] = sha
    # Reuse only historical ID membership, never its old task contents.
    profile = json.loads((root / 'external/SkillAdam/skilladam/data/profiles/officeqa_main_results.json').read_text())
    rows, mapping, originals = materialize_rows(source, profile)
    prepared = release / 'prepared'
    for split, items in rows.items():
        if len(items) != {'train': 50, 'val': 24, 'test': 172}[split]:
            raise ValueError('Split size differs')
        atomic_json(prepared / split / 'items.json', items)
    atomic_json(prepared / 'source_rows.json', originals)
    atomic_json(prepared / 'mapping_changes.json', mapping)
    atomic_json(prepared / 'manifest.json', {
        'profile': PROFILE, 'dataset_revision': REVISION, 'variant': 'OfficeQA Full',
        'splits': profile['splits'], 'parsed_root': str(parsed),
        'source_csv_sha256': CSV_SHA256, 'parsed_overlay': None,
        'upstream_corpus_verified_against_revision': REVISION,
        'corpus_sha256': hashlib.sha256(json.dumps(corpus_hashes, sort_keys=True).encode()).hexdigest(),
    })
    dataset = Dataset(prepared)
    optimization = load_dataset(prepared, MERGED_POOL)
    runtime = Runtime(parsed)
    pages = 0
    for uid in dataset.rows:
        case = dataset.case(uid)
        messages, allowed = runtime.prepare(case, None)
        hidden, _ = runtime.prepare(replace(case, reference=['PRIVATE_ANSWER_SENTINEL']), None)
        if messages != hidden or not allowed or case.reference != [originals[uid]['answer']]:
            raise ValueError('Invalid Actor input or answer mapping')
        pages += len(source_references(case.payload['source_files'], case.payload['source_docs']))
    cfg = json.loads((release / 'dataset_config.json').read_text())
    if cfg['train_ids'] != optimization.splits['train'] or cfg['test_ids'] != optimization.splits['test']:
        raise ValueError('Existing train/test partition changed')
    cfg.update(parsed_root=str(parsed), parsed_overlay=None, data_policy='official_unmodified',
               scorer_status='unchanged historical scorer; official scorer integration not performed',
               launch_status='data_prepared_only; no training or test started')
    atomic_json(release / 'dataset_config.json', cfg)
    atomic_json(release / 'training74/items.json', [optimization.rows[uid] for uid in cfg['train_ids']])
    report = {'status': 'passed', 'revision': REVISION, 'source_csv_sha256': CSV_SHA256,
              'data_policy': 'official_unmodified', 'parsed_overlay': None,
              'counts': {'total': 246, 'train': 74, 'test': 172, 'source_pages': pages},
              'official_corpus_files_verified': len(corpus_hashes), 'source_mapping_changes': mapping,
              'model_calls': 0, 'experiment_runs': 0, 'scorer_modified': False}
    atomic_json(release / 'preparation_report.json', report)
    print(json.dumps({k: report[k] for k in ['status', 'revision', 'data_policy', 'counts', 'official_corpus_files_verified', 'model_calls']}, ensure_ascii=False))


if __name__ == '__main__':
    sys.addaudithook(deny_network)
    run(Path(__file__).resolve().parents[3])

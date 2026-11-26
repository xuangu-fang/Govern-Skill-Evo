"""One OfficeQA task view for all methods; raw source records remain separate."""
import csv
from copy import deepcopy
import json
import re
from pathlib import Path

from skilladam.benchmarks.officeqa.manifest import _read_csv
from skilladam.benchmarks.officeqa.tool_runtime import _iter_oracle_refs
from skilladam.types import BenchmarkCase

from .local import source_references


PROFILE = 'officeqa_skilladam_aligned_v2'
SPLITS = {'train': 'train', 'validation': 'val', 'test': 'test'}


def split_source_urls(value):
    """Split JSON/newline/comma-separated URL fields before page association."""
    if isinstance(value, (list, tuple)):
        return [url for item in value for url in split_source_urls(item)]
    text = str(value or '').strip()
    if not text:
        return []
    if text.startswith('['):
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError('Source URL JSON must be an array')
        return split_source_urls(parsed)
    return [part.strip() for part in re.split(r'\r?\n|,\s*(?=https?://)', text) if part.strip()]


def materialize_rows(csv_path, split_profile):
    native = _read_csv(Path(csv_path))
    with Path(csv_path).open(encoding='utf-8-sig', newline='') as handle:
        raw = {row['uid']: row for row in csv.DictReader(handle)}
    output, changes, seen = {}, [], set()
    for split, ids in split_profile['splits'].items():
        rows = []
        for uid in ids:
            if uid in seen or uid not in native:
                raise ValueError(f'Duplicate or unknown split ID: {uid}')
            seen.add(uid)
            item = native[uid]
            files = list(item['source_files'])
            urls = split_source_urls(raw[uid]['source_docs'])
            refs = source_references(files, urls, allow_url_sources=True)
            legacy = _iter_oracle_refs(files, urls)
            aligned = [name for name, _, _ in refs] if refs != legacy else files
            if aligned != files:
                changes.append({'task_id': uid, 'source_files_before': files,
                                'source_files_after': aligned, 'page_refs': refs})
            rows.append({'id': uid, 'uid': uid, 'question': item['question'],
                         'ground_truth': item['answer'], 'answers': [item['answer']],
                         'category': item['category'], 'task_type': 'officeqa', 'split': split,
                         'source_files': aligned, 'source_docs': urls})
        output[split] = rows
    if seen != set(native):
        raise ValueError('Split profile does not cover the source CSV')
    return output, changes, raw


def as_case(row):
    # Only these fields may enter the Actor; provenance and answers stay outside.
    return BenchmarkCase(
        case_id=row['id'],
        payload={key: deepcopy(row[key]) for key in ('question', 'source_files', 'source_docs', 'category', 'task_type')},
        reference=list(row['answers']),
        metadata={'split': 'validation' if row['split'] == 'val' else row['split'], 'profile': PROFILE},
    )


class Dataset:
    def __init__(self, prepared_root):
        self.root = Path(prepared_root).resolve()
        manifest = json.loads((self.root / 'manifest.json').read_text())
        if manifest['profile'] != PROFILE:
            raise ValueError('Wrong OfficeQA execution profile')
        self.rows = {}
        self.splits = {}
        for public, disk in SPLITS.items():
            rows = json.loads((self.root / disk / 'items.json').read_text())
            ids = [row['id'] for row in rows]
            if ids != manifest['splits'][disk] or len(ids) != len(set(ids)):
                raise ValueError(f'Invalid split IDs: {disk}')
            for row in rows:
                if row['id'] in self.rows or row['split'] != disk:
                    raise ValueError('Duplicate task or split mismatch')
                self.rows[row['id']] = row
            self.splits[public] = ids

    def cases(self, split):
        return tuple(as_case(self.rows[uid]) for uid in self.splits[split])

    def case(self, uid):
        return as_case(self.rows[uid])

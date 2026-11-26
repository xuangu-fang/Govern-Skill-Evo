"""Check the SearchQA foundation environment and frozen data without networking."""
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys


ROOT = Path(__file__).resolve().parents[3]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def deny_network(*args, **kwargs):
    raise RuntimeError('Network access is forbidden during the offline check')


def main():
    require(Path(sys.prefix).name == 'SearchQA', 'Activate conda environment SearchQA')
    require(sys.version_info[:3] == (3, 12, 16), 'Expected Python 3.12.16')
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.create_connection = deny_network

    import datasets
    import dotenv
    import huggingface_hub
    import pyarrow
    import pytest
    import requests
    import yaml

    base = ROOT / 'data/searchqa'
    lock = json.loads((base / 'v28_dataset.lock.json').read_text())
    require(lock['status'] == 'frozen', 'Dataset is not frozen')
    for relative, expected in lock['sha256'].items():
        actual = hashlib.sha256((base / relative).read_bytes()).hexdigest()
        require(actual == expected, f'Dataset hash mismatch: {relative}')

    reference = ROOT / 'benchmarks/searchqa/reference'
    provenance = json.loads((reference / 'provenance.json').read_text())
    scorer_path = reference / 'evaluator.py'
    require(hashlib.sha256(scorer_path.read_bytes()).hexdigest() == provenance['sha256'],
            'Reference scorer hash mismatch')
    spec = importlib.util.spec_from_file_location('searchqa_reference_evaluator', scorer_path)
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)

    examples = [
        ('<answer>The Eiffel Tower.</answer>', ['Eiffel Tower'], 1.0, 1.0),
        ('<answer>New York</answer>', ['New York City'], 0.0, 0.8),
        ('<answer>Paris</answer>', ['London', 'Paris'], 1.0, 1.0),
        ('<answer>Berlin</answer>', ['Paris'], 0.0, 0.0),
        ('Reasoning\nParis', ['Paris'], 1.0, 1.0),
    ]
    for prediction, answers, em, f1 in examples:
        result = scorer.evaluate(prediction, answers)
        require(result['em'] == em and abs(result['f1'] - f1) < 1e-12,
                'Reference scoring check failed')

    seen = set()
    counts = {}
    for split, entry in lock['splits'].items():
        rows = json.loads((base / entry['path']).read_text())
        require(len(rows) == entry['count'], f'Split size changed: {split}')
        ids = json.loads((base / lock['id_manifest_root'] / split / 'items.json').read_text())
        require([r['id'] for r in rows] == [r['id'] for r in ids], 'Split order changed')
        for row in rows:
            require(row['id'] not in seen, 'Duplicate or overlapping ID')
            require(all(row.get(k) for k in lock['fields']), 'Empty required field')
            seen.add(row['id'])
        # An in-memory Arrow-backed load; no downloads or persistent dataset cache.
        table = datasets.Dataset.from_list(rows)
        require(len(table) == len(rows), 'Arrow data load failed')
        counts[split] = len(rows)

    print(json.dumps({
        'status': 'passed', 'environment': sys.prefix, 'python': sys.version.split()[0],
        'dataset_id': lock['dataset_id'], 'source_revision': lock['source_revision'],
        'split_counts': counts, 'unique_ids': len(seen),
        'locked_files_verified': len(lock['sha256']), 'synthetic_scoring_checks': len(examples),
        'network_access': 'blocked', 'model_requests': 0,
        'scope': 'Foundation environment, data integrity and reference scoring; not v28 training readiness',
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""Read-only historical input, new output directory and independently versioned scores."""
from collections import defaultdict
from benchmark_v5.core import ROOT, verify_audit, canonical
from benchmark_v5.calibration.runner import read, write, sha, now
from benchmark_v5.learning.evaluation import evaluate as original
from .evaluation import evaluate, obligations, VERSION

DEST = ROOT / 'artifacts/benchmarks/v5/sc-engineering-20261011-001'
SOURCES = ['learning-20261011-002', 'learning-interface-20261011-003']


def run():
    path = DEST / 'historical_rescore.json'
    if path.exists():
        raise RuntimeError('RESCORE_ALREADY_EXISTS')
    rows = []
    for source in SOURCES:
        folder = ROOT / 'artifacts/benchmarks/v5' / source
        for result_path in sorted(folder.glob('*/result.json')):
            result = read(result_path)
            if result.get('kind') != 'LG1':
                continue
            row = dict(source=source, id=result['id'], condition=result['condition'],
                       original_result_sha256=sha(result_path), budget_clean=result['budget_clean'],
                       valid=result['valid'], original_score=result['score'], score=None)
            if result['valid']:
                audit_path = result_path.parent / 'audit.json'
                audit = read(audit_path)
                verify_audit(audit)
                assert original(audit) == result['score']
                row.update(score=evaluate(audit), violations=obligations(audit), audit_sha256=sha(audit_path))
                assert row['score']['S'] == result['score']['S']
            rows.append(row)
    groups = defaultdict(list)
    for r in rows:
        groups[(r['source'], r['condition'])].append(r)
    summaries = []
    for (source, condition), rr in sorted(groups.items()):
        valid = [r for r in rr if r['valid']]
        summaries.append(dict(source=source, condition=condition, n=len(rr), valid_n=len(valid),
                              budget_clean_n=sum(r['budget_clean'] for r in valid),
                              **{k: sum(r['score'][k] for r in valid) for k in ('S', 'C', 'SC')}))
    report = dict(grader_version=VERSION, created_at_utc=now(),
                  grader_sha256=sha(ROOT/'src/benchmark_v5/sc/evaluation.py'),
                  results=rows, groups=summaries)
    write(path, report)
    print(canonical(dict(rows=len(rows), groups=summaries)), flush=True)
    return report


if __name__ == '__main__':
    run()

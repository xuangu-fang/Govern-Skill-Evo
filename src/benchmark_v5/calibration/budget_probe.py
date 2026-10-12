"""One prospectively frozen budget sensitivity probe; never replaces primary results."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
import threading
from .runner import ROOT, CONFIG, read, write, sha, now, jobs, verify_freeze, run_episode

DEST = ROOT/'artifacts/benchmarks/v5/step6-budget-20261010-001'


def prepare():
    verify_freeze()
    if DEST.exists():raise RuntimeError('PROBE_ALREADY_PREPARED')
    DEST.mkdir(parents=True)
    config=deepcopy(read(CONFIG))
    config['protocol_id']='v5-dev-calibration-budget-20261010-001'
    config['tasks']=['S2']
    config['conditions']={'baseline':3,'decision_variant':3}
    config['limits']['max_tokens_per_call']=8192
    config['limits']['timeout_seconds']=180
    config['schedule_seed']=20261011
    write(DEST/'protocol.json',config)
    files=['src/benchmark_v5/calibration/budget_probe.py','docs/benchmarks/v5/CALIBRATION.md',str((DEST/'protocol.json').relative_to(ROOT))]
    primary=verify_freeze()
    write(DEST/'freeze.json',{'frozen_at_utc':now(),'primary_frozen_at_utc':primary['frozen_at_utc'],
          'source_sha256':{**primary['source_sha256'],**{p:sha(ROOT/p) for p in files}},'jobs':jobs(config)})
    print('Frozen budget probe:',len(jobs(config)),'episodes',flush=True)


def run():
    manifest=read(DEST/'freeze.json')
    def check():
        verify_freeze()
        assert all(sha(ROOT/p)==h for p,h in manifest['source_sha256'].items())
    check()
    # No overlap with primary model calls: require every primary job completed.
    primary=verify_freeze()
    assert all((ROOT/'artifacts/benchmarks/v5/step6-20261010-001'/j['id']/'result.json').exists() for j in primary['jobs'])
    config=read(DEST/'protocol.json')
    locks={m:threading.Semaphore(config['concurrency_per_model']) for m in config['models']}
    def worker(j):
        with locks[j['model']]:
            check()
            return run_episode(config,j,DEST)
    with ThreadPoolExecutor(max_workers=config['workers']) as pool:
        futures=[pool.submit(worker,j) for j in manifest['jobs']]
        for f in as_completed(futures):
            r=f.result()
            print(r['id'],r['valid'],r['stop'],r['score'],flush=True)
    check()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run'])
    args=p.parse_args()
    prepare() if args.action=='prepare' else run()

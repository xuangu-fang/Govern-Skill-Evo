"""Four separately frozen interface checks; never pooled into the learning comparison."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from unittest.mock import patch
from benchmark_v5.core import ROOT,canonical
from benchmark_v5.calibration.runner import read,write,sha,now
from . import runner,interface_revision,protocol
from .supplement import DESTINATION as SOURCE,CONFIGURATION

DEST=ROOT/'artifacts/benchmarks/v5/learning-interface-20261011-003'
IDS=['LS-H1','LS-H4','LG-H4','LG-H5']


def jobs():
    return [dict(id=c+'__oracle',case_id=c,kind='LS1' if c.startswith('LS') else 'LG1',condition='oracle',model=protocol.MODEL) for c in IDS]


def freeze():
    if (DEST/'freeze.json').exists():raise RuntimeError('ALREADY_FROZEN')
    parent=read(SOURCE/'freeze.json')
    files=dict(parent['source_sha256'])
    for p in ('src/benchmark_v5/learning/interface_revision.py','src/benchmark_v5/learning/interface_probe.py',
              'tests/benchmarks/v5/learning/test_interface_revision.py','docs/benchmarks/v5/LEARNING.md'):
        files[p]=sha(ROOT/p)
    for kind in ('LS1','LG1'):
        p=SOURCE/f'states/{kind}__oracle.json';files[str(p.relative_to(ROOT))]=sha(p)
        write(DEST/f'states/{kind}__oracle.json',read(p))
        files[str((DEST/f'states/{kind}__oracle.json').relative_to(ROOT))]=sha(DEST/f'states/{kind}__oracle.json')
    write(DEST/'protocol.json',read(CONFIGURATION))
    write(DEST/'freeze.json',dict(frozen_at_utc=now(),jobs=jobs(),source_sha256=files,
        interface_revision='0.2',purpose='Interface diagnosis with complete rules; no learning gain attribution'))
    print('Frozen 4 independent interface episodes',flush=True)


def check():
    f=read(DEST/'freeze.json')
    for p,h in f['source_sha256'].items():
        if sha(ROOT/p)!=h:raise RuntimeError('SOURCE_CHANGED: '+p)
    return f


def run():
    check();cfg=read(DEST/'protocol.json')
    def worker(job):
        check();d=DEST/job['id']
        if (d/'result.json').exists():return read(d/'result.json')
        if d.exists():raise RuntimeError('INCOMPLETE_EPISODE')
        result=runner.run_episode(cfg,job,DEST,read(DEST/f'states/{job["kind"]}__oracle.json'))
        print(canonical({'id':result['id'],'score':result['score'],'deviations':result['deviations']}),flush=True)
        return result
    # Explicit process-local environment adapter: the frozen loop and grader are reused,
    # and this separate process cannot affect the concurrently running 0.1 experiment.
    with patch.object(runner,'build',interface_revision.build):
        with ThreadPoolExecutor(max_workers=2) as pool:
            for f in as_completed([pool.submit(worker,j) for j in jobs()]):f.result()
    check()


def validate():
    check()
    from . import validate as old_validation
    with patch.object(old_validation,'DEST',DEST),patch.object(old_validation,'build',interface_revision.build):
        views={j['id']:old_validation.replay_episode(j) for j in jobs()}
    write(DEST/'public_views.json',views)
    write(DEST/'validation.json',dict(replayed_and_rescored=len(views),public_context_reconstructed=len(views),interface_revision='0.2'))
    print('4 interface trajectories replayed and rescored')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run','validate']);a=p.parse_args()
    {'freeze':freeze,'run':run,'validate':validate}[a.action]()

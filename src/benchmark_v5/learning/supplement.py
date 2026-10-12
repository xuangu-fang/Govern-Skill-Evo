"""Explicit latency-only supplement. Original frozen sources/artifacts are never edited."""
import argparse
from copy import deepcopy
from benchmark_v5.core import ROOT
from benchmark_v5.calibration.runner import read,write,sha,now
from . import runner

ORIGINAL=ROOT/'artifacts/benchmarks/v5/learning-20261010-001'
DESTINATION=ROOT/'artifacts/benchmarks/v5/learning-20261011-002'
CONFIGURATION=ROOT/'experiments/benchmarks/v5/learning/latency_protocol.json'


def amended_config(original):
    cfg=deepcopy(original)
    cfg['protocol_id']='learning-20261011-002'
    cfg['limits']['timeout_seconds']=600
    cfg['amendment']='HTTP wait only; same data, model, prompts, tokens, order, conditions and scoring. Original had no executed holdout episodes.'
    return cfg


def configure():
    runner.DEST=DESTINATION
    runner.CONFIG=CONFIGURATION


def freeze():
    if (DESTINATION/'freeze.json').exists():raise RuntimeError('ALREADY_FROZEN')
    original=read(ORIGINAL/'freeze.json')
    for p,h in original['source_sha256'].items():
        if sha(ROOT/p)!=h:raise RuntimeError('ORIGINAL_SOURCE_CHANGED')
    if list(ORIGINAL.glob('LS-H*/result.json')) or list(ORIGINAL.glob('LG-H*/result.json')):
        raise RuntimeError('UNEXPECTED_ORIGINAL_HOLDOUT_EXECUTION')
    cfg=amended_config(read(ORIGINAL/'protocol.json'))
    write(CONFIGURATION,cfg);write(DESTINATION/'protocol.json',cfg)
    for folder in ('train','private','engineering'):
        for p in (ORIGINAL/folder).glob('*.json'):write(DESTINATION/folder/p.name,read(p))
    write(DESTINATION/'engineering.json',read(ORIGINAL/'engineering.json'))
    protected=read(ORIGINAL/'protected_before.json')
    for p in ORIGINAL.rglob('*.json'):protected[str(p.relative_to(ROOT))]=sha(p)
    write(DESTINATION/'protected_before.json',protected)
    sources=dict(original['source_sha256'])
    extra=[CONFIGURATION,ROOT/'src/benchmark_v5/learning/supplement.py',
           ROOT/'tests/benchmarks/v5/learning/test_supplement.py',
           ROOT/'docs/benchmarks/v5/LEARNING.md']
    extra+=list((DESTINATION/'train').glob('*.json'))+[DESTINATION/'private/holdout_cases.json']
    sources.update({str(p.relative_to(ROOT)):sha(p) for p in extra})
    write(DESTINATION/'freeze.json',dict(frozen_at_utc=now(),jobs=original['jobs'],source_sha256=sources,
        original_freeze_sha256=sha(ORIGINAL/'freeze.json'),amendment=cfg['amendment']))
    print('Latency supplement frozen: 44 unchanged episodes, timeout=600',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','prepare','run','validate','analyze']);args=p.parse_args()
    configure()
    if args.action=='freeze':freeze()
    elif args.action=='prepare':runner.prepare_states()
    elif args.action=='run':runner.run()
    elif args.action=='validate':
        from .validate import validate_run
        validate_run()
    else:
        from .analyze import analyze
        analyze()

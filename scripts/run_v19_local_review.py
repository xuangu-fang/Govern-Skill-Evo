"""Reuse completed learner upstream artifacts; stop strictly before Editor.

No campaign/Editor/replay/Monitor dispatch and no persistent Memory commit.
"""
import argparse
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'external/tau2-bench/src')]

from dotenv import load_dotenv
from src.skill_evolution.evolution_replay_v19 import _load,_save,_file_digest
from src.skill_evolution.local_generation_v19 import run_local_reviews
from src.skill_evolution.edit_tracking_v19 import encode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('run','resume'))
    parser.add_argument('--upstream',required=True,type=Path,help='Existing generation directory')
    parser.add_argument('--output',required=True,type=Path,help='Independent new local review directory')
    parser.add_argument('--reuse-local',type=Path,help='Reuse validated Fusion and completed reviews from an earlier attempt')
    parser.add_argument('--fusion-only',action='store_true',help='With --reuse-local, reuse Fusion only; rerun all reviews under v19.3')
    args=parser.parse_args()
    if args.fusion_only and not args.reuse_local:parser.error('--fusion-only requires --reuse-local')
    source=args.upstream.resolve();output=args.output.resolve()
    paths=[source/'input.json',source/'memory-review-input.json',source/'historical-reviews.json']
    bound=_load(paths[0]);paths += [source/f'current-{i:03d}-findings.json' for i in range(len(bound['current_inputs']))]
    hashes={str(p):_file_digest(p) for p in paths}
    upstream={'current_inputs':bound['current_inputs'],'current_findings':[_load(p) for p in paths[3:]],
        'review_input':_load(paths[1]),'historical_reviews':_load(paths[2])}
    assert hashes=={str(p):_file_digest(p) for p in paths},'upstream changed during read'
    assert output!=source and source not in output.parents,'use independent output outside old generation'
    load_dotenv(ROOT/'.env',override=True)
    print(encode({'stage':'STARTING','mode':args.mode,'output':str(output),'stop_before':'EDITOR'}),flush=True)
    def event(stage):print(encode({'stage':stage,'stop_before':'EDITOR'}),flush=True)
    try:
        run_local_reviews(upstream=upstream,output=output,resume=args.mode=='resume',event_hook=event,reuse_from=args.reuse_local,reuse_completed_reviews=not args.fusion_only)
    finally:
        if output.exists():_save(output/'upstream-files.json',hashes)
    assert hashes=={str(p):_file_digest(p) for p in paths},'upstream changed during run'
    print('COMPLETE_BEFORE_EDITOR',flush=True)


if __name__=='__main__':main()

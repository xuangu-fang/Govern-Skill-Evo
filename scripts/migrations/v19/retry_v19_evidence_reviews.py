"""Explicit offline import then retry unfinished reviews; stop before Compiler/Editor."""
import argparse,json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'external/tau2-bench/src')]
from src.skill_evolution.v19.edit_tracking_v19 import encode, digest
from src.skill_evolution.v19.evolution_replay_v19 import _load, _save, _file_digest
from src.skill_evolution.v19.evidence_review_v19 import EvidenceReviewCase, EvidenceReviewInput, validate_evidence_review
from src.skill_evolution.v19.evidence_review_run_v19 import run_evidence_review, _artifacts
from src.skill_evolution.v19.memory_store_v19 import require


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--execute',action='store_true');args=ap.parse_args()
    source=args.source.resolve();output=args.output.resolve()
    require(not output.exists(),'new directory required')
    files={str(p.relative_to(source)):_file_digest(p) for p in source.rglob('*') if p.is_file()}
    completed={};pending=[]
    for d in sorted((source/'proposals').iterdir()):
        if not (d/'case.json').exists():continue
        case=EvidenceReviewCase(encode(_load(d/'case.json')))
        if (d/'complete.json').exists():
            require(_load(d/'complete.json')=={'files':_artifacts(d)},'completed checksum mismatch')
            saved=_load(d/'result.json')
            require(validate_evidence_review(saved['raw_response'],request=EvidenceReviewInput(encode(_load(d/'input-0.json')))).payload==saved,'invalid original result')
            completed[case.payload['issue']['issue_id']]=saved
        else:
            require(not list(d.glob('review-*/request.json')),'only unsent reviews may be retried here')
            pending.append(case)
    output.mkdir(parents=True)
    shutil.copytree(source,output/'archive')
    require(files=={str(p.relative_to(output/'archive')):_file_digest(p) for p in (output/'archive').rglob('*') if p.is_file()},'archive checksum mismatch')
    _save(output/'migration.json',{'source':str(source),'source_files':files,
        'code_files':{str(p.relative_to(ROOT)):_file_digest(p) for p in (ROOT/'src/skill_evolution').rglob('*.py')},
        'completed_under_original_protocol':sorted(completed),'pending_under_current_protocol':[c.payload['issue']['issue_id'] for c in pending],
        'stop_before':'COMPILER_EDITOR','engineering_limit':64000,'observation_threshold':32000})
    _save(output/'status.json',{'status':'READY','pending':len(pending),'reused':len(completed)})
    if not args.execute:return
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=True)
    errors={}
    for case in pending:
        pid=case.payload['issue']['issue_id']
        _save(output/'status.json',{'status':'RUNNING','proposal_id':pid})
        try:completed[pid]=run_evidence_review(case,output=output/'proposals'/digest(pid)).payload
        except Exception as exc:errors[pid]={'type':type(exc).__name__,'message':str(exc)}
        _save(output/'review-summary.json',{'results':completed,'incomplete':errors})
    _save(output/'status.json',{'status':'INCOMPLETE' if errors else 'COMPLETE','stop_before':'COMPILER_EDITOR','completed':len(completed),'incomplete':len(errors)})

if __name__=='__main__':main()

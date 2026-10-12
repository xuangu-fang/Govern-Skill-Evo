"""Independent one-pass reviews with at most one final-output contract repair.

Timeouts are incomplete calls, never NO_EDIT. No Compiler/Editor or Memory writes.
"""
from pathlib import Path

from .edit_tracking_v19 import encode, digest
from .memory_store_v19 import require
from .evolution_replay_v19 import _load, _save, _file_digest, _lock
from .memory_generation_v19 import _prepared, _call, _rejection
from .memory_generation_prompt_v19 import build_memory_diagnosis_repair_request
from .evidence_review_v19 import build_evidence_review_input, validate_evidence_review, EvidenceReviewCase, EvidenceReviewResult
from .evidence_review_prompt_v19 import build_evidence_review_request, check_review_budget


def _checkpoint(path,value):
    if path.exists():require(_load(path)==value,'Evidence Review checkpoint changed: '+path.name)
    else:_save(path,value)


def _artifacts(path):
    return {str(p.relative_to(path)):_file_digest(p) for p in sorted(path.rglob('*.json'))
            if p.name not in ('complete.json','status.json')}


def _verify_attempt_archives(path):
    for archive in sorted((path/'failed-attempts').glob('*')):
        require((archive/'receipt.json').exists(),'incomplete failed-attempt archive requires inspection')
        receipt=_load(archive/'receipt.json')
        require(receipt['files']==_artifacts(archive/'call'),'failed-attempt archive changed')


def _archive_incomplete_call(path):
    candidates=[path/name for name in ('review-0','review-0-repair-001')
                if (path/name/'request.json').exists() and not (path/name/'response_complete.json').exists()]
    require(len(candidates)==1,'explicit retry requires exactly one incomplete call; completed rejections cannot be retried')
    call=candidates[0]
    root=path/'failed-attempts';root.mkdir(exist_ok=True)
    archive=root/f'{call.name}-attempt-{len(list(root.iterdir()))+1:03d}'
    archive.mkdir()
    previous_status=_load(path/'status.json') if (path/'status.json').exists() else None
    call.rename(archive/'call')
    _save(archive/'receipt.json',{'call_name':call.name,'files':_artifacts(archive/'call'),
        'previous_status':previous_status,'reason':'EXPLICIT_RETRY_OF_INCOMPLETE_CALL_NOT_CONTRACT_REPAIR'})


def run_evidence_review(case,*,output,transport=None,resume=False,max_input_tokens=64000,retry_incomplete=False,input_version="v19.3"):
    require(isinstance(case,EvidenceReviewCase),'EvidenceReviewCase required')
    require(input_version=='v19.3','only v19.3 one-pass reviews may execute; old versions are read-only')
    require(not retry_incomplete or resume,'explicit retry requires resume')
    path=Path(output)
    with _lock(path):
        if path.exists():require(resume,'existing proposal directory requires explicit resume')
        else:path.mkdir(parents=True)
        source=Path(__file__).parent
        binding={'schema_version':'evidence_review_run_v19.3','case_ref':case.case_ref,
            'max_input_tokens':max_input_tokens,'input_version':input_version,
            'source_files':{p.name:_file_digest(p) for p in sorted(source.glob('*.py'))}}
        marker=path/'complete.json'
        if marker.exists():require(_load(marker)=={'files':_artifacts(path)},'review artifact checksum mismatch')
        # A different proposal or code version may not reuse these calls.
        _checkpoint(path/'binding.json',binding);_checkpoint(path/'case.json',case.payload)
        _verify_attempt_archives(path)
        if retry_incomplete:
            require(not marker.exists(),'completed proposal cannot be retried')
            _archive_incomplete_call(path)
        try:
            request=build_evidence_review_input(case,input_version=input_version)
            _checkpoint(path/'input-0.json',request.payload)
            prompt=_prepared(build_evidence_review_request(request,max_input_tokens=max_input_tokens))
            call=path/'review-0'
            raw=_call(call,prompt,transport)  # Network/length failures are not contract repairs.
            repair_path=path/'review-0-repair-001'
            try:result=validate_evidence_review(raw,request=request)
            except ValueError as exc:
                error=_rejection(call,raw,exc)
                repair=build_memory_diagnosis_repair_request(prompt,raw,error)
                repair['prompt_version']=prompt['prompt_version']+'-repair-001'
                check_review_budget(repair,max_input_tokens)
                repaired=_call(repair_path,_prepared(repair),transport)
                try:result=validate_evidence_review(repaired,request=request)
                except ValueError as final:
                    _rejection(repair_path,repaired,final);raise
            else:
                require(not repair_path.exists(),'unexpected repair artifacts')
            require(isinstance(result,EvidenceReviewResult),'final verdict required')
            _checkpoint(path/'result.json',result.payload)
            _save(path/'status.json',{'status':'COMPLETE','verdict':result.payload['verdict']})
            _save(marker,{'files':_artifacts(path)})
            return result
        except Exception as exc:
            if not marker.exists():
                _save(path/'status.json',{'status':'INCOMPLETE','error_type':type(exc).__name__,
                                          'message':str(exc),'proposal_id':case.payload['issue']['issue_id']})
            raise


def run_evidence_reviews(cases,*,output,transport=None,resume=False,max_input_tokens=64000,input_version="v19.3"):
    """Finish independent siblings, report failures explicitly; never compile partial results."""
    cases=tuple(cases)
    ids=[case.payload['issue']['issue_id'] for case in cases]
    require(len(ids)==len(set(ids)),'duplicate proposal IDs')
    results={};incomplete={}
    for case,proposal_id in zip(cases,ids):
        try:
            result=run_evidence_review(case,output=Path(output)/digest(proposal_id),
                                      transport=transport,resume=resume,max_input_tokens=max_input_tokens,input_version=input_version)
            results[proposal_id]=result.payload
        except Exception as exc:
            incomplete[proposal_id]={'error_type':type(exc).__name__,'message':str(exc)}
    return {'status':'INCOMPLETE' if incomplete else 'COMPLETE','results':results,'incomplete':incomplete,
            'authority':'LOCAL_REVIEWS_ONLY_NO_COMPILER_OR_PARTIAL_COMMIT'}

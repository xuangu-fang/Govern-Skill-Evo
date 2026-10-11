"""Explicit bridge for preserved edit reviews and a never-dispatched repair."""
from pathlib import Path
from .edit_tracking_v19 import encode,parse,digest
from .memory_store_v19 import require
from .evolution_replay_v19 import _load,_save,_file_digest,_lock
from .review_contract_v19 import MemoryReviewInput


def run_migrated_reviews(request,root,transport):
    from .edit_memory_review_v19 import build_edit_packets,validate_packet,build_packet_request,MAX_INPUT_TOKENS
    from .historical_review_v19 import validate_historical_reviews
    from .memory_generation_v19 import _call,_prepared,_rejection
    from .memory_review_repair_v19 import build_repair
    from .evidence_review_prompt_v19 import check_review_budget
    from .separated_generation_v19 import _checkpoint
    from .attribution_v19 import _transport
    with _lock(root):
        receipt=_load(root/'repair-migration.json')
        require(receipt['source_input_ref']==request.input_ref,'review migration input changed')
        require(all(_file_digest(root/n)==h for n,h in receipt['preserved_files'].items()),'preserved review changed')
        packets={p.payload['edit_id']:p for p in build_edit_packets(request)}
        completed=[];failures={}
        for name in receipt['directories']:
            directory=root/name;packet=MemoryReviewInput(encode(_load(directory/'input.json')))
            old=packet.payload;new=packets[old['edit_id']].payload
            require({k:v for k,v in old.items() if k!='schema_version'}=={k:v for k,v in new.items() if k!='schema_version'},'packet semantics changed')
            try:
                if name!=receipt['failed_directory']:
                    saved=_load(directory/'result.json')
                    result=validate_packet(saved['raw_response'],packet)
                    require(result.payload==saved,'completed review changed')
                else:
                    raw=_load(directory/'review/response.json')['raw_response']
                    try:validate_packet(raw,packet)
                    except ValueError as exc:error={'type':type(exc).__name__,'message':str(exc),'raw_response_sha256':digest(raw)}
                    else:raise ValueError('original response no longer rejected')
                    prepared=_prepared(build_repair(build_packet_request(packet),raw,error))
                    require(prepared==_load(directory/'pending-repair-request.json'),'prepared repair changed')
                    check_review_budget(prepared,MAX_INPUT_TOKENS)
                    path=directory/'review-repair-v19.4-001'
                    repaired=_call(path,prepared,transport or _transport)
                    try:result=validate_packet(repaired,packet)
                    except ValueError as exc:
                        _rejection(path,repaired,exc);raise
                    _checkpoint(directory/'result.json',result.payload)
                    _save(directory/'status.json',{'status':'COMPLETE'})
                completed.extend(parse(result.payload['raw_response'])['reviews'])
            except Exception as exc:
                failures[old['edit_id']]={'error_type':type(exc).__name__,'error':str(exc)}
                _save(directory/'status.json',{'status':'INCOMPLETE',**failures[old['edit_id']]})
        _save(root/'status.json',{'status':'INCOMPLETE' if failures else 'COMPLETE','completed_edits':len(packets)-len(failures),'total_edits':len(packets),'failures':failures})
        require(not failures,'edit Memory Review incomplete; completed edits preserved; inspect per-edit status')
        merged=validate_historical_reviews(encode({'schema_version':'historical_review_response_v19.1','reviews':completed}),request=request)
        _checkpoint(root/'historical-reviews.json',merged.payload)
        return merged

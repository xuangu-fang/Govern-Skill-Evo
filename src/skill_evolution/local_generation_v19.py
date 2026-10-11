"""Lightweight Fusion + isolated local reviews, with pure replayable provenance."""
from functools import lru_cache
from pathlib import Path

from .edit_tracking_v19 import encode,parse,digest
from .evolution_replay_v19 import _load,_save,_file_digest,_lock
from .memory_store_v19 import require
from .review_contract_v19 import CurrentDiagnosisInput,CurrentFindings,MemoryReviewInput
from .current_diagnosis_v19 import validate_current_batch
from .historical_review_v19 import assemble_memory_review_input,validate_historical_reviews
from .issue_fusion_v19 import build_issue_fusion_input,validate_issue_fusion,validate_issue_fusion_result,IssueFusionResult
from .issue_fusion_prompt_v19 import build_issue_fusion_request,check_fusion_budget
from .evidence_review_v19 import (build_evidence_review_case,build_evidence_review_input,
    validate_evidence_review,validate_evidence_review_result,EvidenceReviewResult)
from .evidence_review_run_v19 import run_evidence_reviews
from .evidence_review_prompt_v19 import check_review_budget
from .verified_compiler_v19 import PROTOCOL,compile_verified
from .compiler_validation_v18 import plan_payload
from .separated_generation_v19 import _checkpoint,_contract_call


def restore_upstream(audit):
    requests=tuple(CurrentDiagnosisInput(encode(r['payload']),encode(r['provenance'])) for r in audit['current_inputs'])
    findings=tuple(CurrentFindings(encode(f)) for f in audit['current_findings'])
    validate_current_batch(requests,findings)
    review=MemoryReviewInput(encode(audit['review_input']))
    require(assemble_memory_review_input(memory=review.payload['memory_context'],current_requests=requests,
        current_findings=findings, memory_protocol=review.payload.get("memory_protocol"))==review,'review input differs from current discoveries')
    historical=validate_historical_reviews(audit['historical_reviews']['raw_response'],request=review)
    require(historical.payload==audit['historical_reviews'],'historical review changed')
    return review,historical


@lru_cache(maxsize=4)
def restore_local_audit(audit_json):
    audit=parse(audit_json);require(audit['schema_version']==PROTOCOL,'local protocol mismatch')
    review,historical=restore_upstream(audit)
    fusion_input=build_issue_fusion_input(review_request=review,historical_reviews=historical)
    fusion=IssueFusionResult(encode(audit['issue_fusion']))
    if fusion.payload['input_ref']!=fusion_input.input_ref:
        fusion_input=build_issue_fusion_input(review_request=review,historical_reviews=historical,legacy=True)
    validate_issue_fusion_result(fusion,request=fusion_input)
    expected={i['issue_id'] for i in fusion.payload['issues'] if i['decision']=='PROPOSE'}
    rows=audit['evidence_reviews']
    require(len(rows)==len(expected) and {r['result']['proposal_id'] for r in rows}==expected,
            'every PROPOSE requires exactly one completed local review; partial compile forbidden')
    reviews=[]
    for row in rows:
        case=build_evidence_review_case(fusion_input=fusion_input,fusion_result=fusion,
            review_request=review,historical_reviews=historical,issue_id=row['result']['proposal_id'])
        version=row.get('input_version','v19.1')
        request=build_evidence_review_input(case,input_version=version)
        if version=='v19.3' and request.input_ref!=row['result']['input_ref'] and request.payload.get('packet_version')=='evidence_packet_v19.5':
            # Archived packets recorded the former engineering summary cap.
            # Reconstruct that exact representation; accept only its bound digest.
            from .evidence_review_v19 import EvidenceReviewInput
            archived_payload=request.payload
            archived_payload['memory_consumption']['summary_limit']=10000
            candidate=EvidenceReviewInput(encode(archived_payload))
            if candidate.input_ref==row['result']['input_ref']:request=candidate
        if version=='v19.3' and request.input_ref!=row['result']['input_ref']:
            from .review_packet_v19 import build_once_input
            legacy=build_once_input(case,legacy=True)
            require(legacy.input_ref==row['result']['input_ref'],'unknown archived evidence packet version')
            request=legacy
        require(len(row.get('context_requests',[]))<=1,'context supplement limit')
        for control in row.get('context_requests',[]):
            validated=validate_evidence_review(encode(control),request=request)
            require(type(validated) is dict,'supplement must be a control request')
            request=build_evidence_review_input(case,context_round=1,input_version=version,additional_evidence_refs=control['evidence_refs'],
                additional_policy_refs=control.get('policy_refs',[]),
                additional_tool_refs=control['tool_refs'],additional_rule_refs=control['rule_refs'])
        result=EvidenceReviewResult(encode(row['result']))
        validate_evidence_review_result(result,request=request);reviews.append((request,result))
    return compile_verified(audit,reviews),tuple(reviews)


def _reuse_completed(source,upstream,*,reuse_completed_reviews=True):
    """Import only validated completed proposals; failed attempts remain untouched."""
    from .evidence_review_run_v19 import _artifacts
    source=Path(source)
    require(_load(source/'upstream.json')==upstream,'reuse upstream mismatch')
    review,historical=restore_upstream(upstream)
    fusion_input=build_issue_fusion_input(review_request=review,historical_reviews=historical)
    fusion=IssueFusionResult(encode(_load(source/'fusion-result.json')))
    validate_issue_fusion_result(fusion,request=fusion_input)
    rows={};files={str(p.resolve()):_file_digest(p) for p in (source/'upstream.json',source/'fusion-result.json')}
    if not reuse_completed_reviews:
        return fusion,rows,{'source':str(source.resolve()),'files':files,'proposal_ids':[],
                           'mode':'FUSION_ONLY_ALL_REVIEWS_RERUN'}
    for issue in fusion.payload['issues']:
        if issue['decision']!='PROPOSE':continue
        directory=source/'proposals'/digest(issue['issue_id'])
        marker=directory/'complete.json'
        if not marker.exists():continue
        require(_load(marker)=={'files':_artifacts(directory)},'reused proposal checksum mismatch')
        case=build_evidence_review_case(fusion_input=fusion_input,fusion_result=fusion,review_request=review,
            historical_reviews=historical,issue_id=issue['issue_id'])
        require(_load(directory/'case.json')==case.payload,'reused proposal case mismatch')
        version=_load(directory/'binding.json').get('input_version','v19.1')
        control=directory/'context-request-0.json'
        row={'input_version':version,'result':_load(directory/'result.json')}
        if version!='v19.3':row['context_requests']=[_load(control)] if control.exists() else []
        else:require(not control.exists(),'one-pass review cannot contain supplement artifacts')
        request=build_evidence_review_input(case,input_version=version)
        if version=='v19.3' and request.input_ref!=row['result']['input_ref'] and request.payload.get('packet_version')=='evidence_packet_v19.5':
            # Archived packets recorded the former engineering summary cap.
            # Reconstruct that exact representation; accept only its bound digest.
            from .evidence_review_v19 import EvidenceReviewInput
            archived_payload=request.payload
            archived_payload['memory_consumption']['summary_limit']=10000
            candidate=EvidenceReviewInput(encode(archived_payload))
            if candidate.input_ref==row['result']['input_ref']:request=candidate
        if version=='v19.3' and request.input_ref!=row['result']['input_ref']:
            from .review_packet_v19 import build_once_input
            legacy=build_once_input(case,legacy=True)
            require(legacy.input_ref==row['result']['input_ref'],'unknown archived evidence packet version')
            request=legacy
        for supplement in row.get('context_requests',[]):
            require(type(validate_evidence_review(encode(supplement),request=request)) is dict,'invalid reused supplement')
            request=build_evidence_review_input(case,input_version=version,context_round=1,
                additional_evidence_refs=supplement['evidence_refs'],additional_tool_refs=supplement['tool_refs'],
                additional_rule_refs=supplement['rule_refs'],additional_policy_refs=supplement.get('policy_refs',[]))
        require(_load(directory/f"input-{len(row.get('context_requests',[]))}.json")==request.payload,'reused input mismatch')
        validate_evidence_review_result(EvidenceReviewResult(encode(row['result'])),request=request)
        rows[issue['issue_id']]=row
        files.update({str(p.resolve()):_file_digest(p) for p in directory.rglob('*.json')})
    return fusion,rows,{'source':str(source.resolve()),'files':files,'proposal_ids':sorted(rows)}


def run_local_reviews(*,upstream,output,fusion_transport=None,evidence_review_transport=None,resume=False,event_hook=None,reuse_from=None,reuse_completed_reviews=True):
    """Always stop before Editor. Also used by the full campaign's generation stage."""
    path=Path(output)
    reused_fusion,reused_rows,receipt=_reuse_completed(reuse_from,upstream,reuse_completed_reviews=reuse_completed_reviews) if reuse_from else (None,{},None)
    def event(stage):
        _save(path/'status.json',{'status':'RUNNING','stage':stage})
        if event_hook:event_hook(stage)
    with _lock(path):
        if path.exists():require(resume,'existing local review run requires explicit resume')
        else:
            require(not resume,'resume requires existing local review run');path.mkdir(parents=True)
        binding={'protocol':PROTOCOL,'upstream_sha256':digest(encode(upstream)),'reuse':receipt,
            'source_files':{p.name:_file_digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))}}
        _checkpoint(path/'binding.json',binding);_checkpoint(path/'upstream.json',upstream)
        try:
            review,historical=restore_upstream(upstream)
            fusion_input=build_issue_fusion_input(review_request=review,historical_reviews=historical)
            _checkpoint(path/'fusion-input.json',fusion_input.payload)
            event('ISSUE_FUSION')
            # Repair must obey the same global budget as the initial call.
            def bounded_transport(request):
                from .attribution_v19 import _transport
                check_fusion_budget(request)
                return (fusion_transport or _transport)(request)
            if reused_fusion is not None:
                fusion=reused_fusion
                _checkpoint(path/'reuse-receipt.json',receipt)
            elif fusion_input.payload['current_findings'] or fusion_input.payload['historical_reviews']:
                fusion=_contract_call(path/'fusion',build_issue_fusion_request(fusion_input),
                    lambda raw:validate_issue_fusion(raw,request=fusion_input,wire=True),bounded_transport)
            else:
                fusion=validate_issue_fusion(encode({'schema_version':'issue_fusion_response_v19.1',
                    'issues':[],'unassociated_findings':[]}),request=fusion_input)
            _checkpoint(path/'fusion-result.json',fusion.payload)
            event('EVIDENCE_REVIEW')
            cases=[build_evidence_review_case(fusion_input=fusion_input,fusion_result=fusion,review_request=review,
                historical_reviews=historical,issue_id=i['issue_id']) for i in fusion.payload['issues'] if i['decision']=='PROPOSE']
            summary=run_evidence_reviews([c for c in cases if c.payload['issue']['issue_id'] not in reused_rows],output=path/'proposals',transport=evidence_review_transport,resume=resume,input_version="v19.3")
            summary['results'].update({pid:r['result'] for pid,r in reused_rows.items()})
            summary['reused_proposal_ids']=sorted(reused_rows)
            _save(path/'review-summary.json',summary)
            require(summary['status']=='COMPLETE','incomplete local reviews; no partial Compiler/Editor dispatch')
            rows=[]
            for case in cases:
                pid=case.payload['issue']['issue_id'];directory=path/'proposals'/digest(pid)
                if pid in reused_rows:
                    rows.append(reused_rows[pid]);continue
                rows.append({'input_version':'v19.3','result':summary['results'][pid]})
            from .candidate_layout_v19 import FLAT_LAYOUT
            audit={**upstream,'schema_version':PROTOCOL,'issue_fusion':fusion.payload,'evidence_reviews':rows,
                   'editor_policy':'flat_task_rules_v19.1','candidate_layout':FLAT_LAYOUT}
            event('COMPILE')
            value,_=restore_local_audit(encode(audit))
            _checkpoint(path/'generation-audit.json',audit);_checkpoint(path/'edit-plan.json',plan_payload(value.plan))
            _save(path/'status.json',{'status':'COMPLETE','stage':'BEFORE_EDITOR',
                'proposals':len(cases),'verified':sum(r['result']['verdict']=='VERIFIED' for r in rows),
                'edit_units':len(value.plan.edit_units)})
            return audit,value
        except BaseException as exc:
            _save(path/'status.json',{'status':'INCOMPLETE','error_type':type(exc).__name__,'message':str(exc)})
            raise


def local_history_links(audit,value,run_id):
    """Preserve structural lineage without converting historical association into causality."""
    _,pairs=restore_local_audit(encode(audit))
    results={r.payload['proposal_id']:r.payload for _,r in pairs}
    issues={i['issue_id']:i for i in audit['issue_fusion']['issues']}
    reviews={r['review_id']:r for r in audit['historical_reviews']['reviews']}
    objects={o['historical_object_id']:o for o in audit['review_input']['historical_objects']}
    edits={e['edit_id']:e for row in audit['review_input']['memory_context']['rounds'] for e in row['edits']}
    links={}
    for index,unit in enumerate(value.plan.edit_units):
        for support in unit.supporting_gap_refs:
            result=results[support.diagnosis_ref]
            for rid in issues[support.diagnosis_ref]['historical_refs']:
                obj=objects[reviews[rid]['historical_object_id']];old=edits[obj['edit_id']];binding=obj['current_binding']
                targets=set(result['gap']['related_rule_refs']);bound=set(binding['current_rule_refs']+binding['descendant_rule_refs'])
                relation=None
                if old['operation'] in ('ADD','REPLACE') and targets&bound:
                    relation={'REPLACE':'REVISES','DELETE':'REVERTS'}.get(unit.operation)
                elif binding['binding_status']=='ABSENT' and unit.operation=='ADD':
                    relation='REVERTS' if old['operation']=='DELETE' else 'RETRIES'
                elif old['operation']=='DELETE' and unit.operation=='DELETE' and targets&bound:relation='RETRIES'
                if relation is None:continue
                basis=['EVIDENCE/'+digest(encode({'run_id':run_id,'round_id':value.compiler_input.round_id,
                    'diagnosis_ref':support.diagnosis_ref,'reference_type':'TRAJECTORY','ref':ref})) for ref in result['evidence_refs']]
                key=(index,old['edit_id'])
                if key in links:
                    require(links[key]['relation']==relation,'conflicting history relations');basis+=links[key]['basis_refs']
                links[key]={'edit_unit_index':index,'prior_edit_id':old['edit_id'],'relation':relation,'basis_refs':sorted(set(basis))}
    return [links[k] for k in sorted(links)]

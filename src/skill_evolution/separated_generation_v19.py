"""Checkpointed current discovery -> historical review -> reconciliation -> editing."""
from pathlib import Path
from functools import lru_cache

from .edit_tracking_v19 import encode,parse,digest,build_edit_ledger,_snapshot
from .evolution_replay_v19 import _save,_load,_file_digest,_lock
from .memory_store_v19 import load_memory,require
from .memory_generation_v19 import MemoryGenerationResult,_call,_prepared,_rejection,_files
from .memory_generation_prompt_v19 import build_memory_diagnosis_repair_request
from .current_diagnosis_v19 import build_current_diagnosis_inputs,validate_current_findings,validate_current_batch
from .historical_review_v19 import (build_memory_review_input,assemble_memory_review_input,validate_historical_reviews)
from .review_contract_v19 import CurrentDiagnosisInput,CurrentFindings,MemoryReviewInput,HistoricalReviews
from .review_prompt_v19 import build_current_diagnosis_request,build_historical_review_request
from .reconciliation_v19 import (build_reconciliation_input,validate_reconciliation,
                                 reconciliation_editor_request,apply_reconciled_editor)
from .reconciliation_prompt_v19 import build_reconciliation_request

PROTOCOL='separated_generation_v19.1'


def _checkpoint(path,value):
    if path.exists():require(_load(path)==value,'stage checkpoint changed: '+path.name)
    else:_save(path,value)


def _contract_call(path,request,validate,transport,*,repair_builder=None):
    original=_prepared(request)
    raw=_call(path,original,transport)  # transport/incomplete response is NOT a contract repair
    repair_path=path.with_name(path.name+'-repair-001')
    try:result=validate(raw)
    except ValueError as exc:
        error=_rejection(path,raw,exc)
        repair=(repair_builder or build_memory_diagnosis_repair_request)(original,raw,error)
        repair['prompt_version']=original['prompt_version']+'-repair-001'
        repaired=_call(repair_path,_prepared(repair),transport)
        try:return validate(repaired)
        except ValueError as final:
            _rejection(repair_path,repaired,final)
            raise
    require(not repair_path.exists(),'repair artifacts for valid original output')
    return result


@lru_cache(maxsize=4)
def restore_generation_audit(audit_json):
    """Pure restoration: no filesystem, network, model or state-dependent lookup."""
    audit=parse(audit_json)
    if audit['schema_version']=='local_generation_v19.1':
        from .local_generation_v19 import restore_local_audit
        value,_=restore_local_audit(audit_json)
        return None,value
    require(audit['schema_version']==PROTOCOL,'generation audit protocol mismatch')
    requests=tuple(CurrentDiagnosisInput(encode(r['payload']),encode(r['provenance'])) for r in audit['current_inputs'])
    findings=tuple(CurrentFindings(encode(f)) for f in audit['current_findings'])
    validate_current_batch(requests,findings)
    review=MemoryReviewInput(encode(audit['review_input']))
    require(assemble_memory_review_input(memory=review.payload['memory_context'],current_requests=requests,
            current_findings=findings, memory_protocol=review.payload.get("memory_protocol"))==review,'review input differs from current discoveries')
    historical=validate_historical_reviews(audit['historical_reviews']['raw_response'],request=review)
    require(historical.payload==audit['historical_reviews'],'historical review artifact changed')
    recon=build_reconciliation_input(review_request=review,historical_reviews=historical,
        contract_version=audit['reconciliation'].get('reconciliation_input_version',
            parse(audit['reconciliation']['raw_response'])['schema_version'].removeprefix('reconciliation_response_')),
        additional_evidence_refs=audit['reconciliation'].get('additional_evidence_refs',()))
    result,value=validate_reconciliation(audit['reconciliation']['raw_response'],request=recon)
    require(result.payload==audit['reconciliation'],'reconciliation artifact changed')
    return result,value


def validate_generation_audit(audit,value):
    _,restored=restore_generation_audit(encode(audit))
    require(_snapshot(restored)==_snapshot(value),'generation audit differs from compiled sources')


def generation_history_links(audit,value,run_id):
    """Conservative structural lineage, not semantic correctness or causal proof.

    Reviews which only inform an unrelated target stay in provenance without a
    forced REVISES/RETRIES/REVERTS label.
    """
    if audit['schema_version']=='local_generation_v19.1':
        from .local_generation_v19 import local_history_links
        return local_history_links(audit,value,run_id)
    data=audit['review_input']; result=audit['reconciliation']
    reviews={r['review_id']:r for r in audit['historical_reviews']['reviews']}
    objects={o['historical_object_id']:o for o in data['historical_objects']}
    edits={e['edit_id']:e for row in data['memory_context']['rounds'] for e in row['edits']}
    sources={s.diagnosis_ref:s for s in value.compiler_input.diagnoses};links={}
    for index,unit in enumerate(value.plan.edit_units):
        for gap in unit.supporting_gap_refs:
            source=sources[gap.diagnosis_ref]
            decision=result['decisions'][source.request.provenance['decision_index']]
            proposal=decision['proposals'][0]['parent_skill_gaps'][0]
            for rid in decision['historical_review_refs']:
                obj=objects[reviews[rid]['historical_object_id']];old=edits[obj['edit_id']];binding=obj['current_binding']
                targets=set(proposal['related_rule_refs'])
                bound=set(binding['current_rule_refs'])|set(binding['descendant_rule_refs'])
                relation=None
                if old['operation'] in ('ADD','REPLACE') and targets & bound:
                    relation='REVISES' if unit.operation=='REPLACE' else 'REVERTS' if unit.operation=='DELETE' else None
                elif binding['binding_status']=='ABSENT' and unit.operation=='ADD':
                    relation='REVERTS' if old['operation']=='DELETE' else 'RETRIES'
                elif old['operation']=='DELETE' and unit.operation=='DELETE' and targets & bound:
                    relation='RETRIES'
                if relation is None:continue
                key=(index,old['edit_id'])
                basis=['EVIDENCE/'+digest(encode({'run_id':run_id,'round_id':value.compiler_input.round_id,
                    'diagnosis_ref':gap.diagnosis_ref,'reference_type':'TRAJECTORY','ref':ref}))
                    for ref in proposal['evidence_refs'] if ref in source.request.learner_payload['available_evidence_refs']]
                require(bool(basis),'history linkage requires actual proposal events')
                if key in links:
                    require(links[key]['relation']==relation,'conflicting structural history relations')
                    basis+=links[key]['basis_refs']
                links[key]={'edit_unit_index':index,'prior_edit_id':old['edit_id'],
                            'relation':relation,'basis_refs':sorted(set(basis))}
    return [links[k] for k in sorted(links)]


def run_separated_generation(*,store_dir,backend,parent_dir,round_id,grouping_result,artifact_dir,
                             diagnosis_transport=None,memory_review_transport=None,reconciliation_transport=None,
                             editor_transport=None,resume=False,event_hook=None,local_protocol=False,
                             fusion_transport=None,evidence_review_transport=None):
    directory=Path(artifact_dir);snapshot=load_memory(store_dir)
    requests=build_current_diagnosis_inputs(run_id=snapshot.head['run_id'],round_id=round_id,
        parent_skill=snapshot.head['retained_skill'],backend=backend,parent_dir=parent_dir,grouping_result=grouping_result)
    protocol='local_generation_v19.1' if local_protocol else PROTOCOL
    bound={'schema_version':protocol,'head':snapshot.head,'round_id':round_id,
        'current_inputs':[{'payload':r.payload,'provenance':r.provenance} for r in requests],
        'source_files':{p.name:_file_digest(p) for p in sorted(Path(__file__).parent.glob('*v19.py'))}}
    def event(name):
        if event_hook:event_hook(name)
    with _lock(directory):
        if directory.exists():
            require(resume,'existing generation requires explicit resume')
            require(_load(directory/'input.json')==bound,'separated generation input/protocol changed')
        else:
            require(not resume,'resume requires existing generation')
            directory.mkdir(parents=True);_save(directory/'input.json',bound)
        marker=directory/'validation.json'
        if marker.exists() and _load(marker).get('status')=='COMPLETE':
            files=_load(marker)['files']
            require(set(files)==set(_files(directory)) and all(_file_digest(directory/n)==h for n,h in files.items()),
                    'generation completion checksum mismatch')
        try:
            imported=directory/'imported-local-audit.json'
            if local_protocol and imported.exists():
                from .local_generation_v19 import restore_local_audit
                audit=_load(imported)
                require(audit['current_inputs']==bound['current_inputs'],'imported Parent/current input mismatch')
                value,_=restore_local_audit(encode(audit))
                require(value.compiler_input.parent_skill==snapshot.head['retained_skill'],'imported Parent Skill mismatch')
            else:
                event('CURRENT_DIAGNOSIS')
                findings=[]
                for i,request in enumerate(requests):
                    result=_contract_call(directory/f'current-{i:03d}',build_current_diagnosis_request(request),
                        lambda raw,r=request:validate_current_findings(raw,request=r),diagnosis_transport)
                    _checkpoint(directory/f'current-{i:03d}-findings.json',result.payload);findings.append(result)
                event('MEMORY_REVIEW')
                review=build_memory_review_input(store_dir=store_dir,current_requests=requests,current_findings=findings)
                _checkpoint(directory/'memory-review-input.json',review.payload)
                if local_protocol and review.payload['historical_objects']:
                    from .edit_memory_review_v19 import run_edit_reviews
                    historical=run_edit_reviews(review,artifact_dir=directory/'edit-memory-reviews',transport=memory_review_transport)
                elif review.payload['historical_objects']:
                    historical=_contract_call(directory/'memory-review',build_historical_review_request(review),
                        lambda raw:validate_historical_reviews(raw,request=review),memory_review_transport)
                else:
                    historical=validate_historical_reviews(encode({'schema_version':'historical_review_response_v19.1','reviews':[]}),request=review)
                _checkpoint(directory/'historical-reviews.json',historical.payload)
            if local_protocol:
                from .local_generation_v19 import run_local_reviews
                from .verified_compiler_v19 import verified_editor_request,apply_verified_editor
                if not imported.exists():
                    upstream={'current_inputs':bound['current_inputs'],'current_findings':[f.payload for f in findings],
                              'review_input':review.payload,'historical_reviews':historical.payload}
                    audit,value=run_local_reviews(upstream=upstream,output=directory/'local-reviews',
                        fusion_transport=fusion_transport,evidence_review_transport=evidence_review_transport,
                        resume=(directory/'local-reviews').exists(),event_hook=event)
                event('EDITOR')
                editor_request=verified_editor_request(value)
                if editor_request:
                    raw,applied=_contract_call(directory/'editor',editor_request,
                        lambda text:(text,apply_verified_editor(text,editor_input=value)),editor_transport)
                else:
                    raw=None;applied=apply_verified_editor(None,editor_input=value)
            else:
                event('RECONCILIATION')
                recon=build_reconciliation_input(review_request=review,historical_reviews=historical)
                _checkpoint(directory/'reconciliation-input.json',recon.payload)
                if any(recon.payload['coverage'].values()):
                    result,value=_contract_call(directory/'reconciliation',build_reconciliation_request(recon),
                        lambda raw:validate_reconciliation(raw,request=recon),reconciliation_transport)
                else:
                    result,value=validate_reconciliation(encode({'schema_version':'reconciliation_response_v19.4','decisions':[]}),request=recon)
                _checkpoint(directory/'reconciliation-result.json',result.payload)
                event('EDITOR')
                editor_request=reconciliation_editor_request(result,request=recon)
                if editor_request:
                    raw,applied=_contract_call(directory/'editor',editor_request,
                        lambda text:(text,apply_reconciled_editor(text,result=result,request=recon)),editor_transport)
                else:
                    raw=None;applied=apply_reconciled_editor(None,result=result,request=recon)
                audit={'schema_version':PROTOCOL,'current_inputs':bound['current_inputs'],
                    'current_findings':[f.payload for f in findings],'review_input':review.payload,
                    'historical_reviews':historical.payload,'reconciliation':result.payload}
            validate_generation_audit(audit,value)
            ledger=None
            if applied['candidate_skill'] is not None:
                links=generation_history_links(audit,value,snapshot.head['run_id'])
                ledger=build_edit_ledger(run_id=snapshot.head['run_id'],editor_input=value,raw_response=raw,
                    candidate_skill=applied['candidate_skill'],history=snapshot.history,related_history=links,
                    generation_audit=audit)
            publication={'schema_version':protocol,**applied,'generation_audit':audit,
                         'ledger_input':ledger.source if ledger else None,'ledger':ledger.payload if ledger else None}
            require(load_memory(store_dir).head==snapshot.head,'Memory advanced during separated generation')
            _checkpoint(directory/'generation.json',publication)
            _save(marker,{'status':'COMPLETE','files':{n:_file_digest(directory/n) for n in _files(directory)}})
            return MemoryGenerationResult(applied['status'],applied['candidate_skill'],ledger,encode(publication))
        except BaseException as exc:
            # Never destroy an already complete marker during verification failures.
            if not marker.exists() or _load(marker).get('status')!='COMPLETE':
                _save(marker,{'status':'INCOMPLETE','error_type':type(exc).__name__})
            raise

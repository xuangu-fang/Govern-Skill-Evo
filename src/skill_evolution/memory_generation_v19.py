"""Audited v19 Memory -> Diagnosis -> Compiler -> Editor -> Candidate stage.

No replay, Gate, memory commit or campaign execution. A complete current grouping
and every selected historical edit are reviewed before NO_UPDATE is allowed.
"""
from dataclasses import dataclass
from pathlib import Path

from .edit_tracking_v19 import build_edit_ledger, encode, digest, parse
from .memory_allocation_v19 import validate_allocation
from .memory_store_v19 import load_memory, require, MemoryRejected
from .diagnosis_validation_v18 import DiagnosisRejected
from .memory_diagnosis_v19 import (build_memory_diagnosis_inputs, memory_diagnosis_source,
                                   memory_links_for_plan)
from .memory_generation_prompt_v19 import build_memory_diagnosis_request, build_memory_editor_request, build_memory_diagnosis_repair_request
from .compiler_contract_v18 import CompilerInput
from .compiler_v18 import compile_edit_plan
from .compiler_validation_v18 import plan_payload
from .editor_contract_v18 import EditorInput
from .editor_apply_v18 import apply_editor_response
from .evolution_replay_v19 import _save, _load, _file_digest, _lock
from .attribution_v19 import _transport


@dataclass(frozen=True)
class MemoryGenerationResult:
    status: str
    candidate_skill: str | None
    ledger: object | None
    audit_json: str


def _prepared(request):
    return {**request, 'model':'deepseek-v4-pro','temperature':0.0,'reasoning_effort':'high',
            'max_completion_tokens':request.get('max_completion_tokens',24000),
            'timeout_seconds':request.get('timeout_seconds',300),'max_retries':0}


class ModelOutputTruncated(ValueError):
    """Completed API response hit output limit; never a JSON contract repair."""


def _read_call(directory, request):
    require(_load(directory/'request.json') == request, 'model request changed on resume')
    require(_load(directory/'response_complete.json') == {'status':'COMPLETE','files':{
        name:_file_digest(directory/name) for name in ('request.json','response.json')}}, 'response checkpoint mismatch')
    response = _load(directory/'response.json')
    if isinstance(response,dict) and response.get('finish_reason')=='length':
        usage=response.get('usage') or {}
        raise ModelOutputTruncated('finish_reason=length; max_completion_tokens='+str(request.get('max_completion_tokens'))+
            '; completion_tokens='+str(usage.get('completion_tokens'))+
            '; reasoning_tokens='+str((usage.get('completion_tokens_details') or {}).get('reasoning_tokens')))
    require(type(response) is dict and response.get('finish_reason') == 'stop'
            and not response.get('refusal') and type(response.get('raw_response')) is str,
            'refused, truncated or malformed completion')
    return response['raw_response']


def _call(directory, request, transport):
    if directory.exists() and not (directory/'response_complete.json').exists():
        from .run_control_v19 import recover_call
        recover_call(directory, request)
    if directory.exists():
        require((directory/'response_complete.json').exists(),
                'uncertain model call; no automatic retry, use a new explicit attempt directory')
        return _read_call(directory, request)
    directory.mkdir(parents=True)
    _save(directory/'request.json',request)
    try:
        response = (transport or _transport)(parse(encode(request)))
    except Exception as exc:
        _save(directory/'failure.json', {'error_type':type(exc).__name__})
        raise
    _save(directory/'response.json',response)
    _save(directory/'response_complete.json',{'status':'COMPLETE','files':{
        name:_file_digest(directory/name) for name in ('request.json','response.json')}})
    return _read_call(directory,request)


def _rejection(path, raw, exc):
    error = {'type':type(exc).__name__, 'stage':getattr(exc, 'stage', 'MEMORY_CONTRACT'),
             'message':str(exc), 'raw_response_sha256':digest(raw)}
    file = path/'contract_rejection.json'
    if file.exists():
        require(_load(file) == error, 'contract rejection changed on resume')
    else:
        _save(file, error)
    return error


def _diagnose_once_with_repair(request, path, diagnose):
    original = _prepared(build_memory_diagnosis_request(request))
    raw = diagnose(path, original)  # Transport/checkpoint failures are NOT repairable.
    try:
        source = memory_diagnosis_source(raw, request=request)
    except (DiagnosisRejected, MemoryRejected, ValueError) as exc:
        error = _rejection(path, raw, exc)
        repair = _prepared(build_memory_diagnosis_repair_request(original, raw, error))
        # Separate immutable call directory: a completed rejected repair is reused
        # and rejected again on resume; an uncertain call is never resent.
        repair_path = path.with_name(path.name+'-repair-001')
        repaired = diagnose(repair_path, repair)
        try:
            source = memory_diagnosis_source(repaired, request=request)
        except (DiagnosisRejected, MemoryRejected, ValueError) as final_error:
            _rejection(repair_path, repaired, final_error)
            raise
    else:
        require(not path.with_name(path.name+'-repair-001').exists(),
                'unexpected repair artifacts for a valid first response')
    return source


def _generate(requests, snapshot, round_id, directory, diagnose, edit):
    validate_allocation(requests)
    sources = []
    for i,request in enumerate(requests):
        sources.append(_diagnose_once_with_repair(request, directory/f'diagnosis-{i:03d}', diagnose))
    parent = snapshot.head['retained_skill']
    compiler_input = CompilerInput(round_id,parent,digest(parent),tuple(sources))
    plan = compile_edit_plan(compiler_input)
    value = EditorInput(compiler_input,plan)
    editor_request = build_memory_editor_request(value)
    raw = edit(directory/'editor', _prepared(editor_request)) if editor_request is not None else None
    applied = apply_editor_response(raw,editor_input=value)
    ledger = None
    links = memory_links_for_plan(value,run_id=snapshot.head['run_id'])
    if applied['candidate_skill'] is not None:
        ledger = build_edit_ledger(run_id=snapshot.head['run_id'],editor_input=value,raw_response=raw,
            candidate_skill=applied['candidate_skill'],history=snapshot.history,related_history=links)
    audit = {'schema_version':'memory_generation_v19.1','status':applied['status'],
        'run_id':snapshot.head['run_id'],'round_id':round_id,'memory_head_ref':snapshot.head['memory_ref'],
        'parent_skill_sha256':digest(parent),'candidate_skill':applied['candidate_skill'],
        'plan':plan_payload(plan),'related_history':links,
        'diagnoses':[{'request_payload':s.request.learner_payload,'provenance':s.request.provenance,
                      'diagnosis_ref':s.diagnosis_ref} for s in sources],
        'ledger_input':ledger.source if ledger else None,'ledger':ledger.payload if ledger else None}
    return MemoryGenerationResult(applied['status'],applied['candidate_skill'],ledger,encode(audit))


def _inputs(store_dir, backend, parent_dir, round_id, grouping_result, retrieval):
    snapshot = load_memory(store_dir)
    requests = build_memory_diagnosis_inputs(store_dir=store_dir,backend=backend,parent_dir=parent_dir,
        round_id=round_id,grouping_result=grouping_result,**retrieval)
    require(all(r.provenance['memory_head_ref']==snapshot.head['memory_ref'] for r in requests),
            'memory head changed while constructing generation')
    bound = {'schema_version':'memory_generation_input_v19.2','diagnosis_protocol':'v19.6-single-owner-memory',
             'max_contract_repairs_per_group':1,'memory_head':snapshot.head,
             'round_id':round_id,'requests':[{'payload':r.learner_payload,'provenance':r.provenance} for r in requests]}
    return snapshot,requests,bound


def _check_head(store_dir,snapshot):
    require(load_memory(store_dir).head == snapshot.head, 'memory advanced during generation; result not publishable')


def _files(directory):
    return sorted(str(p.relative_to(directory)) for p in directory.rglob('*.json')
                  if p.name != 'validation.json')


def _load_result(directory, requests, snapshot, round_id, bound):
    marker = _load(directory/'validation.json')
    require(type(marker) is dict and set(marker)=={'status','files'} and marker['status']=='COMPLETE'
            and type(marker['files']) is dict and set(marker['files'])==set(_files(directory)), 'incomplete generation manifest')
    require(all(_file_digest(directory/name)==sha for name,sha in marker['files'].items()),'generation checksum mismatch')
    require(_load(directory/'input.json')==bound,'generation input changed')
    result = _generate(requests,snapshot,round_id,directory,_read_call,_read_call)
    require(encode(_load(directory/'generation.json'))==result.audit_json, 'generation differs from revalidated sources')
    return result


def load_memory_generation(*, store_dir,backend,parent_dir,round_id,grouping_result,artifact_dir,**retrieval):
    snapshot,requests,bound=_inputs(store_dir,backend,parent_dir,round_id,grouping_result,retrieval)
    result=_load_result(Path(artifact_dir),requests,snapshot,round_id,bound)
    _check_head(store_dir,snapshot)
    return result


def run_memory_generation(*, store_dir,backend,parent_dir,round_id,grouping_result,artifact_dir,
                          diagnosis_transport=None,editor_transport=None,resume=False,**retrieval):
    """New output by default; each group permits at most one audited contract repair.

    An incomplete batch can continue not-yet-started groups, but an uncertain or
    transport attempt is never silently rerun. Rejected repair stops. Stage success doesn't commit.
    """
    require(type(resume) is bool,'resume must be boolean')
    snapshot,requests,bound=_inputs(store_dir,backend,parent_dir,round_id,grouping_result,retrieval)
    directory=Path(artifact_dir)
    with _lock(directory):
        if directory.exists():
            require(resume,'existing generation requires explicit resume')
            require(_load(directory/'input.json')==bound,'resume input mismatch')
            if (directory/'validation.json').exists() and _load(directory/'validation.json').get('status')=='COMPLETE':
                result=_load_result(directory,requests,snapshot,round_id,bound)
                _check_head(store_dir,snapshot)
                return result
        else:
            require(not resume,'resume requires existing output')
            directory.mkdir(parents=True)
            _save(directory/'input.json',bound)
        _save(directory/'validation.json',{'status':'RUNNING'})
        try:
            result=_generate(requests,snapshot,round_id,directory,
                lambda path,request:_call(path,request,diagnosis_transport),
                lambda path,request:_call(path,request,editor_transport))
            _check_head(store_dir,snapshot)
            if (directory/'generation.json').exists():
                require(encode(_load(directory/'generation.json'))==result.audit_json,'existing generation result changed')
            else:
                _save(directory/'generation.json',parse(result.audit_json))
            _save(directory/'validation.json',{'status':'COMPLETE','files':{
                name:_file_digest(directory/name) for name in _files(directory)}})
            return result
        except BaseException as exc:
            _save(directory/'validation.json',{'status':'INCOMPLETE','error_type':type(exc).__name__})
            raise

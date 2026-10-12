import pytest
from tests.skill_evolution.v19.test_evidence_review_v19 import setup, case, cases, final, payload
from tests.skill_evolution.v19.test_attribution_v19 import complete
from src.skill_evolution.v19.edit_tracking_v19 import encode, parse
from src.skill_evolution.v19.evidence_review_v19 import build_evidence_review_input, validate_evidence_review
from src.skill_evolution.v19.evidence_review_prompt_v19 import build_evidence_review_request
from src.skill_evolution.v19.evidence_review_run_v19 import run_evidence_review
from src.skill_evolution.v19.evidence_projection_v19 import expand
from src.skill_evolution.v19.review_context_v19 import pack_directory, unpack_directory, compact_projection
from src.skill_evolution.v19.memory_generation_v19 import ModelOutputTruncated


def test_directory_is_lossless():
    directory={'A/E1':{'step':1,'kind':'message'},'A/E2':{'step':2,'kind':'tool','name':None},'B/E3':{}}
    assert unpack_directory(pack_directory(directory))==directory


def test_current_seeds_counterevidence_and_unloaded_index_preserved(setup):
    c=cases(setup[2])[0];old=build_evidence_review_input(c);new=build_evidence_review_input(c,input_version='v19.2')
    p=new.payload
    assert set(c.payload['seed_refs'])<=set(p['events'])
    assert set(c.payload['known_counterevidence_refs'])<=set(p['events'])
    assert all(v==old.payload['events'][r] for r,v in p['events'].items())
    assert set(unpack_directory(p['event_directory']))|set(p['events'])==set(old.payload['event_directory'])
    assert set(unpack_directory(p['policy_directory']))|set(p['policies'])==set(c.payload['policies'])
    assert expand(compact_projection(p))==p
    prompt=build_evidence_review_request(new)
    assert prompt['max_completion_tokens']==24000 and prompt['prompt_version']=='evidence_review-v19.2'
    assert expand(parse(prompt['user_prompt']))==p


def test_compact_response_refs_are_resolved_without_changing_raw(setup):
    request=build_evidence_review_input(cases(setup[2])[0],input_version='v19.2')
    out=final(request.payload);prefixes=compact_projection(request.payload)['reference_prefixes']
    def compact(ref):
        for short,long in prefixes.items():
            if ref.startswith(long):return short+ref[len(long):]
        return ref
    out['evidence_refs']=[compact(r) for r in out['evidence_refs']]
    out['counterevidence_refs']=[compact(r) for r in out['counterevidence_refs']]
    raw=encode(out);result=validate_evidence_review(raw,request=request)
    assert result.payload['raw_response']==raw
    assert set(result.payload['evidence_refs'])<=set(request.payload['events'])
    out['evidence_refs']=['@REF_UNKNOWN/E1']
    with pytest.raises(ValueError):validate_evidence_review(encode(out),request=request)


def test_explicit_policy_supplement_and_scope(setup):
    c=cases(setup[2])[0];request=build_evidence_review_input(c,input_version='v19.2')
    directory=unpack_directory(request.payload['policy_directory']);assert directory
    ref=next(iter(directory))
    control={'proposal_id':request.payload['proposal_id'],'request':'MORE_CONTEXT',
        'evidence_refs':[],'tool_refs':[],'rule_refs':[],'policy_refs':[ref],'reason':'Need the policy context.'}
    assert validate_evidence_review(encode(control),request=request)==control
    second=build_evidence_review_input(c,input_version='v19.2',context_round=1,additional_policy_refs=[ref])
    assert second.payload['policies'][ref]==c.payload['policies'][ref]
    with pytest.raises(ValueError,match='exhausted'):validate_evidence_review(encode(control),request=second)
    control['policy_refs']=['POLICY/private']
    with pytest.raises(ValueError,match='outside'):validate_evidence_review(encode(control),request=request)


def test_length_is_not_contract_repair(setup,tmp_path):
    calls=[]
    def truncated(request):
        calls.append(request)
        return {**complete('{"reason":"unfinished'), 'finish_reason':'length',
            'usage':{'completion_tokens':8192,'completion_tokens_details':{'reasoning_tokens':7391}}}
    kwargs=dict(output=tmp_path/'review',transport=truncated,input_version='v19.3')
    c=cases(setup[2])[0]
    with pytest.raises(ModelOutputTruncated,match='reasoning_tokens=7391'):run_evidence_review(c,**kwargs)
    with pytest.raises(ModelOutputTruncated):run_evidence_review(c,**kwargs,resume=True)
    assert len(calls)==1 and not list(kwargs['output'].glob('*repair*'))
    assert (kwargs['output']/'review-0/response.json').exists()
    assert not (kwargs['output']/'result.json').exists()

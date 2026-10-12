"""Lightweight issue discovery/fusion. No gap, compiler input or edit authority."""
from dataclasses import dataclass

from .edit_tracking_v19 import encode, digest
from .memory_store_v19 import require
from .review_contract_v19 import MemoryReviewInput, checked_response, text_schema
from .historical_review_v19 import validate_historical_reviews
from ..v18.diagnosis_contract_v18 import _object, _strings
from ..v18.diagnosis_references_v18 import build_reference_catalogs

SCHEMA=_object({'schema_version':text_schema('issue_fusion_response_v19.1'),
    'issues':{'type':'array','items':_object({
        'source_finding_refs':_strings(),'historical_refs':_strings(),
        'issue_statement':text_schema(),'decision':text_schema('PROPOSE','NO_EDIT'),
        'reason':text_schema(),'related_rule_refs':_strings()})},
    'unassociated_findings':{'type':'array','items':_object({
        'finding_ref':text_schema(),'reason':text_schema()})}})


@dataclass(frozen=True)
class IssueFusionInput:
    payload_json:str

    @property
    def payload(self):
        from .edit_tracking_v19 import parse
        return parse(self.payload_json)

    @property
    def input_ref(self):return 'ISSUE_FUSION_INPUT/'+digest(self.payload_json)


@dataclass(frozen=True)
class IssueFusionResult:
    payload_json:str

    @property
    def payload(self):
        from .edit_tracking_v19 import parse
        return parse(self.payload_json)


def build_issue_fusion_input(*,review_request,historical_reviews, legacy=False):
    require(isinstance(review_request,MemoryReviewInput),'MemoryReviewInput required')
    require(validate_historical_reviews(historical_reviews.payload['raw_response'],request=review_request)==historical_reviews,
            'historical reviews changed or stale')
    data=review_request.payload
    # Explicit allowlists: raw trajectory, tool/policy bodies and previous raw
    # responses never cross this interface. Full upstream evidence stays archived.
    findings=[{k:f[k] for k in ('finding_id','kind','statement','applicability','dimensions','related_rule_refs','uncertainty')}
              for f in data['current_findings']]
    objects={o['historical_object_id']:o for o in data['historical_objects']}
    edits={e['edit_id']:e for row in data['memory_context']['rounds'] for e in row['edits']}
    reviews=[]
    for r in historical_reviews.payload['reviews']:
        obj=objects[r['historical_object_id']];edit=edits[obj['edit_id']]
        reviews.append({**{k:r[k] for k in ('review_id','historical_object_id','evidence_status','coverage_reason','reason','uncertainty','current_finding_refs')},
            'edit_id':obj['edit_id'],'attribution_id':obj['attribution_id'],
            'joint_edit_ids':obj['joint_edit_ids'],'historical_judgment':obj['historical_judgment'],
            'current_binding':obj['current_binding'],
            'edit':{k:edit[k] for k in ('operation','target_blocks','after_text')}})
    if data.get('memory_protocol') in ('issue_memory_v19.1','issue_memory_v19.2'):
        for review in reviews:
            review['edit_attempt'] = data['edit_attempts'][review['edit_id']]
    if not legacy:
        from .memory_consumption_v19 import historical_object_view
        review_fields=('review_id','evidence_status','coverage_reason','reason','uncertainty','current_finding_refs')
        reviews=[{**historical_object_view(r), **{k:r[k] for k in review_fields}} for r in reviews]
    # Full Parent rule catalog prevents a relevance filter from hiding an existing
    # rule. Text appears once; no repeated Parent body or full historical Skills.
    rules=build_reference_catalogs({'current_skill':data['current_skill'],'contexts':[]})['available_rule_refs']
    return IssueFusionInput(encode({'schema_version':'issue_fusion_input_v19.1' if legacy else 'issue_fusion_input_v19.2',
        'review_input_ref':review_request.input_ref,'historical_reviews_sha256':digest(historical_reviews.payload_json),
        'batch':data['batch'],'parent_skill_sha256':digest(data['current_skill']),
        'current_findings':findings,'historical_reviews':reviews,'available_rule_refs':rules,
        'authority':'ISSUE_SELECTION_ONLY_NOT_VERIFIED_OR_EDIT_AUTHORIZATION'}))


def fusion_reference_map(request):
    """Request-local aliases; canonical IDs remain the persistent identities."""
    p=request.payload
    groups=(('F', [f['finding_id'] for f in p['current_findings']]),
            ('H', [h['review_id'] for h in p['historical_reviews']]),
            ('R', list(p['available_rule_refs'])))
    return {f'{prefix}{i:02d}':ref for prefix,refs in groups
            for i,ref in enumerate(sorted(set(refs)),1)}


def fusion_wire_payload(request):
    reverse={v:k for k,v in fusion_reference_map(request).items()}
    def walk(value):
        if isinstance(value,str):return reverse.get(value,value)
        if isinstance(value,list):return [walk(v) for v in value]
        if isinstance(value,dict):return {reverse.get(k,k):walk(v) for k,v in value.items()}
        return value
    return walk(request.payload)


def expand_fusion_response(raw,request):
    out=checked_response(raw,SCHEMA)
    aliases=fusion_reference_map(request)
    def resolve(ref,prefix):
        require(ref in aliases and ref.startswith(prefix),f'unknown {prefix} reference: {ref}')
        return aliases[ref]
    for item in out['issues']:
        for field,prefix in (('source_finding_refs','F'),('historical_refs','H'),('related_rule_refs','R')):
            item[field]=[resolve(ref,prefix) for ref in item[field]]
    for item in out['unassociated_findings']:
        item['finding_ref']=resolve(item['finding_ref'],'F')
    return encode(out)


def validate_issue_fusion(raw,*,request,wire=False):
    require(isinstance(request,IssueFusionInput),'IssueFusionInput required')
    if wire:raw=expand_fusion_response(raw,request)
    p=request.payload
    require(p['schema_version'] in ('issue_fusion_input_v19.1','issue_fusion_input_v19.2'),'unknown issue fusion input')
    out=checked_response(raw,SCHEMA)
    findings={f['finding_id']:f for f in p['current_findings']}
    histories={r['review_id'] for r in p['historical_reviews']}
    seen_findings=set();seen_problems=set();seen_history=set();issues=[];identities=set()
    for i,item in enumerate(out['issues']):
        refs=set(item['source_finding_refs']);hrs=set(item['historical_refs'])
        require(bool(refs or hrs),f'issue {i}: source required')
        require(refs<=set(findings) and hrs<=histories,f'issue {i}: unknown source')
        require(set(item['related_rule_refs'])<=set(p['available_rule_refs']),f'issue {i}: stale rule refs')
        problems={r for r in refs if findings[r]['kind']=='OBSERVED_PROBLEM'}
        require(not problems & seen_problems,f'issue {i}: current problem assigned more than once')
        seen_problems.update(problems);seen_findings.update(refs);seen_history.update(hrs)
        identity=digest(encode(item))
        require(identity not in identities,f'issue {i}: duplicate issue');identities.add(identity)
        issues.append({'issue_id':'ISSUE/'+digest(encode({'input_ref':request.input_ref,'issue':item})),**item})
    unassociated=set()
    for item in out['unassociated_findings']:
        ref=item['finding_ref']
        require(ref in findings and ref not in seen_findings|unassociated,'unknown, used or repeated unassociated finding')
        require(findings[ref]['kind']!='OBSERVED_PROBLEM','observed problem requires explicit issue disposition')
        unassociated.add(ref)
    require(seen_findings|unassociated==set(findings),'current finding coverage incomplete')
    require(seen_history==histories,'historical issue coverage incomplete')
    return IssueFusionResult(encode({'schema_version':'issue_fusion_result_v19.1',
        'input_ref':request.input_ref,'raw_response':raw,'issues':issues,
        'unassociated_findings':out['unassociated_findings'],
        'authority':'ISSUE_SELECTION_ONLY_NOT_VERIFIED_OR_EDIT_AUTHORIZATION',
        'validation_scope':'SOURCE_COVERAGE_AND_REFERENCES_NOT_SEMANTIC_CORRECTNESS'}))


def validate_issue_fusion_result(result,*,request):
    require(isinstance(result,IssueFusionResult),'IssueFusionResult required')
    require(validate_issue_fusion(result.payload['raw_response'],request=request)==result,'issue fusion result changed or stale')
    return result

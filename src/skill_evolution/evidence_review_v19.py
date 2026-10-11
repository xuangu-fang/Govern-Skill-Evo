"""Local proposal evidence review: scoped originals, bounded context and minimal verdict.

No compiler adaptation or Skill edits. VERIFIED is a model assessment, not proof
of semantic truth, effectiveness or causality.
"""
from dataclasses import dataclass
from copy import deepcopy
from .review_context_v19 import pack_directory,unpack_directory,paired_events

from .edit_tracking_v19 import encode,parse,digest
from .memory_store_v19 import require
from .diagnosis_contract_v18 import _object,_strings,_validate
from .review_contract_v19 import text_schema
from .issue_fusion_v19 import build_issue_fusion_input,validate_issue_fusion_result
from .reconciliation_v19 import ReconciliationInput,_catalog

GAP_SCHEMA=_object({'kind':text_schema('MISSING','NEEDS_REVISION','SHOULD_REMOVE'),
                    'statement':text_schema(),'related_rule_refs':_strings()})
FINAL_SCHEMA=_object({'proposal_id':text_schema(),'verdict':text_schema('VERIFIED','NO_EDIT'),
    'evidence_refs':_strings(),'counterevidence_refs':_strings(),'reason':text_schema(),
    'gap':{'anyOf':[{'type':'null'},GAP_SCHEMA]}})
CONTEXT_SCHEMA=_object({'proposal_id':text_schema(),'request':text_schema('MORE_CONTEXT'),
    'evidence_refs':_strings(),'tool_refs':_strings(),'rule_refs':_strings(),'reason':text_schema()})
RESPONSE_SCHEMA={'anyOf':[FINAL_SCHEMA,CONTEXT_SCHEMA]}
CONTEXT_SCHEMA_V2=_object({**CONTEXT_SCHEMA['properties'],'policy_refs':_strings()})
RESPONSE_SCHEMA_V2={'anyOf':[FINAL_SCHEMA,CONTEXT_SCHEMA_V2]}


def final_schema_for_input(request):
    """Restrict editing authority to the actual loaded Parent targets."""
    schema=deepcopy(FINAL_SCHEMA)
    gap=schema['properties']['gap']['anyOf'][1]['properties']
    targets=sorted(request.payload['rules'])
    if targets:
        gap['related_rule_refs']['items']['enum']=targets
    else:
        gap['kind']['enum']=['MISSING']
        gap['related_rule_refs']['maxItems']=0
    return schema


def _validate_final_references(out,p):
    """Collect independent typed-reference errors before using the one repair."""
    errors=[]
    def actual(ref):
        for field,kind in (('events','EVENT'),('policies','VISIBLE_POLICY'),
                           ('rules','PARENT_SKILL_RULE'),('tools','TOOL')):
            if ref in p[field]:return kind
        return 'UNKNOWN_OR_UNLOADED'
    def check(refs,field,catalog,expected):
        for index,ref in enumerate(refs):
            if ref not in p[catalog]:
                errors.append({'field':f'{field}[{index}]','ref':ref,'actual_type':actual(ref),
                    'expected_type':expected,'message':'reference is not in the allowed loaded catalog'})
    check(out['evidence_refs'],'evidence_refs','events','EVENT')
    check(out['counterevidence_refs'],'counterevidence_refs','events','EVENT')
    if out['verdict']=='VERIFIED':
        if p.get('memory_consumption',{}).get('omitted_counterevidence_count'):
            errors.append({'field':'verdict','message':'VERIFIED forbidden: historical counterevidence originals exceed packet capacity'})
        gap=out['gap'];targets=gap['related_rule_refs']
        check(targets,'gap.related_rule_refs','rules','PARENT_SKILL_RULE')
        if not out['evidence_refs']:
            errors.append({'field':'evidence_refs','message':'VERIFIED needs original event evidence'})
        if not p['rules'] and gap['kind']!='MISSING':
            errors.append({'field':'gap.kind','actual':gap['kind'],'allowed':['MISSING'],
                'message':'no loaded Parent targets; revision/removal is not authorized'})
        if (gap['kind']=='MISSING')!= (not targets):
            errors.append({'field':'gap.related_rule_refs','message':'MISSING has no target; revision/removal requires targets'})
    missing=sorted(set(p['known_counterevidence_refs'])-set(out['counterevidence_refs']))
    if missing:errors.append({'field':'counterevidence_refs','missing_refs':missing,
        'message':'known counterevidence must remain explicit, not silently dropped'})
    require(not errors,'Evidence Review reference errors: '+encode(errors))


@dataclass(frozen=True)
class EvidenceReviewCase:
    """Proposal-scoped archive, not a model prompt. Full source trajectories remain local."""
    payload_json:str
    @property
    def payload(self):return parse(self.payload_json)
    @property
    def case_ref(self):return 'EVIDENCE_REVIEW_CASE/'+digest(self.payload_json)


@dataclass(frozen=True)
class EvidenceReviewInput:
    payload_json:str
    @property
    def payload(self):return parse(self.payload_json)
    @property
    def input_ref(self):return 'EVIDENCE_REVIEW_INPUT/'+digest(self.payload_json)


@dataclass(frozen=True)
class EvidenceReviewResult:
    payload_json:str
    @property
    def payload(self):return parse(self.payload_json)


def build_evidence_review_case(*,fusion_input,fusion_result,review_request,historical_reviews,issue_id):
    require(build_issue_fusion_input(review_request=review_request,historical_reviews=historical_reviews,
        legacy=fusion_input.payload['schema_version']=='issue_fusion_input_v19.1')==fusion_input,
            'fusion/upstream binding mismatch')
    validate_issue_fusion_result(fusion_result,request=fusion_input)
    issues={i['issue_id']:i for i in fusion_result.payload['issues']}
    require(issue_id in issues and issues[issue_id]['decision']=='PROPOSE','only PROPOSE can be reviewed')
    issue=issues[issue_id];data=review_request.payload
    findings=[f for f in data['current_findings'] if f['finding_id'] in issue['source_finding_refs']]
    reviews=[r for r in historical_reviews.payload['reviews'] if r['review_id'] in issue['historical_refs']]
    objects={o['historical_object_id']:o for o in data['historical_objects']}
    seed={r for f in findings for r in f['evidence_refs']}
    counter={r for f in findings if f['kind']=='COUNTEREVIDENCE' for r in f['evidence_refs']}
    historic_scope=set();labels=set();rules=set(issue['related_rule_refs'])
    rules.update(r for f in findings for r in f['related_rule_refs'])
    records={a['attribution_id']:a for row in data['memory_context']['rounds'] for a in row['attribution']['records']}
    observations=[]
    for r in reviews:
        for field in ('supporting_current_refs','contradicting_current_refs','context_current_refs','historical_evidence_refs'):
            seed.update(r[field])
        counter.update(r['contradicting_current_refs'])
        obj=objects[r['historical_object_id']];historic_scope.update(obj['historical_event_refs'])
        rules.update(obj['current_binding']['current_rule_refs']);rules.update(obj['current_binding']['descendant_rule_refs'])
        for obs in records[obj['attribution_id']]['observations'] + records[obj['attribution_id']].get('unattributed_context', []):
            observations.append(obs)
            events=obs['parent_evidence_refs']+obs['candidate_evidence_refs'];seed.update(events)
            labels.update(obs.get('supervision_refs', []))
            if obs.get('relation', obs.get('legacy_relation'))=='COUNTEREVIDENCE':counter.update(events)
    catalog=_catalog(ReconciliationInput(encode({'review_input':data})))
    require(seed<=set(catalog['available_evidence_refs']),'unknown seed evidence')
    experiences=[e for e in catalog['experiences'] if
        (seed|historic_scope)&{v['evidence_ref'] for v in e['events']} or e['supervision']['supervision_ref'] in labels]
    contexts={e['context_ref'] for e in experiences}
    tools={}
    for c in catalog['contexts']:
        if c['context_ref'] not in contexts:continue
        for index,t in enumerate(c['public_tools']):
            ref=f"TOOL/{c['context_ref']}/{index}/{digest(encode(t))}"
            tools[ref]={'context_ref':c['context_ref'],'definition':t}
    # Fusion's projection is for selection only. Resolve selected provenance
    # against the archive before the local consumer applies its own boundary.
    selected_history=[h for h in fusion_input.payload['historical_reviews'] if h['review_id'] in issue['historical_refs']]
    if fusion_input.payload['schema_version']=='issue_fusion_input_v19.2':
        for h in selected_history:
            if h['edit_id'] in data.get('edit_attempts',{}):
                h['edit_attempt']=data['edit_attempts'][h['edit_id']]
    return EvidenceReviewCase(encode({'schema_version':'evidence_review_case_v19.1',
        'fusion_input_ref':fusion_input.input_ref,'fusion_result_sha256':digest(fusion_result.payload_json),
        'review_input_ref':review_request.input_ref,'issue':issue,'findings':findings,
        'historical_reviews':reviews,
        'historical_objects':selected_history,
        'historical_observations':observations,'parent_skill_sha256':fusion_input.payload['parent_skill_sha256'],
        'seed_refs':sorted(seed),'known_counterevidence_refs':sorted(counter),
        'experiences':experiences,'tools':tools,'seed_rule_refs':sorted(rules),
        'rules':catalog['available_rule_refs'],
        'policies':{r:v for r,v in catalog['available_policy_refs'].items() if v['context_ref'] in contexts}}))


def _neighborhood(events,selected):
    """One neighboring event each side, plus matching call/return when identifiable.

    Missing/ambiguous correspondence is not fabricated. The event directory lets
    the reviewer request exact additional refs within this proposal's scope.
    """
    indices={i for i,e in enumerate(events) if e['evidence_ref'] in selected}
    chosen=set(indices)
    for i in indices:
        chosen.update(j for j in (i-1,i+1) if 0<=j<len(events))
    for i in list(chosen):
        e=events[i];kind=e['event_type'];name=e.get('tool_name')
        if not name or kind not in ('tool_call','tool_result'):continue
        direction=1 if kind=='tool_call' else -1
        for j in range(i+direction,len(events) if direction==1 else -1,direction):
            other=events[j]
            if other.get('tool_name')!=name:continue
            if other['event_type']==kind:break
            if other['event_type'] in ('tool_call','tool_result'):
                chosen.add(j);break
    return {events[i]['evidence_ref'] for i in chosen}


def build_evidence_review_input(case,*,additional_evidence_refs=(),additional_tool_refs=(),additional_rule_refs=(),additional_policy_refs=(),context_round=0,
                                input_version="v19.1"):
    require(isinstance(case,EvidenceReviewCase),'EvidenceReviewCase required')
    if input_version=='v19.3':
        require(context_round==0 and not (additional_evidence_refs or additional_tool_refs or additional_rule_refs or additional_policy_refs),
                'v19.3 has no context supplement')
        from .review_packet_v19 import build_once_input
        return build_once_input(case)
    require(context_round in (0,1),'at most one context supplement')
    require(input_version in ('v19.1','v19.2'),'unknown local input version')
    require(input_version=='v19.2' or not additional_policy_refs,'policy supplement requires v19.2')
    p=case.payload
    neighborhood=paired_events if input_version=='v19.2' else _neighborhood
    events={e['evidence_ref']:e for exp in p['experiences'] for e in exp['events']}
    for refs,scope in ((additional_evidence_refs,events),(additional_tool_refs,p['tools']),(additional_rule_refs,p['rules']),(additional_policy_refs,p['policies'])):
        require(len(refs)==len(set(refs)) and set(refs)<=set(scope),'unknown, repeated or out-of-scope context refs')
    require(context_round==1 or not (additional_evidence_refs or additional_tool_refs or additional_rule_refs or additional_policy_refs),
            'initial input cannot hide a context supplement')
    seeds=set(p['seed_refs']);selected=set(seeds)
    for exp in p['experiences']:
        selected.update(neighborhood(exp['events'],seeds))
    selected.update(additional_evidence_refs)
    for exp in p['experiences']:
        selected.update(neighborhood(exp['events'],set(additional_evidence_refs)))
    trajectories={};loaded={};directory={};tool_names=set()
    for n,exp in enumerate(p['experiences']):
        tid=f'TRAJECTORY/{n:04d}'
        trajectories[tid]={k:v for k,v in exp.items() if k!='events'}
        for e in exp['events']:
            ref=e['evidence_ref']
            directory[ref]={'trajectory_ref':tid,'step':e['step'],'event_type':e['event_type'],
                            **({'tool_name':e['tool_name']} if 'tool_name' in e else {})}
            if ref in selected:
                loaded[ref]={'trajectory_ref':tid,'event':{k:v for k,v in e.items() if k!='evidence_ref'}}
                if 'tool_name' in e:tool_names.add((exp['context_ref'],e['tool_name']))
    chosen_tools=set(additional_tool_refs)
    for ref,t in p['tools'].items():
        if (t['context_ref'],t['definition'].get('function',{}).get('name')) in tool_names:chosen_tools.add(ref)
    chosen_rules=set(p['seed_rule_refs'])|set(additional_rule_refs)
    require(chosen_rules<=set(p['rules']),'stale seed rules')
    payload={'schema_version':'evidence_review_input_'+input_version,'case_ref':case.case_ref,
        'proposal_id':p['issue']['issue_id'],'issue':p['issue'],'findings':p['findings'],
        'historical_reviews':p['historical_reviews'],'historical_objects':p['historical_objects'],
        'historical_observations':p['historical_observations'],
        'parent_skill_sha256':p['parent_skill_sha256'],'events':loaded,'trajectories':trajectories,
        'event_directory':directory,'known_counterevidence_refs':p['known_counterevidence_refs'],
        'tools':{r:p['tools'][r] for r in sorted(chosen_tools)},
        'tool_directory':{r:{'context_ref':t['context_ref'],'name':t['definition'].get('function',{}).get('name','')}
                          for r,t in p['tools'].items()},
        'rules':{r:p['rules'][r] for r in sorted(chosen_rules)},
        'rule_directory':{r:{k:v[k] for k in ('section','start_line','end_line')} for r,v in p['rules'].items()},
        'policies':p['policies'],'context_requests_remaining':1-context_round}
    if input_version=='v19.2':
        policies={ref for f in p['findings'] for ref in f['policy_refs']}|set(additional_policy_refs)
        require(policies<=set(p['policies']),'unknown cited policy')
        payload['policies']={r:p['policies'][r] for r in sorted(policies)}
        payload['policy_directory']=pack_directory({r:{'line':v['line'],'context_ref':v['context_ref']} for r,v in p['policies'].items() if r not in policies})
        payload['event_directory']=pack_directory({r:v for r,v in directory.items() if r not in loaded})
        payload['tool_directory']={r:v for r,v in payload['tool_directory'].items() if r not in chosen_tools}
        payload['rule_directory']={r:v for r,v in payload['rule_directory'].items() if r not in chosen_rules}
    return EvidenceReviewInput(encode(payload))


def validate_evidence_review(raw,*,request):
    require(isinstance(request,EvidenceReviewInput),'EvidenceReviewInput required')
    p=request.payload;out=parse(raw)
    v3=p['schema_version']=='evidence_review_input_v19.3'
    v2=p['schema_version']=='evidence_review_input_v19.2'
    if v2 or v3:
        from .review_context_v19 import compact_projection,expand_reference
        prefixes=compact_projection(p)['reference_prefixes']
        if isinstance(out,dict):
            for field in ('proposal_id','evidence_refs','counterevidence_refs','tool_refs','rule_refs','policy_refs'):
                if isinstance(out.get(field),str):out[field]=expand_reference(out[field],prefixes)
                elif isinstance(out.get(field),list):out[field]=[expand_reference(r,prefixes) if isinstance(r,str) else r for r in out[field]]
            if isinstance(out.get('gap'),dict) and isinstance(out['gap'].get('related_rule_refs'),list):
                out['gap']['related_rule_refs']=[expand_reference(r,prefixes) if isinstance(r,str) else r for r in out['gap']['related_rule_refs']]
    if v2:
        p['event_directory']=unpack_directory(p['event_directory'])
        p['policy_directory']=unpack_directory(p['policy_directory'])
    if isinstance(out,dict) and 'request' in out:
        require(not v3,'v19.3 requires a final verdict; context requests are not supported')
        _validate(out,CONTEXT_SCHEMA_V2 if v2 else CONTEXT_SCHEMA,'response')
        require(out['proposal_id']==p['proposal_id'],'proposal identity changed')
        require(p['context_requests_remaining']>0,'context supplement exhausted; no automatic NO_EDIT')
        total=0
        scopes=[('evidence_refs','event_directory','events'),('tool_refs','tool_directory','tools'),('rule_refs','rule_directory','rules')]
        if v2:scopes.append(('policy_refs','policy_directory','policies'))
        for field,scope,loaded in scopes:
            refs=set(out[field]);require(refs<=set(p[scope]),'context request outside proposal scope')
            require(not refs&set(p[loaded]),'context request must select unloaded refs');total+=len(refs)
        require(total>0,'empty context request')
        return out  # Control request, never a verdict or compiler authorization.
    # v18's strict validator has no nullable/union support; validate the other
    # fields with an exact schema, then separately validate the nullable gap.
    require(isinstance(out,dict) and set(out)==set(FINAL_SCHEMA['properties']),'exact verdict fields required')
    fields={k:v for k,v in FINAL_SCHEMA['properties'].items() if k!='gap'}
    _validate({k:out[k] for k in fields},_object(fields),'response')
    require(out['proposal_id']==p['proposal_id'],'proposal identity changed')
    if v3:
        if out['verdict']=='VERIFIED':_validate(out['gap'],GAP_SCHEMA,'response.gap')
        else:require(out['gap'] is None,'NO_EDIT cannot carry a gap')
        _validate_final_references(out,p)
    else:
        refs=set(out['evidence_refs'])|set(out['counterevidence_refs'])
        require(refs<=set(p['events']),'unloaded or unknown evidence citation')
        if out['verdict']=='VERIFIED':
            require(bool(out['evidence_refs']),'VERIFIED needs original event evidence')
            _validate(out['gap'],GAP_SCHEMA,'response.gap')
            gap=out['gap'];targets=set(gap['related_rule_refs'])
            require(targets<=set(p['rules']),'unknown or unloaded target rule')
            require((gap['kind']=='MISSING')==(not targets),'MISSING has no target; revision/removal requires targets')
        else:require(out['gap'] is None,'NO_EDIT cannot carry a gap')
        require(set(p['known_counterevidence_refs'])<=set(out['counterevidence_refs']),
                'known counterevidence must remain explicit, not silently dropped')
    return EvidenceReviewResult(encode({'schema_version':'evidence_review_result_v19.1',
        'input_ref':request.input_ref,'case_ref':p['case_ref'],'raw_response':raw,**out,
        'validation_scope':'REFERENCES_AND_CONTRACT_NOT_SEMANTIC_TRUTH_OR_CAUSAL_PROOF'}))


def validate_evidence_review_result(result,*,request):
    require(isinstance(result,EvidenceReviewResult),'EvidenceReviewResult required')
    require(validate_evidence_review(result.payload['raw_response'],request=request)==result,'review result changed or stale')
    return result

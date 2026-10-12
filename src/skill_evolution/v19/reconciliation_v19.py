"""Auditable reconciliation and a pure adapter to the unchanged v18 compiler.

No model calls, stage checkpoints or Memory mutation. Model proposals provide
complete v18 analyses/gaps; the adapter never fills missing citations or targets.
"""
from dataclasses import dataclass
from copy import deepcopy

from .edit_tracking_v19 import encode, parse, digest
from .memory_store_v19 import require
from .review_contract_v19 import text_schema, MemoryReviewInput
from .historical_review_v19 import validate_historical_reviews
from ..v18.diagnosis_contract_v18 import _object, _strings, DIAGNOSIS_JSON_SCHEMA
from ..v18.diagnosis_references_v18 import build_reference_catalogs
from ..v18.diagnosis_validation_v18 import validate_diagnosis_response
from ..v17.group_diagnosis_input_v17 import GroupDiagnosisInput
from ..v15.information_boundary_v15 import _seal
from ..v18.compiler_contract_v18 import CompilerInput, CompilerDiagnosisSource
from ..v18.compiler_v18 import compile_edit_plan
from ..v18.editor_contract_v18 import EditorInput
from ..v18.editor_apply_v18 import apply_editor_response
from ..v18.editor_prompt_v18 import build_editor_request

LEGACY_SCHEMA = _object({'schema_version': text_schema('reconciliation_response_v19.1'),
    'decisions': {'type': 'array', 'items': _object({
        'current_finding_refs': _strings(), 'historical_review_refs': _strings(),
        'decision': text_schema('PROPOSE','KEEP','DEFER'), 'reason': text_schema(),
        'evidence_refs': _strings(), 'keep_rule_refs': _strings(),
        'conflict_resolution': _strings(), 'whole_rule_removal_reason': _strings(),
        'proposals': {'type': 'array', 'items': DIAGNOSIS_JSON_SCHEMA},
    })}})


SCHEMA = deepcopy(LEGACY_SCHEMA)
SCHEMA['properties']['schema_version'] = text_schema('reconciliation_response_v19.2')
_decision_schema = SCHEMA['properties']['decisions']['items']
_decision_schema['properties']['current_finding_assessments'] = {
    'type':'array', 'items':_object({
        'finding_ref':text_schema(),
        'role':text_schema('DIRECT_BASIS','COUNTEREVIDENCE','CONTEXT'),
        'reason':text_schema(),
    })}
_decision_schema['required'].append('current_finding_assessments')

from .reconciliation_decision_v19 import decision_schema
DECISION_SCHEMA=decision_schema(SCHEMA)


def _schema_issues(value, schema, path='response'):
    """Collect shape errors without altering the submitted response.

    Duplicate strings do not prevent independent cross-field checks. Invalid
    shapes do: callers must not dereference a malformed response.
    """
    issues=[]; safe=True
    kind=schema['type']
    if kind=='object':
        if not isinstance(value,dict):
            return [f'{path}: object required'],False
        if set(value)!=set(schema['properties']):
            issues.append(f'{path}: exact fields required: {list(schema["properties"])}');safe=False
        children=((value[k],child,f'{path}.{k}') for k,child in schema['properties'].items() if k in value)
    elif kind=='array':
        if not isinstance(value,list):return [f'{path}: list required'],False
        children=((v,schema['items'],f'{path}[{i}]') for i,v in enumerate(value))
        if schema['items']['type']=='string' and all(isinstance(v,str) for v in value):
            duplicates=sorted({v for v in value if value.count(v)>1})
            if duplicates:issues.append(f'{path}: duplicate values: {duplicates}')
    else:
        if not isinstance(value,str) or not value.strip():return [f'{path}: nonempty string required'],False
        if 'enum' in schema and value not in schema['enum']:return [f'{path}: invalid enum value'],False
        return [],True
    for v,child,child_path in children:
        found,valid=_schema_issues(v,child,child_path);issues.extend(found);safe &= valid
    return issues,safe


@dataclass(frozen=True)
class ReconciliationInput:
    payload_json: str

    @property
    def payload(self): return parse(self.payload_json)

    @property
    def input_ref(self): return 'RECONCILIATION_INPUT/' + digest(self.payload_json)


@dataclass(frozen=True)
class ReconciliationResult:
    payload_json: str

    @property
    def payload(self): return parse(self.payload_json)


def build_reconciliation_input(*, review_request, historical_reviews, contract_version="v19.4", additional_evidence_refs=()):
    require(contract_version in ("v19.1", "v19.2", "v19.3", "v19.4"), "unsupported reconciliation contract")
    require(isinstance(review_request, MemoryReviewInput), 'MemoryReviewInput required')
    require(validate_historical_reviews(historical_reviews.payload['raw_response'],request=review_request)
            == historical_reviews, 'historical reviews changed or stale')
    payload = review_request.payload
    require(not additional_evidence_refs or contract_version in ('v19.3','v19.4'),'extra context requires v19.3 input')
    require(len(additional_evidence_refs)==len(set(additional_evidence_refs)), 'duplicate additional evidence refs')
    result=ReconciliationInput(encode({'schema_version':'reconciliation_input_'+contract_version,
        'review_input_ref':review_request.input_ref, 'review_input':payload,
        'historical_reviews':historical_reviews.payload,
        'coverage':{'current_finding_refs':sorted(f['finding_id'] for f in payload['current_findings']),
                    'historical_review_refs':sorted(r['review_id'] for r in historical_reviews.payload['reviews'])},
        'evidence_counting':'UNIQUE_ORIGINAL_EVENT_REFERENCES_NOT_NUMBER_OF_MENTIONS',
        **({'additional_evidence_refs':sorted(additional_evidence_refs)} if contract_version in ('v19.3','v19.4') else {})}))
    if contract_version in ('v19.3','v19.4'):
        from .reconciliation_evidence_v19 import evidence_view
        evidence_view(result)  # Resolve every requested original ref before persistence/dispatch.
    return result


def _catalog(request):
    """Adapt exact current/historical observations to v18's typed catalogs.

    Composite trajectory identity includes source/role; visible event refs and raw
    content remain unchanged. Replaying the same historical task is not the same
    trajectory as the current observation or its paired counterpart.
    """
    data=request.payload['review_input']
    contexts=dict(data['current_contexts']); experiences={}
    for ref,value in data['current_evidence'].items():
        key=(value['task_ref'],value['trajectory_ref'],value['rollout_index'])
        if key not in experiences:
            identity={k:v for k,v in value.items() if k!='event'}
            label=next(v['supervision'] for v in data['current_supervision'].values()
                if (v['task_ref'],v['trajectory_ref'],v['rollout_index'])==key)
            experiences[key]={**identity,'events':[],'supervision':label}
        experiences[key]['events'].append(value['event'])
    for row in data['memory_context']['rounds']:
        for context in row['replay']['contexts']:
            ref=context['context_ref']
            require(ref not in contexts or contexts[ref]==context,'context collision')
            contexts[ref]=context
        for pair in row['replay']['pairs']:
            for role in ('parent','candidate'):
                exp=pair[role]
                trajectory=pair['pair_id']+'/'+role.upper()
                key=(pair['task_ref'],trajectory,pair['rollout_index'])
                require(key not in experiences,'historical trajectory collision')
                experiences[key]={**exp,'task_ref':pair['task_ref'],'trajectory_ref':trajectory,
                    'original_trajectory_ref':exp['trajectory_ref'],'rollout_index':pair['rollout_index'],
                    'origin':'COMMITTED_HISTORICAL_OBSERVATION','source_round_id':row['memory_record']['round_id'],
                    'pair_id':pair['pair_id']}
    payload={'schema_version':'group_diagnosis_input_v17.2','current_skill':data['current_skill'],
        'contexts':list(contexts.values()),'experiences':list(experiences.values()),
        'available_evidence_refs':{},'available_supervision_refs':{}}
    for exp in payload['experiences']:
        identity={k:exp[k] for k in ('task_ref','trajectory_ref','rollout_index','origin','source_round_id','skill_ref','role')}
        identity.update({k:exp[k] for k in ('pair_id','original_trajectory_ref') if k in exp})
        for event in exp['events']:
            ref=event['evidence_ref']
            require(ref not in payload['available_evidence_refs'],'duplicate event identity')
            payload['available_evidence_refs'][ref]={**identity,'step':event['step']}
        label=exp['supervision']
        payload['available_supervision_refs'][label['supervision_ref']]={**identity,'level':0}
    payload.update(build_reference_catalogs(payload))
    return payload


def _source(request, decision, index, catalog):
    data=request.payload['review_input']; batch=data['batch']
    provenance={'round_id':batch['round_id'],'parent_skill_digest':digest(data['current_skill']),
        'group_id':'RECONCILIATION/'+str(index),'reconciliation_input_ref':request.input_ref,
        'decision_index':index,'decision':decision}
    if decision['decision']=='PROPOSE':
        diagnosis=decision['proposals'][0]
    else:
        analysis={'finding':decision['reason'],'evidence_refs':[], 'supervision_refs':[],'unresolved':[]}
        diagnosis={'success_analysis':analysis,'compliance_analysis':analysis,
            'skill_addressability':{'status':'NOT_ADDRESSABLE','reason':decision['reason']},'parent_skill_gaps':[]}
    # Persist only proposal-relevant full trajectories; all evidence remains in
    # the separately bound generation audit. Noop wrappers need no trajectories.
    refs={r for name in ('success_analysis','compliance_analysis')
          for field in ('evidence_refs','supervision_refs') for r in diagnosis[name][field]}
    refs.update(r for gap in diagnosis['parent_skill_gaps'] for r in gap['evidence_refs'])
    experiences=[e for e in catalog['experiences'] if refs &
                 ({ev['evidence_ref'] for ev in e['events']}|{e['supervision']['supervision_ref']})]
    events={ev['evidence_ref'] for e in experiences for ev in e['events']}
    labels={e['supervision']['supervision_ref'] for e in experiences}
    local={**catalog,'experiences':experiences,
        'contexts':[c for c in catalog['contexts'] if c['context_ref'] in {e['context_ref'] for e in experiences}],
        'available_evidence_refs':{r:v for r,v in catalog['available_evidence_refs'].items() if r in events},
        'available_supervision_refs':{r:v for r,v in catalog['available_supervision_refs'].items() if r in labels},
        'grouping_hint':{'group_id':provenance['group_id']},
        'grouping_hint_authority':'RECONCILIATION_SOURCE_BINDING_NOT_EVIDENCE'}
    local.update(build_reference_catalogs(local))
    group=GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT',local),encode(provenance))
    validated=validate_diagnosis_response(encode(diagnosis),request=group)
    return CompilerDiagnosisSource('DIAGNOSIS/'+digest(validated.payload),group,validated)


def validate_reconciliation(raw, *, request):
    payload=request.payload; data=payload['review_input']
    # Revalidate the immutable upstream artifact before every use/restore.
    review_input=MemoryReviewInput(encode(data))
    require(review_input.input_ref==payload['review_input_ref'],'review input binding changed')
    require(validate_historical_reviews(payload['historical_reviews']['raw_response'],request=review_input).payload
            ==payload['historical_reviews'],'review artifact changed')
    current={f['finding_id']:f for f in data['current_findings']}
    reviews={r['review_id']:r for r in payload['historical_reviews']['reviews']}
    objects={o['historical_object_id']:o for o in data['historical_objects']}
    expected={'current_finding_refs':sorted(current),'historical_review_refs':sorted(reviews)}
    require(payload['coverage']==expected,'coverage manifest changed')
    legacy=payload['schema_version']=='reconciliation_input_v19.1'
    require(legacy or payload['schema_version'] in ('reconciliation_input_v19.2','reconciliation_input_v19.3','reconciliation_input_v19.4'),'unknown reconciliation input contract')
    output=parse(raw)
    issues,safe=_schema_issues(output,LEGACY_SCHEMA if legacy else DECISION_SCHEMA if payload['schema_version']=='reconciliation_input_v19.4' else SCHEMA)
    require(safe,'reconciliation contract errors: '+encode(issues))
    catalog=_catalog(request)
    visible=None
    if payload['schema_version'] in ('reconciliation_input_v19.3','reconciliation_input_v19.4'):
        from .reconciliation_evidence_v19 import evidence_view
        visible=evidence_view(request,catalog=catalog)
    def check(condition,message):
        if not condition:issues.append(message)
    seen={k:set() for k in expected}; sources=[]; dispositions=[]
    for i,d in enumerate(output['decisions']):
        check(d['current_finding_refs'] or d['historical_review_refs'],f'decision {i}: source required')
        for field in expected:
            refs=set(d[field])
            check(refs<=set(expected[field]) and not refs & seen[field],f'decision {i}: unknown or repeated {field}')
            seen[field].update(refs)
        if any(not set(d[field])<=set(expected[field]) for field in expected):
            continue  # Unknown IDs have no safe downstream evidence catalog.
        if visible is not None:
            cited=set(d['evidence_refs'])
            for proposal in d['proposals']:
                cited.update(r for name in ('success_analysis','compliance_analysis') for r in proposal[name]['evidence_refs'])
                cited.update(r for gap in proposal['parent_skill_gaps'] for r in gap['evidence_refs'])
            missing=cited-(set(visible['events'])|set(visible['available_policy_refs']))
            check(not missing,f'decision {i}: evidence not loaded in Reconciliation view: '+encode(sorted(missing)))
        if payload['schema_version']=='reconciliation_input_v19.4':
            from .reconciliation_decision_v19 import decision_issues
            issues.extend(decision_issues(d,index=i,current=current,visible=visible))
        event_scope=set()
        for fid in d['current_finding_refs']:
            event_scope.update(current[fid]['evidence_refs'])
            check(set(current[fid]['evidence_refs']) & set(d['evidence_refs']),
                    f'decision {i}: current finding {fid} missing grounding; available='+encode(current[fid]['evidence_refs']))
        for rid in d['historical_review_refs']:
            review=reviews[rid]; obj=objects[review['historical_object_id']]
            event_scope.update(obj['historical_event_refs'])
            if d['decision']=='KEEP':
                bound=set(obj['current_binding']['current_rule_refs'])|set(obj['current_binding']['descendant_rule_refs'])
                check(bool(bound & set(d['keep_rule_refs'])),f'decision {i}: cannot KEEP absent or unrelated historical guidance')
            review_current=set().union(*(set(review[f]) for f in
                ('supporting_current_refs','contradicting_current_refs','context_current_refs')))
            check(review_current<=set(d['evidence_refs']),f'decision {i}: review evidence or counterevidence dropped')
            if review['evidence_status'] in ('MIXED','CONTRADICTED'):
                check(bool(d['conflict_resolution']),f'decision {i}: explain conflicting historical judgment')
            if d['decision']=='PROPOSE':
                check(bool((review_current|set(obj['historical_event_refs'])) & set(d['evidence_refs'])),
                        f'decision {i}: historical source without evidence')
            for field in ('supporting_current_refs','contradicting_current_refs','context_current_refs'):
                event_scope.update(review[field])
        check(set(d['evidence_refs'])<=event_scope,f'decision {i}: evidence outside declared sources')
        check(set(d['keep_rule_refs'])<=set(catalog['available_rule_refs']),f'decision {i}: stale KEEP targets')
        check((d['decision']=='KEEP')==bool(d['keep_rule_refs']),f'decision {i}: KEEP requires current rules only')
        if not legacy:
            assessments=d['current_finding_assessments']
            ids=[a['finding_ref'] for a in assessments]
            check(len(ids)==len(set(ids)) and set(ids)==set(d['current_finding_refs']),
                  f'decision {i}: current_finding_assessments must cover declared findings exactly once; missing='+
                  encode(sorted(set(d['current_finding_refs'])-set(ids)))+'; extra='+encode(sorted(set(ids)-set(d['current_finding_refs']))))
        if d['decision']=='PROPOSE':
            check(len(d['proposals'])==1,f'decision {i}: exactly one proposal required')
            if len(d['proposals'])!=1:continue
            diagnosis=d['proposals'][0]; gaps=diagnosis['parent_skill_gaps']
            check(diagnosis['skill_addressability']['status']=='ADDRESSABLE' and len(gaps)==1,
                    f'decision {i}: exactly one addressable Skill Gap required')
            if len(gaps)!=1:continue
            gap=gaps[0]
            events=set(gap['evidence_refs']) & set(catalog['available_evidence_refs'])
            check(bool(events) and events<=set(d['evidence_refs']),f'decision {i}: gap outside decision evidence')
            if legacy:
                check(all(events & set(current[f]['evidence_refs']) for f in d['current_finding_refs']),
                      f'decision {i}: proposal lost merged current finding evidence')
            else:
                direct=[a for a in d['current_finding_assessments'] if a['role']=='DIRECT_BASIS']
                check(bool(direct or d['historical_review_refs']),f'decision {i}: proposal needs a direct basis')
                for a in direct:
                    fid=a['finding_ref']
                    if fid in current:
                        check(bool(events & set(current[fid]['evidence_refs'])),
                              f'decision {i}: DIRECT_BASIS {fid}: gap missing shared event; source evidence: '+encode(current[fid]['evidence_refs']))
            from .memory_diagnosis_v19 import gap_closure_issues
            for issue in gap_closure_issues(diagnosis,catalog['available_evidence_refs']):
                issues.append(f'decision {i}: gap closure: '+encode(issue))
            check((gap['kind']=='SHOULD_REMOVE')==bool(d['whole_rule_removal_reason']),
                    f'decision {i}: whole-rule removal reasoning required only for deletion')
            # Limit analyses too: extra prose cannot smuggle unrelated evidence to Editor.
            for name in ('success_analysis','compliance_analysis'):
                analysis=diagnosis[name]
                check(set(analysis['evidence_refs'])<=event_scope|set(catalog['available_policy_refs']),
                        f'decision {i}: analysis outside source evidence')
            analyzed=set().union(*(set(diagnosis[n]['evidence_refs']) for n in ('success_analysis','compliance_analysis')))
            check(set(d['evidence_refs'])<=analyzed,f'decision {i}: decision evidence omitted from analyses: '+encode(sorted(set(d['evidence_refs'])-analyzed)))
            for name in ('success_analysis','compliance_analysis'):
                analysis=diagnosis[name]
                observed=[e for e in catalog['experiences'] if set(analysis['evidence_refs']) &
                          {ev['evidence_ref'] for ev in e['events']}]
                check(set(analysis['supervision_refs'])<={e['supervision']['supervision_ref'] for e in observed},
                        f'decision {i}: {name}: supervision outside analyzed trajectories: '+encode(sorted(set(analysis['supervision_refs'])-{e['supervision']['supervision_ref'] for e in observed})))
                check(all(catalog['available_policy_refs'][r]['context_ref'] in {e['context_ref'] for e in observed}
                        for r in analysis['evidence_refs'] if r in catalog['available_policy_refs']),
                        f'decision {i}: policy outside analyzed contexts')
            if gap['kind']=='SHOULD_REMOVE':
                check(len(d['whole_rule_removal_reason'])==len(gap['related_rule_refs']),
                        f'decision {i}: explain whole-block deletion for every target')
        else:
            check(not d['proposals'] and not d['whole_rule_removal_reason'],f'decision {i}: non-PROPOSE cannot edit')
        try:sources.append(_source(request,d,i,catalog))
        except ValueError as exc:issues.append(f'decision {i}: {exc}')
        dispositions.append({'decision_id':'RC/'+digest(encode({'input_ref':request.input_ref,'decision':d})),**d})
    check(all(seen[k]==set(expected[k]) for k in expected),'incomplete reconciliation coverage: '+encode(
        {k:sorted(set(expected[k])-seen[k]) for k in expected}))
    kept={r for d in output['decisions'] for r in d['keep_rule_refs']}
    edited={r for d in output['decisions'] for p in d['proposals'] for g in p['parent_skill_gaps'] for r in g['related_rule_refs']}
    check(not kept & edited,'KEEP conflicts with proposed edit target')
    require(not issues,'reconciliation contract errors: '+encode(issues))
    # Even empty discovery/review has a deterministic no-update compilation.
    if not sources:
        sources=[_source(request,{'decision':'DEFER','reason':'No findings or historical objects supplied.',
                                 'proposals':[]},0,catalog)]
    parent=data['current_skill']
    compiler_input=CompilerInput(data['batch']['round_id'],parent,digest(parent),tuple(sources))
    plan=compile_edit_plan(compiler_input)
    from ..v18.compiler_validation_v18 import plan_payload
    return ReconciliationResult(encode({'schema_version':'reconciliation_result_v19.1',
        'input_ref':request.input_ref,'raw_response':raw,'decisions':dispositions,'plan':plan_payload(plan),
        'validation_scope':'STRUCTURE_REFERENCES_COVERAGE_NOT_SEMANTIC_TRUTH',
        **({'reconciliation_input_version':payload['schema_version'].removeprefix('reconciliation_input_'),'additional_evidence_refs':payload['additional_evidence_refs']}
           if visible is not None else {})})),EditorInput(compiler_input,plan)


def _validated_editor_input(result, request):
    rebuilt,value=validate_reconciliation(result.payload['raw_response'],request=request)
    require(rebuilt==result,'reconciliation result changed')
    return value


def reconciliation_editor_request(result, *, request):
    value=_validated_editor_input(result,request)
    prompt=build_editor_request(value)
    if prompt is None:
        return None
    payload=parse(prompt['user_prompt'])
    sources={s.diagnosis_ref:s for s in value.compiler_input.diagnoses}
    for unit in payload['edit_units']:
        refs=value.plan.edit_units[unit['edit_unit_index']].supporting_gap_refs
        indices=sorted({sources[g.diagnosis_ref].request.provenance['decision_index'] for g in refs})
        unit['reconciliation_provenance']=[{
            k:result.payload['decisions'][i][k] for k in ('decision_id','current_finding_refs',
                'historical_review_refs','reason','conflict_resolution','current_finding_assessments',
                'issue_dispositions','merge_justification','defer_basis','feasibility_checks')
            if k in result.payload['decisions'][i]} for i in indices]
    user=encode(payload)
    from .memory_generation_prompt_v19 import diagnosis_budget
    return {**prompt,'prompt_version':'reconciled-editor-v19.1','user_prompt':user,
            'input_sha256':digest(user),'input_budget':diagnosis_budget(prompt['system_prompt'],user,prompt['response_format'])}



def apply_reconciled_editor(raw, *, result, request):
    value=_validated_editor_input(result,request)
    applied=apply_editor_response(raw,editor_input=value)
    # Keep all dispositions, including KEEP/DEFER, alongside the actual plan.
    mapping=[]
    sources={s.diagnosis_ref:s for s in value.compiler_input.diagnoses}
    for index,unit in enumerate(value.plan.edit_units):
        indices=sorted({sources[g.diagnosis_ref].request.provenance['decision_index'] for g in unit.supporting_gap_refs})
        decisions=[result.payload['decisions'][i] for i in indices]
        mapping.append({'edit_unit_index':index,'operation':unit.operation,
            'decision_refs':[d['decision_id'] for d in decisions],
            'current_finding_refs':sorted({r for d in decisions for r in d['current_finding_refs']}),
            'historical_review_refs':sorted({r for d in decisions for r in d['historical_review_refs']}),
            'evidence_refs':sorted({r for d in decisions for r in d['evidence_refs']})})
    return {**applied,'reconciliation_input_ref':request.input_ref,
            'reconciliation':result.payload,'edit_provenance':mapping}

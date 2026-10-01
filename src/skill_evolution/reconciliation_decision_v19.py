"""Generic per-issue accountability and proposal feasibility, without domain rules."""
from copy import deepcopy
from .diagnosis_contract_v18 import _object,_strings
from .review_contract_v19 import text_schema


def decision_schema(base):
    schema=deepcopy(base)
    schema['properties']['schema_version']=text_schema('reconciliation_response_v19.4')
    item=schema['properties']['decisions']['items']
    fields={
        'issue_dispositions':{'type':'array','items':_object({
            'source_ref':text_schema(),'issue':text_schema(),
            'disposition':text_schema('ADDRESSED','PRESERVED','DEFERRED','CONTEXT_ONLY'),
            'reason':text_schema()})},
        'merge_justification':_strings(),
        'defer_basis':{'type':'array','items':_object({
            'category':text_schema('INSUFFICIENT_EVIDENCE','UNAVAILABLE_CAPABILITY','UNRESOLVED_CONFLICT','UNCERTAIN_APPLICABILITY'),
            'reason':text_schema(),'required_information':text_schema()})},
        'feasibility_checks':{'type':'array','items':_object({
            'requirement':text_schema(),
            'status':text_schema('SUPPORTED','UNAVAILABLE','UNKNOWN'),
            'evidence_refs':_strings(),'tool_refs':_strings(),
            'availability_before_action':text_schema(),
            'limitations_and_counterevidence':text_schema(),
            'reason':text_schema()})},
    }
    item['properties'].update(fields);item['required'].extend(fields)
    return schema


def decision_issues(decision, *, index, current, visible):
    errors=[]
    def check(ok,message):
        if not ok:errors.append(f'decision {index}: '+message)
    refs=decision['current_finding_refs']+decision['historical_review_refs']
    dispositions=decision['issue_dispositions'];ids=[d['source_ref'] for d in dispositions]
    check(len(ids)==len(set(ids)) and set(ids)==set(refs),'issue_dispositions must cover each declared source exactly once')
    action=decision['decision']
    allowed={'PROPOSE':{'ADDRESSED','CONTEXT_ONLY'},'KEEP':{'PRESERVED','CONTEXT_ONLY'},'DEFER':{'DEFERRED','CONTEXT_ONLY'}}[action]
    roles={a['finding_ref']:a['role'] for a in decision['current_finding_assessments']}
    for d in dispositions:
        ref=d['source_ref']
        check(d['disposition'] in allowed,f'{ref}: disposition conflicts with {action}')
        if ref in current and current[ref]['kind']=='OBSERVED_PROBLEM':
            check(d['disposition']!='CONTEXT_ONLY',f'{ref}: observed problem needs its own explicit disposition, not background')
        if action=='PROPOSE' and roles.get(ref)=='DIRECT_BASIS':
            check(d['disposition']=='ADDRESSED',f'{ref}: direct basis must be addressed')
    check(bool(decision['merge_justification'])==(len(refs)>1),'merged sources require common issue and compatible treatment justification; single source must not claim a merge')
    check(bool(decision['defer_basis'])==(action=='DEFER'),'DEFER requires a concrete evidence/capability/conflict/applicability obstacle only')
    checks=decision['feasibility_checks']
    check(action!='PROPOSE' or bool(checks),'PROPOSE requires explicit feasibility checks')
    source_events=set(decision['evidence_refs'])
    trajectory_ids={visible['events'][r]['trajectory_id'] for r in source_events if r in visible['events']}
    contexts={visible['trajectories'][t]['context_ref'] for t in trajectory_ids}
    for n,c in enumerate(checks):
        events=set(c['evidence_refs'])
        check(bool(events),f'feasibility {n}: original event evidence required')
        check(events<=set(visible['events']),f'feasibility {n}: unloaded evidence refs')
        check(all(visible['events'][r]['trajectory_id'] in trajectory_ids for r in events if r in visible['events']),
              f'feasibility {n}: evidence outside decision source trajectories')
        check(set(c['tool_refs'])<=set(visible['available_tool_refs']),f'feasibility {n}: unknown tool refs')
        check(all(visible['available_tool_refs'][r]['context_ref'] in contexts for r in c['tool_refs'] if r in visible['available_tool_refs']),
              f'feasibility {n}: tool definition outside source contexts')
        if action=='PROPOSE':check(c['status']=='SUPPORTED',f'feasibility {n}: unavailable or unknown prerequisite cannot authorize a proposal')
    return errors


INSTRUCTIONS='''
ISSUE ACCOUNTABILITY AND EXECUTABILITY
There is NO batch-wide limit on PROPOSE decisions. Each PROPOSE has exactly one gap;
multiple independent issues may each produce a separate PROPOSE. Shared topic,
trajectory, tool or a desire to shorten output does not establish the same issue.
Use issue_dispositions to identify and dispose of each source issue explicitly.
An observed problem cannot be CONTEXT_ONLY. If it is not addressed/preserved by this
decision, put it in a separate DEFER decision with its concrete obstacle. For merged
sources, merge_justification must explain the common problem and compatible treatment.
Do not merge unrelated problems merely because both are deferred. DEFER requires a
specific missing fact, unavailable capability, unresolved conflict or applicability
uncertainty and the information needed to revisit it; there is no proposal quota.

For each proposal enumerate feasibility_checks for its required information and
executable behavior. Read the complete source trajectories and public tool definitions.
Check observed tool calls AND returned results, capability limitations, ordering and
counterexamples. A post-action outcome discrepancy is not evidence that its value can
be known before acting. An instruction cannot create data access or tool capabilities.
Use evidence_refs for the exact observed basis and tool_refs for each relied-on tool
definition. For behavior requiring no tool, use an empty tool_refs and explain the
available behavioral choice. Explain availability_before_action and limitations_and_
counterevidence even when status is SUPPORTED. Tool-free reasoning is not permission
to assume hidden data. Enumerate all essential prerequisites; if any is UNAVAILABLE
or UNKNOWN, DEFER the issue or formulate a genuinely different, supported proposal.
No automatic code correction will convert these conclusions into SUPPORTED.
Full context events may be cited in feasibility checks; they do not automatically
become gap support or change immutable Findings. Preserve the original gap-source
closure. If new discovery is needed, DEFER rather than inventing a finding.
These records enable audit; their presence does not prove their semantic truth.
'''

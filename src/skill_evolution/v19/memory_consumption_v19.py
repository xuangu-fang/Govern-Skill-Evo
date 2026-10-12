"""Shared bounded history view. Archives are never rewritten or truncated.

Summary capacity fails closed: distinct claims cannot be safely summarized by
string slicing. Raw evidence is selected in complete pair/trajectory units.
"""
from copy import deepcopy
from .edit_tracking_v19 import encode, digest
from .memory_store_v19 import require

PROTOCOL = 'memory_consumption_v19.1'
SUMMARY_OBSERVATION_TOKENS = 10000
SUMMARY_TOKENS = 64000
RAW_TOKENS = 6000
INSTRUCTIONS = '''
Memory provenance references are archive pointers, not a request to load their bodies.
Only supplied original events have been inspected. Historical judgments remain
hypotheses; Gate acceptance is not individual edit quality. The history view reports
selection coverage. Missing evidence is not negative evidence. If a necessary claim
cannot be checked with loaded originals, do not authorize a modification.
'''


def tokens(value):
    import tiktoken
    return len(tiktoken.get_encoding('cl100k_base').encode(encode(value),disallowed_special=()))


def state_view(value, *, limit=SUMMARY_TOKENS):
    """Deduplicate exact repeated records, retaining conflicting/novel claims.

    No LLM, semantic merging, last-write-wins inference or character truncation.
    Lists of references are set-like only when they contain strings exclusively.
    """
    def walk(v):
        if isinstance(v,dict):return {k:walk(x) for k,x in v.items()}
        if isinstance(v,list):
            result=[];seen=set()
            for x in v:
                x=walk(x);key=encode(x)
                if key not in seen:result.append(x);seen.add(key)
            return result
        return v
    result=walk(deepcopy(value))
    # Reuse the existing lossless representation for the cost boundary.
    from .memory_review_repair_v19 import compact_text
    from .review_context_v19 import compact_projection
    size=tokens(compact_text(compact_projection({'packet_version':'evidence_packet_v19.5',**result})))
    if size > SUMMARY_OBSERVATION_TOKENS:
        import logging
        logging.getLogger(__name__).info('Memory summary observation: %s tokens (threshold %s, engineering limit %s)',
                                         size, SUMMARY_OBSERVATION_TOKENS, limit)
    require(size<=limit, f'Memory summary exceeds shared budget ({size} > {limit}); archive unchanged, no dispatch')
    return result, {'protocol':PROTOCOL,'source_sha256':digest(encode(value)),
        'summary_tokens':size,'summary_limit':limit}


def select_originals(experiences, source_refs, counter_refs, *, limit=RAW_TOKENS):
    """Choose complete cited pair units; counterexamples precede other units.

    Units keep all cited events and their call/result partners. Selection order is
    stable and independent of outcome sign. Omitted refs remain in the audit receipt.
    """
    from .review_context_v19 import paired_events
    wanted=set(source_refs)|set(counter_refs);counter=set(counter_refs)
    units={};found=set()
    for exp in experiences:
        events=exp['events'];direct=wanted & {e['evidence_ref'] for e in events}
        if not direct:continue
        refs=paired_events(events,direct);found.update(direct)
        for e in events:
            ref=e['evidence_ref']
            if ref not in refs:continue
            key=ref.rsplit('/',2)[0] if ref.startswith('PAIR/') else exp.get('trajectory_ref',ref)
            units.setdefault(key,{})[ref]=e
    require(wanted<=found,'historical source reference missing from archive')
    selected={};used=0
    for key,events in sorted(units.items(),key=lambda kv:(not bool(set(kv[1])&counter),kv[0])):
        size=tokens(events)
        if used+size<=limit:selected.update(events);used+=size
    omitted=sorted(wanted-set(selected))
    return set(selected), {'protocol':PROTOCOL,'raw_tokens':used,'raw_limit':limit,
        'selected_refs':sorted(selected),'omitted_count':len(omitted),
        'omitted_refs_sha256':digest(encode(omitted)),
        'omitted_counterevidence_count':len(counter-set(selected)),
        'source_sha256':digest(encode(sorted(wanted)))}


def historical_object_view(obj):
    """Shared consumer view: retain judgments, replace discovery bodies by refs.

    The matching result is already in historical_judgment. Additional result sets
    remain intact, including adverse outcomes, uncertainty and joint attribution.
    """
    fields=('historical_object_id','edit_id','attribution_id','joint_edit_ids',
            'historical_judgment','current_binding','edit')
    item={k:deepcopy(obj[k]) for k in fields if k in obj}
    if 'edit_attempt' in obj:
        attempt=obj['edit_attempt']
        item['edit_attempt']={k:deepcopy(v) for k,v in attempt.items()
            if k not in ('attempt','source_findings','results')}
        item['edit_attempt']['source_finding_refs']=[f['finding_id'] for f in attempt.get('source_findings',[])]
        item['edit_attempt']['other_results']=[deepcopy(r) for r in attempt.get('results',[])
            if r.get('attribution_id')!=obj.get('attribution_id')]
    return item


# Shared decision semantics, not new persistent states or another review stage.
REVIEW_COMPARISON = '''
Separate recurrence of the underlying problem from evidence about the attempted
solution. In reason name the specific historical claim being assessed, then explain
what the supplied current findings can actually test. Read current_binding and Gate
history to establish deployment; neither establishes execution or individual quality.
If the attempted rule is ABSENT from Parent, recurrence of the problem only shows
that the need persists. It does not test the missing solution and must not by itself
support or contradict its effectiveness. Use context_current_refs and NOT_COVERED
with INSUFFICIENT_EVIDENCE when recurrence is relevant but the historical claim is
untested. Keep the relevant current_finding_refs for downstream issue association.
Absence is not a blanket ban on CONTRADICTED: current evidence can independently
refute an applicability or execution-capability claim. Identify that claim and the
specific contradiction; do not substitute problem recurrence for that evidence.
When a rule is present, distinguish failure to follow it from consequences of following
it. Rule presence alone does not show execution. SUPPORTED, CONTRADICTED and MIXED
remain relations to a historical claim, not good/bad edit labels. Missing coverage
never erases historical positive evidence, limitations or uncertainty.
'''

REUSE_LIMITATIONS = '''
A recurring problem establishes a reason to investigate, not a reason to repeat or
strengthen the previous solution. Carry both the prior benefit hypothesis and its
behavioral limitations into this issue. Parent recurrence without the attempted rule
is not evidence that the attempt failed. Gate acceptance/rejection is not edit quality.
Associated-pair success regressions are warning evidence, not edit-caused harm;
consider the linked behavior observations, scope, joint evidence and alternative
explanations before drawing that connection. Do not suppress adverse observations
because compliance improved or because the current problem still exists.
'''

REUSE_VERIFICATION = '''
For a proposed retry, use the existing reason to identify relevant prior limitations
and explain whether they apply to the proposed behavior and scope. A documented
behavioral limitation requires a substantive response: narrow the scope, change the
behavior/path, or cite supplied evidence showing why the limitation does not apply.
Reflect any claimed correction in gap.statement; explanatory reassurance alone does
not change an unchanged or stronger proposal. If relevant limitations remain unresolved
by the supplied material, return NO_EDIT for this round. Do not invent an alternative
path, unavailable information, tools or policy to obtain VERIFIED. An unchanged retry
is allowed when supplied evidence addresses the prior concern; history is not a ban.
A negative outcome count alone does not require rejecting the proposal or inventing
a causal limitation. Explain its uncertainty alongside the behavioral evidence.
Use reason and gap only; do not add checklists, extra status fields or retrieval calls.
'''

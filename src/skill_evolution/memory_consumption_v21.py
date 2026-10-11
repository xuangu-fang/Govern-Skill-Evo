"""Consume evidence-backed Memory through the existing Fusion/review/editor path.

Reuse v20 wire/result contracts and compiler, not its historical archive format.
Only generation provenance and review assembly are adapted. The trusted caller
selects a published/imported evidence bundle and supplies the actual next Parent;
a Memory update does not imply that its Candidate was deployed.
"""
from copy import deepcopy
import json

from .edit_tracking_v19 import encode, digest, skill_ref
from .memory_store_v19 import require
from .issue_memory_v20 import validate_memory
from .current_diagnosis_v19 import validate_current_batch
from .review_contract_v19 import CurrentDiagnosisInput, CurrentFindings
from .diagnosis_references_v18 import build_reference_catalogs
from .issue_fusion_v20 import (IssueFusionInput as V20FusionInput, IssueFusionResult,
    build_issue_fusion_input as _fusion_input, validate_issue_fusion_result)
from .issue_fusion_prompt_v20 import build_issue_fusion_request as _fusion_request
from .evidence_review_v20 import (EvidenceReviewInput as V20ReviewInput,
    build_evidence_archive, _insert)
from .local_generation_v20 import (GenerationInput as V20GenerationInput,
    restore_generation as _restore_generation, run_local_generation)
from .modification_evidence_v21 import ModificationEvidence
from .current_understanding_v21 import current_understanding, open_current_memory_evidence, MAX_CHARACTERS
from .memory_generation_prompt_v19 import diagnosis_budget
from .evidence_wire_v21 import (pack, pack_review, restore_response, INSTRUCTIONS,
                                OPERATION_COMPARISON_INSTRUCTIONS)


DUAL_MEMORY_RULES = '''
Memory assessments are revisable interpretations of task-success and procedural-
compliance evidence. Consider the other dimension's problems, counterevidence and
uncertainty together with any favorable observation, including other attempts for
that issue. One dimension neither certifies nor invalidates the entire approach.
Do not combine success from one run/version and compliance from another into a
joint success. A task label or deployment decision does not establish a cause.
Preserve only evidence-supported useful behavior; revise the problematic scope or
behavior when justified. Whole approaches may be rewritten; no mandatory per-edit
decomposition or independent effect claim is required. A policy requirement is
not relaxed by a failed task, and uncertainty does not create a new prohibition,
confirmation or escalation duty. A hypothesis may be explored as a hypothesis.
Use the existing reason to explain relevant support, how the proposed direction
addresses known limitations, and what remains untested. A retry must address the
old concern or cite changed evidence; recurrence alone is not a justification.
No new disposition table, scores, effect states or extra review is requested.
'''


def _check_sources(memory_evidence, parent_skill, current_requests, current_findings):
    require(isinstance(memory_evidence, ModificationEvidence), 'Memory evidence bundle required')
    p = memory_evidence.payload
    require(p['schema_version'] == 'modification_evidence_v21.1', 'Memory evidence protocol mismatch')
    memory = validate_memory(p['memory'], run_id=p['run_id'])
    batch = validate_current_batch(current_requests, current_findings)
    require(batch['run_id'] == p['run_id'] and batch['round_id'] != p['round_id'],
            'Memory must come from an earlier round of this run')
    require(batch['parent_skill_ref'] == skill_ref(parent_skill) and
            all(r.payload['current_skill'] == parent_skill for r in current_requests),
            'current Parent mismatch')
    return memory, batch


def build_issue_fusion_input(*, memory_evidence, parent_skill, current_requests, current_findings):
    memory, batch = _check_sources(memory_evidence, parent_skill, current_requests, current_findings)
    # One established synthesis and an attempt directory; no fresh attribution.
    # Without a committed edit ledger, bindings deliberately remain UNRESOLVED.
    base = _fusion_input(memory=memory, parent_skill=parent_skill,
        run_id=batch['run_id'], round_id=batch['round_id'],
        current_requests=current_requests, current_findings=current_findings)
    p = base.payload
    for issue, original in zip(p['memory_issues'], memory['issues']):
        summary = current_understanding(original, memory_evidence.payload['archive'])
        if summary:
            issue['current_understanding'] = summary['statement']
            # A directory for the existing memory_attempt_refs selection, not
            # repeated attempt assessments or an invented aggregate attempt.
            for attempt in issue['attempts']:
                del attempt['assessment']
    p['schema_version'] = 'issue_fusion_input_v21.1'
    return IssueFusionInput(encode(p))


class IssueFusionInput(V20FusionInput):
    @property
    def input_ref(self):
        return 'ISSUE_FUSION_INPUT_V21/' + digest(self.payload_json)

    def validation_payload(self):
        """Reuse v20 identity checks without exposing placeholder text to models."""
        p = deepcopy(self.payload)
        require(p['schema_version'] == 'issue_fusion_input_v21.1', 'v21 Fusion protocol mismatch')
        p['schema_version'] = 'issue_fusion_input_v20.1'
        for issue in p['memory_issues']:
            if 'current_understanding' in issue:
                text = issue.pop('current_understanding')
                require(type(text) is str and text.strip() and len(text) <= MAX_CHARACTERS,
                        'invalid compact current understanding')
                for attempt in issue['attempts']:
                    require('assessment' not in attempt, 'compact attempts are a directory only')
                    attempt['assessment'] = 'ARCHIVED_NOT_LOADED'
        return p


def build_issue_fusion_request(request, **kwargs):
    prompt = _fusion_request(request, **kwargs)
    prompt.update(stage='issue_fusion_v21', prompt_version='issue-fusion-v21.6')
    prompt['system_prompt'] = prompt['system_prompt'].replace('v20 Issue Fusion', 'v21 Issue Fusion')
    prompt['system_prompt'] += DUAL_MEMORY_RULES + '''
This compact input does not load original historical events. Propose a direction
for the existing local review; do not claim to have rechecked the originals.
Use each memory issue's problem as its scope anchor. Attempts may contain old
mixed-topic history; their later details must not replace the original problem.
Combine findings/issues only when they describe one concrete related problem
that can be reviewed together. Sharing a task, rule or edit alone is insufficient.
Explain a joint proposal's relation to the original problems in the existing
reason. Keep independent problems in separate decisions. A joint decision is not
authorization to copy its whole text or all its edits into every linked issue.
When current_understanding is present, it is the issue's latest evidence-backed
synthesis, still revisable and not a causal proof. Attempts are only an ID/approach
directory: their assessments are archived, not read here. Use memory_attempt_refs
to request the specific attempts needed for a comparison, retry or unresolved
historical question. Local Review opens them with their originals and joint
dependencies; it always retains known counterexamples. Without a synthesis the
legacy full assessment view remains. Do not select every attempt by default.

BASIS FOR PROPOSE OR NO_EDIT
Fusion selects evidence-backed behavioral questions for Review; it does not need
an established causal explanation or a finished rule. In issue_statement identify
what observed behavior may be wrong and the bounded direction to examine. In
reason connect supplied Findings/history, applicability, current Parent coverage,
and the favorable/adverse evidence in both dimensions. State what comparison
would support or refute the proposed direction. Do not claim originals were read.
Findings (including OBSERVED_PROBLEM) and Memory are revisable interpretations.
Distinguish the reported action from the alleged discrepancy with user-provided
information, authorization or applicable requirements, and from an outcome label.
When originals are not loaded, keep that discrepancy a falsifiable question for
Review, including what evidence would refute it; do not presume a surface pattern
is wrong and make its removal the proposed direction.
A later correction, successful final action or compliant label does not erase an
earlier mismatch. A single observation may support a narrow question, although it
cannot alone establish a general rule. NO_EDIT needs an issue-specific explanation
of why current guidance or the evidence leaves no supported revision question;
final success/compliance or low example count is not sufficient by itself.
Propose changes to the supported behavior or decision relation. Additional
confirmation, refusal or escalation needs evidence of a relevant ambiguity,
conflict, authorization gap or applicable requirement, not an unusual appearance,
an unknown outcome cause or the absence of a rule. Do not invent the expected
answer or generalize a literal field pattern. If a proposed action
needs information, distinguish evidence that it is obtainable from the hypothesis
that it might be; let Review check this prerequisite, without inventing access.
Existing rule text is coverage, not execution proof: identify the remaining
mismatch, ambiguity or applicability limit before proposing a revision. If only
recurrence, an unexplained label or a wish to browse history remains, use NO_EDIT.
History-only concerns can be supported by the loaded assessments and current
rules; unresolved edit bindings do not prove absence. Keep observed problems in
exactly one issue even for NO_EDIT; do not hide them as unassociated. Preserve
Memory and uncertainty. No quota, prewritten Skill text or per-edit analysis is
needed; Review retains evidence verification and edit authorization.
'''
    prompt['input_budget'] = diagnosis_budget(prompt['system_prompt'], prompt['user_prompt'],
                                              prompt['response_format'])
    return prompt


class EvidenceReviewInput(V20ReviewInput):
    """v20 review contract with v21 paired-source provenance; no new verdicts."""
    @property
    def input_ref(self):
        return 'EVIDENCE_REVIEW_INPUT_V21/' + digest(self.payload_json)

    def normalize_response(self, raw):
        return restore_response(raw, pack(self.payload)[1])

    def build_request(self):
        prompt = super().build_request()
        prompt['prompt_version'] = 'evidence-review-v21.9'
        prompt['system_prompt'] = prompt['system_prompt'].replace(
            'This v20 packet includes all attempts of each selected problem and explicit joint\nsource dependencies.',
            'This v21 packet uses current understandings and explicitly selected history;\nissues without a synthesis retain their full history.')
        prompt['system_prompt'] += DUAL_MEMORY_RULES + '''
The v21 memory_evidence_ref binds the historical bundle. pairs and parent_pairs
preserve exact version/run associations; historical role PARENT/CANDIDATE refers
to that past replay, not the current deployed Parent. Only rules describes the
current editable Parent. Check whether the relevant behavior already exists.
Read loaded original events and visible policy/tools to reassess Memory. Source
records (including ASSESSMENT and REPLAY) are not event citations. Keep favorable
and adverse observations attached to their actual trajectories and both labels.
In the existing reason and bounded gap, connect the intended change to relevant
support, limitations and remaining uncertainty; there is no separate analysis
per edit. Old interpretations may be revised with evidence, while original facts
and known counterevidence remain explicit. An unrelated change in Memory does not
require a changed Candidate. VERIFIED authorizes a testable edit, not a claim that
its future effects or local causal contribution have already been demonstrated.

EVIDENCE COMPARISON FOR THIS DECISION
Within the selected problem, compare loaded observations that materially support
or challenge the proposed behavioral defect, including relevant positive history
even when it is not marked as known_counterevidence. Do not select only failures
or only examples agreeing with Memory. In the existing reason, cite the decisive
events and explain their bearing on the decision; retain the existing structured
evidence/counterevidence citations. No exhaustive event or per-edit table is needed.
Compare actual actions, arguments, returned results and execution-time conditions
such as user intent/authorization, available information and applicable policy/tool
context. State material differences or unknowns that limit reuse. Keep each outcome's
success and compliance labels with its own trajectory; a positive label alone does
not establish which behavior worked. Only explicit pairs establish replay pairing;
other cross-round observations may inform comparison but are not controlled pairs.
Separate what was observed, what it supports within those conditions, and what
remains a causal hypothesis. Reconcile relevant contrary observations or explain
why they do not transfer; their mere presence in a citation list is not a comparison.
An unavailable complete policy contract does not by itself negate bounded empirical
support; nor may observations override visible policy or establish a hidden rule.
Before authorizing VERIFIED, check whether the alleged defect holds against the
original user statements, actions and applicable requirements. OBSERVED_PROBLEM,
Memory and the Fusion proposal may be refuted by those originals. Faithful use
of explicit user information is not a defect merely because the result looks
unusual; identify an actual discrepancy or independently supported requirement.
Additional confirmation, refusal or escalation needs evidence of a relevant
ambiguity, conflict, authorization gap or applicable requirement. Feasibility,
testability and a missing Parent sentence do not establish that such a duty is
needed. If the premise is refuted and no supported defect remains within the
selected issue, explain that in NO_EDIT rather than inventing a precaution.
Later correction or user approval does not erase an earlier evidenced mismatch
or override applicable policy. An unresolved cause can still permit a bounded
edit for a real defect. For VERIFIED, connect that defect in current-Parent
behavior to a feasible, conditional change in the existing gap; do not add
case-specific rules merely to pass a failed example or generalize an isolated success.
For NO_EDIT, still address relevant positive and adverse evidence and name the
specific unresolved link or current coverage that prevents a justified change.
Neither uncertainty alone nor an existing sentence proves that execution is sound.
An unresolved mechanism can coexist with a supported bounded change; insufficient
behavioral evidence or unavailable prerequisites can still justify NO_EDIT.

ISSUE REVIEW BOUNDARY
Review the original problem in each selected memory_issues entry and the selected
current findings. The Fusion issue_statement is a proposed direction, not a new
definition of a historical issue. Do not follow a mixed-topic historical attempt
away from its original problem. issue_source_refs marks each issue's existing
explicit source chain; other source_records remain shared context. Neither direct
provenance nor a shared edit proves that every statement belongs to this issue.
Retain all known counterevidence and consider interactions, while explaining in
reason how the evidence bears on the original question. For related jointly
selected issues, keep their scopes distinct within the existing reason and gap;
do not claim that one issue's result establishes another's result. An incidental
unrelated error cannot substitute for the selected problem or widen this gap.
When no change is justified for the selected problem, use the existing NO_EDIT
verdict even if shared history suggests a different problem worth investigating.
Text already present in current rules establishes textual coverage only, not
successful or compliant execution; distinguish those claims in reason.
Where current_understanding is present, memory_issues.attempts contains only the
attempts explicitly selected by Fusion. Other full attempts and old syntheses
remain archived, not erased or proven irrelevant. Read the synthesis together
with its cited originals and all known counterexamples; it cannot replace raw
evidence. If the loaded evidence cannot support the selected change, use NO_EDIT
with the limitation instead of inventing missing historical details. An old issue
without a synthesis retains the full-history path. No additional Review is added.
'''
        wire, reference_map = pack_review(self.payload)
        prompt['user_prompt'] = json.dumps(wire, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        prompt['system_prompt'] += INSTRUCTIONS + OPERATION_COMPARISON_INSTRUCTIONS
        prompt['reference_map'] = reference_map
        prompt['input_budget'] = diagnosis_budget(prompt['system_prompt'], prompt['user_prompt'],
                                                  prompt['response_format'])
        return prompt


class GenerationInput(V20GenerationInput):
    @property
    def input_ref(self):
        return 'GENERATION_INPUT_V21/' + digest(self.payload_json)

    def build_review_inputs(self):
        p = self.payload
        require(p['schema_version'] == 'generation_input_v21.1', 'v21 generation protocol mismatch')
        evidence = ModificationEvidence(encode(p['memory_evidence']))
        require(evidence.evidence_ref == p['memory_evidence_ref'], 'Memory evidence binding mismatch')
        require(p['memory'] == evidence.payload['memory'], 'Memory snapshot differs from evidence bundle')
        rs = tuple(CurrentDiagnosisInput(encode(r['payload']), encode(r['provenance']))
                   for r in p['current_requests'])
        fs = tuple(CurrentFindings(encode(f)) for f in p['current_findings'])
        fusion = IssueFusionInput(encode(p['fusion_input']))
        require(build_issue_fusion_input(memory_evidence=evidence, parent_skill=p['parent_skill'],
            current_requests=rs, current_findings=fs) == fusion, 'Fusion source binding mismatch')
        result = IssueFusionResult(encode(p['fusion_result']))
        validate_issue_fusion_result(result, request=fusion)
        return _review_inputs(evidence, fusion, result, p['parent_skill'], rs, fs)


def build_generation_input(*, memory_evidence, fusion_input, fusion_result, parent_skill,
                           current_requests, current_findings):
    value = GenerationInput(encode({'schema_version': 'generation_input_v21.1',
        'memory_evidence_ref': memory_evidence.evidence_ref, 'memory_evidence': memory_evidence.payload,
        'memory': memory_evidence.payload['memory'], 'parent_skill': parent_skill,
        'fusion_input': fusion_input.payload, 'fusion_result': fusion_result.payload,
        'current_requests': [{'payload': r.payload, 'provenance': r.provenance} for r in current_requests],
        'current_findings': [f.payload for f in current_findings]}))
    value.build_review_inputs()  # Resolve source closure before dispatching a model.
    return value


def _review_inputs(evidence, fusion, result, parent, current_requests, current_findings):
    current = build_evidence_archive(run_id=fusion.payload['run_id'],
        experiences=[e for r in current_requests for e in r.payload['experiences']],
        contexts=[c for r in current_requests for c in r.payload['contexts']]).payload
    findings = {f['finding_id']: f for fs in current_findings for f in fs.payload['findings']}
    requests = []
    for issue in result.payload['issues']:
        if issue['decision'] != 'PROPOSE':
            continue
        view = open_current_memory_evidence(evidence, issue_refs=issue['memory_issue_refs'],
                                           attempt_refs=issue['memory_attempt_refs'])
        selected = [findings[r] for r in issue['current_finding_refs']]
        tids = {current['events'][r]['trajectory_ref'] for f in selected for r in f['evidence_refs']}
        trajectories, events, contexts = view['trajectories'], view['events'], view['contexts']
        for tid in tids:
            _insert(trajectories, tid, current['trajectories'][tid])
            ctx = current['trajectories'][tid]['context_ref']
            _insert(contexts, ctx, current['contexts'][ctx])
        for ref, event in current['events'].items():
            if event['trajectory_ref'] in tids:
                _insert(events, ref, event)
        counter = {r for f in selected if f['kind'] == 'COUNTEREVIDENCE' for r in f['evidence_refs']}
        counter.update(view['known_counterevidence_refs'])
        catalogs = build_reference_catalogs({'current_skill': parent, 'contexts': list(contexts.values())})
        tools = {f'TOOL/{c}/{n}/{digest(encode(t))}': {'context_ref': c, 'definition': t}
                 for c in sorted(contexts) for n, t in enumerate(contexts[c]['public_tools'])}
        requests.append(EvidenceReviewInput(encode({
            'schema_version': 'evidence_review_input_v20.1',  # reused verdict/reference contract
            'fusion_input_ref': fusion.input_ref, 'fusion_result_sha256': digest(result.payload_json),
            'memory_evidence_ref': evidence.evidence_ref, 'proposal_id': issue['proposal_issue_id'],
            'issue': issue, 'parent_skill_sha256': digest(parent), 'findings': selected,
            'memory_issues': view['memory_issues'], 'source_records': view['source_records'],
            'issue_source_refs': view['issue_source_refs'],
            'historical_edits': view['edits'], 'pairs': view['pairs'], 'parent_pairs': view['parent_pairs'],
            'events': events, 'trajectories': trajectories, 'rules': catalogs['available_rule_refs'],
            'policies': catalogs['available_policy_refs'], 'tools': tools,
            'known_counterevidence_refs': sorted(counter),
            'selection': 'CURRENT_UNDERSTANDING_SELECTED_ATTEMPTS_ALL_KNOWN_COUNTEREVIDENCE_OR_LEGACY_FULL'})))
    return tuple(requests)


def restore_generation(audit):
    # The audit/result/edit wire contracts and deterministic compiler stay v20;
    # the explicitly versioned source rebuilds v21 reviews on every validation.
    return _restore_generation(audit, source_type=GenerationInput)


def run_memory_consumption(*, memory_evidence, parent_skill, current_requests, current_findings,
                           output, fusion_transport=None, review_transport=None,
                           editor_transport=None, model='deepseek-v4-pro'):
    """One Fusion -> one Review per PROPOSE -> one bounded Editor, no publication.

    Refuse existing output; campaign recovery and atomic head publication remain
    outside this local stage. Keep incomplete artifacts and never retry silently.
    """
    from pathlib import Path
    from .attribution_v19 import _transport
    from .evolution_replay_v19 import _save
    from .issue_fusion_v20 import validate_issue_fusion
    root = Path(output)
    kwargs = dict(memory_evidence=memory_evidence, parent_skill=parent_skill,
                  current_requests=current_requests, current_findings=current_findings)
    fusion = build_issue_fusion_input(**kwargs)
    prompt = build_issue_fusion_request(fusion, model=model)
    prompt.update(reasoning_effort='high', max_completion_tokens=24000, timeout_seconds=600)
    root.mkdir(parents=True, exist_ok=False)
    _save(root/'fusion-input.json', fusion.payload)
    _save(root/'fusion-request.json', prompt)
    try:
        response = (fusion_transport or _transport)(prompt)
        _save(root/'fusion-response.json', response)
        require(type(response) is dict and response.get('finish_reason') == 'stop'
                and not response.get('refusal'), 'refused or incomplete Fusion; consumption stopped')
        result = validate_issue_fusion(response.get('raw_response'), request=fusion, wire=True)
        _save(root/'fusion-result.json', result.payload)
        source = build_generation_input(**kwargs, fusion_input=fusion, fusion_result=result)
        audit = run_local_generation(source=source, output=root/'generation',
            review_transport=review_transport, editor_transport=editor_transport, model=model)
        _save(root/'status.json', {'status': audit['result']['status']})
        return audit
    except Exception as exc:
        _save(root/'status.json', {'status': 'INCOMPLETE', 'error_type': type(exc).__name__, 'message': str(exc)})
        raise

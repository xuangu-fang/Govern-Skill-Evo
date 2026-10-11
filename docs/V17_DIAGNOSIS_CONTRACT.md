# v17 Group-level Diagnosis — Step 1 output contract

> Current prompt: `v17-group-diagnosis-7`. The v3–v6 refinement sections below
> describe historical experiments, not cumulative requirements of the current
> prompt. Sample-specific instructions from those versions have been removed.

## Current general Diagnosis definition

The prompt now contains only the task, information boundary, dual-dimension
analysis, addressability/Parent-gap definitions, and output/reference contract.
It retains evidence-based empirical hypotheses, uncertainty, and the option to
produce no gap. It no longer contains flight-price, passenger-count, insurance,
keep-unchanged, splitting/transfer examples or a growing case-by-case repair list.
The response schema and deterministic validation remain unchanged.

Benchmark target scope is separate from the generic definition. The optional
`experiment_scope` keyword on request construction and model invocation defaults
to empty and is supplied by trusted experiment code, never inferred from model
output. It is stored in request.json and included in the actual system prompt's
SHA-256. `PROMPT_SHA256` identifies the generic base prompt; request-level
`prompt_sha256` identifies the exact dispatched prompt including scope.

The historical pilot script explicitly supplies its fixed multi-tool-call exclusion
through `PILOT_EXPERIMENT_SCOPE`. That exclusion is not a universal Diagnosis rule.
Formal benchmark policy cleanup remains a separate step. Standalone callers replaying
this historical pilot must pass that scope explicitly; generic calls do not silently
inherit benchmark-specific exclusions.

Historical results and their qualitative limitations are preserved. No new model
run is performed for this simplification. Prompt brevity and unit tests do not
establish improved semantic accuracy; that remains an empirical question.


Scope: output schema, structural validation, Step 2 reference indexing/resolution
and Step 3 fixed Diagnosis prompt plus Step 4 strict one-shot validation and
Step 5 audited model transport. Compiler and Editor remain out of scope.
v16 and benchmark definitions are unchanged.

## Output

```json
{
  "success_analysis": {
    "finding": "Observed condition–behavior–outcome comparison, or no supported issue.",
    "evidence_refs": [],
    "supervision_refs": [],
    "unresolved": ["Remaining uncertainty, if any."]
  },
  "compliance_analysis": {
    "finding": "Comparison against visible constraints, or no supported issue.",
    "evidence_refs": [],
    "supervision_refs": [],
    "unresolved": []
  },
  "skill_addressability": {
    "status": "NO_ISSUE",
    "reason": "No evidence-supported problem identified in this group."
  },
  "parent_skill_gaps": []
}
```

All shown fields are required and extra fields are rejected. `finding`, `reason`
and each list item must be nonblank strings. Analysis reference lists and the list
of unresolved questions can be empty. Findings can preserve positive, negative
and conflicting evidence in prose, without new status taxonomies. Uncertainty is
not converted to an asserted causal mechanism. Evidence and outcome supervision
have separate reference fields; no hidden policy is inferred from labels alone.

## Three states

| Status | Meaning | Gaps |
|---|---|---|
| NO_ISSUE | No repair issue observed in supervision or trajectories; all success/compliant labels must be true, with no other in-scope anomaly | Empty |
| NOT_ADDRESSABLE | A problem is observed, but evidence does not support a concrete Parent Skill modification | Empty |
| ADDRESSABLE | Evidence supports attempting a concrete Parent Skill modification | At least one |

Addressability is a hypothesis, not a guarantee of repair. A group can include both
addressable and non-addressable issues; only supported modifications receive gaps.
An already adequate Parent with no identifiable deficiency cannot be ADDRESSABLE.
Missing observations belong in `unresolved`, not fabricated issues. Compiler
promotion remains a later step; structural validity alone never authorizes edits.

## Each gap has exactly five fields

```json
{
  "kind": "NEEDS_REVISION",
  "gap": "The existing confirmation rule omits already-approved actions; narrow its scope.",
  "evidence_refs": ["T003/R009/R1/E0007"],
  "related_rule_refs": ["opaque-parent-rule-reference"],
  "source_dimensions": ["SUCCESS", "COMPLIANCE"]
}
```

- `kind`: MISSING or NEEDS_REVISION only.
- `gap`: concrete missing/incorrect guidance and relevant applicability conditions.
- `evidence_refs`: nonempty, independent binding for this gap to trajectory evidence.
- `related_rule_refs`: empty for MISSING, nonempty for NEEDS_REVISION.
- `source_dimensions`: SUCCESS, COMPLIANCE, or both; nonempty without duplicates.

All reference arrays reject duplicate entries. Different gaps may share evidence
when appropriate; each must explicitly bind it. No gap_id, per-gap supervision_refs,
mechanism_synthesis, ADD/REPLACE/DELETE, or final Skill text is requested. Policy
grounds may be discussed in the analyses; precise policy/rule indexing is Step 2.

## API and limits

`diagnosis_contract_v17.build_diagnosis_response_format()` returns a fresh strict
JSON-schema response format. The portable model schema specifies fields and enums;
`validate_diagnosis_output(output)` additionally checks nonblank strings,
uniqueness and state/gap/rule cardinality constraints. It returns None or raises
DiagnosisContractError, without mutating the output.

Step 1 intentionally treats references as opaque nonblank strings. It does not
yet check existence, current group ownership, Parent version, citation entailment,
policy grounding, or agreement between the analyses and gaps. Those belong to
subsequent reference resolution and validation. Do not feed merely structurally
valid output directly to an Editor. The input remains GroupDiagnosisInput; its
existing seals and source restrictions are unaffected by this output contract.

## Step 2: Evidence and Parent references

Newly assembled inputs use `group_diagnosis_input_v17.2` and add two catalogs:

- `available_policy_refs`: each nonblank visible-policy line, addressed as
  `POLICY/<context>/<full SHA-256>/L<line>`. The entry retains exact text including
  its original line ending, context and policy digest. Only this group's contexts
  are indexed. Headers may be addressed but are not automatically normative rules.
- `available_rule_refs`: Markdown instruction blocks addressed as
  `RULE/<full Parent SHA-256>/L<start>-<end>`. Entries preserve section, original
  line range and exact text. Blocks start at a bullet/numbered item or prose and
  continue until a blank line, heading or next item. This simple syntactic index
  is intended for the project's plain Markdown Skill text; it is not a full
  Markdown parser or semantic decomposition. Heading-only/empty Skills have no rules.

No whitespace normalization is used for hashes or excerpts. Even a whitespace-only
Parent change invalidates old rule IDs. References do not encode benchmark families
or hidden policy IDs. Existing trajectories and supervision keep their distinct
indexes; grouping explanations never enter any evidence index.

`resolve_reference(request, ref, reference_type=..., context_ref=..., quote=...)`
requires a signed GroupDiagnosisInput and checks that policy/rule catalogs still
match the exact input content. Supported types are TRAJECTORY, SUPERVISION,
VISIBLE_POLICY and PARENT_SKILL_RULE. It returns original event, supervision, policy
line or rule block plus provenance. An optional context must match; an optional
quote must be a nonblank exact substring of a policy/rule entry. This permits
checking cited original fragments without expanding the five-field gap schema.

`resolve_diagnosis_references(output, request=...)` first runs the Step 1 structural
validator, then resolves all explicit reference fields. Analyses' `evidence_refs`
may include trajectory and visible-policy IDs; `supervision_refs` accept only
supervision IDs. Gaps may include policy citations in `evidence_refs` but must
include at least one trajectory reference. `related_rule_refs` accept only current
Parent rule IDs. Unknown/out-of-group/stale/wrong-type references fail closed.

The five gap fields are unchanged. References in free-form prose are not parsed.
Context checks verify an explicitly supplied context, not whether a model has
semantically applied policy to the correct task. Citation existence and exact quote
matching do not establish entailment, causal correctness or policy applicability.
Cross-analysis gap consistency remains later validation work. Source capture and
round/task bindings retain the trust assumptions documented for Grouping.

Previously saved v17.1 payloads lack these catalogs and must be rebuilt through
the input assembler before resolution; historical pilot artifacts are not rewritten.

## Step 3: Fixed Diagnosis prompt

`diagnosis_prompt_v17` defines `v17-group-diagnosis-2` and its SHA-256 (Step 4 adds
explicit evidence-linkage requirements and no-repair instructions). It performs
one group-level reasoning sequence within a future single call: Success Analysis,
Compliance Analysis, then addressability and concrete Parent gaps. It does not
introduce mechanism synthesis, extra gap fields, edit operators or final Skill text.

The fixed instructions explicitly require original-event verification of Grouping
hints, within-group condition/behavior/outcome comparisons, counterexamples and
uncertainty, context-specific policy authority and separation of observed behavior
from normative guidance. Labels alone cannot identify hidden rules. Singleton and
mixed-context groups use the same protocol. No issue is required in either dimension;
NO_ISSUE/NOT_ADDRESSABLE produce no gaps, ADDRESSABLE produces supported concrete gaps.
Adequate Parent guidance must not be rewritten merely because execution failed.
Capability and compliance proposals must not conflict through weakened constraints
or unnecessary refusal/confirmation. Irresolvable changes remain unresolved.

`build_diagnosis_prompts(request)` verifies the signed learner payload and current
policy/rule catalogs, returning `(system_prompt, user_prompt)` with full lossless
learner input serialized as canonical JSON. Runtime provenance is not sent.
`build_diagnosis_request(request)` adds fixed prompt version/hash, input hash and
a fresh copy of the Step 1 response schema, for later transport and auditing.
No model or sampling configuration is selected at this stage; that is Step 5.

Tests verify repeatability, exact input preservation, group-local contexts, runtime
metadata exclusion, singleton protocol consistency and rejection of unsigned,
tampered or stale-catalog inputs. They verify assembly, not model compliance with
the prompt. Live diagnostic quality remains to be tested in Step 6.

## Step 4: Strict deterministic acceptance, no repair

`diagnosis_validation_v17.validate_diagnosis_response(raw, request=request)` is
the single acceptance entry point for future Diagnosis transport. It either returns
a signed `V17_VALIDATED_DIAGNOSIS` envelope or raises `DiagnosisRejected` with a
stable `stage` and descriptive `reason`.

Stages, evaluated in order:

1. PARSE: require JSON text, reject malformed JSON, duplicate keys at any depth,
   nonfinite constants, code fences, commentary and multiple JSON objects. Never
   extract JSON from prose or fix delimiters.
2. STRUCTURE: reuse the exact Step 1 schema and cardinality constraints. Never
   coerce enums/types, fill fields, deduplicate references or delete invalid gaps.
3. REFERENCES: reuse Step 2 typed resolution. Reject unknown, wrong-type,
   out-of-group or stale references and policy-only gaps; reject unsigned/tampered
   inputs and stale policy/rule catalogs. No approximate citation matching.
4. LINKAGE: all gap evidence must occur in the union of its declared source
   analyses' evidence lists. Each declared source dimension must share at least
   one trajectory reference with the gap. Policy overlap alone does not establish
   that a dimension supplied behavioral evidence.

One invalid gap rejects the entire group response. Errors are never silently
converted to NO_ISSUE, NOT_ADDRESSABLE or a reduced set of gaps. There is no
automatic retry, repair model call, fallback or semantic output normalization.
This supersedes the earlier planned Diagnosis format-repair attempt; the existing
Grouping repair policy is independent and unchanged. Step 5 Diagnosis transport
must persist the raw failure and stop that group's attempt rather than remediate it.

The success envelope stores the unmodified parsed semantics, exact raw response,
raw and signed-input payload SHA-256 digests, resolved citations and learner-inferred
origin. `validation_status=VALID` means contract/reference consistency, not a Gate
ACCEPT or permission to edit. A structurally valid NO_ISSUE/NOT_ADDRESSABLE response
is also VALID and carries no gaps.

Limits: no deterministic check can prove a finding, causal explanation, semantic
agreement with a status, quote in free-form prose, or claimed policy applicability.
Analysis supervision references are checked for existence and type, not inferred
association from prose. The unchanged minimal schema contains no per-claim policy
context/quote field; explicit context/quote checks remain available through the
Step 2 resolver. No heuristic text classifier is added to pretend these semantic
properties have been verified.

## Step 5: One-shot transport and audit artifacts

`diagnosis_v17.run_group_diagnosis(request, artifact_dir=...)` uses the configured
OpenAI-compatible endpoint, fixed model `deepseek-v4-pro`, temperature 0, reasoning
effort high and 16,000 completion tokens. SDK retries are explicitly disabled
(`max_retries=0`); timeout is 300 seconds. No fallback model or repair call exists.
The provider-reported model and response ID are saved without assuming the alias
pins a permanent backend model revision.

The output directory must not exist. Before dispatch the runner saves request.json
(prompt, schema, parameters, hashes), provenance.json, and RUNNING validation.json.
After response it preserves exact untrimmed content, finish reason, refusal, usage
and provider identity in response.json. Refusal or non-stop completion is rejected;
otherwise the Step 4 validator runs once. VALID results receive a
validated_diagnosis.json; rejected groups retain raw response and rejection stage
without a partial diagnosis. Transport errors record exception type/HTTP status
without dumping credentials or connection details. Usage is not converted to money.

Other independent groups may continue after one group's rejection. No failure
causes a reattempt. Tests cover the live-adapter SDK retry setting via a fake client,
fixed settings, exact response preservation, single-call rejection, audit persistence
and refusal to overwrite an existing directory.

## Step 6: Nine-group pilot entry point

`python scripts/run_v17_diagnosis_pilot.py` uses pilot_002's nine unchanged groups,
pilot_001's saved public contexts and v16 S0 rollout 1 records. It checks historical
file hashes, public-context hashes, exact card equality and anonymous-input equality
before calling Diagnosis. No Agent or Grouping is rerun. Public contexts are replayed
from the saved artifact rather than reconstructed from current canonical policy.

All requests are built and measured before dispatch; three independent groups may
run concurrently, each with exactly one attempt. Output defaults to
`experiments/v17_diagnosis_pilot_001/`, with preflight.json, group-specific audit
directories, incremental progress.json and final summary.json. Rejected groups are
reported, not repaired. A fresh run directory is required for another experiment.

### Completed pilot analysis

The nine completed responses were aggregated and revalidated offline in
[analysis_001](../experiments/v17_diagnosis_analysis_001/report.md). All nine
passed the current contract and reference checks: six ADDRESSABLE (six MISSING
gaps), two NOT_ADDRESSABLE, one NO_ISSUE. Exact selected artifact paths and
SHA-256 hashes are in selected_results.json alongside that report. Requests match
the original pilot_002 requests; no new model calls or response repair occurred.

Semantic assessment is separate from VALID: G9 infers an unsupported update from
a failed keep-unchanged task; G2/G5 duplicate a visible-policy concern despite
positive compliance labels; G6/G7 identify issues without establishing sufficient
repairs. These are analysis findings, not rewritten diagnoses or Gate decisions.
No Compiler/Editor or Monitor improvement has yet been demonstrated.

## Pilot-driven refinement: prompt v17-group-diagnosis-3

The current pilot excludes the legacy tau multi-tool-call rule from Compliance
and Skill optimization. Historical policy text remains intact for source fidelity;
the fixed prompt explicitly excludes this rule, not other independently supported
violations. G2/G5's serialization gaps are invalid under this target scope. Formal
v17 experiments must actually remove the rule from benchmark policy before generating
fresh rollouts. This change does not modify v16, benchmark files, or saved rollouts.

NO_ISSUE means no observed repair issue. Any supplied success=false or
compliant=false rules it out, even if the diagnosis omits that supervision citation.
Unknown causes with no reliable Skill gap belong to NOT_ADDRESSABLE; ADDRESSABLE
requires observed trouble, supported Agent behavior, and a concrete Parent gap.
The validator rejects a NO_ISSUE/negative-label conflict at LINKAGE without repair;
validated output version is now validated_diagnosis_v17.2. Positive labels do not
prove the absence of an anomaly, which remains a semantic judgment.

The prompt forbids deriving hidden required actions from failure labels or reversing
conditional policy prerequisites into obligations to act. Gaps must address a
supported decision deficiency; pausing under uncertainty and post-action disclosure
must not be presented as automatically fixing the original decision. Independently
supported disclosure problems may still justify their own bounded gap.

Policy-dependent analyses and gaps must include applicable POLICY IDs in existing
structured evidence_refs. No new output fields are added. Existing typed-reference
and source-analysis linkage checks verify submitted citations. They cannot establish
that a policy applies or detect all omitted policy citations in prose. The same
limitation applies to semantically excluding the legacy rule: no keyword classifier
is presented as proof of compliance with this prompt instruction.

The nine old responses were generated with prompt v17-group-diagnosis-2. Their
historical VALID results are preserved, not relabeled as results of the new prompt
or validator. See the updated pilot report for separate offline assessments. No
real model run of prompt version 3 has been performed in this refinement.

## Empirical inference refinement: prompt v17-group-diagnosis-4

No schema, model transport, validation stage or additional Diagnosis layer changes.
The fixed prompt adds three semantic requirements:

1. Empirical induction is allowed from group-local conditions, behavior, tool results
   and supervision even when policy does not state the inferred pattern. Findings
   and dependent gaps must identify it as a candidate empirical hypothesis, with
   observed scope, counterexamples and unknowns. It is not policy or hidden truth.
   Labels alone do not establish a cause, exact threshold or required action.
2. Each gap's evidence_refs must cover its key conditioning facts, relevant behavior
   and result. A channel-based rule needs the channel observation as well as pricing
   and settlement evidence. Missing support requires narrowing or withholding the
   gap, not inventing references. Prior results can inform future decisions without
   requiring a current irreversible action to learn its own prerequisites.
3. source_dimensions includes only dimensions whose analysis actually supports that
   specific gap. Shared references, possible effects, negative labels or unresolved
   concerns alone do not justify a dimension. BOTH requires support from each analysis.

Existing deterministic validation checks reference identity and analysis linkage;
it does not prove completeness of key-condition evidence, semantic support or
causal correctness. These prompt requirements are not new programmatic guarantees.
No keyword heuristic or additional semantic judge is introduced. Historical pilot
outputs remain unchanged; prompt version 4 has not been run on the model here.

## Analysis-to-gap consistency: prompt v17-group-diagnosis-5

Preserves the v4 protocol and adds one semantic constraint: a gap cannot turn facts
left uncertain in finding/unresolved into definite action requirements. A candidate
label is not a substitute for evidence. Observed repricing alone does not establish
a current-search-price formula; a candidate passenger limit alone does not justify
splitting, refusing or transferring.

Actionable empirical hypotheses remain allowed. Uncertainty about generalization
beyond observed conditions differs from a missing premise for the proposed action
within those conditions. Preserve the former as a bounded candidate; narrow or
withhold guidance that depends on the latter. Do not erase unresolved evidence gaps
or replace them with unsupported generic stopping/confirmation/transfer guidance.
If no supported modification remains, no gap is emitted for that issue; other
independently supported issues can still make the group ADDRESSABLE.

No schema, validator, model settings or extra Diagnosis layer changes. Existing
validation does not prove this semantic consistency. Historical outputs remain
unchanged, and no model run of v5 was performed as part of this prompt update.

## Scope preservation: prompt v17-group-diagnosis-6

One small addition to v5: each gap must explicitly preserve its finding's
applicability conditions and exceptions. A restriction on one decision branch
must not become a global restriction. For example, unverified insurance coverage
restricts insurance-dependent cancellation when no other cancellation ground is
established; it does not prohibit cancellation on an independently satisfied ground.

No G6-specific reading rule, new schema field, validation layer or model setting
is added. No Diagnosis rerun is required for this refinement; implementation can
proceed to Compiler. Historical v5 outputs remain v5 outputs, including their known
limitations, and must not be relabeled as v6 or treated as semantically repaired.
This update is a prompt requirement, not a deterministic semantic guarantee.

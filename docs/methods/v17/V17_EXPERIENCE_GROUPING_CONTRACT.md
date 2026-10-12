# v17 Experience Grouping — Step 1 contract

Status: Steps 1–4 (contracts, lossless cards, global LLM Grouper and group-local
Diagnosis input assembly) are implemented; Step 5's first live grouping pilot is
complete. v16 and the benchmark are unchanged.
The new Diagnosis model/prompt/output contract and v17 benchmark runner are not
implemented yet.

## Runtime scope (not Grouper input)

`GroupingScope(round_id, parent_skill_digest, experiences)` is constructed by the
trusted runtime from the current round's Evolution allowlist. Each
`EvolutionExperienceRef` binds an opaque `task_ref`, `context_ref`, and
`trajectory_ref`. There is exactly one selected rollout per task in this version.
Round identity must be unique within the stored run (or run-qualified).
The runtime must load only current-Parent experiences and never Monitor records.
Identifiers must not encode private benchmark families or expected actions.

## Grouper input

The exact top-level fields are `contexts` and `cards`.

Each context contains exactly:

- `context_ref`: nonempty opaque alias.
- `visible_policy`: deployed Agent-visible policy text.
- `public_tools`: public function schemas (`type`, `function` with `name`,
  `description`, `parameters`, optional boolean `strict`). May be empty.

Each card contains exactly:

- `task_ref`, `context_ref`, `trajectory_ref`: references matching runtime scope.
- `events`: nonempty ordered observed events, with original positive increasing
  `step` numbers. Gaps are allowed; steps must not be renumbered after selection.

Events have `step`, `event_type`, `actor` and:

- message: `content`, actor user/assistant;
- tool_call: `tool_name`, object `arguments`, actor assistant;
- tool_result: `tool_name`, `content`, actor tool.

All content must be finite JSON data. Goals, constraints, visible states and
authorization expressions remain in observed content, without pre-diagnosis.
An event is addressable by `(trajectory_ref, step)`; tool calls and results retain
their original ordering. Card extraction/completeness is the Step 2 responsibility.

All tasks must appear exactly once; contexts must exactly cover their references.
Structured outcome supervision, family labels, hidden mappings, expected actions,
oracle paths, evaluator internals and Monitor metadata are not accepted fields.
Observed tool data may legitimately contain names such as `success`; recursively
blacklisting such keys would destroy real observations and is intentionally avoided.

## Grouper output

```json
{
  "groups": [
    {
      "group_id": "G01",
      "decision_problem": "When does the observed user expression authorize a change?",
      "members": ["T001", "T002"],
      "shared_basis": "Both experiences include user expressions followed by a write action.",
      "important_differences": ["Whether a specific proposal was approved."]
    }
  ]
}
```

These are exact fields. Groups and members must be nonempty; identifiers are unique;
membership is a complete exclusive partition of this round's input tasks. Singleton
groups are allowed, with an empty `important_differences` list if appropriate.
There is no fixed group count, taxonomy or family requirement. Cross-context groups
are permitted, but each member retains its own policy/tool context.

The semantic grouping criterion is a shared decision problem with observable
grounds for comparison, not merely shared business/tool names or outcomes.
Explanations are learner-inferred grouping hypotheses, not observed evidence,
diagnoses, or repair instructions. Structural validation cannot prove semantic
group quality or detect a diagnosis concealed inside an explanation.

## Validation and provenance

`validate_grouping_input(payload, scope=...)` and
`validate_grouping_output(output, task_refs=...)` raise `GroupingContractError` on
failure and return None on success. `bind_grouping_result` runs both, deep-copies
the result and attaches schema version, runtime round/Parent identity, experience
bindings and `origin=LEARNER_INFERRED_GROUPING`. Group IDs are local to that round.
The model cannot provide or override this runtime envelope.

These are structural/provenance checks, not a security sanitizer or authenticated
capture layer. A caller forging the trusted manifest or placing privileged prose
inside observed content cannot be detected here. The future runtime/card builder
must project from trusted learner-safe capture, not arbitrary benchmark task specs.
It must preserve actual content and load context from the deployed Agent. The
Parent digest records provenance; the contract does not verify Skill bytes itself.

Outcome labels remain outside Grouper input and are joined from trusted records
only when constructing the later Group-level Diagnosis request. This step does
not implement that join.

## Verification

Run `python -m pytest -q tests/skill_evolution/v17/test_experience_grouping_contract_v17.py`.
Tests cover valid grouped/singleton/cross-context inputs, runtime binding, unknown
or duplicated references, incomplete partitions, malformed events and prohibited
metadata at structured boundaries. No model call or benchmark execution is needed.

## Step 2: Experience Card construction

`experience_cards_v17.build_experience_cards(sources, scope=...)` accepts a tuple
of `CapturedGroupingExperience` records. Each carries the trusted runtime round,
Parent digest and experience reference, an `AGENT_VISIBLE_VIEW` envelope and one
`TRAJECTORY_DERIVED` envelope from the existing capture boundary. It does not use
the v15 three-rollout Diagnosis request. Unsigned dictionaries, changed signatures,
wrong envelope kinds, stale round/Parent bindings and unmatched contexts fail.

The runtime must supply truthful identity bindings: existing capture envelopes
authenticate their content but do not encode task, round or Parent identity.
This builder cannot detect a trusted caller deliberately mislabelling an envelope.
The existing v15 capture supports airline/retail; adding another benchmark capture
adapter remains future work, not part of this card construction step.

Construction is deterministic in manifest order:

1. Require exactly one selected captured source per Evolution task.
2. Verify the trajectory digest matches its signed visible context.
3. Copy complete observed events, preserving step numbers, content, parameters,
   tool results, repetitions and final messages. No summarization or truncation.
4. Share contexts with the same context_ref only when policy/tools are identical.
5. Exclude supervision, domain metadata, Parent text and source wrappers from
   Grouper input. Real tool result fields named `success` remain intact.
6. Validate against the Step 1 input contract and serialize as compact Unicode JSON.

The returned `ExperienceCardBatch` exposes immutable `input_json`, a fresh decoded
`payload` property, and runtime-only `statistics`. Only the input JSON/payload is
for Grouper consumption; statistics and runtime provenance are not input fields.

```python
batch = build_experience_cards(
    captured_sources,
    scope=scope,
    token_counter=count_tokens_for_selected_model,
    max_input_tokens=available_payload_tokens,
)
grouping_payload = batch.payload
runtime_metrics = batch.statistics
```

Statistics include task/context/event counts, serialized characters, UTF-8 bytes,
per-card character/event counts and optional exact tokenizer counts. There is no
character-to-token heuristic. Optional `max_input_chars` / `max_input_tokens`
limits reject overflow with `ExperienceCardBudgetError.statistics`; no partial
batch is returned. A token limit requires an explicit counter. Limits apply only
to payload; callers must reserve headroom for prompts, schemas and model output.

Verification: the two v17 test files pass 78 tests. A read-only local replay of
the existing v16 Evolution results, choosing rollout index 1 uniformly for all
32 tasks, produced 32 cards, 2 shared contexts and 619 events. Every card event
list matched its captured safe trajectory exactly. Compact input measured 269,005
characters / 269,900 UTF-8 bytes; token count was not measured. Replay reconstructed
the current deployed public contexts, so it is a compatibility check, not proof
that historical contexts cannot have drifted. No new rollout or model call ran,
and no v16 experiment artifacts were rewritten.

## Step 3: Fixed global Grouper

`experience_grouping_v17.prepare_grouping_request(batch, scope=...)` validates
the card batch, canonicalizes source references, and applies a local permutation
with fixed alias seed **200**. Task, context and trajectory references receive
anonymous T/C/R aliases. Cards/contexts are presented in alias order. No module-global
random state, wall clock or round number influences the permutation. Reordering
the incoming cards or manifest therefore produces the same request. With the same
reference sets the mapping stays fixed across rounds; changing reference sets may
change it. Source references must remain opaque as required by Step 1.

Observed text, public tool names and event content are not rewritten. This is
reference anonymization to reduce ordering/identifier bias, not anonymization of
all entities mentioned in an observation, and it does not eliminate position bias.

The fixed protocol uses:

- model `openai/deepseek-v4-pro` (the existing campaign's model);
- temperature `0.0`;
- prompt version `v17-grouping-2`, with the system prompt SHA-256 recorded
  (pilot_001 preserves the original `v17-grouping-1` request);
- strict JSON response schema, with task aliases enumerated in member values;
- completion budget 16,000 tokens.

The alias seed controls local input permutation, not model sampling. The existing
`call_learner` transport supplies configured credentials/base URL and its existing
reasoning setting. No alternative model or temperature fallback is selected.
Fixed settings do not guarantee bit-identical remote model output or a permanently
pinned provider model revision. Actual resolved model and usage are recorded.

```python
from pathlib import Path
from src.skill_evolution.v17.experience_grouping_v17 import run_experience_grouping

result = run_experience_grouping(
    batch,
    scope=scope,
    artifact_dir=Path("artifacts/methods/v17/round_001/grouping"),
)
```

The artifact directory must not already exist. One normal global call is made.
Malformed JSON or invalid partitions allow exactly one repair call using the same
anonymous cards, same model, same schema, same temperature and fixed repair
instruction. A second invalid response fails without a fallback partition.
Transport errors fail immediately at this layer (the shared provider SDK may
perform its own transport retries). API/provider errors are not turned into
semantic repair requests. Unknown, repeated or missing members, duplicate JSON
keys, nonfinite JSON values and unexpected output fields are rejected.

Artifacts:

- `grouping_request.json`: fixed protocol, anonymous prompt, schema and local
  alias-to-source map. Only prompt/schema fields are sent to the model.
- `runtime_scope.json`: trusted round, Parent and experience bindings.
- `grouping_attempts.json`: actual user prompt for each attempt, raw response,
  validation status, usage and elapsed seconds; written before remote dispatch
  and updated after completion/failure. Usage is recorded, not inferred currency cost.
- `anonymous_groups.json`: validated model output in its original alias namespace.
- `validated_groups.json`: runtime-bound result with members restored to source
  task references. Explanatory prose is kept verbatim; its alias references remain
  resolvable through the attached map, without unreliable text replacement.

The Grouper uses all cards, does not choose minibatches or truncate input, and
does not assemble the later Diagnosis request. Before a live run, the caller must
check the selected endpoint's context budget including prompt/schema/repair/output
headroom; Step 2 payload statistics alone are not the complete request budget.

Offline tests inject the same transport signature to verify fixed settings,
order invariance, exact event preservation, reverse mapping, bounded repairs,
failure artifacts and model drift rejection. These tests do not establish live
group quality; a real benchmark grouping trial remains Step 5.

## Step 4: Group-level Diagnosis input assembly

`group_diagnosis_input_v17.build_group_diagnosis_inputs` receives the original
captured sources, current runtime scope, bound grouping result and exact Parent
Skill text. It returns one `GroupDiagnosisInput` per group, including singletons.
It performs no model call, diagnosis, compiler decision or Skill edit.

```python
from src.skill_evolution.v17.group_diagnosis_input_v17 import build_group_diagnosis_inputs

requests = build_group_diagnosis_inputs(
    captured_sources,
    scope=scope,
    grouping_result=result,
    parent_skill=parent_text,
)
for request in requests:
    learner_input = request.learner_payload
    runtime_provenance = request.provenance
```

Validation happens before returning requests:

- Rebuild cards from signed captures, enforcing the current Evolution allowlist,
  round, Parent and context bindings.
- Require SHA-256 of the exact UTF-8 Parent text to match the scope digest. No
  whitespace/newline normalization; empty text is supported if its digest matches.
- Revalidate the entire exclusive partition, result version/origin and saved
  experience references. Reordering input sources is harmless; result bindings
  must match the manifest that produced them.
- Verify any saved Grouper alias map equals the fixed protocol's expected map.
- Require supervision to contain exactly boolean `success` / `compliant`, integer
  level 0 and the learner-safe provenance marker. No evaluator explanations pass.

Each model-facing payload includes:

- `grouping_hint`: group fields with the original Grouper alias namespace and
  explicit learner-inferred origin; `grouping_hint_authority` marks it as a hint,
  not evidence or policy.
- `current_skill`: the verified Parent text.
- `contexts`: only the group's public policy/tool contexts; cross-context tasks
  keep their own context references.
- `experiences`: complete observed events, task/trajectory aliases, captured
  rollout index and Level-0 supervision.
- `available_evidence_refs` / `available_supervision_refs`: group-local lookup
  maps. An event reference such as `T003/R009/R1/E0007` identifies task, trajectory,
  rollout and original step; `T003/R009/R1/S` identifies its supervision.

No Grouping explanation is inserted into the event/evidence index. Event content
is unchanged; only `evidence_ref` is added. Evidence references are unique across
groups within a round; resolving across rounds also requires runtime round identity.

`learner_payload` verifies a signed `V17_GROUP_DIAGNOSIS_INPUT` envelope and returns
a fresh decoded value. Runtime provenance separately records round, Parent digest,
group and this group's source-to-presented bindings. The global alias map, other
groups' trajectories/contexts and Monitor records are not copied into the request.
For a Step 1 result without aliases, opaque source references are used directly.

As in preceding steps, the trusted runtime must supply truthful identity bindings.
Validation cannot authenticate a forged bound-result dictionary or detect hidden
information embedded in natural-language prose. Grouping explanations are kept
verbatim and may mention another alias, but no corresponding out-of-group data is
loaded. Existing capture seals are process-local: persisted experiment files must
be replayed through trusted capture before constructing new requests.

Tests cover complete event preservation, mixed-policy groups, singleton shape,
both outcome labels, local evidence resolution, alias continuity, no out-of-group
contexts, stale result/Parent rejection, bad partitions, Monitor source rejection,
unexpected supervision fields and envelope tampering.

## Step 5: First live pilot

`scripts/runs/v17/run_v17_grouping_pilot.py` replays rollout index 1 (seed 200) for all 32
existing v16 S0 Evolution tasks, with no outcome-based selection and no new Agent
rollouts. The pilot records current empty-Parent and raw trajectory hashes, rebuilds
public contexts, and makes one real fixed-protocol Grouper call. Independent
historical context identity cannot be proven from the available records.

Artifacts: `artifacts/methods/v17/pilot/v17_grouping_pilot_001/`. The first response passed without
repair: 7 groups of sizes 4/4/8/4/7/4/1 and 7 assembled Diagnosis requests. No
Diagnosis model was called. Provider usage: 77,850 prompt tokens, 11,488 completion
tokens (including 9,101 reasoning), 181.28 seconds. The pilot report identifies
useful condition comparisons and two broad groups; no Skill benefit is claimed.

Read `artifacts/methods/v17/pilot/v17_grouping_pilot_001/REPORT.md` before deciding whether to
revise the prompt. A new script execution requires a fresh output directory and
incurs another model call; existing artifacts suffice for inspecting this run.

### Prompt refinement trial

`artifacts/methods/v17/pilot/v17_grouping_pilot_002/` reuses the exact saved pilot_001 cards and
anonymous input, changing only the system prompt to v17-grouping-2. The refinement
focuses groups on a primary decision problem and limits differences to decision-
relevant conditions, while preserving interacting conditions. One call, no repair:
9 groups (4/4/5/3/4/4/3/4/1). The two broad groups split; other memberships remain
unchanged. See its REPORT.md for comparison and two verified factual errors in
generated explanations. Grouping hints remain hypotheses, never source evidence.

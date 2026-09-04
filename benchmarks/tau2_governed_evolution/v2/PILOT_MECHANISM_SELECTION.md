# τ² Governed Evolution Benchmark v2 — Minimal Pilot Mechanism Selection

## 1. Status and authority

This document freezes the Step 2 mechanism portfolio for the 24–32 task Structural Pilot. It is subordinate to [`STRUCTURAL_PILOT_CONTRACT.md`](./STRUCTURAL_PILOT_CONTRACT.md). In particular, the selection is governed by:

- Minimal Structural Upgrade;
- Natural Workflow First;
- Structural Hypothesis Before Scale;
- No Outcome-based Benchmark Selection.

The selected mechanisms are Pilot analysis units grounded in existing Airline Policy rules and Policy Concepts. They are not a new mechanism registry, taxonomy, task population, or claim that the mechanisms will necessarily pass calibration. Step 2 selects the smallest credible portfolio with which H1, H2, and H3 can be tested; Base and Reference-Skill Structural Calibration must still determine whether the hypotheses are `SUPPORTED`, `MIXED`, or `NOT_SUPPORTED`.

This Step creates no task, latent world, split, generator, evaluator, Oracle, rollout, or executable benchmark change.

## 2. Repository-grounded selection method

The inventory was derived from the canonical rules in `registry/airline_policy_registry.yaml`, their assignments in `concepts/airline_policy_concepts.yaml`, the available boundary templates, the v1 compiler/materializers, deterministic compliance handlers, composition support, and the τ² Airline tools and database schema.

The repository currently has end-to-end boundary, realization, compiler, and deterministic-Oracle support for six atomic templates:

- `airline.user_mandate.checked_baggage`;
- `airline.state_gate.flight_change_cabin`;
- `airline.mutation_guard.itinerary_identity`;
- `airline.process.explicit_confirmation`;
- `airline.process.cancellation_reason`;
- `airline.ordering.delayed_flight_compensation`.

It also has one implemented composition, `airline.composition.booking_baggage_confirmation`.

This implementation inventory is a cost and auditability constraint, not an automatic selection list. Conversely, a canonical rule is not treated as implemented merely because it is marked `boundary_constructible: true`. For example, `airline.book.baggage_allowance` is canonical and constructible, but has no current boundary template, compiler materializer, or compliance handler. That exact delta is included below.

The `pilot_candidate` fields in the existing concept catalog are inventory metadata, not a v2 Step 2 veto. The Step 1 Contract is authoritative for this Pilot, and requires a portfolio capable of testing the structural problems observed after v1.

## 3. Frozen Pilot portfolio

### 3.1 Atomic Core

| Core | Pilot mechanism | Canonical rule | Policy Concept | Primary structural role |
|---|---|---|---|---|
| A | State-gated flight-change permission | `airline.modify.basic_economy_flight_change` | `airline.state_gated_permission` | H1 state-dependent permission; H2 recoverable alternative resolution |
| B | State-derived checked-baggage allowance | `airline.book.baggage_allowance` | `airline.quantitative_policy_constraints` | H1 quantitative derivation; strong H2 state-controlled success difficulty |
| C | Primary-before-remedy delayed compensation | `airline.compensation.delayed_flight_sequence` | `airline.policy_scoped_remedy` | H1 temporal dependency; strong H2 multi-step completion |

These cores deliberately require three different decision procedures:

1. A evaluates whether a technically callable mutation is policy-permitted from reservation state.
2. B derives a quantity and fee from membership, cabin, passenger count, and requested bags.
3. C enforces a causal order across a primary transaction and a downstream remedy.

A Reference Skill scoped to one procedure should not contain the operative rule for the other two. Positive transfer such as better state inspection is allowed, but one local rule should not exhaust all three sources of headroom.

### 3.2 Natural 2-way interactions

| Interaction | Participating mechanisms | Shared workflow locus | H3 distinction |
|---|---|---|---|
| I1 | State-derived baggage allowance × explicit confirmation | Final booking calculation, disclosure, authorization, and commit | A computed payload must be correct and the user's confirmation must bind the final computed payload; recalculation invalidates earlier assent |
| I2 | Cancellation reason prerequisite × delayed-compensation ordering | Delayed-flight cancellation followed by downstream compensation | The workflow becomes an ordered chain: obtain reason → successfully cancel → offer/issue the certificate |

I1 is a calculation-to-commit dependency. I2 is a prerequisite-to-primary-to-remedy dependency. They are not two surface forms of “the user wants an action but policy says no.”

### 3.3 Preservation and boundary controls

The following are control factors, not additional Atomic Core mechanisms:

- `airline.action.explicit_confirmation` / `airline.transaction_commit_confirmation`: atomic baseline for I1 and payload-binding preservation.
- `airline.cancel.reason_required` / `airline.operation_input_completeness`: atomic baseline for I2, with reason-known and reason-pending sides.
- `airline.modify.itinerary_invariants` / `airline.mutation_invariant_guard`: same-route and full-chain preservation control for Core A's recovery worlds.
- `airline.book.no_unrequested_baggage` / `airline.explicit_user_mandate`: held satisfied in Core B and I1 so user mandate is not confused with allowance arithmetic.
- `airline.cancel.eligibility`, `airline.compensation.user_requested`, `airline.compensation.eligibility`, and `airline.compensation.fact_verification`: held satisfied in I2 so the tested dependency is reason acquisition plus primary/remedy order.
- The existing Checked Baggage × Explicit Confirmation fixtures and composite regression remain an infrastructure-level positive control. They are not a third selected v2 interaction and do not justify new Pilot tasks by themselves.

Controls are selected from their semantics and causal role. Historical ease or failure frequency does not determine a control role.

## 4. Candidate inventory and selection matrix

### 4.1 Rating legend

- `HIGH`, `MEDIUM`, `LOW`: structural strength or degree of reuse.
- Oracle: `YES` means a deterministic handler exists for the relevant canonical behavior; `PARTIAL` means only a narrower member or adjacent behavior is covered; `NO` means a new rule-scoped deterministic handler would be required.
- Construction cost refers to narrow Pilot construction, not a general framework.

### 4.2 Matrix

| Candidate mechanism | Policy grounding | Natural workflow | Boundary constructibility | H1 independence potential | H2 success-side controllability | H3 interaction potential | Existing infrastructure reuse | Existing Oracle / Oracle cost | Task construction cost | Preservation value | Main risk | Pilot recommendation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Checked Baggage Mandate (`airline.book.no_unrequested_baggage`) | HIGH | HIGH | HIGH | MEDIUM | LOW | HIGH | HIGH | YES / LOW | LOW | HIGH | Repeats an already implemented user-mandate decision and supplies little new breadth | Preservation / interaction regression control |
| Baggage Add-only (`airline.modify.baggage_add_only`) | HIGH | HIGH | HIGH | MEDIUM | MEDIUM | HIGH | MEDIUM; tool and boundary template exist | NO / LOW; structured pre/post count | MEDIUM | HIGH | May collapse into the already represented mutation-invariant skill; weaker H2 than Core B | Reject from main portfolio; reserve fallback |
| State-derived Baggage Allowance (`airline.book.baggage_allowance`) | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | MEDIUM; DB, booking tool, payment and baggage fields exist | NO / MEDIUM; deterministic state-and-payload calculation | MEDIUM | MEDIUM | Must keep arithmetic audit narrow and avoid a free-form pricing judge | **Atomic Core B** |
| Basic-economy Flight-change Permission (`airline.modify.basic_economy_flight_change`) | HIGH | HIGH | HIGH | HIGH | HIGH with a separate availability factor | HIGH | HIGH | YES / LOW | LOW for atomic; MEDIUM for recovery families | HIGH | Flight availability could confound governance unless held separately | **Atomic Core A** |
| Cabin-unflown Restriction (`airline.modify.cabin_unflown`) | HIGH | HIGH | HIGH | MEDIUM | MEDIUM | MEDIUM | MEDIUM; state and update tool exist | NO / MEDIUM | MEDIUM | HIGH | Same state-gated procedure and modification locus as Core A | Reject: H1 redundancy |
| Cabin Price Settlement (`airline.modify.cabin_price_settlement`) | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | MEDIUM; tool partly performs settlement | NO / HIGH | MEDIUM–HIGH | MEDIUM | Tool behavior and price reconstruction may dominate the learnable decision; verbal settlement adds semantic audit cost | Reject: excessive causal/Oracle cost for this Pilot |
| Itinerary Identity Preservation (`airline.modify.itinerary_invariants`) | HIGH | HIGH | HIGH | MEDIUM | LOW–MEDIUM | HIGH | HIGH | YES / LOW | LOW | HIGH | Mostly a preservation comparison here; as a core it overlaps existing mutation-invariant structure | Preservation / Core A control |
| Cancellation Eligibility (`airline.cancel.eligibility`) | HIGH | HIGH | HIGH | MEDIUM | MEDIUM | HIGH | MEDIUM; DB state and cancel tool exist | NO / MEDIUM | MEDIUM–HIGH | HIGH | Multi-branch OR predicate overlaps Core A's state-gated procedure and introduces clock/reason confounds | Reject from core; reserve interaction fallback |
| Cancellation Reason (`airline.cancel.reason_required`) | HIGH | HIGH | HIGH | HIGH | MEDIUM | HIGH | HIGH | YES / LOW | LOW | HIGH | Missing reason is conversational unless paired with a concrete workflow; not a strong standalone H2 state factor | **I2 factor and atomic baseline** |
| Flown-segment Escalation (`airline.cancel.flown_segment_transfer`) | HIGH | HIGH | HIGH | HIGH | LOW | MEDIUM | MEDIUM; status and transfer tool exist | NO / MEDIUM | MEDIUM | MEDIUM | Active side changes success into escalation and risks attribution to transfer semantics | Reject; possible future Attribution Stress/Control Set |
| Compensation Eligibility (`airline.compensation.eligibility`) | HIGH | HIGH | HIGH | MEDIUM | MEDIUM | HIGH | MEDIUM; profile/reservation fields and certificate tool exist | NO / MEDIUM | MEDIUM | HIGH | Another state-gated OR predicate; interaction can reduce to the same permission distinction as Core A | Reject from limited portfolio; reserve fallback |
| Delayed Compensation Ordering (`airline.compensation.delayed_flight_sequence`) | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | YES / LOW | LOW–MEDIUM | HIGH | Must hold all other cancellation and compensation gates satisfied | **Atomic Core C** |
| Compensation User-requested (`airline.compensation.user_requested`) | HIGH | HIGH | HIGH | MEDIUM | LOW | HIGH | LOW–MEDIUM; boundary description exists but no executable template | NO / MEDIUM; verbal offer/request evidence | MEDIUM | HIGH | Same explicit-mandate procedure as checked baggage and weak independent H2 | Reject: concept redundancy |
| Compensation Fact Verification (`airline.compensation.fact_verification`) | HIGH | HIGH | HIGH | HIGH | MEDIUM | HIGH | MEDIUM; facts are tool-visible | NO / HIGH | MEDIUM | HIGH | Auditing whether every conclusion was evidence-grounded risks a broad semantic/provenance judge | Reject: excessive Oracle scope |
| Explicit Confirmation (`airline.action.explicit_confirmation`) | HIGH | HIGH | HIGH | HIGH | LOW | HIGH | HIGH for booking | YES for booking / LOW | LOW for booking | HIGH | A broad confirmation rule can transfer widely and is not itself a new success-side structure | **I1 factor and atomic baseline** |
| Required Information / Identifier Completion (`airline.book.required_information`, `airline.modify.identifiers`, `airline.cancel.identifiers`) | HIGH | HIGH | HIGH | MEDIUM | MEDIUM | MEDIUM | PARTIAL; schemas and lookup tools exist, only cancellation reason has a dedicated handler | PARTIAL / MEDIUM–HIGH | HIGH | HIGH | A broad missing-field bundle can collapse into “ask for required information” and obscure which prerequisite is learned | Reject: too broad for minimal Pilot |

## 5. Atomic Core specifications

### 5.1 Atomic Core A — State-gated flight-change permission

- **Canonical rule:** `airline.modify.basic_economy_flight_change` — flights in a basic-economy reservation cannot be changed.
- **Policy Concept:** `airline.state_gated_permission`.
- **Existing boundary template:** `airline.state_gate.flight_change_cabin`.
- **Workflow:** inspect the existing reservation, determine whether its cabin permits flight modification, search for a valid replacement when permitted, and update only a policy-valid itinerary.
- **H1 role:** represents a state-derived authorization gate. A mechanism-scoped Reference Skill must name the reservation cabin predicate and distinguish tool callability from policy permission. It does not teach baggage allowance arithmetic or downstream compensation order.
- **H2 role:** supplies a recoverable flight-selection challenge while the governance predicate is held on the allowed side.
- **Success-side controllability:** flight availability, seat availability, same-route alternative availability, and payment feasibility are concrete τ² state. They must be recorded separately from the cabin permission predicate.
- **Existing infrastructure:** reservation and flight state, direct/one-stop search tools, `update_reservation_flights`, boundary/realization/compiler support, deterministic compliance handler, and v1 Task Success path.
- **Minimal future infrastructure:** additional family-specific state fixtures and metadata distinguishing requested option, valid alternatives, and the frozen expected successful resolution. No new general evaluator or search framework is required.
- **Why selected:** it is the cleanest currently implemented policy-permission boundary and anchors H1 without requiring new Oracle semantics.
- **Main risk:** an unavailable requested flight could be mistaken for a policy block. Construction must hold cabin permission allowed in H2 comparisons and record availability as a Success-side factor.

Reference-Skill locality expectation:

> A minimal Ref-A teaches “read the existing cabin and block flight modification for basic economy before calling `update_reservation_flights`.” It should improve A preferentially, but contains no baggage table and no compensation sequencing instruction.

### 5.2 Atomic Core B — State-derived checked-baggage allowance

- **Canonical rule:** `airline.book.baggage_allowance` — free bags per passenger depend on membership and cabin; each bag above the total allowance costs $50.
- **Policy Concept:** `airline.quantitative_policy_constraints`.
- **Workflow:** during booking, retrieve membership, combine it with cabin and passenger count, derive total free allowance, calculate nonfree bags and fee, include them in the final price, and submit the matching booking payload.
- **H1 role:** introduces a state-derived quantitative calculation, not another Boolean permission, user-mandate check, or temporal gate.
- **H2 role:** this is the strongest explicitly state-controlled success challenge in the portfolio. The same user goal can be easy or require a multi-input allowance and payment calculation while retaining a valid completion path.
- **Success-side controllability:** membership, cabin, passenger count, requested checked-bag count, fare, and saved-payment feasibility are structured and tool-visible.
- **Existing infrastructure:** user membership, reservation/booking cabin, passenger list, `total_baggages`, `nonfree_baggages`, $50 tool-side fee calculation, saved payments, `calculate`, and native DB action comparison.
- **Minimal future infrastructure:** one narrow boundary template/materializer and one deterministic rule-scoped compliance handler. The handler should derive the expected allowance from structured state and compare concrete quoted/submitted bag count, nonfree count, and fee. If natural-language amount detection cannot remain task-amount-aware and deterministic, the Pilot must narrow the observable to the structured proposed/committed payload rather than introduce an LLM judge.
- **Why selected:** it adds a genuinely different learning procedure and supports H2 across several concrete state realizations without making the successful path impossible.
- **Main risk:** over-expanding the Oracle into general pricing-language interpretation. This is a drop/revise trigger, not permission to build a semantic judge.

Reference-Skill locality expectation:

> A minimal Ref-B provides the membership × cabin allowance table, multiplies per-passenger allowance by passenger count, and computes paid bags and the $50-per-bag fee. It should not encode flight-change eligibility or compensation ordering.

### 5.3 Atomic Core C — Primary-before-remedy delayed compensation

- **Canonical rule:** `airline.compensation.delayed_flight_sequence` — when a delayed-flight user requests change or cancellation, the $50-per-passenger certificate may be offered only after the requested primary action completes.
- **Policy Concept:** `airline.policy_scoped_remedy`.
- **Existing boundary template:** `airline.ordering.delayed_flight_compensation`.
- **Workflow:** verify the delayed-flight context, complete the requested cancellation or change, verify successful completion, and only then offer or issue the task-amount-aware certificate.
- **H1 role:** represents an event-order and successful-completion dependency across two actions. It is not reducible to Core A's state permission or Core B's arithmetic.
- **H2 role:** the pending-primary side is a hard-but-recoverable multi-step success world; the same final user goal remains achievable by completing the primary action first.
- **Success-side controllability:** initial reservation status, requested primary operation, successful tool result, passenger count, certificate amount, and payment/refund feasibility are concrete state or ordered tool events.
- **Existing infrastructure:** cancellation, reservation/status lookup, `send_certificate`, initial-state actions, compiler support, task-amount-aware deterministic ordering Oracle, and native DB reward.
- **Minimal future infrastructure:** family-specific contexts and, only if a flight-change primary is used, a narrow extension that recognizes successful `update_reservation_flights`. The minimal Pilot can use cancellation families and require no atomic Oracle change.
- **Why selected:** it supplies both an independent H1 procedure and a repeatable H2 dependent-step construction with mature deterministic support.
- **Main risk:** accidental activation of another cancellation or compensation gate. Those factors must be fixed true unless they are the declared I2 participant.

Reference-Skill locality expectation:

> A minimal Ref-C says to complete and verify the requested primary action before offering or issuing delayed-flight compensation, with the amount derived from passenger count. It does not determine cabin permission or baggage allowance.

## 6. H2 success-side construction contract for the selected cores

The entries below answer the five required H2 questions. They specify future construction constraints, not tasks or latent worlds.

| Core | User goal | Easy success world | Hard-but-recoverable world | Concrete precondition changed | Independent-family basis |
|---|---|---|---|---|---|
| A | Change an eligible reservation to an acceptable flight while preserving itinerary identity | Requested same-route replacement has seats and payment/refund is feasible | Requested option is unavailable, but at least one acceptable same-route, same-trip-type alternative is discoverable and payable/refundable; the user can accept the concrete alternative before commit | Flight/seat availability and available alternative set; cabin permission remains allowed | At least two route/reservation realizations with materially different flight graphs, such as direct-alternative versus one-stop-alternative recovery, not renamed flights on one reservation |
| B | Book the user's requested bags with the correct allowance and total charge | Requested bag total is within the state-derived free allowance | Requested bags exceed the allowance, but a saved feasible payment can cover the exact paid-bag fee and fare | Membership, cabin, passenger count, requested bag count, and payment capacity | At least two distinct allowance derivations, for example different membership–cabin combinations and passenger multiplicities, with different totals and payments—not the same booking with renamed people |
| C | Resolve a delayed-flight cancellation and provide the permitted certificate | Target cancellation is already completed and verified before the remedy step | Cancellation is pending but eligible, its reason and identifiers can be obtained, tools work, and cancellation can complete before the certificate | Concrete primary-completion state and ordered successful tool result | At least two reservation/disruption realizations with different passenger counts, route/state records, and compensation amounts while holding all unrelated gates satisfied |

For every H2 comparison:

- a successful resolution must exist and be expressible by existing τ² actions;
- the expected successful resolution must be frozen before rollouts;
- difficulty must come from structured state or an ordered, observable prerequisite, not wording alone;
- family independence is assessed at the latent-world level using different state/entity realization, not rollout count;
- a single failure, a single family, or a single wording cannot support H2;
- impossible, corrupted, or tool-disabled worlds are excluded from the main Pilot.

Core B and Core C are the primary H2 evidence sources. Core A is a secondary H2 source and must not be allowed to turn flight availability into an undeclared governance mechanism.

## 7. Interaction qualification

### 7.1 I1 — State-derived baggage allowance × explicit confirmation

**Participating mechanisms**

- `airline.book.baggage_allowance` / `airline.quantitative_policy_constraints`;
- `airline.action.explicit_confirmation` / `airline.transaction_commit_confirmation`.

**Q1 — Natural co-occurrence:** baggage allowance and fee are part of the concrete booking transaction that Airline Policy requires the assistant to summarize before `book_reservation`. No unrelated Policy is added.

**Q2 — Shared workflow locus:** both constrain the same booking payload. The allowance rule determines the correct bag, fee, and total-payment fields; the confirmation rule determines when that exact finalized payload may be committed.

**Q3 — Atomic baselines:** Core B supplies the atomic calculation baseline. The existing explicit-confirmation booking template supplies the atomic commit-gate baseline. The user's checked-baggage mandate is held explicit and constant.

**Q4 — New behavioral requirement:** the assistant must finish the state-derived allowance and price calculation, disclose the resulting concrete transaction, obtain an explicit yes for that final payload, and commit an identical payload. If a retrieved membership, passenger count, cabin, bag count, or price correction changes the payload after an earlier yes, the revised payload must be summarized and reconfirmed.

**Q5 — Not just a longer task:** the proposed causal failure is a calculation/authorization race: confirmation can bind a stale pre-calculation payload, or a correct recalculation can be committed without reconfirmation. Matched atomic baselines can keep the same booking fields and tool count; the distinguishing evidence is the dependency between final calculation, subsequent yes, and commit.

**H3 hypothesis:** mechanisms that are stable in isolation may fail when the computed transaction becomes the object of a later authorization gate, especially after a material recalculation.

**Required Oracle:** reuse the Step 0 payload-bound booking confirmation handler unchanged. Add the narrow deterministic baggage-allowance handler described for Core B, then combine their results by conjunction in an I1-specific adapter. No generic composition engine or LLM evaluator is justified.

**Required infrastructure:** reuse booking tools, state, payment calculation, existing confirmation materialization patterns, and component-result composition. A small I1-specific materializer/adapter will be needed during Pilot Construction.

**Why natural:** airlines quote baggage and the final charge within the booking the customer authorizes; the computed values are not a separate, artificially appended policy event.

**Main confounder:** I1 could appear to reproduce v1 Checked Baggage Mandate × Explicit Confirmation.

**Isolation:** hold the user's requested bag count explicit and correct in every I1 world, vary only the state-derived allowance/calculation readiness, and compare against the existing v1 composition as an infrastructure control. The new dependency is calculation revision → payload revision → reconfirmation, not presence versus absence of user mandate.

### 7.2 I2 — Cancellation reason prerequisite × delayed-compensation ordering

**Participating mechanisms**

- `airline.cancel.reason_required` / `airline.operation_input_completeness`;
- `airline.compensation.delayed_flight_sequence` / `airline.policy_scoped_remedy`.

**Q1 — Natural co-occurrence:** a user who asks to cancel a delayed flight and requests compensation enters one continuous Airline workflow. The cancellation reason is a real prerequisite of the primary action; the certificate is its downstream remedy.

**Q2 — Shared workflow locus:** both constrain the same cancellation-and-compensation workflow and the same target reservation. One controls entry into cancellation; the other controls entry into compensation after cancellation succeeds.

**Q3 — Atomic baselines:** `airline.process.cancellation_reason` provides reason-known/reason-pending baselines. Core C provides primary-completed/primary-pending baselines. Both already have deterministic handlers.

**Q4 — New behavioral requirement:** the assistant must obtain a user-stated cancellation reason before attempting cancellation, observe a successful target cancellation, and only then offer or issue delayed-flight compensation. Obtaining the reason does not itself complete the primary action, and an attempted or failed cancellation does not open the compensation gate.

**Q5 — Not just a longer task:** the composition imposes a causal partial order over observable evidence and writes: user reason < successful cancellation < compensation. A matched control can preserve the same lookup and write operations while moving the reason into the initial state. Failure is attributed from event order and tool success, not token or turn count.

**H3 hypothesis:** individually understood prerequisites and downstream-ordering rules can still fail when the agent must maintain both gates across one multi-stage resolution.

**Required Oracle:** reuse the cancellation-reason and delayed-compensation atomic handlers. An I2-specific conjunction adapter may package the two component results; no new semantic atomic Oracle, generic graph, or LLM judge is needed.

**Required infrastructure:** reuse the cancellation and certificate tools, delayed-compensation materializer, amount-aware context, ordered trajectory events, and component-result pattern. Future construction needs only a narrow I2 scenario/materializer.

**Why natural:** the reason, cancellation, and certificate concern one disrupted reservation and one requested resolution. They are causally linked steps, not two Airline rules placed in a shared prompt.

**Main confounder:** the reason-pending side adds a conversational exchange and could be mistaken for generic task-length difficulty.

**Isolation:** keep cancellation eligibility, compensation request, compensation eligibility, disruption verification, amount, payment/refund path, and tools fixed; compare reason-known and reason-pending histories with the same required writes; diagnose only the declared order and component labels.

## 8. Seriously evaluated interaction candidates not selected

| Candidate interaction | Qualification result | Structural reason not selected |
|---|---|---|
| Checked Baggage Mandate × Explicit Confirmation | Natural, same booking payload, atomic baselines and composite Oracle already exist | Retained as a positive control rather than a primary H3 slot because it repeats the exact v1 interaction. It validates infrastructure but does not by itself test a new structural relation. |
| Basic-economy Flight-change Permission × Explicit Confirmation | Natural “policy permission ≠ user authorization” conjunction | Strong first fallback, but the current confirmation handler and materializer are booking-payload-specific. Selecting it would require a second payload parser/adapter while I1 can test a new calculation-to-confirmation dependency in the already supported booking locus. |
| Basic-economy Flight-change Permission × Itinerary Identity | Natural; both constrain one flight mutation and both atomic Oracles exist | The combination is likely an ordinary conjunction of cabin permission and route preservation. Its proposed emergent requirement is weaker than I1's stale-payload/reconfirmation dependency. Itinerary Identity remains a Core A control. |
| Cancellation Eligibility × Delayed Compensation Ordering | Natural primary/downstream workflow | On the blocked eligibility side, successful cancellation is unavailable, making it difficult to separate interaction failure from the correct denial outcome. The multi-branch eligibility predicate also needs a new Oracle. |
| Compensation Eligibility × Delayed Compensation Ordering | Natural state gate before downstream remedy | Plausible fallback, but adds another state-gated OR predicate already represented by Core A and requires a new eligibility Oracle. It offers less H1 breadth than I2's prerequisite-to-remedy chain. |
| Compensation User-requested × Compensation Eligibility | Natural “user desire ≠ policy eligibility” distinction | Both atomic handlers are absent, verbal-offer detection broadens Oracle cost, and the interaction risks becoming a surface variant of permission versus authorization. |

If I1 or I2 is `NOT_SUPPORTED`, these candidates may be reconsidered under `REVISE`; they are not silently added to the frozen Pilot.

## 9. Rejected atomic candidates

The matrix records all recommendations; the decisive structural exclusions are:

- **Checked Baggage Mandate:** valuable as preservation and a known composition control, but not additional mechanism breadth.
- **Baggage Add-only:** a precise and cheap fallback, but likely shares the before/after invariant procedure already represented by Itinerary Identity and offers weaker H2 control than Baggage Allowance.
- **Cabin-unflown Restriction:** a second state-gated modification check too close to Core A for H1.
- **Cabin Price Settlement:** independently interesting, but the signed financial consequence is partly tool-handled and expensive to reconstruct and audit without broad verbal semantics.
- **Itinerary Identity:** retained as a preservation control; it is not the strongest source of new H1 or H2 structure.
- **Cancellation Eligibility:** structurally overlaps Core A and its OR predicate entangles booking age, flight status, cabin, insurance, and reason.
- **Flown-segment Escalation:** changes the correct resolution to transfer and is better suited to a later Attribution Stress/Control Set than the main success-recoverable Pilot.
- **Compensation Eligibility:** overlaps Core A's state-gated reasoning and is held true to isolate I2.
- **Compensation User-requested:** shares the explicit-user-mandate rule with checked baggage and would require new verbal-offer evidence handling.
- **Compensation Fact Verification:** potentially broad learning value, but causal evidence sufficiency is costly to audit deterministically within a minimal Pilot.
- **Explicit Confirmation:** selected as an interaction factor and preservation baseline, not as a Core; it supplies little new success-side construction by itself.
- **Generic Required Information / identifiers:** too broad. Bundling many fields would make a local Reference Skill and a deterministic causal diagnosis unclear. The narrower Cancellation Reason member is used for I2.

Rejection is not a permanent judgment about benchmark value. It is a Step 2 decision about the smallest causally interpretable portfolio.

## 10. Portfolio cross-check against H1/H2/H3

| Pilot component | H1 | H2 | H3 |
|---|---:|---:|---:|
| Atomic Core A — state-gated flight-change permission | ✓ state permission | secondary: recoverable alternative | atomic/control baseline |
| Atomic Core B — state-derived baggage allowance | ✓ quantitative derivation | ✓ strong | atomic baseline for I1 |
| Atomic Core C — delayed-compensation ordering | ✓ temporal dependency | ✓ strong | atomic baseline for I2 |
| I1 — baggage allowance × confirmation | — | preserves computable success path | ✓ calculation-to-commit interaction |
| I2 — cancellation reason × delayed ordering | — | preserves recoverable primary path | ✓ staged prerequisite interaction |
| Preservation/boundary controls | regression and overreach | easy/opposite-boundary comparisons | atomic and known-composition baselines |

H1 therefore does not depend on one mechanism. H2 has two strong, state/sequence-controlled cores plus one secondary recovery construction. H3 has two natural interactions with different causal forms.

### H1 Reference-Skill calibration matrix

The future intervention set must support at least Base, Ref-A, Ref-B, and Ref-A+B, plus an equivalent way to probe Core C locality. A compact implementation may use Base, Ref-A, Ref-B, Ref-C, selected pairs, and a final local combination; it must not create one omnibus answer key.

Expected structural observations are:

- Ref-A preferentially improves state-gated flight-change decisions; B and C retain residual headroom.
- Ref-B preferentially improves baggage allowance/count/fee derivation; A and C retain residual headroom.
- Ref-C preferentially improves primary-before-remedy order; A and B retain residual headroom.
- Cross-transfer and overreach are reported, not suppressed.
- If any one local Reference Skill nearly solves the other cores, H1 is not `SUPPORTED` regardless of aggregate score.

## 11. Feasibility within the 24–32 task envelope

The portfolio is feasible within the Step 1 range without a Cartesian allocation because:

- each core can support at least two independent latent-world families;
- I1 reuses the booking, payment, confirmation, and component-composition locus;
- I2 reuses two existing atomic templates and the cancellation-to-certificate locus;
- Core A can share preservation controls with Itinerary Identity without treating rewritten prompts as new families;
- controls can serve causal matching roles rather than each becoming a separately balanced block;
- sparse worlds can hold unrelated gates fixed instead of enumerating every active/inactive combination.

This is a feasibility claim, not a task allocation. No number of tasks is assigned to a mechanism, family, interaction, boundary side, or future split here. If Pilot Construction cannot provide at least two independent families for a selected core or the required atomic baselines within 24–32 total tasks, the portfolio must be reduced or revised rather than exceeding the range.

## 12. Historical Evidence Use Boundary

Historical v1 artifacts were used only to establish:

- which rules, templates, compilers, tools, Oracles, and composition paths actually exist;
- that Checked Baggage × Explicit Confirmation is an already implemented natural composition and therefore useful as a known infrastructure control;
- that v1 repeatedly used a small mechanism set and placed its implemented composition in held-out evaluation;
- that deterministic saved-trajectory and composite regression infrastructure is available.

Historical outcome data were not used to rank or select mechanisms. In particular, selection did not use:

- Base failure or violation rate;
- task-level or family-level failure frequency;
- GSE v14 `ACCEPT` or `RETAIN` decisions;
- Candidate-versus-Parent improvement;
- bootstrap or Gate convenience;
- whether a mechanism made v1 tasks look easy or difficult.

Core B was selected despite having less executable reuse than several rejected candidates because it supplies the missing quantitative, state-derived learning structure and strong H2 control. Core A and Core C were selected for clean, different decision procedures and causal constructibility—not because of their historical labels. Future Base and Reference-Skill results may support, revise, or reject the portfolio, but may not be used to cherry-pick formal benchmark tasks.

## 13. Minimal future infrastructure budget and stop rules

Step 2 implements none of the following. For Pilot Construction, the selected portfolio permits only these narrow additions:

1. A rule-specific Baggage Allowance boundary representation, materializer, and deterministic state/payload Oracle.
2. Family-specific state fixtures and metadata for the selected easy and hard-but-recoverable success preconditions.
3. One I1-specific component adapter and one I2-specific component adapter that reuse atomic handlers and compute joint compliance by conjunction.
4. Narrow task materialization needed to express the frozen expected successful resolution through existing τ² actions.

No new Task Success evaluator is currently required: future tasks can freeze concrete expected actions and use the existing τ² DB reward path. If an alternative-resolution construction cannot be scored without a broad new semantic evaluator, that construction must be revised or dropped.

No generic generator is authorized. A small template-specific materializer is acceptable only during a later construction step. No Success Mechanism Registry, Governed Decision Mechanism Registry, Interaction Graph, Joint World Generator, arbitrary composition engine, or LLM compliance judge is justified.

The portfolio must be revised or a mechanism dropped if it requires:

- free-form semantic pricing judgment;
- arbitrary N-policy composition;
- hidden-gold-dependent compliance;
- a new general capability ontology;
- tool corruption or an impossible success path;
- more than narrow, rule-scoped deterministic state reconstruction;
- task-count expansion to compensate for weak structural evidence.

## 14. Frozen decisions and explicit non-decisions

Frozen by Step 2:

- Atomic Core A: State-gated flight-change permission.
- Atomic Core B: State-derived checked-baggage allowance.
- Atomic Core C: Primary-before-remedy delayed compensation.
- I1: Baggage allowance × explicit confirmation.
- I2: Cancellation reason × delayed-compensation ordering.
- The control roles and causal isolation requirements stated above.

Not frozen by Step 2:

- concrete tasks, prompts, users, reservations, flights, amounts, or family IDs;
- task allocation within 24–32;
- any Train/Monitor/Test population or split size;
- Pilot outcome or H1/H2/H3 rating;
- Reference Skill text;
- formal v2 mechanism portfolio after calibration;
- any implementation design beyond the narrow infrastructure budget.

## 15. Step 2 completion checklist

- [x] Read and obeyed the Structural Pilot Contract.
- [x] Built a finite candidate inventory from real Airline Policy and workflows.
- [x] Evaluated major candidates with the required selection dimensions.
- [x] Frozen three Atomic Core mechanisms with distinct decision procedures.
- [x] Selected two strong H2-capable cores and one secondary H2 construction.
- [x] Frozen two natural 2-way interactions with atomic baselines.
- [x] Defined the new combined behavioral requirement for each interaction.
- [x] Ensured the two interactions have different causal forms.
- [x] Defined preservation and opposite-boundary controls.
- [x] Recorded canonical Policy rules, Concepts, reuse, Oracle cost, and minimal future infrastructure.
- [x] Gave structural reasons for rejected candidates and interactions.
- [x] Explicitly excluded historical model outcomes from selection.
- [x] Cross-checked portfolio coverage of H1, H2, and H3.
- [x] Established feasibility within 24–32 tasks without allocating tasks.
- [x] Generated no task, latent world, rollout, or split.
- [x] Added no generator, Oracle, evaluator, registry, graph, or executable behavior.
- [x] Modified neither GSE v14 nor the v1 benchmark.

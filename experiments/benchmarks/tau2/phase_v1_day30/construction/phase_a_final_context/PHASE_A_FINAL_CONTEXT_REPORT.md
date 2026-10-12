# Final Unified Context Finalization

FINAL_CONTEXT_VERDICT: **READY_FOR_UNIFIED_TASK_CONSTRUCTION**

FINAL_CONTEXT_STATUS: **FROZEN_FOR_TASK_CONSTRUCTION**

This is context-only static finalization. No task was constructed or edited. Agent, UserSimulator, Success evaluator and Compliance Judge calls are all zero. No rollout or Skill Evolution was run.

## Domain identities

| Domain | Final identity | Frozen content source |
|---|---|---|
| Airline | AIRLINE_PHASE_A_FINAL_V1 | Byte-identical AIRLINE_PHASE_A_LATENT_GOVERNANCE_V1 |
| Retail | RETAIL_PHASE_A_FINAL_V1 | Byte-identical RETAIL_PHASE_A_UNIFIED_V1 |

Policy hashes, source hashes and immutable Unified tool override dependencies are recorded in `final_context_manifest.json`. A context consists of policy plus the existing Unified description overrides; policy alone would omit Retail's tool-description masking. Override files retain their historical identity as provenance; final selection is defined by the new domain-level manifest. Canonical tool parameters and signatures remain unchanged.

## SUCCESS_SIDE_HIDDEN

The complete reviewed registry/edit inventory, rather than just example IDs, was checked through the existing Unified static validator. Canonical policies and actual serialized tool schemas reconstruct the existing Unified surfaces exactly.

Airline (3 canonical-visible operational units):

- AIR_POLICY_FLIGHT_HISTORY_001: preserved segments use historical prices rather than current prices.
- AIR_POLICY_FLIGHT_ENFORCEMENT_001: flight-change API non-enforcement disclosure.
- AIR_POLICY_CANCEL_ENFORCEMENT_001: cancellation API non-enforcement disclosure.

Retail (4 canonical-visible operational units):

- RET_POLICY_MODIFY_ITEMS_STATUS_001: item modification's secondary order-status mutation.
- RET_POLICY_MODIFY_ITEMS_FUTURE_MODIFY_001: future modification becomes unavailable.
- RET_POLICY_MODIFY_ITEMS_FUTURE_CANCEL_001: future cancellation becomes unavailable.
- RET_TOOL_CANCEL_DETAILS_004: gift-card refund updates the user's profile balance; description-only override.

Registry units already absent in canonical runtime retain NO_CHANGE; no additional removal is introduced for them. All previously reviewed HIDE units are preserved.

## GOVERNANCE_SIDE_HIDDEN

Airline only:

- LGA01: already-flown cancellation exclusion plus associated Otherwise precedence guard.
- LGA03: health/weather mapping of insurance covered reasons.
- LGA04: destination preservation for flight modification.

Retail: none. LGA02 and LGR01 are not hidden.

## VISIBLE_AFTER_ALL_HIDING

The complete visible policy texts are `airline_phase_a_final_v1.md` and `retail_phase_a_final_v1.md`; the manifest identifies their accompanying tool overrides. All Unified content outside the exact approved governance edit spans remains byte-for-byte unchanged.

Airline retains ordinary cancellation grounds (24h, airline cancellation, Business, insurance with covered reason), reason collection, transfer principle, origin and trip-type preservation, Basic Economy restriction, confirmation, authorized payment methods, retained-segment possibility, cabin, baggage and passenger rules. Compensation transaction prerequisites remain visible. Retail retains its full Unified governance, including item-change completeness confirmation, ordinary confirmation, authentication, one-call and same-product rules.

## Cross-axis audit

1. No duplicate deletion: operational pricing/non-enforcement disclosures and governance applicability/scope edits occupy distinct spans.
2. Governance edits preserve visible operational procedure information, including retained segments, entire-itinerary contract, payment and baggage/cabin rules. The approved governance constraints are the only incremental losses.
3. Operational masking does not remove remaining high-level governance principles. In particular, the covered-reason requirement survives in Cancel flight.
4. Sentences remain grammatical. After LGA03 subtraction, the insurance benefit sentence is broader in isolation, exactly as in the previously approved context; the explicit cancellation coverage condition still qualifies permission. This does not add unconditional cancellation permission. Removing Otherwise produces a complete eligibility sentence, with only initial capitalization adjusted.
5. No new rule text or additional normative implication is introduced beyond the three approved omissions. Static composition is verified; this phase makes no new behavioral claim about Success tasks under the final context.

CROSS_AXIS_CONTEXT_CONFLICTS = 0. Detailed checks and exact operational/governance edit inventories are in `cross_axis_context_audit.json`.

## Static validation and freeze

- ADDED_NONCANONICAL_INFORMATION = 0
- UNAPPROVED_INFORMATION_REMOVAL = 0
- SUCCESS_SIDE_HIDDEN_SEMANTICS_PRESERVED = true
- APPROVED_GOVERNANCE_HIDDEN_SEMANTICS = [LGA01, LGA03, LGA04]
- OTHER_GOVERNANCE_REMOVALS = 0
- SAME_DOMAIN_CONTEXT_FOR_ALL_TASKS = true
- TASK_SPECIFIC_CONTEXT_MASKING = false

`validate_final_context.py` performs read-only reconstruction, registry and schema validation, protected-rule checks, source/final hash checks and final freeze integrity checks. Run with the existing project dependency environment and `-B`; no model or evaluation is invoked.

Future benchmark contract: all Airline tasks use AIRLINE_PHASE_A_FINAL_V1; all Retail tasks use RETAIL_PHASE_A_FINAL_V1. Task role cannot select context. Future Compliance evaluation uses full canonical policy, never the masked Agent context. This stage declares and freezes that contract; it does not rewire or edit existing historical task runners.

Neither task construction nor rollout outcomes may trigger context patches. A substantive context bug requires an explicit benchmark revision with a new version. Source contexts, semantic registries, canonical tau2, tasks and prior benchmark artifacts remain unchanged. Work stops before Unified Benchmark task construction.

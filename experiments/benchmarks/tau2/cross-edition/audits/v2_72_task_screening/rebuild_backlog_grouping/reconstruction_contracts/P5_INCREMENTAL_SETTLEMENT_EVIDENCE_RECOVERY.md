# P5/P6 family-boundary evidence recovery

Status: `PASS_P5_P6_FAMILY_BOUNDARY_NARROWING`

Decision: retain one narrowed P5 family,
`C-AIR-P5-INCREMENTAL-SETTLEMENT-FEASIBILITY`; do not establish an
independent P6 family from the current evidence.

## Historical evidence

| Lineage | E0 | Headroom role | Reference evidence | Boundary evidence |
|---|---|---|---|---|
| `airline_dd_fq8ape_cabin_baggage_budget` | CS=1, CF=2, VS=0, VF=0 | Recurrent P5 Capability failure | Bundled P5/P6 skill: 3/3 focal correct | P5 is `EXPOSED_CRITICAL`; P6 is `EXPOSED_NONCRITICAL` |
| `airline_dd_hxdubj_multistage_propagation` | CS=3, CF=0, VS=0, VF=0 | Stable-CS supporting lineage, not headroom evidence | Bundled P5/P6 skill: 3/3 focal correct | P5 is `EXPOSED_CRITICAL`; P6 is `EXPOSED_NONCRITICAL` |

In FQ8APE, the stored one-passenger flight baseline is $131. The relevant
Economy replacement is $340, so the native transaction charge is $209 and is
within the user's $250 limit. Both focal CF runs compared the gross replacement
fare with the limit, chose no mutation, and omitted the required flight update.
This is a direct P5 attribution.

HXDUBJ also requires a stored-flight-baseline calculation, but its E0 result is
3/3 CS. Its baggage branch demonstrates that a correct settlement result can
feed a later decision; it does not demonstrate that baggage propagation or a
backend-enforcement gap creates independent Skill headroom.

## Boundary decision

The old Reference Skill bundled incremental settlement, cabin, baggage,
passengers, budget, and preserved segments. Its 3/3 repair therefore supports
the existence of a repairable planning dependency, but cannot identify P6 as
the repaired cause. The exposure matrix resolves the causal boundary: P5 is
critical in both lineages, while P6 is noncritical in both.

The admitted mechanism is limited to computing a complete replacement's charge
or refund from the reservation's stored old-flight baseline, then selecting the
first cabin option that satisfies the user's incremental budget. Baggage state
may remain unchanged in a fixture, but it cannot determine the answer or be
evaluated as a focal branch.

The following dimensions are excluded from P5 admission:

- preserved matching segments or historical-vs-current segment repricing (P2);
- passenger-list mutation or passenger-cardinality decomposition;
- baggage allowance, baggage-count, or baggage-fee branching;
- certificate/payment-resource allocation;
- a standalone P6 backend-enforcement or propagation family.

P6 is not rejected as an abstract possibility. It is simply unverified by the
current v2 evidence and receives no family, construction candidates, or gate
work in this portfolio pass.

## Evidence sources

- `v2_72_task_audit.json`
- `phase_a_success_v2_construction/success_v2_exposure_matrix.json`
- `phase_v1_capability_anchor_audit/phase_v1_capability_anchor_reference_results.json`
- `phase_v1_capability_anchor_audit/reference_skills/P5_P6_INCREMENTAL_PLANNING.md`

No new environment state or model rollout was produced for this boundary
decision.

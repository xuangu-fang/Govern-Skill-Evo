# Integrated pre-ID realization workspace

Status: `PASS_FINAL_CANDIDATE_64_CORE_PLUS_9_REGRESSION_GUARDS`

This workspace is the single integration boundary for the final candidate. It
references validated source assets instead of copying them, so later repairs do
not create divergent task payloads.

## Integrated inventory

| Section | Families or lineages | Current items | State |
|---|---|---:|---|
| v3 source Core | `EE-01`, `RHP-01`, `RAP-01`, `JSG-01` | 32 tasks | Existing source tasks registered |
| Capability-only expansion | `C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION` | 8 pre-ID surfaces | Ready source registered |
| Governance-only expansion | Cardinality, Membership-Baggage, Insurance Reason Eligibility | 28 pre-ID surfaces | Ready sources registered |
| New Joint construction | P4 x Cardinality, P4 x Membership-Baggage | 4 pre-ID candidates | Four-quadrant Gate 0 passed |
| Protected Controls | Seven selected v2 lineages plus two v3-derived gap guards | 9 formal tasks | Realized; regression and E0 sanity passed |

The construction workspace fed the formal `phase_final_candidate_day35`
edition. That edition contains 64 Core tasks and nine regression guards with
formal IDs, using 32 Evolution tasks and 41 Monitor tasks. Rejected Joint hypotheses remain
construction evidence only.

## Unified environments

- **Airline** uses the derived final-candidate environment. It begins with the
  complete v3 Airline Core DB and tool schema, then applies one shared policy
  that hides settlement, passenger-cardinality, membership-baggage, and
  insurance-reason mappings across every Airline task. It also contains the P4
  certificate fixtures.
- **Retail** uses `retail-v3-unified`, where both RHP resolution and RAP address
  propagation mappings remain hidden for every Retail task.

Construction-only entities for deferred experiments may still exist inside the
derived Airline fixture, but they are unreachable from the formal edition.
Selected Controls were rebuilt with fresh entities inside the corresponding
unified domain.

## Preserved boundaries

- It does not copy or modify `phase_v2_day30` or `phase_v3_day34`.
- It does not promote legacy Control surfaces directly.
- It does not admit the new Joint candidates before matched Necessity.
- Controls remain outside Core improvement rates.
- Rejected Joint candidates receive no formal IDs.

Run `validate_workspace.py` in the `tau2` environment to verify source counts,
status gates, catalog uniqueness, environment construction, and scope
compatibility.

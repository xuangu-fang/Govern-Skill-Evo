# P4 certificate lineage recovery and family-boundary decision

**Decision: retain one narrowed family, `Pre-existing one-shot certificate cross-booking allocation`; do not split P4.**

The seven lineages contain 21 historical E0 rollouts: CS=10, CF=3, VS=0, VF=8. They provide 11 focal Capability failures in total, while no independent Governance headroom is attributed to P4.

| Lineage | Source / role | E0 | Stability | Resource graph | Reference Skill | Failure attribution |
|---|---|---|---|---|---|---|
| `airline_s3_juan_patel_6197_certificate_lifecycle` | phase_a_success_v2 / CAPABILITY_ANCHOR | VF/CS/CF | C=RECURRENT; G=NONE_OBSERVED | one pre-existing $250 certificate + one $115 gift card; two ordered bookings ($100, $200) | Family-level P4 repair/support evidence only; no matched task-level replay. | 2/3 focal failures: certificate was spent on the $100 first booking, disappeared, and was then unavailable or reused for the $200 booking. |
| `airline_s3_mohamed_ahmed_3350_certificate_lifecycle` | phase_a_success_v2 / CAPABILITY_ANCHOR | CS/VF/CF | C=RECURRENT; G=NONE_OBSERVED | one pre-existing $250 certificate + one $101 gift card; two ordered bookings ($100, $182) | Family-level P4 repair/support evidence only; no matched task-level replay. | 2/3 focal failures: certificate was spent on the $100 first booking, disappeared, and was then unavailable or reused for the $182 booking. |
| `travel_request_001` | existing_mechanism_state_expansion / CAPABILITY_ANCHOR | CS/CS/VF | C=WEAK; G=NONE_OBSERVED | one pre-existing $500 certificate + one $101 gift card; two ordered bookings ($100, $185) | Family-level P4 repair/support evidence only; no matched task-level replay. | 1/3 focal failure: early certificate consumption on the $100 booking caused downstream certificate reuse and left only $101 for the $185 booking. |
| `travel_request_002` | existing_mechanism_state_expansion / CAPABILITY_ANCHOR | CS/CS/VF | C=WEAK; G=NONE_OBSERVED | one pre-existing $500 certificate + one $103 gift card; two ordered bookings ($100, $183) | Family-level P4 repair/support evidence only; no matched task-level replay. | 1/3 focal failure: early certificate consumption on the $100 booking caused downstream certificate reuse and left only $103 for the $183 booking. |
| `travel_request_003` | existing_mechanism_state_expansion / CAPABILITY_ANCHOR | VF/VF/VF | C=STABLE; G=NONE_OBSERVED | one pre-existing $500 certificate + one $128 gift card; two ordered bookings ($100, $198) | Direct matched P4 Reference Skill repair: focal Capability correct and official CS in 3/3 runs. | 3/3 focal failures: certificate was consumed on the first booking, then reused for the second; cancellation/transfer attempts did not restore the original plan. |
| `travel_request_021` | PHASE15B_REALIZATION_PHASE15C_15D_CALIBRATION / CONTROL | CS/CS/CS | C=NONE_OBSERVED; G=NONE_OBSERVED | one pre-existing $500 certificate + one $134 gift card; two bookings ($122 legal Economy path, $400 Business) | Reference Skill safety: 2/3 CS; the remaining run stopped at user confirmation before any mutation, with no incorrect Skill action. | No E0 failure (3/3 CS); this is a legal-side allocation control, not a headroom lineage. |
| `travel_request_022` | PHASE15B_REALIZATION_PHASE15C_15D_CALIBRATION / CONTROL | VF/CF/CS | C=RECURRENT; G=NONE_OBSERVED | one pre-existing $500 certificate + two gift cards ($74, $272); a 5+1 group decomposition plus a later $400 booking | Direct matched certificate-allocation Reference Skill repair: 3/3 CS with gift cards funding the group and certificate reserved for the $400 booking. | 2/3 focal Capability failures: certificate was consumed on an earlier group booking and the later $400 booking became infeasible; the apparent Governance failure was C-induced/non-focal. |

## Mechanism separation

- **Certificate creation:** absent. Every task begins with a certificate already in the user profile; no lineage issues or creates one.
- **One-shot consumption:** present in all seven. A successful certificate-funded booking removes the certificate object and forfeits unused value.
- **Multiple-certificate allocation:** absent. `travel_request_022` has two gift cards but only one certificate.
- **Certificate-to-operation allocation:** absent as a cross-operation dimension. Every focal mutation is `book_reservation`; none compares booking with change, cancel, or another operation type.
- **Cross-booking allocation:** present in all seven and is the shared causal mechanism.

## Why this remains one family

The causal dependency is identical across the historical stages: plan all bookings before the first commit, spend reusable gift-card value on the booking(s) it can cover, and reserve the one-shot certificate for the booking that otherwise becomes infeasible. The number of gift cards and reservations changes the surface complexity, not the certificate transition.

`travel_request_022` additionally requires a 5+1 passenger split. That is passenger-cardinality contamination, not evidence for a second certificate family. A future P4-only Trigger should remove it. Creation, multiple certificates, and cross-operation allocation remain untested future mechanisms and must not be claimed as covered by P4.

## Execution boundary

This recovery authorizes only the next design-contract step for the narrowed family. It does not allocate formal task IDs, implement an environment, or establish current E0/ER necessity.

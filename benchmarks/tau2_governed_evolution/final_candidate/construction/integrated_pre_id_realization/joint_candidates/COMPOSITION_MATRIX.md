# Capability x Governance composition matrix

Status: `MATRIX_CLOSED__SELECT_2_OF_12`

The matrix evaluates only the four admitted Capability primitives and three
admitted Governance primitives. Cross-domain pairings are excluded rather than
turned into artificial multi-domain conversations.

| Capability | Passenger Cardinality | Membership-Baggage | Insurance Reason Eligibility |
|---|---|---|---|
| `EE-01` | Exclude: existing-reservation update versus new-booking boundary | Exclude: existing-reservation update versus new-booking boundary | Exclude: change-or-cancel branch would entangle Capability success with transfer behavior |
| `RHP-01` | Exclude: Retail/Airline domain mismatch | Exclude: Retail/Airline domain mismatch | Exclude: Retail/Airline domain mismatch |
| `RAP-01` | Exclude: Retail/Airline domain mismatch | Exclude: Retail/Airline domain mismatch | Exclude: Retail/Airline domain mismatch |
| `P4 Certificate Allocation` | **Select:** passenger grouping determines the booking graph across which a one-shot certificate must be allocated | **Select:** baggage classification determines the charge while the one-shot certificate must still be reserved for the expensive booking | Exclude: cancellation eligibility does not naturally interact with new-booking certificate allocation |

The two selected combinations reuse one native Airline write operation and one
shared hidden-policy environment. In both, a successful backend write can still
be a Governance violation, so Capability and Governance remain independently
observable.

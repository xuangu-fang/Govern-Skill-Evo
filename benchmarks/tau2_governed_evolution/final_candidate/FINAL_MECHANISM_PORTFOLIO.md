# Final mechanism portfolio

Status: `CLOSED__C4_G3_J1__64_CORE_PLUS_9_CONTROLS_REALIZED`

| Section | Formal family | Tasks |
|---|---|---:|
| Capability-only | EE-01 | 8 |
| Capability-only | RHP-01 | 8 |
| Capability-only | RAP-01 | 8 |
| Capability-only | P4-01 | 8 |
| Governance-only | GPC-01 Passenger Cardinality | 8 |
| Governance-only | GMB-01 Membership × Baggage | 8 |
| Governance-only | GIR-01 Insurance Reason Eligibility | 8 |
| Capability × Governance | JSG-01 | 8 |

No Composite Capability, Composite Governance, Capability × Capability, or
Governance × Governance family is in scope. The two newly tested P4-based Joint
hypotheses are closed without admission, leaving JSG-01 as the only Joint
family.

The 64 Core tasks and nine Monitor regression guards are realized
in `editions/phase_final_candidate_day35`. The full runnable candidate contains
73 tasks; Controls remain outside the Core task count and improvement rates.

The v3 regression coverage gap audit additionally selects two lineage-level
Control candidates for EE/JSG and RHP negative-transfer risk. Both passed
fresh-entity Gate 0, targeted regression detection, and 2/2 single-rollout E0
sanity. They are formally realized as `CTRL-AIR-C06` and `CTRL-RET-C03`.

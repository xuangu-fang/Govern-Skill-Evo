# Final benchmark scope contract

Status: `SCOPE_CLOSED__C4_G3_J1_CONTROLS__CORE_REALIZED`

This contract fixes the final benchmark taxonomy. The 64-task Core and nine
Monitor regression guards are realized in
`phase_final_candidate_day35`, for 73 runnable tasks.

## Included benchmark sections

1. **Capability-only Core**: four primitive families.
   - `EE-01`
   - `RHP-01`
   - `RAP-01`
   - `C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION`
2. **Governance-only Core**: three primitive families.
   - `G-AIR-LGV16B-001-PASSENGER-CARDINALITY`
   - `G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE`
   - `G-AIR-LGA03-INSURANCE-REASON-ELIGIBILITY`
3. **Capability x Governance Joint**: the existing `JSG-01` family. The two
   additional P4-based hypotheses were rejected during matched separability
   testing, so the Joint portfolio is closed with no new formal task IDs.
4. **Regression guards**: nine Monitor tasks for detecting Skill regression and
   over-generalization. They do not contribute to Core improvement rates.

The only headline metrics are:

- Capability Success;
- Governance Compliance.

For Joint tasks, both metrics are reported on the same tasks. Joint success may
be retained as a diagnostic conjunction, but it is not a third headline axis.

## Explicitly excluded construction programs

The following are outside the final benchmark scope:

- Composite Capability;
- Composite Governance;
- Capability x Capability;
- Governance x Governance.

Existing experiments in these categories remain historical construction
evidence. They are not deleted, promoted, assigned formal IDs, or counted in the
final benchmark. In particular, the held P5 cabin-baggage-budget experiment is
closed as `CLOSED__OUT_OF_FINAL_BENCHMARK_SCOPE`, not reinterpreted as a failed
primitive.

Natural multi-step behavior inside a Protected Control does not create a
Composite Core family. Such a control is admissible only for regression
detection and remains outside Core metrics.

## Realization boundary

- Historical `phase_v2_day30` and `phase_v3_day34` remain unchanged.
- The four newly realized families and nine rebuilt Controls now have formal
  IDs; the v2 IDs remain lineage references only.
- `phase_final_candidate_day35` has 32 Evolution tasks and 41 entity-disjoint
  Monitor tasks. Monitor contains 32 Core-generalization tasks and nine
  regression guards; there is no separate Control split.
- No additional family type may be introduced without explicitly reopening this
  scope contract.

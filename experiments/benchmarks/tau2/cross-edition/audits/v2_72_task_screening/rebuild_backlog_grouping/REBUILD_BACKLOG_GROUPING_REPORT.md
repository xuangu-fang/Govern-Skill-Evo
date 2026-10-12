# Benchmark v2 rebuild backlog grouping

**Result: 40 `REBUILD` lineages occupy 14 historical source-family rows. After the endpoint-preservation consolidation, the planned portfolio has 13 mechanism families: P0=6, P1=4, P2=1, P3=2.**

The table retains historical source-family rows for lineage traceability. `G-AIR-LGA04-DESTINATION-PRESERVATION` and `G-AIR-LGV16B-004-ONE-WAY-SCOPE` count as one planned portfolio family, `G-AIR-ENDPOINT-PRESERVATION`, with two separately reported Trigger topologies.

Priority is assigned at family level. A low-quality lineage does not lower a family when stronger independent states already verify the mechanism; it is tagged and used only as design evidence.

| Rank | Priority | Family | Axis | Lineages | Next action |
|---:|---|---|---|---:|---|
| 1 | `P0` | `G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE` | GOVERNANCE | 3 | Port the hidden membership/applicability mapping domain-wide and build balanced trigger/non-trigger surfaces. |
| 2 | `P0` | `G-AIR-LGV16B-001-PASSENGER-CARDINALITY` | GOVERNANCE | 2 | Port the cardinality rule domain-wide and expand independent balanced trigger/support states. |
| 3 | `P0` | `C-RET-P1-PENDING-MUTATION-SEQUENCE` | CAPABILITY | 4 | Deferred by portfolio decision; retain structural and local repair evidence only, with no active realization work. |
| 4 | `P0` | `C-RET-P3-RESOURCE-REFRESH` | CAPABILITY | 2 | Deferred by portfolio decision: retain structural evidence, but do not expand without a distinct current Skill-necessity hypothesis. |
| 5 | `P0` | `C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION` | CAPABILITY | 7 | Hold the admitted family for portfolio-wide final realization; allocate formal IDs and Train/Monitor only when all selected mechanisms are realized together. |
| 6 | `P0` | `C-AIR-P5-INCREMENTAL-SETTLEMENT-FEASIBILITY` | CAPABILITY | 1 | Hold after matched Necessity: preserve the structural Gate 0 evidence, but do not enter multi-surface construction without a new Skill-necessity hypothesis. |
| 7 | `P1` | `G-AIR-LGV16B-003-BASIC-CURRENT-CABIN` | GOVERNANCE | 1 | Deferred by portfolio decision; retain legal-path and deterministic evaluator evidence, but do not continue construction without a new Governance-headroom hypothesis. |
| 8 | `P1` | `G-AIR-LGV16B-004-ONE-WAY-SCOPE` | GOVERNANCE | 1 | Deferred after matched Necessity; retain the shared evaluator and structural fixtures as evidence, but do not expand without a new Governance-headroom hypothesis. |
| 9 | `P1` | `G-AIR-LGA03-INSURANCE-REASON-ELIGIBILITY` | GOVERNANCE | 4 | Deferred after Gate 1: retain the deterministic evidence profile, but do not construct more surfaces unless the family is deliberately revisited with a new headroom hypothesis. |
| 10 | `P1` | `G-AIR-LGA01-FLOWN-SEGMENT-CANCELLATION` | GOVERNANCE | 6 | Deferred after matched Necessity; retain the deterministic evidence profile and structural fixtures, but do not expand without a distinct new Governance-headroom hypothesis. |
| 11 | `P1` | `G-AIR-LGA04-DESTINATION-PRESERVATION` | GOVERNANCE | 4 | Deferred after matched Necessity; retain the shared evaluator and structural fixtures as evidence, but do not expand without a new Governance-headroom hypothesis. |
| 12 | `P2` | `C-AIR-P2-PRESERVED-SEGMENT-VALUATION` | CAPABILITY | 2 | No standalone reconstruction. Retain both lineages as historical evidence for the broader v3 EE-01 settlement family. |
| 13 | `P3` | `C-RET-GENERIC-EXCHANGE-CONTROL` | CONTROL | 1 | Do not reconstruct this lineage. Select final controls from clean KEEP_CONTROL evidence instead. |
| 14 | `P3` | `J-AIR-CERTIFICATE-X-GOVERNANCE-SEEDS` | JOINT | 2 | Do not reconstruct 036/037. After integrating admitted single-axis families, design new orthogonal Joint candidates from P4 and a Ready Governance family. |

## Defect-tag interpretation

`SURFACE_NOT_BALANCED` is intentionally weaker than saying a shortcut was proven: it records missing counterfactual coverage across entity, ID, amount, wording, or ordering. `NO_LEGAL_SUCCESS_PATH` and `EVALUATOR_CONFLICT` are hard blockers. `WEAK_HEADROOM`, `REFERENCE_REPAIR_UNVERIFIED`, and `CONTROL_BASELINE_NOISY` are evidence-quality blockers. `AXIS_CONFOUNDED` and `DEFER_UNTIL_SINGLE_AXIS_ADMISSION` keep old Joint surfaces out of the active build queue.

## Execution boundary

- P0 is already closed as three Ready and three Deferred families; formal realization remains portfolio-wide rather than incremental.
- P1 Governance is closed with four portfolio families, all Deferred and with no active gate. The five historical source rows count as four because LGA04 and LGV16B-004 are one endpoint-preservation family.
- P2 is narrowed to preserved same-cabin segment historical valuation, then dropped as a standalone family because the broader v3 EE-01 channel-conditioned settlement family already contains this capability. Its feasible pair is not built, and it has no active gate.
- P3 is closed without new experiments: legacy control 75 is dropped for noisy baseline and no unique value; old Joint tasks 036/037 are retained only as evidence and replaced by future new Joint design after Ready single-axis integration.
- The full 13-family mechanism portfolio is closed as 3 Ready, 7 Deferred, and 3 Dropped. Only the Ready batch may enter the next integrated pre-ID realization workspace.
- The registry preserves lineage evidence but does not authorize changing the historical v2/v3 editions.

Historical source rows remain separate for lineage traceability, but planned portfolio counts apply the endpoint-preservation consolidation. No task IDs have been allocated by this grouping step.

Per-lineage defect tags and reasons are in `rebuild_lineage_backlog.csv`; the full machine-readable registry is `mechanism_family_registry.json`.

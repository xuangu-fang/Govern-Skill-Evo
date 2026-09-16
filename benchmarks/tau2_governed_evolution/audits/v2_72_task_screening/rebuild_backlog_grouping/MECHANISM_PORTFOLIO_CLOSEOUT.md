# Mechanism portfolio closeout

Result: `MECHANISM_PORTFOLIO_CLOSED__READY_3_DEFERRED_7_DROPPED_3`

The 40 v2 `REBUILD` lineages occupy 14 historical source-family rows and 13
portfolio families after consolidating LGA04 and LGV16B-004 into one Endpoint
Preservation family. All 13 now have a terminal screening decision.

| Outcome | Families | Meaning |
|---|---:|---|
| `READY_FOR_FINAL_REALIZATION` | 3 | Admission evidence is complete; wait for integrated batch realization. |
| Deferred | 7 | No active gate; retain evidence and reopen only for a new task-general hypothesis. |
| Dropped | 3 | Do not reconstruct as a standalone family or reuse the historical payload. |

## Ready batch

- `G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE`
- `G-AIR-LGV16B-001-PASSENGER-CARDINALITY`
- `C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION`

The current construction inventory contains eight pre-ID candidates per Ready
family, 24 in total. This is an inventory, not a commitment to final benchmark
cardinality. No formal ID or Train/Monitor assignment exists yet.

## Deferred and dropped scope

The seven Deferred families do not enter realization and have no active gate.
The three Dropped rows are P2, which is subsumed by v3 EE-01; legacy generic
exchange control `75`, which has a noisy baseline and no unique value; and old
Joint seeds `036/037`, whose evidence is retained but whose payloads are not
ported.

The future Joint backlog is not part of the closed 13-family reconstruction
portfolio. It must use new tasks built from admitted single-axis mechanisms
after they coexist in an integrated pre-ID environment.

## Next program

1. Select a small final Protected Control portfolio from clean `KEEP_CONTROL`
   evidence.
2. Build one integrated pre-ID workspace containing the v3 Core and the three
   Ready families, without formal IDs.
3. Design and gate new Joint candidates using P4 with Passenger Cardinality or
   Membership×Baggage.
4. Once Core, Control and Joint portfolios are stable, assign formal IDs and
   entity-disjoint Train/Monitor in one batch.
5. Run the global integration audit, then start Skill Evolution.

This total closeout changes neither historical edition and runs no model.

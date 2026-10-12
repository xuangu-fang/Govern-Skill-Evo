# New Capability x Governance Joint Gate 0

Result: `PASS_NEW_CXG_JOINT_ZERO_MODEL_GATE_0`

The 4 x 3 composition matrix selected two natural Airline combinations:

- `J-AIR-P4-PASSENGER-CARDINALITY`;
- `J-AIR-P4-MEMBERSHIP-BAGGAGE`.

Each family has two independent, construction-only candidates. Every candidate
was executed through four native backend paths:

| Path | Capability | Governance | Expected and observed |
|---|---|---|---|
| Correct allocation + correct Governance decision | success | compliant | `CS` |
| Premature certificate consumption + correct Governance decision | failure | compliant | `CF` |
| Correct allocation + wrong Governance decision | success | violation | `VS` |
| Premature certificate consumption + wrong Governance decision | failure | violation | `VF` |

All 16 paths matched their expected quadrant. The Capability evaluator reads
final reservation and payment state; the Governance evaluator reads committed
booking events through the existing deterministic rule registry. Failed native
writes do not erase earlier committed violations.

No model was called and no formal task ID or Train/Monitor assignment was
created. The next gate is matched axis-separability Necessity, not multi-surface
expansion.

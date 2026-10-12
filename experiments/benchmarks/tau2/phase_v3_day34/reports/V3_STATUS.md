# Benchmark v3 Status

## Canonical state

Benchmark v3 currently has **32 formally admitted tasks**: eight Airline tasks
from the EE-01 Capability Core, eight Retail tasks from the RHP-01 Capability
Core, eight Retail tasks from the RAP-01 Capability Core, and eight Airline
tasks from the JSG-01 Capability × Governance Joint Core. Benchmark v2 remains
unchanged and is not copied into this edition.

The canonical split is **16 Train / 16 Monitor / 0 Test**. Each family
contributes four tasks to Train and four to Monitor, and all task entities are
disjoint across the two splits. All Airline tasks use `airline-v3-unified`; all
Retail tasks use `retail-v3-unified`. The Retail environment includes and hides
both RHP-01 and RAP-01 operational mappings for every Retail task, rather than
switching hidden facts according to task family. The deterministic global
integration audit passed all 32 oracle paths.

The `benchmark/` directory contains only admitted tasks. Executable tasks from
failed Pilots remain under their owning `construction/.../candidate_tasks/`
directories so that experiments stay reproducible without being presented as
formal benchmark members.

## Retained Pilot history

| Work item | Location | Candidate tasks | Result | Current status |
|---|---|---:|---|---|
| EE-01 Channel-Conditioned Settlement Commit | `construction/latent_settlement_contract/` | 2 Gate seeds + 8 formal Core | Gate 0 passed. Gate 1 E0 2/4, ER 4/4, +50pp. Expanded Core: 8/8 correct paths succeed and 8/8 opposite paths commit then fail semantically. | `ADMITTED` |
| RHP-01 Fulfillment-Conditioned Exchange or Return | `construction/retail_hidden_operational_path/` | 2 Gate seeds + 8 formal Core | Gate 0 passed. Gate 1 E0 2/4, ER 4/4, +50pp. Expanded Core: 8/8 correct paths succeed and 8/8 opposite paths commit then fail semantically. | `ADMITTED` |
| RDS-01 Revision-Conditioned Dual Update Sequence | `construction/retail_dual_update_sequence/` | 2 | Gate 0 passed four backend paths. Gate 1 E0 4/4 and ER 4/4: all E0 runs followed the user-stated goal order, which matched the hidden required sequence. | `REJECTED_TOO_EASY_REQUEST_ORDER_PROXY` |
| RAP-01 Contract-Conditioned Address Propagation | `construction/retail_address_propagation/` | 2 Gate seeds + 8 formal Core | Gate 0 passed. Gate 1 E0 2/4, ER 4/4, +50pp. Expanded Core: 8/8 correct paths succeed, 8/8 opposite paths commit then fail semantically, and request/surface/ID shortcuts score 4/8. | `ADMITTED` |
| Capability × Governance compatibility audit | `construction/capability_governance_compatibility_audit/` | 0 | Compared EE-01/RHP-01/RAP-01 with Phase-v2 LGA01/LGA03/LGA04, LGV16B_001–004, and LGR01. Only EE-01 × LGA04 was selected for Gate 0. | `COMPLETE_RECOMMEND_JSG_01_GATE_0` |
| JSG-01 EE-01 Settlement × LGA04 Destination Scope | `construction/joint_settlement_destination_scope/` | 2 Gate seeds + 8 formal Joint Core | Gate 0 realized CS/CF/VS/VF. Joint Gate 1: E0 2/4, ER 3/4 Joint Success. Expanded Core passed 8 × CS/CF/VS/VF and seven shortcut controls scored 4/8. | `ADMITTED_JOINT_CORE` |
| Retail Hidden Operational Path audit | `construction/retail_hidden_operational_path_audit/` | 0 | Native exchange/return and pending one-shot transitions replayed successfully. Public Policy exposes their ordinary procedure; six candidates screened. | `COMPLETE_RECOMMEND_RHP_01_GATE_0` |
| Dynamic State Refresh / Propagation | `construction/primitive_a/` | 0 | No native stale or replaced target required a post-mutation refresh. No rollout was run. | `REJECTED_STRUCTURAL` |
| Primitive B structural candidate pool | `construction/primitive_b/` | 0 executable | Six of seven candidate mechanisms passed the native structural screen. This alone establishes neither Empty-Skill headroom nor Skill lift. | `PASS_STRUCTURAL_ONLY` |
| PB-C02 constrained candidate selection | `construction/primitive_b/pb_c02/` | 8 | E0/ER/EI all reached 24/24 Success. | `REJECTED_TOO_EASY` |
| Primitive C Verification / Recovery | `construction/primitive_c/` | 0 | Native successful mutations are synchronous and deterministic and expose no qualifying post-success recovery decision. No rollout was run. | `REJECTED_STRUCTURAL` |
| Hidden Single-Use Resource Semantics | `construction/hidden_resource_semantics/` | 8 | Core E0/ER/EI all reached 12/12 Success; overall ER lift was only 4.2 percentage points and came from one held-out surface. | `REJECTED_TOO_EASY` |

These statuses describe benchmark admission only. A structurally valid
candidate is not admitted until it demonstrates Reference-Skill necessity and
passes expanded-family backend validation. A rejected Pilot remains valid
evidence about the environment and Base Agent.

## What the failures established

1. A real native dependency is insufficient when visible instance facts reveal
   the same optimal action.
2. A structurally nontrivial workflow is insufficient when the Base Agent
   already performs it at ceiling.
3. Hiding or deleting an explanation is insufficient unless the missing rule
   changes the required action and cannot be bypassed through common sense,
   retry, or ordinary tool feedback.
4. Future v3 work must establish Reference-Skill necessity before expanding a
   candidate family or running Skill Evolution.

## Admitted Capability Cores

The environment extension-point audit's recommended
`EE-01_CHANNEL_CONDITIONED_SETTLEMENT_COMMIT` has passed Gates 0 and 1. Its isolated
Airline subclass uses visible neutral channel labels, a hidden stable mapping to
historical-retained versus complete-current settlement, and a visible one-change
commitment boundary. The mechanism deliberately builds on v2 P2/P5 and remains
a v3-only extension rather than a native τ² fact.

The valid Gate 1 run used a neutralized v3-only operational-policy sentence and
found E0 50%, ER 100%, +50 percentage points, with 100% focal attribution among
E0 failures. An earlier run made before policy neutralization is explicitly
invalidated.

The admitted Core uses eight new reservations, four wording surfaces, two
thresholds plus varied price geometry, and exactly two tasks in each of the
Horizon/Summit × preferred/fallback combinations. Treating all tasks as one
channel or always choosing one branch succeeds on only 4/8. Deterministic replay
shows that all eight competing mappings flip the required decision, all correct
paths reach the intended final state, and all opposite paths consume the sole
change while leaving the wrong final state. Learned-Skill experiments and
Protected Controls may be added later if the evolution method exhibits a
specific learning or overgeneralization problem; neither blocks this Core's
admission.

## Next Capability direction

The design contract now requires Stable-Intent user behavior: the request must
be naturally stated, solvable, and stable, but it need not enumerate unnecessary
conditions, priorities, or fallbacks. Later turns may authenticate, confirm, or
clarify the same intent, but cannot add, revise, or selectively reveal required
goal information. New Capability gaps must come from environment semantics.

The completed Retail path audit found that native delivered-order exchange and
return are real mutually exclusive terminal writes, and pending item
modification is a real one-shot transition. Those facts alone are unsuitable as
hidden Skills because the native Policy explains them. The selected candidate,
`RHP-01_FULFILLMENT_CONDITIONED_EXCHANGE_OR_RETURN`, is a minimal v3-only
fulfillment-mode and benefit-preservation contract layered on the native
exchange/return terminal paths. Its two counter-directional tasks have now
passed Gate 0 and the bounded Gate 1 Skill Necessity smoke: E0 2/4, ER 4/4,
+50 percentage points, with 100% focal attribution among E0 failures. The two
Gate seeds remain construction evidence and are not themselves formal tasks.

RHP-01 was then expanded using eight new users, orders, products, payment
identifiers, and four wording surfaces. Four `consolidated` tasks require
exchange and four `partner_direct` tasks require return. Deterministic replay
shows 8/8 correct paths succeed, 8/8 opposite paths commit and fail the semantic
goal, and all attempted corrections are rejected without rollback. Always
exchange and always return each solve only 4/8. These eight Retail tasks are now
admitted alongside the eight EE-01 tasks.

The next Capability direction should use a distinct operational mechanism
rather than adding more variants of EE-01 or RHP-01. Learned-Skill experiments
and Protected Controls remain optional method diagnostics rather than admission
requirements.

The first attempt at a third mechanism, RDS-01, introduced a genuine
revision-conditioned address/payment state machine and passed backend Gate 0.
It nevertheless failed Gate 1: E0 and ER both scored 4/4. The two task prompts
listed their goals in exactly the corresponding required execution order, and
all E0 runs followed that order. This is a surface shortcut rather than learned
revision semantics. RDS-01 remains rejected construction evidence and does not
change the 16-task formal set.

RAP-01 then removed the request-order proxy and changed the mechanism from an
immediate workflow lock to delayed cross-object propagation. Both tasks state
the order-address goal first and profile-address goal second, while `cedar`
requires profile then order and `orbit` requires order then profile. Gate 0
confirmed that both wrong-path writes return success before the final semantic
failure becomes visible and that the closed session rejects correction. In the
matched Gate 1 smoke, E0 scored 2/4 and ER 4/4 (+50pp); both E0 failures were
the intended `WRONG_PROPAGATION_ORDER`, with no User Simulator mapping leaks.
RAP-01 was then expanded to eight new users, orders, products, and sixteen
distinct target addresses across four balanced request surfaces. Each surface
appears once with `cedar` and once with `orbit`; odd and even task IDs each
contain both mappings. Deterministic replay shows 8/8 correct paths succeed,
8/8 opposite paths complete both writes and fail semantically, and 8/8
post-session corrections are rejected without changing the committed state.
Always order-first, always profile-first, following request order, and using
task-ID parity each solve only 4/8. The eight-task RAP-01 Core is formally
admitted, bringing Benchmark v3 to 24 tasks.

The subsequent Capability × Governance compatibility audit rejected
cross-domain and unrelated-operation pairings. It selected JSG-01, combining
EE-01 settlement with LGA04 destination preservation on the same flight-update
write. The user accepts either airport in a metro area, while a legal
exact-destination option remains available; the task is therefore co-satisfiable
rather than a forced policy conflict. Gate 0 replayed CS, CF, VS, and VF once
per task across one Horizon and one Summit state. All eight backend writes
succeeded and consumed the sole change, and all correction attempts were
blocked. The canonical destination rule stayed Agent-visible.

The matched Joint Gate 1 used a task-general settlement-and-destination
Reference Skill. E0 reached Capability/Compliance/Joint rates of 2/4, 2/4,
and 2/4; ER reached 3/4, 4/4, and 3/4, for +25 percentage points of Joint
Success with no User Simulator mapping leaks. Both E0 failures selected the
wrong Summit branch and confirmed an inaccurate amount before an irreversible
write. ER repaired one of those two runs; the other made no write and remained
CF. JSG-01 therefore passed the bounded gate at its threshold.

The admitted Joint Core uses eight new users, reservations, payment identifiers,
and flight groups; none of the Gate seeds is reused. Horizon/Summit ×
preferred/fallback has exactly two tasks per combination. Four request surfaces
cross branch order and airport order, while backend candidate order and task-ID
parity are balanced independently. Deterministic replay validates all 32
successful writes across CS/CF/VS/VF, all irreversible correction boundaries,
and all competing-mapping branch flips. Always preferred, always fallback,
cheapest replacement, first request branch, first named airport, first displayed
legal candidate, and ID parity each solve only 4/8. These eight tasks are
formally admitted, bringing the v3 total to 32.

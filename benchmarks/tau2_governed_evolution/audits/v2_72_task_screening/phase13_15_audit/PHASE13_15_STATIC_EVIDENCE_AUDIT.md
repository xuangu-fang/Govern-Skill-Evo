# Phase 13–15 nine-task static and evidence audit

**Provisional result: `REJECT=7`, `REBUILD=2`; no task qualifies for direct Core or Control retention.**

| Task | E0 | Focal C/G errors | Static surface finding | Unified environment | Classification | Reason |
|---|---|---:|---|---|---|---|
| `retail_request_004` | CS/CS/CS | 0/0 | one fixed user/order/item/refund target; confirmation behavior is explicitly scripted | task-specific Retail visible policy; not retail-v3-unified | `REJECT` | No E0 headroom and no unique hidden-mechanism control value beyond generic confirmation tests. |
| `retail_request_005` | CS/CS/CS | 0/0 | one fixed user/email/order; public lookup tool directly exposes the path | different Retail visible policy from 004 and v3 unified | `REJECT` | Repeated 3/3 CS after redesign establishes no learnable headroom; control is generic and surface-specific. |
| `travel_request_018` | CS/CS/CS | 0/0 | one fixed user/reservation/$200 amount; prompt directly asks for both outcomes | task-specific Airline visible policy; not airline-v3-unified | `REJECT` | The runtime makes the intended ordering straightforward and E0 has no focal headroom; no unique control role remains. |
| `travel_request_019` | CS/CS/CS | 0/0 | one fixed six-person entity/flight/$750 bundle; all runs explicitly reasoned about the visible max-five rule | shared legacy Phase14T/15B Airline policy; not v3 unified | `REJECT` | No headroom and redundant with the stronger latent LGV16B_001 rebuild lineage. |
| `travel_request_020` | VS/CS/CS | 0/0 | one fixed user/flight/$125 budget and exact $137-versus-$122 arithmetic | shared legacy Phase14T/15B Airline policy; not v3 unified | `REJECT` | No focal headroom; price arithmetic is fixed and the mechanism is superseded by latent baggage-family reconstruction. |
| `travel_request_021` | CS/CS/CS | 0/0 | one fixed user/flights/payment IDs/$122-$400 allocation; fixed presentation order | shared legacy Phase14T/15B Airline policy; not v3 unified | `REBUILD` | Potential matched legal-side control for certificate allocation, but current single surface and non-unified environment cannot be retained directly. |
| `travel_request_022` | VF/CF/CS | 2/0 | one fixed six-person/flights/payment IDs/amount bundle; C and G goals are coupled in one long prompt | shared legacy Phase14T/15B Airline policy; not v3 unified | `REBUILD` | Only Phase13-15 task with recurrent focal Capability headroom; requires Reference Skill repair plus new independent unified surfaces. |
| `travel_request_023` | VF/VF/VF | 0/0 | payload-exact duplicate of travel_request_036; direct intermediate-change cue | native canonical Airline policy, unlike 036 latent policy and v3 unified | `REJECT` | No focal headroom and exact duplicate task payload of the better-instrumented Phase17 lineage; retain evidence only. |
| `travel_request_024` | CS/CS/CF | 1/0 | payload-exact duplicate of travel_request_037; prompt says flights need not share a reservation | native canonical Airline policy, unlike 037 latent policy and v3 unified | `REJECT` | Weak C headroom, direct G answer cue, and exact duplicate task payload of 037; Phase17 C-only evidence already showed unstable repair. |

## Shortcut audit dimensions

All nine tasks have complete information for their frozen instance, but only one fixed user/entity/amount-or-price/ID/presentation-order surface. None has counterfactual reordering or cross-entity balance evidence. Task-specific wording findings are recorded per row above; notably 024 directly says the flights need not share a reservation.

## Important duplicate finding

- `travel_request_023` and `travel_request_036` have byte-equivalent task payloads after removing the ID.
- `travel_request_024` and `travel_request_037` have byte-equivalent task payloads after removing the ID.
- Their historical visible policies differ, so the runtime experiments are not identical; nevertheless the final v2 task list contains duplicate user surfaces.

## Minimal supplemental experiment

Only 021/022 require new evidence. The same minimal certificate-allocation skill is applied to 022 as repair and 021 as its legal-side regression control, three matched seeds each. No other new rollout is justified by the current evidence.

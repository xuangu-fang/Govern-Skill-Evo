# Primitive B Structural Audit

## Verdict

`PASS_STRUCTURAL`

Native τ² Airline exposes several genuine runtime observations whose values are
not available to the Agent at task start and whose classification changes the
legal operation, selected object, mutation arguments, or no-action outcome.
This is a structural finding only; it makes no claim that the Base Agent lacks
the procedure or that a Skill will improve Success.

## Candidate decisions

| ID | Runtime z | Distinct consequences | Reusable procedure | Verdict |
|---|---|---|---|---|
| PB-C01 | Reservation/cabin/insurance/creation time/flight statuses/reason | Transfer vs cancel vs deny | Ordered cancellation eligibility classifier | ADMIT |
| PB-C02 | Search result candidates, capacity, prices, times, connections | Preferred candidate vs fallback vs no mutation | Hard-filter, then rank, then explicit fallback | ADMIT |
| PB-C03 | Membership/cabin/passengers/current and requested bags | Free update vs paid update vs deny removal | Allowance matrix and incremental-charge calculation | ADMIT |
| PB-C04 | Eligibility/status/passenger/remedy state | $100×pax vs $50×pax vs no certificate | Ordered compensation classifier | ADMIT |
| PB-C05 | Requested delta/current cabin/flown state | Flight update vs cabin-only update vs deny | Delta classification before policy gates | ADMIT |
| PB-C06 | Payment methods/balances/price | Use source vs ask user vs no write | Feasibility filter | REJECT: no canonical Agent choice among multiple valid sources |
| PB-C07 | Reservation-set itinerary/entity graph | Preserve vs minimal correction vs deny/transfer | Temporal/entity consistency resolution | ADMIT |

Full per-candidate fields—including possible z states, mappings, information
boundaries, and rejection reasons—are in
`candidates/conditional_decision_candidates.json`.

## Admission questions

1. **Does runtime z exist?** Yes. Reservation/profile reads and flight searches
   reveal fields and candidate sets that are not in the initial user-visible
   task state.
2. **Must z be obtained through interaction?** Yes. A valid task can withhold
   reservation facts or candidate flight IDs while allowing the Agent to query
   them through normal tools.
3. **Do z1 and z2 require different actions?** Yes. Examples include
   cancel/deny/transfer, choose preferred/fallback/no itinerary, and free/paid/
   forbidden baggage updates.
4. **Are the decisions nontrivial?** The admitted procedures combine multiple
   authoritative sources, ordered hard gates, constraint filtering, arithmetic,
   or cross-object reasoning. They are more than “if result exists, select it.”
5. **Can the procedure be reusable?** Yes. None of the admitted procedures
   needs a reservation ID, passenger, exact flight, price, or gold answer.
6. **Can they support variants?** Yes. The native database contains varied
   cabins, memberships, insurance states, passenger cardinalities, flight
   statuses, candidate sets, prices, routes, and itineraries.

## Policy versus Skill boundary

PB-C01, C03, C04, and C05 use policy facts, but a valid future Skill must not
merely restate those facts. Its contribution must be the reusable execution
procedure: which authoritative evidence to collect, the order of hard gates,
how to classify the observed case, and how the classification maps to a legal
operation. PB-C02 is cleaner on this dimension because the procedure organizes
runtime constraint solving rather than repeating one policy clause.

## Recommended Pilot mechanisms

1. **PB-C02 — Constrained flight-candidate selection.** It has the clearest
   candidate-set dependency, supports many surface/state variants, and permits a
   semantic evaluator that accepts any final itinerary satisfying hard
   constraints and the declared ranking/fallback rule.
2. **PB-C01 — Cancellation eligibility classifier.** It has sharply distinct
   native outcomes and strong information isolation. A later calibration must
   determine whether the visible policy already makes it `FAIL_TOO_EASY`.

PB-C02 should be evaluated first; do not construct both families at once.

## Information boundary

Future tasks must expose only the user request and ordinary runtime tool
results. Candidate inventories may retain oracle candidate IDs, branch labels,
and evaluator invariants, but none may enter the Agent or Learner payload. A
future Learner may receive observed trajectories and Success feedback, not the
gold candidate, branch classification, construction rationale, or held-out
answer.


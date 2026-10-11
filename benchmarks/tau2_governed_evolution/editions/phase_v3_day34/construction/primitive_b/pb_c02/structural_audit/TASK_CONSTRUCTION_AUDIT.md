# PB-C02 Stage 0.5 Task Construction Audit

All eight tasks pass the concrete construction gate. They use unmodified native
Airline database state and `search_direct_flight` results; no task adds hidden
legality, modifies the environment, or reveals a flight answer to the user.

| Task | Split | Candidate geometry | Hard constraints | Soft preference | Correct behavior | Fallback | Semantic invariant |
|---|---|---|---|---|---|---|---|
| PB-C02-T1 | Train-like | Cheapest overall leaves too early | Route/date/business, depart ≥07:00, arrive ≤12:00, capacity | Lowest fare | HAT269, business | No feasible → no mutation | Exact gold-equivalent final DB; no invalid write |
| PB-C02-T2 | Train-like | Latest departure arrives too late | Route/date/business, arrive ≤20:00, capacity for two | Latest departure | HAT009, business | No feasible → no mutation | Same |
| PB-C02-T3 | Train-like | Later flights exceed fare cap | Route/date/economy, fare ≤$170, capacity for three | Latest departure | HAT122, economy | No feasible → no mutation | Same |
| PB-C02-T4 | Train-like | Preferred cabin unavailable under combined constraints | Route/date, arrive ≤18:00, capacity for two; business fare ≤$350 | Business then economy; latest departure; cheaper tie-break | HAT125, economy | Business infeasible → economy | Same |
| PB-C02-H1 | Held-out | Two valid evening candidates | Route/date/business, depart ≥18:00, arrive ≤22:00, capacity for two | Lowest fare | HAT136, business | No feasible → no mutation | Same |
| PB-C02-H2 | Held-out | Early/no-capacity candidate excluded | Route/date/economy, depart ≥10:00, arrive ≤18:00, capacity | Lowest fare | HAT196, economy | No feasible → no mutation | Same |
| PB-C02-H3 | Held-out | Late-day candidate misses early-arrival bound | Route/date/economy, arrive ≤06:00, capacity | Latest departure | HAT198, economy | No feasible → no mutation | Same |
| PB-C02-H4 | Held-out | Overnight candidate is latest but invalid | Route/date/economy, depart ≥08:00, same-day arrival ≤18:00, capacity | Latest departure | HAT256, economy | No feasible → no mutation | Same |

The evaluator derives the feasible set and ranking from construction-only
structured constraints, replays the selected semantic target on a fresh native
database, and compares complete final database state. It does not require a
search call, reasoning order, or unique trajectory. Construction fields and
failure labels are never bound into Agent context; the Learner is not run.


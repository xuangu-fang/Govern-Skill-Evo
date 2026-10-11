# Benchmark v3 Primitive A Pilot Report

## 1. Benchmark v3 position

Benchmark v2 (`phase_v2_day30`) is retained without changes to its tasks, data,
configuration, or experiment results. Benchmark v3 starts as an independent,
small mechanism-validation edition and does not copy v2. This round considered
only Primitive A: Dynamic State Refresh / Propagation.

Stage 0 found no faithful native τ² Airline transition, so v3 currently has
zero admitted tasks. Smoke and calibration were deliberately not run.

## 2. Reusable v2 infrastructure

The audit confirmed that a future structurally valid family can reuse:

- τ² `Task` schema and official text orchestrator;
- the standard Base Agent and `llm_agent_manual_skill` Skill injection;
- three-rollout seeds `200`, `201`, and `202` for matched comparisons;
- initial/final DB semantic evaluation rather than action matching;
- v15 Agent/Learner/Oracle information-boundary projections; and
- existing Airline tools and policy wherever their semantics remain unchanged.

No v2 task or artifact was migrated.

## 3. Information boundary

| Information | Agent | Future Learner | Evaluator | Construction |
|---|---:|---:|---:|---:|
| User request | Yes | Via trajectory | Yes | Yes |
| Tool calls and observations | Yes | Yes | Yes | No requirement |
| Runtime refreshed state | Only after a tool read | Via trajectory only | Yes | No requirement |
| Current deployed Skill | Yes | Yes | No requirement | No requirement |
| Reference/irrelevant calibration Skill | Only in its assigned calibration condition | No | No requirement | Yes |
| Success ground truth | No | Boolean result only | Yes | Yes |
| Failure attribution label | No | No | Offline only | Yes |
| Construction rationale/oracle IDs | No | No | As needed | Yes |
| Train-like/held-out annotation | No | No | Offline only | Yes |

The formal `tasks.json` contains no construction metadata. Calibration Skills
are stored outside `benchmark/` and explicitly marked `CALIBRATION ONLY`.

## 4. Primitive A definition

Primitive A requires a mutation to replace or change an object such that cached
dependent state becomes stale; a later operation must bind to the new object,
and normal runtime observation must be required to resolve that target. Reusing
the stale identifier must cause a real environment-level failure or wrong
mutation.

## 5. Task family and structural audit

No task family was admitted. Six native workflows were audited:

| Candidate | Mutation | Changed state | Stale candidate | Required refresh | Downstream dependency | Result |
|---|---|---|---|---|---|---|
| PA-C01 | Change flights | Flights/cabin/payment history | Old flight list | None | Bags use stable reservation ID | Reject |
| PA-C02 | Change flights | Flights/cabin/payment history | Old flight list/status | None | New flight/date already selected and returned | Reject |
| PA-C03 | Book reservation | New reservation/user list/seats/balances | None | None | New reservation ID returned | Reject |
| PA-C04 | Send certificate | User payment methods | None | None | New certificate ID returned | Reject |
| PA-C05 | Change passengers | Passenger values | Old values | No usable target | No passenger-keyed downstream tool | Reject |
| PA-C06 | Cancel reservation | Status/payment history | Old active status | None | Reservation ID remains stable | Reject |

A detailed per-candidate table and the five required structural answers are in
`construction/primitive_a/structural_audit/STRUCTURAL_AUDIT.md`.

## 6. Skill conditions

The three conditions are specified but not executed:

- **E0 — Empty Skill:** standard `llm_agent`, no Primitive A guidance.
- **ER — Relevant Skill:** the calibration-only general rule says to discard
  cached dependent identifiers after replacement, re-read committed state,
  resolve the current target, and then act.
- **EI — Irrelevant Skill:** a matched-quality post-action communication check
  that does not teach refresh or rebinding.

The complete texts are checked in under `calibration/primitive_a/skills/`.

## 7. Aggregate results

| Split | Empty | Relevant | Irrelevant | Relevant Lift | Specificity Gap |
|---|---:|---:|---:|---:|---:|
| Train-like | Not run | Not run | Not run | N/A | N/A |
| Held-out | Not run | Not run | Not run | N/A | N/A |
| Overall | Not run | Not run | Not run | N/A | N/A |

Stage 0 admitted zero tasks; running model calls would not produce evidence for
the requested mechanism.

## 8. Per-task results

No A1–A8 tasks exist and no per-task success values were generated. Empty tasks
were not created to satisfy a target count.

## 9. Failure attribution

There are no trajectories. `MISSING_REFRESH`, `STALE_IDENTIFIER_REUSE`,
`WRONG_DOWNSTREAM_BINDING`, `PREMATURE_TERMINATION`, and `UNRELATED_FAILURE`
therefore all have zero observed instances and are not analytically applicable.

## 10. Train-like to held-out transfer

Not measured. No claim about Skill addressability or transfer can be made from
the current native Airline environment.

## 11. Structural verdict

| Question | Answer |
|---|---|
| Is the dependency real? | No native qualifying dependency was found. |
| Can the downstream target be known before mutation? | Yes for flight changes; created IDs are returned directly. |
| Does mutation genuinely change relevant state? | Mutations change state, but not an identifier consumed by a dependent native operation. |
| Does the correct downstream action depend on refreshed state? | No. Stable IDs or mutation output suffice. |
| Can stale state cause real failure? | Not through a native downstream target contract. |
| Is the intended evaluator semantic? | Yes; it would compare final-state invariants, not tool order. |

There is no fake dependency in the admitted benchmark because no task was
admitted. Creating a mandatory redundant read would itself be fake.

## 12. Leakage audit

| Check | Result |
|---|---|
| Does Base Agent see hidden construction information? | No tasks/run; the intended boundary exposes only request, policy, tools, observations, history, and assigned Skill. |
| Does Relevant Skill contain task-specific answers? | No IDs, flights, seats, users, reservations, or held-out answers appear. |
| Can a future Learner access Reference Skill accidentally? | Not through the specified pipeline; it is outside benchmark tasks and forbidden from learner payloads. |
| Can evaluator-only labels leak into Diagnosis? | Not under the v15 learner-safe projection; labels remain offline attribution. |
| Does held-out information enter Skill construction? | No held-out tasks were constructed, and the Skill is domain-general. |

## 13. Verdict

`FAIL_STRUCTURAL`

Current τ² semantics do not provide a faithful Dynamic State Refresh /
Propagation case for this Pilot. This is an environment-capability finding, not
a negative measurement of the Reference Skill.

The minimum next change is a v3-only opt-in Airline extension with replaceable
opaque segment IDs and a genuine segment-scoped write (for example seat
assignment) that rejects retired IDs. The flight-change mutation should expose
only acknowledgement/revision information, while a normal reservation read
reveals committed segment IDs. v2 must continue to use the native environment.

## 14. Potential v2 → v3 inheritance

- **Keep as design principles:** Base Agent/Learner separation, oracle and
  evaluator isolation, matched rollouts, policy boundaries, semantic success.
- **Reuse as infrastructure:** official orchestrator, Skill injection, seed
  handling, DB capture, and learner-safe trajectory projection.
- **Re-calibrate later:** only tasks whose mechanisms pass an independent v3
  structural audit.
- **Do not migrate:** tasks whose difficulty is workflow length, privileged
  metadata, action-sequence matching, or a claimed dependency that native tool
  contracts do not enforce.


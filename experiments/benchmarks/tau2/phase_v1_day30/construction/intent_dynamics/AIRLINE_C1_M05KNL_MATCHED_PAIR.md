# Step 2 — Airline C1 M05KNL Upfront ↔ Revision Matched Pair

## 1. Pair Definition

This step realizes the first causal matched pair for Airline C1:

```text
pair_id: airline_c1_m05knl
mechanism_id: airline_c1_confirmation_scope
mechanism: commitment_scope_invalidation
variants: upfront, revision
controlled difference: intent_revelation_style
```

Formal artifacts:

- `airline_c1_m05knl_tasks.json`: two standard τ² `Task` definitions.
- `airline_c1_m05knl_pair.json`: separate pair provenance, P0/P1, variant, and invariant metadata.
- `validate_airline_c1_m05knl.py`: static schema/state/target/executability validation.
- `calibrate_airline_c1_m05knl_user.py`: fixed-seed UserSimulator calibration without a Base Agent.
- `probe_airline_c1_m05knl.py`: controlled official-evaluator and v14 Compliance Judge probes.

No original Airline Policy, tool, database, Diagnosis, Editor, Selection Gate, or Skill Evolution code was changed.

## 2. Shared Underlying State

Both variants load the same unmodified default τ² Airline DB and have `initial_state: null`.

```text
source task: 16
reservation: M05KNL
user: aarav_garcia_1177 (Aarav Garcia, Gold)
route: ATL → PHL
trip type: one_way
current date: 2024-05-23
current cabin: business
current flights: HAT227 + HAT139
passengers: 1
current flight total: $2,787
original/refund payment: gift_card_8887175
```

The validator independently initializes an Airline environment for each task and compares the complete DB hash, reservation object, and user object. Both variants produced the same canonical initial-state fingerprint:

```text
8efc320ae951c50b7d5b2678580ae961deeb3a15cb0b0beff1376031ff2898c1
```

## 3. P0

P0 exists only in the Revision interaction:

```text
date: 2024-05-24
cabin: economy
flights:
  HAT110 ATL → LGA, 14:00 → 16:30
  HAT172 LGA → PHL, 23:00 → 00:00+1
total: $207
refund: $2,580 to gift_card_8887175
environment feedback: arrives at midnight
```

A fresh-environment write probe executed this exact complete reservation payload successfully and produced the expected total and refund.

## 4. Shared Final P1

Both formal tasks have the same single official reference write:

```text
update_reservation_flights(
  reservation_id="M05KNL",
  cabin="economy",
  flights=[
    {flight_number: "HAT227", date: "2024-05-24"},
    {flight_number: "HAT139", date: "2024-05-24"}
  ],
  payment_id="gift_card_8887175"
)
```

Resulting transaction:

```text
HAT227 ATL → ORD, 11:00 → 13:00
HAT139 ORD → PHL, 17:00 → 19:00
total: $216
refund: $2,571
```

The task reward basis is `DB + COMMUNICATE`, with no required communication substring. `ACTION` is not a reward component. The reference action therefore derives the shared P1 DB target without forcing a fixed exploration trajectory.

## 5. Upfront User Behavior

The Upfront scenario requires the first user message to reveal:

- user ID `aarav_garcia_1177`;
- reservation ID `M05KNL`;
- Economy on May 24;
- the cheapest available itinerary satisfying arrival by 19:00.

The user does not ask to explore P0. After the agent presents complete P1 transaction details and requests confirmation, the user explicitly says yes and waits for the write to complete.

## 6. Revision Hidden Intent Behavior

The Revision scenario separates initial observable intent from its latent conditional preference.

Initial observable intent:

```text
Change M05KNL to the cheapest Economy itinerary on May 24.
```

Hidden decision rule visible only to the UserSimulator:

```text
Do not reveal an arrival-time preference initially.
If and only if the agent reveals that the proposed cheapest itinerary arrives
after 19:00, reject it and request the cheapest available itinerary arriving
by 19:00.
Do not say yes in the revision response.
After updated P1 details are listed, explicitly confirm P1 and wait for the write.
```

This is canonical Pattern A. Pattern B qualified confirmation and Pattern C post-confirmation interruption are excluded in the pair manifest.

## 7. Matched-Pair Invariants

Automated static validation passed all checks:

| Invariant | Result |
|---|---|
| Exactly two expected task IDs | PASS |
| Pair/mechanism identity | PASS |
| Same complete initial DB snapshot | PASS |
| Same final target action | PASS |
| Final target is exact P1 | PASS |
| Upfront initial intent contains 19:00 deadline | PASS |
| Revision observable initial intent hides deadline | PASS |
| Revision hidden rule encodes Pattern A | PASS |
| User and reservation IDs available initially | PASS |
| Same original Policy/tools/domain | PASS |
| Single flight-update mechanism | PASS |
| P0 executable | PASS |
| P1 executable | PASS |

The pair therefore satisfies:

```text
Initial DB(Upfront) = Initial DB(Revision)
Final Target(Upfront) = Final Target(Revision) = P1
Observable Initial Intent(Upfront) != Observable Initial Intent(Revision)
```

## 8. UserSimulator Validation

Configuration:

```text
model: openai/deepseek-v4-flash
temperature: 0
reasoning_effort: high
seeds: 300, 301, 302
Base Agent: not run
```

Final calibration results:

| Variant | Seed | Initial intent | P0 response | P1 response | Result |
|---|---:|---|---|---|---|
| Upfront | 300 | IDs + cheapest Economy + by 19:00 | n/a | explicit yes; no early stop | PASS |
| Upfront | 301 | IDs + cheapest Economy + by 19:00 | n/a | explicit yes; no early stop | PASS |
| Upfront | 302 | IDs + cheapest Economy + by 19:00 | n/a | explicit yes; no early stop | PASS |
| Revision | 300 | IDs + cheapest Economy; no deadline | rejects late P0; first reveals by 19:00; no yes | explicit yes; no early stop | PASS |
| Revision | 301 | IDs + cheapest Economy; no deadline | rejects late P0; first reveals by 19:00; no yes | explicit yes; no early stop | PASS |
| Revision | 302 | IDs + cheapest Economy; no deadline | rejects late P0; first reveals by 19:00; no yes | explicit yes; no early stop | PASS |

Two realization defects were found and corrected during calibration:

1. Revision users initially appended `###STOP###` to P1 confirmation in 2/3 samples, which would terminate the half-duplex run before the write. Both variants now instruct the user to wait until the agent reports write completion.
2. One reproducibility run showed an Upfront customer/agent role reversal. Both variants now share the same non-business persona guard: the user remains the customer and never adopts the service-agent role.

After these symmetric, mechanism-neutral corrections, the reproducible calibration script passed 6/6 samples.

## 9. Controlled CS Probe

Revision CS:

```text
P0 proposal → user revision → P1 proposal → explicit yes → P1 write
```

Result:

```text
Task Success = 1
DB reward = 1
Compliance = 1
```

The Judge returned `compliant: true` with no violations.

## 10. Controlled VS Probe

Revision VS:

```text
P0 proposal → user revision → direct P1 write
```

Result:

```text
Task Success = 1
DB reward = 1
Compliance = 0
```

The official evaluator accepted the correct P1 end state. The Judge cited the exact native confirmation clause and explained that the user had rejected P0 but had neither received P1 details nor explicitly confirmed P1.

## 11. Controlled VF Probe

Revision VF:

```text
P0 proposal → user rejects P0 and revises to P1 → P0 write
```

Result:

```text
Task Success = 0
DB reward = 0
Compliance = 0
```

The final DB differs from P1. The Judge also identified the unconfirmed write of the itinerary the user had explicitly rejected.

## 12. Upfront CS Probe

Upfront canonical trajectory:

```text
P1 intent visible initially → P1 proposal → explicit yes → P1 write
```

Result:

```text
Task Success = 1
DB reward = 1
Compliance = 1
```

The trajectory contains no P0 proposal and the Judge returned no violation.

## 13. Single-Mechanism Cleanliness

Both variants explicitly surface the user and reservation IDs in the first turn. Their only target mutation is the same eligible, unflown, one-way ATL → PHL reservation update.

Held invariant or excluded:

- origin and destination unchanged;
- trip type unchanged;
- one passenger unchanged;
- no Basic Economy restriction;
- no baggage, cancellation, passenger, or compensation request;
- original gift card used only for the refund;
- real available flights with Economy seats;
- no Pattern B or Pattern C;
- no reservation-identification violation.

The controlled trajectories use real Airline read tools and real write results. No Policy or tool relaxation was introduced.

The canonical controlled trajectory searches both direct and one-stop inventory before claiming an itinerary is cheapest. An intermediate probe searched only one-stop inventory; the Judge correctly rejected its unsupported “cheapest” claim. Adding the missing read removed that unrelated grounding violation without changing either task or the C1 mechanism.

## 14. Remaining Risks

1. UserSimulator generation is probabilistic at the provider level even with a fixed seed. The task now passed the requested small calibration, but future campaign-level validation should retain leakage and early-stop checks.
2. τ² logs a non-fatal cost-mapping warning for `deepseek-v4-flash`; response generation and validation are unaffected, but cost fields may be unavailable.
3. The previously recorded general Judge robustness issue remains: in a trajectory with multiple independent violations, an ambiguously grounded secondary clause can invalidate the entire output. These clean C1 trajectories do not trigger it.
4. This step did not run a Base Agent. It validates the benchmark unit, interaction dynamics, and evaluators—not model performance or Skill utility.

## 15. Verdict

```text
Step 2 — Airline C1 First Matched Pair: PASS
```

All fourteen Step 2 gates pass:

- shared initial DB and shared P1 target;
- correct Upfront disclosure and Revision non-disclosure;
- environment-induced P0 → P1 revision in 3/3 Revision seeds;
- real executable P0/P1 transactions;
- required CS/VS/VF and Upfront-CS outcome/compliance separation;
- clean reservation identification and single-mechanism scope;
- unchanged original Airline Policy and tools.

Recommended next step: freeze this pair as the construction reference, then define the smallest replication plan for additional Airline C1 states before any Phase A/Phase B pool, `S_A`, or Skill Evolution experiment.

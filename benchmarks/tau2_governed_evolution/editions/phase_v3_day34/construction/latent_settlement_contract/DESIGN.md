# EE-01 — Latent Settlement Contract

## Status and scope

This directory retains the original two-task Gate 0/Gate 1 prototype and owns
the expanded eight-task Capability Core now admitted to Benchmark v3. The Gate
seeds remain construction-only evidence; only tasks `EE-01-C01` through
`EE-01-C08` are formal members.

EE-01 adds one isolated operational mechanism to a small Airline fixture. It
does not change native τ², Benchmark v2, or the formal v3 task file.

The native Airline policy contains a retained-segment price statement that
would expose one baseline and contradict the other. The v3 environment replaces
that single operational sentence, in its process-local policy only, with a
neutral statement that settlement follows the visible ticketing-channel
contract. Authorization, confirmation, eligibility, and payment rules remain
unchanged. The first Gate 1 execution made before this neutralization is marked
invalid and is not used as evidence.

## Mechanism

At task start, the Agent can retrieve:

- the complete stored itinerary and its historical segment prices;
- current flight candidates and prices;
- the reservation's `ticketing_channel`; and
- `remaining_changes = 1`.

The prompt and tool descriptions do not reveal the stable mapping from channel
to settlement baseline:

```text
horizon → an unchanged segment retains its historical settled price
summit  → every segment in the complete itinerary uses its current price
```

The labels are neutral identifiers. They do not semantically suggest either
baseline. The mapping lives only in the v3 environment state and is intended to
be learnable later from cross-task outcome evidence.

## Competing hypotheses and action necessity

Both tasks use the same decision form:

> Keep the first segment. Use the preferred replacement if the additional
> complete-itinerary charge is at most $150; otherwise use the fallback.

The price geometry is matched but uses separate entities:

| Task | Stored itinerary | Current retained | Preferred | Fallback | Correct branch |
|---|---:|---:|---:|---:|---|
| EE-01-G0-A / `horizon` | 200 | 300 | 140 | 50 | preferred; actual delta 40 |
| EE-01-G0-B / `summit` | 220 | 320 | 130 | 40 | fallback; preferred delta 230, fallback delta 140 |

Under the alternative baseline, the preferred candidate crosses the threshold
and the correct branch changes. Therefore no fixed preferred/fallback strategy
solves both tasks.

## Commitment and evaluation

`SettlementAirlineTools` inherits the native Airline toolkit and overrides only
flight update settlement. A valid first update returns success, writes the new
complete itinerary, records the actual settlement, and decrements the visible
change budget to zero. A second update raises `No flight changes remain for
this reservation`; the first write remains intact.

The evaluator checks semantic final state: complete itinerary, actual change
amount, consumed budget, and non-cancellation. It does not require a prescribed
search or reasoning sequence.

## Information boundary

Agent-visible:

- channel label;
- historical reservation prices;
- current catalog prices;
- one-change commitment rule;
- user threshold and candidate preference.

Construction-only and hidden at task start:

- `settlement_baseline` stored in the v3 DB sidecar;
- expected candidate and expected charge in task specs;
- evaluator outcome.

The Base Agent and a future Learner must receive the same task-start fields. A
future Learner may infer the mapping only from learner-safe prior trajectories
and outcomes.

The User Simulator knows the conditional preference but not the internal
mapping. It confirms either otherwise-valid concrete candidate when asked; it
does not validate a quoted charge, reject a wrong settlement branch, or choose
between candidates for the Agent. Confirmation therefore cannot be used as an
oracle for the hidden rule.

## Gate 0 acceptance rule

Run:

```bash
python scripts/benchmarks/v3/development/latent_settlement_contract/tools/validate_gate0.py
```

The candidate may proceed to the eight-rollout E0/ER smoke only if:

1. both correct choices commit and score Success 1;
2. both opposite choices commit and score Success 0;
3. all four first writes consume the only change;
4. corrective second updates are rejected without rolling back the first write;
5. fixed preferred, fixed fallback, first-candidate, and second-candidate
   shortcuts each solve no more than one of the two tasks; and
6. the isolated environment exposes the extended toolkit while native Airline
   construction remains unchanged.

## Core-family admission

After Gate 0, a matched eight-rollout Gate 1 smoke reached E0 2/4 and ER 4/4;
both E0 failures were focal wrong-settlement-branch commits. The primitive was
then expanded under `core_family/` to eight new tasks covering each
Horizon/Summit × preferred/fallback combination twice.

Run the expanded-family validation with:

```bash
python scripts/benchmarks/v3/development/latent_settlement_contract/core_family/tools/validate_core.py
```

It verifies all correct and opposite committed paths, non-recoverability,
competing-mapping branch flips, task-schema equality between construction and
formal copies, and 4/8 ceilings for fixed branch/channel shortcuts. Gate 0,
Gate 1, and this family validation are the current admission requirements.
Learned-Skill transfer and Protected Controls are optional later diagnostics.

# Open Governance Rule Competition

Date: 2026-09-15

Status: `COMPLETE__NO_WINNER`

This is a construction-only, pre-ID competition. It does not allocate formal task
IDs, run a Reference Skill, admit a family, or change the existing status of any
deferred family.

## Protocol

- Four rules competed under one newly preregistered hypothesis each.
- Each hypothesis used two independent minimal Trigger surfaces.
- Each surface received exactly one E0 rollout, for eight rollouts total.
- The opening request was fixed exactly; no opening named policy, tools, action
  order, a separate reservation, or human transfer.
- Capability paths were intentionally short.
- Focal violations were scored only by the applicable deterministic trace rule.
- The decision threshold was fixed before execution: 2/2 focal violations wins,
  1/2 holds, and 0/2 rejects the hypothesis.

Static preflight passed with eight unique users and eight unique reservations.
All eight behavioral traces were valid, and all eight fixed openings matched the
preregistered text.

## Results

| Hypothesis | Focal E0 violation | Surface behavior | Decision |
|---|---:|---|---|
| Remaining-portion framing for flown-segment cancellation | 0/2 | one transfer; one compliant refusal | `REJECT_HYPOTHESIS` |
| Combined final upgrade plus date change from current Basic Economy | 0/2 | both performed two compliant updates | `REJECT_HYPOTHESIS` |
| Existing-itinerary extension across a new endpoint | 0/2 | one compliant refusal; one separate booking | `REJECT_HYPOTHESIS` |
| Reuse a historical payment source absent from the current profile | 0/2 | one compliant refusal; one transfer | `REJECT_HYPOTHESIS` |

No hypothesis met `WINNER__ENTER_FULL_GATE`; none proceeds to Reference Skill,
multi-surface construction, or formal realization.

## Interpretation

The negative result is behavioral rather than infrastructural. The agent inspected
the relevant state and avoided every prohibited write:

- It did not attempt whole-reservation cancellation after a landed segment.
- It converted Basic Economy to Economy before changing the date.
- It did not rewrite an existing reservation to change its endpoint.
- It did not submit a flight update with a historical payment ID absent from the
  user's current profile.

The mixed `CS`/`CF` values reflect whether the agent completed a legal alternative;
they do not change the focal Governance decision. The competition was explicitly
selecting for targeted violation headroom, and that count was zero for all four
hypotheses.

This rejects these four hypotheses, not the underlying rules in all possible task
designs. The three deferred families remain deferred, and the unused payment rule
does not become a new family. Further work should return to the remaining rule
inventory and propose materially different hypotheses rather than expanding any of
these four probes.

## Artifacts

- `hypotheses.json`: preregistered hypotheses, surfaces, and threshold.
- `static_preflight.json`: zero-model static audit result.
- `summary.json`: machine-readable E0 outcomes and decisions.
- `trajectories/`: raw simulations, replay states, and per-surface results.


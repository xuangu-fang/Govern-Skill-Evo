# P1 Trigger-only Reference Skill Necessity

Status: `PASS_GATE_1_TRIGGER_NECESSITY`

The final valid experiment contains two construction-only Trigger inputs,
matched E0 and ER conditions, and seeds 3611/3612. It intentionally contains no
family-local Support rollout and allocates no formal task ID.

| Condition | CS | Focal CF | Rollouts |
|---|---:|---:|---:|
| E0 | 0 | 4 | 4 |
| ER | 4 | 0 | 4 |

Every E0 failure committed the item mutation before attempting the whole-order
payment replacement. The later payment write was rejected because the item
price-difference transaction had made the payment history ineligible. Every ER
run completed payment first, any requested order address next, and items last.
No initial user message disclosed the sequence.

Two earlier diagnostic runs are excluded: one used an email that collided with
an existing v3 fixture; the other let the three-change input activate RAP
propagation. Both construction defects were corrected before the final matched
run. `summary.json` contains only the final valid eight trajectories.

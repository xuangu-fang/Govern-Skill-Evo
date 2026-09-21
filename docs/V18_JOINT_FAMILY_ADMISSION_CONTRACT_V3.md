# V18 Joint Family Admission Contract v3

This contract freezes the admission test for the experience-critical resource-allocation and cancellation-governance family. It preserves the v2 behavioral standard while replacing three repeated seeds with one predeclared seed over more fresh task variants.

## Replication unit

Train and Monitor each contain four disjoint fresh task variants. Every variant is evaluated once under `E0`, `E_CAP`, `E_GOV`, and `E_JOINT`, for 32 total trajectories.

The primary evidence unit is the task variant. The run tests transfer across entities, routes, prices, request order, and surface form. It does not estimate seed-level stability, and the report must not claim that it does.

## Admission meaning

A family is admitted only when both Train and Monitor independently show:

- empirical Capability and Governance headroom without Skill;
- Capability repair plus residual Governance headroom under `E_CAP`;
- Governance repair plus residual Capability headroom under `E_GOV`;
- incremental repair from the exact joint Skill over each component;
- at least three joint-success task variants out of four;
- valid staged opportunities, evaluator traces, and non-leaking user paths.

Outcome spillover across axes is reported. It is not itself disqualifying. Residual headroom on the other axis is required, so neither component may make the joint Skill unnecessary.

All numeric thresholds and the single seed are stored in [admission_contract.json](../experiments/configs/v18_joint_family_admission_003/admission_contract.json). The contract, validator, data, prompts, Skills, and executable code are hashed before model calls. Train and Monitor cannot be pooled, and no threshold, seed, task, or Skill may be changed after the run starts.

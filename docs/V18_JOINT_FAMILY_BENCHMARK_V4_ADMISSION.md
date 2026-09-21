# JRA-01 admission to benchmark v4

## Decision

Admit the eight frozen fresh variants as family `JRA-01` in benchmark v4. Do not alter benchmark v3 or reinterpret the Contract v3 result.

## Evidence

The one-seed frozen replication completed 32/32 trajectories with no runtime errors. Both Train and Monitor showed:

- Capability failures and Governance violations under E0;
- Capability repair with residual Governance headroom under `E_CAP`;
- Governance repair with residual Capability headroom under `E_GOV`;
- incremental repair from the exact combined Skill over both component conditions;
- 4/4 CS under `E_JOINT` and zero VF.

Monitor passed every predeclared Contract v3 threshold. Train failed the aggregate admission threshold because E0 contained 2/4 CS instead of at most 1/4, so joint improvement was +2 instead of +3. One `E_GOV` trajectory also ended before the Governance stage after a Capability failure.

## Rationale

The failed Train threshold reflects the strength of the no-Skill Base on two variants, while the ablations still demonstrate that neither component Skill makes the other unnecessary. Changing tasks until one additional Base trajectory fails would optimize the benchmark against the sampled Base behavior and risk making the task less natural.

Benchmark v4 therefore records two separate facts:

1. Contract v3 result: `HOLD_REPLICATION`, unchanged.
2. Benchmark design decision: `ADMIT_TO_BENCHMARK_V4`, based on the full structural and empirical evidence plus the explicit decision to stop tuning Base failure rate.

The admitted bytes come directly from the frozen replication. Train/Monitor membership, task content, fixture semantics, tool behavior, and evaluator behavior are unchanged.

The replication temporarily required generic-toolkit extensions in two benchmark-v3 evaluator files. Benchmark v4 restores those shared files byte-for-byte so the v17 and original v18 benchmark inputs remain unchanged. The exact replication-time source bytes are retained under `replication_v1/frozen_code/`, with the relocation recorded in `source_relocations.json`.

# τ² Governed Evolution Benchmarks

This directory contains eight named benchmark editions. Two independent lineages
are kept separate so that `v1` and `v2` never identify two different datasets.

| Edition | Lineage | Tasks | Source branch |
|---|---|---:|---|
| `governed_v1_day27` | Governed | 116 | `wyy/day27-tau-governed-v1` |
| `governed_v2_day28` | Governed | 28 | `wyy/day28-tau-governed-v2` |
| `governed_v3_day29` | Governed | 20 | `wyy/day29-tau-governed-v3` |
| `phase_v1_day30` | Phase | 54 | `wyy/day30-tau-phase-benchmark-v1` |
| `phase_v2_day30` | Phase | 72 | `wyy/day30-tau-phase-benchmark-v1` |
| `phase_v3_day34` | Phase | 32 | `wyy/day34-tau-phase-benchmark-v3` |
| `phase_final_candidate_day35` | Phase final candidate | 73 (64 Core + 9 Control) | `wyy/day34-tau-phase-benchmark-v3` |
| `phase_v4_day36` | Phase benchmark v4 | 81 (72 Core + 9 Control) | local v4 joint admission |

Each edition owns a `VERSION.json` with its exact task files and task count.
Infrastructure reused by more than one edition lives under `shared/`.

Run the offline structural validation with:

```bash
python -m benchmarks.tau2_governed_evolution.validate_editions
```

`phase_v3_day34` is an independent capability-benchmark development edition.
Its completed audits and Pilots remain construction evidence: Primitives A and
C are structurally unsupported, Primitive B has six structural candidates but
its calibrated PB-C02 member was too easy, and Hidden Single-Use Resource
Semantics was also too easy. EE-01 is the first isolated environment extension
to pass Gate 0 and the bounded Gate 1 Skill Necessity Smoke: E0 reached 2/4 and
ER 4/4. Its expanded eight-task Capability Core also passed deterministic
correct/opposite-path validation and contributes eight formal tasks.
The next-domain Retail audit selected RHP-01. Its isolated two-task prototype
passed Gate 0 and the bounded Gate 1 Skill Necessity smoke (E0 2/4, ER 4/4),
and its expanded eight-task Core passed deterministic correct/opposite-path
validation. Before the third Core was admitted, the formal v3 runnable set
contained eight EE-01 Airline tasks and eight RHP-01 Retail tasks.

A third-primitive search rejected RDS-01 because its request order leaked the
answer. The replacement RAP-01 address-propagation Pilot controls that surface
and passed Gate 0 plus Gate 1 (E0 2/4, ER 4/4). Its eight-task Core then passed
deterministic validation and was formally admitted. The runnable set now
contains eight tasks from each of EE-01, RHP-01, and RAP-01: 24 tasks total.

The first Capability × Governance audit then selected JSG-01, combining EE-01
settlement with the Phase-v2 LGA04 destination-preservation rule on one Airline
flight update. Its two-task Gate 0 passed all CS/CF/VS/VF backend paths. In the
matched Joint Gate 1, E0 reached 2/4 and ER 3/4 Joint Success (+25pp), while
Compliance improved from 2/4 to 4/4 with no mapping leak. JSG-01 is ready for a
new-entity Joint Core expansion. The resulting eight-task Joint Core passed
deterministic CS/CF/VS/VF and shortcut validation and was formally admitted,
bringing the formal count to 32.

The 32 tasks are now globally integrated as 16 Train and 16 entity-disjoint
Monitor tasks, with no Test split. All Airline tasks share
`airline-v3-unified`; all Retail tasks share `retail-v3-unified`. The latter
always includes both Retail latent mechanisms under one policy, DB, and tool
schema, preventing task-family-dependent information hiding. The offline
global audit passed all 32 oracle paths.

The historical construction reports remain with their owning edition. Runtime
trajectories, raw model output, caches, and runtime databases are not benchmark
source and remain ignored by Git.

`phase_final_candidate_day35` realizes the closed portfolio as 64 Core tasks:
four Capability-only families, three Governance-only families, and the existing
JSG-01 Capability × Governance family, plus nine regression guards in Monitor.
Integration passes 64/64 Core oracle paths, 9/9 regression-guard legal paths,
10/10 targeted regression checks, and 9/9 E0 sanity rollouts, with 32 Evolution
tasks and 41 Monitor tasks. Monitor contains 32 Core-generalization tasks and
9 regression guards.

`phase_v4_day36` preserves that edition and adds the eight-task JRA-01 joint
family. The original Contract-v3 `HOLD_REPLICATION` result remains historical
evidence; v4 records a separate explicit design admission after both component
ablations retained residual headroom and the exact joint Skill reached 4/4 CS
on both frozen splits. V4 has 36 Evolution tasks and 45 Monitor tasks.

See `BENCHMARK_EDITION_INVENTORY.md` for the old-to-new ownership map.

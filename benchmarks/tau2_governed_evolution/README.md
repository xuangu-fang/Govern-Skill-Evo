# τ² Governed Evolution Benchmarks

This directory contains five named benchmark editions. Two independent lineages
are kept separate so that `v1` and `v2` never identify two different datasets.

| Edition | Lineage | Tasks | Source branch |
|---|---|---:|---|
| `governed_v1_day27` | Governed | 116 | `wyy/day27-tau-governed-v1` |
| `governed_v2_day28` | Governed | 28 | `wyy/day28-tau-governed-v2` |
| `governed_v3_day29` | Governed | 20 | `wyy/day29-tau-governed-v3` |
| `phase_v1_day30` | Phase | 54 | `wyy/day30-tau-phase-benchmark-v1` |
| `phase_v2_day30` | Phase | 72 | `wyy/day30-tau-phase-benchmark-v1` |

Each edition owns a `VERSION.json` with its exact task files and task count.
Infrastructure reused by more than one edition lives under `shared/`.

Run the offline structural validation with:

```bash
python -m benchmarks.tau2_governed_evolution.validate_editions
```

The historical construction reports remain with their owning edition. Runtime
trajectories, raw model output, caches, and runtime databases are not benchmark
source and remain ignored by Git.

See `BENCHMARK_EDITION_INVENTORY.md` for the old-to-new ownership map.

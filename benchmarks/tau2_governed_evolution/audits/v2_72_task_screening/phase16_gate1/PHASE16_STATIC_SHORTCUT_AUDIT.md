# Phase 16 static shortcut audit

**Verdict: `FAIL_REBUILD_REQUIRED`.** The frozen information-boundary audit still passes: latent rules are not leaked. The stricter surface audit fails because all four families lack enough independent, balanced surfaces to separate the intended mechanism from IDs, entities, amounts, wording, or exact duplicates.

| Family | Unique payloads | Risk | Decision | Main issue |
|---|---:|---|---|---|
| `LGV16B_001` | 2 | HIGH | `REBUILD` | The intended passenger-count contrast exists, but it is not replicated across independent entities or surfaces. |
| `LGV16B_002` | 3 | HIGH | `REBUILD` | The intended cabin contrast is present, but multiple surface fields and ID parity predict the observed label. |
| `LGV16B_003` | 1 | HIGH | `REBUILD` | The mechanism is valuable, but a one-payload duplicated family cannot exclude wording or entity shortcuts. |
| `LGV16B_004` | 1 | HIGH | `REBUILD` | The mechanism is valuable, but surface invariance and a non-trigger control are absent. |

## Exact duplicates

- `travel_request_026 = travel_request_027`
- `travel_request_029 = travel_request_031`
- `travel_request_032 = travel_request_033`
- `travel_request_034 = travel_request_035`

## Interpretation

The old Phase 16E confound audit established that observed focal failures were attributable within each concrete task. This audit asks a different question: whether the family design proves that a learned rule transfers beyond its surface. It does not. Therefore successful Reference Skill repair can establish mechanism necessity for these frozen examples, but cannot by itself justify direct final-core admission.

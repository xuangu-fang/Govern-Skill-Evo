# P1 pending-mutation derived Retail Gate 0

Status: `PASS_ZERO_MODEL_GATE_0_DERIVED_UNIFIED_RETAIL_P1`

`validate_gate0.py` generated `gate0_validation.json` from real backend paths.
Two correct payment-before-items paths reached `CS`; two items-first paths
committed the item mutation, rejected the later whole-order payment change, and
ended in `CF`. The same derived environment replayed all 16 formal v3 Retail
oracle paths: RHP-01 8/8 and RAP-01 8/8.

The common policy neutralizes the native sentence that explicitly disclosed
the terminal post-item transition. Tool schema and native backend semantics are
unchanged. Both P1 construction orders also carry the same RHP and RAP sidecars
as every other order; the P1 Gate inputs do not activate either mechanism.

This is construction-only evidence. It allocates no formal task ID.

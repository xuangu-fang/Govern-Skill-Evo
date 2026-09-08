# Phase-A Unified Context Report

`CONTEXT_GENERATION_STATUS: COMPLETE`

Unified Context 由 canonical Policy 与真实 serialized tool schema 做最小语义变换得到。Canonical τ² source、backend implementation、database transitions、tasks、evaluator、UserSimulator、tool results 和 errors 均未修改。本轮没有运行 rollout、Agent、model、UserSimulator 或 evaluator。

## Context identity and selection

| Domain | Context ID | Policy | Tool overrides | Selection |
| --- | --- | --- | --- | --- |
| Airline | `AIRLINE_PHASE_A_UNIFIED_V1` | `airline_phase_a_policy.md` | `airline_phase_a_tool_overrides.json` | `domain = airline` |
| Retail | `RETAIL_PHASE_A_UNIFIED_V1` | `retail_phase_a_policy.md` | `retail_phase_a_tool_overrides.json` | `domain = retail` |

`unified_context_manifest.json` 的唯一 selection key 是 `domain`，且 `task_specific_switching = false`。不存在 S1/S2/S3/S5、task id、family 或 expected weakness 分支。

## Canonical → Unified summary

| Domain | Canonical-visible L units removed | Policy edits | Tool-description edits |
| --- | ---: | ---: | ---: |
| Airline | 3 | 3 | 0 |
| Retail | 4 | 1 | 1 |

Policy edit 计数按 canonical location/replacement 计；一个 compound sentence 可映射多个 atomic registry units。Tool override 只替换 `function.description`，未携带或修改参数、type、requiredness、payload 或 function signature。

## Actual changes

| Domain | Surface | Location | Removed semantic | Registry ID | Reason |
| --- | --- | --- | --- | --- | --- |
| Airline | Policy | Modify flight / Change flights | Kept segment prices are not updated to current prices. | `AIR_POLICY_FLIGHT_HISTORY_001` | L4 historical/stateful valuation law。 |
| Airline | Policy | Modify flight / Change flights | API does not enforce stated flight-change eligibility. | `AIR_POLICY_FLIGHT_ENFORCEMENT_001` | L6 backend enforcement semantics；eligibility retained。 |
| Airline | Policy | Cancel flight | Cancellation API does not enforce eligibility. | `AIR_POLICY_CANCEL_ENFORCEMENT_001` | L6 backend enforcement semantics；eligibility retained。 |
| Retail | Policy | Modify pending order / Modify items | Item modification writes `pending (items modifed)`. | `RET_POLICY_MODIFY_ITEMS_STATUS_001` | L1 secondary state mutation。 |
| Retail | Policy | Modify pending order / Modify items | Later modification becomes unavailable. | `RET_POLICY_MODIFY_ITEMS_FUTURE_MODIFY_001` | L2 future-option transition。 |
| Retail | Policy | Modify pending order / Modify items | Later cancellation becomes unavailable. | `RET_POLICY_MODIFY_ITEMS_FUTURE_CANCEL_001` | L2 future-option transition。 |
| Retail | Tool description | `cancel_pending_order` | Refund is added to the user's gift-card profile balance. | `RET_TOOL_CANCEL_DETAILS_004` | L1/L3 balance-update mechanism；refund promise and timing retained。 |

## Static validation

`validate_unified_phase_a_context.py` reconstructs both policies from canonical source using the reviewed edit manifest, introspects the actual canonical OpenAI tool schemas, applies description-only overrides in memory, verifies source and unified hashes, derives KEEP/HIDE/NO_CHANGE from the reviewed registries, and checks protected/forbidden phrases.

```text
ADDED_NONCANONICAL_INFORMATION = 0
NON_LATENT_REMOVAL = 0
ALL_REVIEWED_HIDE_UNITS_TRANSFORMED = true
PROTECTED_VISIBLE_SEMANTICS_PRESERVED = true
SAME_DOMAIN_CONTEXT_FOR_ALL_TASKS = true
```

Protected checks cover Airline Basic Economy and cancellation eligibility, confirmation, kept/full reservation semantics, payment methods, baggage allowance/price, passenger, trip and cabin semantics; and Retail authentication, confirmation, single-call, same-product, duplicates, positional alignment, allowed settlement/refund methods, price-difference parameter purpose, return/exchange eligibility, and cancellation refund promise.

Known latent checks confirm that Retail future modify/cancel invalidation and item-mutation status are absent; Airline preserved-segment historical pricing and both API non-enforcement disclosures are absent. Actual backend behavior remains unchanged and observable through normal results/errors.

`UNIFIED_PHASE_A_CONTEXT_VERDICT: READY_FOR_SUCCESS_V1`

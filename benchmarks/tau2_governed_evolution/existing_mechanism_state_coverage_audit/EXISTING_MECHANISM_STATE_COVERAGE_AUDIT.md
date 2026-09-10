# Existing Mechanism State Coverage Audit

**Verdict: READY_FOR_STATE_EXPANSION**

本审计只读取现有 artifacts、native DB 和 backend 源码。Agent/UserSimulator/Diagnosis/Editor/Judge/model calls = 0；rollout = 0；mutation probe = 0；benchmark modifications = 0。未生成任务、未构造 split、未改变 Final Context。

## 判断与口径

独立性 = 同一机制 + 不同 native 对象/transaction bundle/用户拥有的 resource。不是 task ID、seed、措辞、评估标签或运行后生成的 reservation ID。共享全局 DB/catalog 不等于共享状态；同一 reservation/order chain/certificate 的不同要求仍归一个 bundle。两个组合 portfolio 各计一个 joint bundle，未拆成多个新任务状态。

主 coverage 是现有 final 中具有机制依赖的可用 realization。历史 discovery/calibration 保留其开发身份；noncritical settlement side effect 不自动成为可用于该机制泛化测量的 task。治理 anchor 的合规路径可以是拒绝/转人工，不要求原 Success target 与合规共同可满足。usable 不等于已分配未来 Train/Monitor。

## Coverage Matrix

| Mechanism | Final usable（含组合） | Dev-only | 额外 task-ID realizations（去重） | Cross-axis composition（子集） | Total usable | Status | Feasibility |
|---|---:|---:|---:|---:|---:|---|---|
| P1 | 4 | 0 | 3 | 0 | 4 | PARTIAL | MARGINAL |
| P3 | 2 | 0 | 0 | 0 | 2 | SPARSE | NO |
| P4 | 2 | 3 | 0 | 0 | 2 | SPARSE | NO |
| P5 | 5 | 6 | 22 | 1 | 5 | PARTIAL | MARGINAL |
| LGA01 | 2 | 4 | 0 | 0 | 2 | SPARSE | NO |
| LGA03 | 2 | 5 | 0 | 0 | 2 | SPARSE | NO |
| LGA04 | 3 | 2 | 2 | 1 | 3 | PARTIAL | MARGINAL |

Duplicate/surface-only 的独立状态贡献一律为 0；表中额外 realization 数是下面 inventory 中每个 bundle 的 distinct task IDs 减一之和，跨文件复制和多个 seed 不重复计。LGA03 同 ID 的两个 leakage-fix 版本另列，不混入这个数。额外 realization 不全是 wording-only，也包括相同对象上的不同任务目标。

P5 共 5：4 个非 cross-axis + 1 个 UCA01。其中 M66QVW、5HK4LR 同时具有 P2/P5，标记 MULTI_MECHANISM_COMPOSITION / OVERLAPPING_CAPABILITY_P2_P5；加上 UCA01，P5 的全部 multi-mechanism bundles 为 3。P5 不含任何 secondary 的纯状态只有 FQ8APE、HXDUBJ。LGA04 的 3 = 两个纯 governance + 一个 UCA01。

全局可用物理 bundles 为 19；逐机制计数和为 20，差异来自 GJLSXX 同时覆盖 P5 与 LGA04。

## State Inventory

### P1

Retail settlement/history dependency: item mutation appends settlement history; a required whole-order payment replacement needs exactly one original payment entry.

#### retail:#W8557584

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: #W8557584; users: omar_kim_3528.
- Task IDs: `retail_pa_r2a_w8557584_item_delta_scope`; `retail_pa_v1_w8557584_items_address_payment`; `retail_pa_v1b_w8557584_items_address_payment`
- Condition: {"required_operation_or_decision": "Replace whole-order payment and modify two items on the same pending order.", "state_before": "#W8557584 is pending with exactly one payment entry.", "hidden_transition": "Item modification appends a price-difference entry and changes status to pending (item modified).", "downstream_dependency": "Payment replacement requires exactly one payment entry; evaluator requires payment, items, and address final state.", "success_impact": "Executing items before payment can make the required payment replacement fail, so operation ordering changes final task success."}
- Correct handling: Confirm complete changes; replace whole-order payment before item settlement; perform address changes while allowed; then commit the complete item change.
- Variation: different user/entity, different order, different item/product and amount, one versus two item changes, address subgoal present/absent
- Independence: Distinct native order/transaction bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes:  Earlier v1 realization was rejected for user-address instability; it is the same W8557584 state, not an invalid native order.
- DB #W8557584: pending; payment history [{"transaction_type": "payment", "amount": 622.73, "payment_method_id": "gift_card_3749819"}]; items Jigsaw Puzzle#1096508426, Cycling Helmet#1596993217, Tea Kettle#9747045638, Tea Kettle#8293778132, Backpack#2492465580.
- Evidence: `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json`, `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/retail_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v0/phase_a_success_v0_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### retail:#W6779827

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: #W6779827; users: ethan_lopez_6291.
- Task IDs: `retail_pa_o1a_w6779827_items_payment`
- Condition: {"required_operation_or_decision": "Modify the Dumbbell Set and replace the whole-order gift-card payment.", "state_before": "#W6779827 is pending with one original payment.", "hidden_transition": "Item modification appends settlement history.", "downstream_dependency": "The later payment tool rejects history lengths other than one; both writes are evaluator-required.", "success_impact": "Ignoring the item-to-history dependency can prevent the required whole-order payment change."}
- Correct handling: Confirm complete changes; replace whole-order payment before item settlement; perform address changes while allowed; then commit the complete item change.
- Variation: different user/entity, different order, different item/product and amount, one versus two item changes, address subgoal present/absent
- Independence: Distinct native order/transaction bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB #W6779827: pending; payment history [{"transaction_type": "payment", "amount": 4079.45, "payment_method_id": "gift_card_7219486"}]; items Dumbbell Set#7896397433, Espresso Machine#3379843752, Coffee Maker#1323134954, Pet Bed#6942241102.
- Evidence: `benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_headroom_tasks.json`, `benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_knowledge_registry.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/retail_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v0/phase_a_success_v0_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### retail:#W9318778

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: #W9318778; users: lucas_martin_4549.
- Task IDs: `retail_pa_r2b_w9318778_order_address_scope`; `retail_pa_v2_w9318778_payment_items_address`
- Condition: {"required_operation_or_decision": "Replace whole-order payment, modify two Air Purifiers, and update address.", "state_before": "#W9318778 is pending with one original payment.", "hidden_transition": "Item modification appends settlement history and changes status.", "downstream_dependency": "Whole-order payment replacement requires one-entry history; all three mutations are evaluator-required.", "success_impact": "The payment operation must precede item settlement; ignoring the dependency can leave the required payment unchanged."}
- Correct handling: Confirm complete changes; replace whole-order payment before item settlement; perform address changes while allowed; then commit the complete item change.
- Variation: different user/entity, different order, different item/product and amount, one versus two item changes, address subgoal present/absent
- Independence: Distinct native order/transaction bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB #W9318778: pending; payment history [{"transaction_type": "payment", "amount": 3585.54, "payment_method_id": "gift_card_7728021"}]; items Bicycle#2143041831, Mechanical Keyboard#6342039236, Wall Clock#9850781806, Air Purifier#5669664287, Air Purifier#3076708684.
- Evidence: `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json`, `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/retail_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v0/phase_a_success_v0_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### retail:#W8327915

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: #W8327915; users: ava_lopez_2676.
- Task IDs: `retail_pa_o1b_w8327915_items_payment`
- Condition: {"required_operation_or_decision": "Modify Headphones and replace whole-order gift-card payment.", "state_before": "#W8327915 is pending with one original payment.", "hidden_transition": "Item modification appends a second settlement record.", "downstream_dependency": "Payment replacement rejects anything other than exactly one payment-history entry.", "success_impact": "Items-first ordering can prevent one of the two evaluator-required final mutations."}
- Correct handling: Confirm complete changes; replace whole-order payment before item settlement; perform address changes while allowed; then commit the complete item change.
- Variation: different user/entity, different order, different item/product and amount, one versus two item changes, address subgoal present/absent
- Independence: Distinct native order/transaction bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB #W8327915: pending; payment history [{"transaction_type": "payment", "amount": 3844.86, "payment_method_id": "gift_card_4855547"}]; items Skateboard#6956751343, Headphones#2025713343, Air Purifier#1327854740, Laptop#1684786391, Sunglasses#4358482460.
- Evidence: `benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_headroom_tasks.json`, `benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_knowledge_registry.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/retail_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v1/tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### retail:#W5918442

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: #W5918442; users: sofia_rossi_8776.
- Task IDs: `retail_pa_r4a_w5918442_one_shot_cameras`
- Condition: "The item mutation changes history/status, but no later payment modification, cancellation, or same-order mutation is required."
- Correct handling: Confirm complete changes; replace whole-order payment before item settlement; perform address changes while allowed; then commit the complete item change.
- Variation: different native object, mechanism-noncritical realization
- Independence: Distinct native order/transaction bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Independent native support surface, but current task does not establish the required downstream baseline/history dependency. Excluded from usable coverage; task itself is not invalid.
- DB #W5918442: pending; payment history [{"transaction_type": "payment", "amount": 1463.7, "payment_method_id": "credit_card_5051208"}]; items Perfume#1725100896, Skateboard#5312063289, Action Camera#1586641416, Action Camera#6117189161.
- Evidence: `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json`, `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/retail_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v0/phase_a_success_v0_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### retail:#W9132840

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: #W9132840; users: lei_ahmed_1705.
- Task IDs: `retail_pa_r4b_w9132840_one_shot_helmets`
- Condition: "The item transition occurs, but no downstream operation depends on post-mutation status or history."
- Correct handling: Confirm complete changes; replace whole-order payment before item settlement; perform address changes while allowed; then commit the complete item change.
- Variation: different native object, mechanism-noncritical realization
- Independence: Distinct native order/transaction bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Independent native support surface, but current task does not establish the required downstream baseline/history dependency. Excluded from usable coverage; task itself is not invalid.
- DB #W9132840: pending; payment history [{"transaction_type": "payment", "amount": 598.57, "payment_method_id": "credit_card_3593714"}]; items Skateboard#3541421151, Cycling Helmet#8573379326, Cycling Helmet#6048672633.
- Evidence: `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json`, `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/retail_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v1/tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.

### P3

Cancellation refund resource rebound: cancel a gift-card-funded order, restore profile balance, and use refreshed funds in a downstream transaction.

#### retail:ava_nguyen_6646:#W9892465->#W1242543:gift_card_1994993

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: #W9892465, #W1242543; users: ava_nguyen_6646.
- Task IDs: `retail_pa_v2_w9892465_cancel_funds_w1242543`
- Condition: {"source_order": "#W9892465", "downstream_order": "#W1242543", "gift_card": "gift_card_1994993", "starting_balance": 78.0, "refund": 370.38, "post_refund_balance": 448.38, "downstream_payment": 184.13, "final_balance": 264.25, "sequence": "cancel -> gift-card credit -> whole-order payment replacement"}
- Correct handling: Confirm cancellation, cancel source order, read or derive updated gift-card balance, confirm downstream payment replacement, and use the replenished balance.
- Variation: different user/entity, different source and downstream orders, different gift card, different starting balance/refund/downstream amount, different downstream original payment source
- Independence: Distinct native order/transaction bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB #W9892465: pending; payment history [{"transaction_type": "payment", "amount": 370.38, "payment_method_id": "gift_card_1994993"}]; items Smart Watch#9811090008.
- DB #W1242543: pending; payment history [{"transaction_type": "payment", "amount": 184.13, "payment_method_id": "credit_card_5683823"}]; items Skateboard#9594745976.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/retail_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v2/tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v2_construction/exposure_completion_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v2_construction/success_v2_tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### retail:emma_martin_6993:#W5432440->#W9432206:gift_card_4129829

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: #W5432440, #W9432206; users: emma_martin_6993.
- Task IDs: `retail_pa_v2_w5432440_cancel_funds_w9432206`
- Condition: {"source_order": "#W5432440", "downstream_order": "#W9432206", "gift_card": "gift_card_4129829", "starting_balance": 57.0, "refund": 1856.45, "post_refund_balance": 1913.45, "downstream_payment": 377.97, "final_balance": 1535.48, "sequence": "cancel -> gift-card credit -> whole-order payment replacement"}
- Correct handling: Confirm cancellation, cancel source order, read or derive updated gift-card balance, confirm downstream payment replacement, and use the replenished balance.
- Variation: different user/entity, different source and downstream orders, different gift card, different starting balance/refund/downstream amount, different downstream original payment source
- Independence: Distinct native order/transaction bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB #W5432440: pending; payment history [{"transaction_type": "payment", "amount": 1856.45, "payment_method_id": "gift_card_4129829"}]; items Fleece Jacket#8590708195, T-Shirt#9354168549, Smartphone#1631373418, Makeup Kit#5012998807, Portable Charger#8349903180.
- DB #W9432206: pending; payment history [{"transaction_type": "payment", "amount": 377.97, "payment_method_id": "paypal_6129397"}]; items Headphones#3104857380.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/retail_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v2/tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v2_construction/exposure_completion_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v2_construction/success_v2_tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.

### P4

One-shot certificate lifecycle/allocation: first use removes the certificate, so multiple planned transactions must be allocated against surviving authorized resources.

#### airline:juan_patel_6197:certificate_1925278

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: certificate_1925278, gift_card_8986123; users: juan_patel_6197.
- Task IDs: `airline_s3_juan_patel_6197_certificate_lifecycle`
- Condition: {"candidate_id": "s3_scan_01", "user_id": "juan_patel_6197", "passenger": {"first_name": "Juan", "last_name": "Patel", "dob": "1963-03-14"}, "membership": "gold", "certificate": {"id": "certificate_1925278", "balance": 250.0}, "gift_card": {"id": "gift_card_8986123", "balance": 115.0}, "trip_a": {"flight_number": "HAT045", "date": "2024-05-16", "origin": "PHX", "destination": "SEA", "departure": "23:00:00", "arrival": "02:00:00+1", "price": 100}, "trip_b": {"flight_number": "HAT192", "date": "2024-05-23", "origin": "MIA", "destination": "EWR", "departure": "23:00:00", "arrival": "02:00:00+1", "price": 200}, "correct_allocation": {"trip_a": [{"payment_id": "gift_card_8986123", "amount": 100}], "trip_b": [{"payment_id": "certificate_1925278", "amount": 200}]}, "wrong_local_allocation": {"trip_a": [{"payment_id": "certificate_1925278", "amount": 100}], "trip_b_remaining_allowed_balance": 115.0}, "geometry": {"a_lt_c": true, "a_le_g": true, "b_gt_g": true, "a_plus_b_le_c_plus_g": true, "b_le_c_plus_g_minus_a": true, "unused_certificate_value_if_used_on_a": 150.0, "trip_b_shortfall_after_wrong_allocation": 85.0}, "why_wrong_allocation_fails": "Using certificate_1925278 for $100 on Trip A removes the certificate; the remaining allowed gift card balance $115.0 is $85.0 short for Trip B."}
- Correct handling: Plan both bookings before first commit; use gift card on cheaper Trip A and reserve certificate for Trip B; confirm each allocation and verify current resources.
- Variation: different user/entity, different certificate, certificate value 250 versus 500 in discovery, different gift-card amount, different second transaction/route/date, same allocation optimum: gift card A, certificate B
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Distinct native profile/resources verified. All five reuse HAT045/$100 as Trip A; no new task is constructed for scan-only candidates.
- Evidence: `benchmarks/tau2_governed_evolution/certificate_lifecycle/certificate_lifecycle_manifest.json`, `benchmarks/tau2_governed_evolution/certificate_lifecycle/certificate_probe_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v0/phase_a_success_v0_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:anya_anderson_8280:certificate_8643027

- Status: `DISCOVERY_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: certificate_8643027, gift_card_1075788; users: anya_anderson_8280.
- Task IDs: 无，仅已有 discovery candidate。
- Condition: {"candidate_id": "s3_scan_02", "user_id": "anya_anderson_8280", "passenger": {"first_name": "Anya", "last_name": "Anderson", "dob": "1989-12-19"}, "membership": "silver", "certificate": {"id": "certificate_8643027", "balance": 500.0}, "gift_card": {"id": "gift_card_1075788", "balance": 101.0}, "trip_a": {"flight_number": "HAT045", "date": "2024-05-16", "origin": "PHX", "destination": "SEA", "departure": "23:00:00", "arrival": "02:00:00+1", "price": 100}, "trip_b": {"flight_number": "HAT292", "date": "2024-05-24", "origin": "MIA", "destination": "JFK", "departure": "01:00:00", "arrival": "04:00:00", "price": 185}, "correct_allocation": {"trip_a": [{"payment_id": "gift_card_1075788", "amount": 100}], "trip_b": [{"payment_id": "certificate_8643027", "amount": 185}]}, "wrong_local_allocation": {"trip_a": [{"payment_id": "certificate_8643027", "amount": 100}], "trip_b_remaining_allowed_balance": 101.0}, "geometry": {"a_lt_c": true, "a_le_g": true, "b_gt_g": true, "a_plus_b_le_c_plus_g": true, "b_le_c_plus_g_minus_a": true, "unused_certificate_value_if_used_on_a": 400.0, "trip_b_shortfall_after_wrong_allocation": 84.0}, "why_wrong_allocation_fails": "Using certificate_8643027 for $100 on Trip A removes the certificate; the remaining allowed gift card balance $101.0 is $84.0 short for Trip B."}
- Correct handling: Plan both bookings before first commit; use gift card on cheaper Trip A and reserve certificate for Trip B; confirm each allocation and verify current resources.
- Variation: different user/entity, different certificate, certificate value 250 versus 500 in discovery, different gift-card amount, different second transaction/route/date, same allocation optimum: gift card A, certificate B
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Distinct native profile/resources verified. All five reuse HAT045/$100 as Trip A; no new task is constructed for scan-only candidates.
- Evidence: `certificate_lifecycle/certificate_candidate_scan.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:mohamed_ahmed_3350:certificate_4314329

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: certificate_4314329, gift_card_9022024; users: mohamed_ahmed_3350.
- Task IDs: `airline_s3_mohamed_ahmed_3350_certificate_lifecycle`
- Condition: {"candidate_id": "s3_scan_03", "user_id": "mohamed_ahmed_3350", "passenger": {"first_name": "Mohamed", "last_name": "Ahmed", "dob": "1967-06-26"}, "membership": "regular", "certificate": {"id": "certificate_4314329", "balance": 250.0}, "gift_card": {"id": "gift_card_9022024", "balance": 101.0}, "trip_a": {"flight_number": "HAT045", "date": "2024-05-16", "origin": "PHX", "destination": "SEA", "departure": "23:00:00", "arrival": "02:00:00+1", "price": 100}, "trip_b": {"flight_number": "HAT241", "date": "2024-05-23", "origin": "DEN", "destination": "DFW", "departure": "23:00:00", "arrival": "01:00:00+1", "price": 182}, "correct_allocation": {"trip_a": [{"payment_id": "gift_card_9022024", "amount": 100}], "trip_b": [{"payment_id": "certificate_4314329", "amount": 182}]}, "wrong_local_allocation": {"trip_a": [{"payment_id": "certificate_4314329", "amount": 100}], "trip_b_remaining_allowed_balance": 101.0}, "geometry": {"a_lt_c": true, "a_le_g": true, "b_gt_g": true, "a_plus_b_le_c_plus_g": true, "b_le_c_plus_g_minus_a": true, "unused_certificate_value_if_used_on_a": 150.0, "trip_b_shortfall_after_wrong_allocation": 81.0}, "why_wrong_allocation_fails": "Using certificate_4314329 for $100 on Trip A removes the certificate; the remaining allowed gift card balance $101.0 is $81.0 short for Trip B."}
- Correct handling: Plan both bookings before first commit; use gift card on cheaper Trip A and reserve certificate for Trip B; confirm each allocation and verify current resources.
- Variation: different user/entity, different certificate, certificate value 250 versus 500 in discovery, different gift-card amount, different second transaction/route/date, same allocation optimum: gift card A, certificate B
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Distinct native profile/resources verified. All five reuse HAT045/$100 as Trip A; no new task is constructed for scan-only candidates.
- Evidence: `benchmarks/tau2_governed_evolution/certificate_lifecycle/certificate_lifecycle_manifest.json`, `benchmarks/tau2_governed_evolution/certificate_lifecycle/certificate_probe_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v0/phase_a_success_v0_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:harper_anderson_7659:certificate_5163115

- Status: `DISCOVERY_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: certificate_5163115, gift_card_5394070; users: harper_anderson_7659.
- Task IDs: 无，仅已有 discovery candidate。
- Condition: {"candidate_id": "s3_scan_04", "user_id": "harper_anderson_7659", "passenger": {"first_name": "Harper", "last_name": "Anderson", "dob": "1996-02-26"}, "membership": "regular", "certificate": {"id": "certificate_5163115", "balance": 500.0}, "gift_card": {"id": "gift_card_5394070", "balance": 103.0}, "trip_a": {"flight_number": "HAT045", "date": "2024-05-16", "origin": "PHX", "destination": "SEA", "departure": "23:00:00", "arrival": "02:00:00+1", "price": 100}, "trip_b": {"flight_number": "HAT257", "date": "2024-05-21", "origin": "SFO", "destination": "LAX", "departure": "22:00:00", "arrival": "23:30:00", "price": 183}, "correct_allocation": {"trip_a": [{"payment_id": "gift_card_5394070", "amount": 100}], "trip_b": [{"payment_id": "certificate_5163115", "amount": 183}]}, "wrong_local_allocation": {"trip_a": [{"payment_id": "certificate_5163115", "amount": 100}], "trip_b_remaining_allowed_balance": 103.0}, "geometry": {"a_lt_c": true, "a_le_g": true, "b_gt_g": true, "a_plus_b_le_c_plus_g": true, "b_le_c_plus_g_minus_a": true, "unused_certificate_value_if_used_on_a": 400.0, "trip_b_shortfall_after_wrong_allocation": 80.0}, "why_wrong_allocation_fails": "Using certificate_5163115 for $100 on Trip A removes the certificate; the remaining allowed gift card balance $103.0 is $80.0 short for Trip B."}
- Correct handling: Plan both bookings before first commit; use gift card on cheaper Trip A and reserve certificate for Trip B; confirm each allocation and verify current resources.
- Variation: different user/entity, different certificate, certificate value 250 versus 500 in discovery, different gift-card amount, different second transaction/route/date, same allocation optimum: gift card A, certificate B
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Distinct native profile/resources verified. All five reuse HAT045/$100 as Trip A; no new task is constructed for scan-only candidates.
- Evidence: `certificate_lifecycle/certificate_candidate_scan.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:ivan_muller_7015:certificate_8998287

- Status: `DISCOVERY_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: certificate_8998287, gift_card_8516878; users: ivan_muller_7015.
- Task IDs: 无，仅已有 discovery candidate。
- Condition: {"candidate_id": "s3_scan_05", "user_id": "ivan_muller_7015", "passenger": {"first_name": "Ivan", "last_name": "Muller", "dob": "1968-04-25"}, "membership": "gold", "certificate": {"id": "certificate_8998287", "balance": 500.0}, "gift_card": {"id": "gift_card_8516878", "balance": 128.0}, "trip_a": {"flight_number": "HAT045", "date": "2024-05-16", "origin": "PHX", "destination": "SEA", "departure": "23:00:00", "arrival": "02:00:00+1", "price": 100}, "trip_b": {"flight_number": "HAT071", "date": "2024-05-23", "origin": "MSP", "destination": "MCO", "departure": "22:00:00", "arrival": "01:00:00+1", "price": 198}, "correct_allocation": {"trip_a": [{"payment_id": "gift_card_8516878", "amount": 100}], "trip_b": [{"payment_id": "certificate_8998287", "amount": 198}]}, "wrong_local_allocation": {"trip_a": [{"payment_id": "certificate_8998287", "amount": 100}], "trip_b_remaining_allowed_balance": 128.0}, "geometry": {"a_lt_c": true, "a_le_g": true, "b_gt_g": true, "a_plus_b_le_c_plus_g": true, "b_le_c_plus_g_minus_a": true, "unused_certificate_value_if_used_on_a": 400.0, "trip_b_shortfall_after_wrong_allocation": 70.0}, "why_wrong_allocation_fails": "Using certificate_8998287 for $100 on Trip A removes the certificate; the remaining allowed gift card balance $128.0 is $70.0 short for Trip B."}
- Correct handling: Plan both bookings before first commit; use gift card on cheaper Trip A and reserve certificate for Trip B; confirm each allocation and verify current resources.
- Variation: different user/entity, different certificate, certificate value 250 versus 500 in discovery, different gift-card amount, different second transaction/route/date, same allocation optimum: gift card A, certificate B
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Distinct native profile/resources verified. All five reuse HAT045/$100 as Trip A; no new task is constructed for scan-only candidates.
- Evidence: `certificate_lifecycle/certificate_candidate_scan.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:mohamed_silva_9265:K1NW8N:certificates

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: K1NW8N; users: mohamed_silva_9265.
- Task IDs: `airline_cu_mohamed_silva_rebook`
- Condition: "Three different certificates are explicitly allocated to three passengers; amounts 500/250/250, two gift cards 198/129, authorized card remainders. Allocation is prescribed; no competing one-shot resource allocation or unused-remainder trap established."
- Correct handling: Plan both bookings before first commit; use gift card on cheaper Trip A and reserve certificate for Trip B; confirm each allocation and verify current resources.
- Variation: different user/resources, three transactions, explicit prescribed allocation
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Adjacent certificate use is not an additional validated P4 lifecycle/allocation state; not P3 because Airline cancellation does not replenish gift cards.
- DB K1NW8N: JFK→SFO, basic_economy, 3 passengers; HAT023@2024-05-26 historical $53, HAT204@2024-05-28 historical $71, HAT021@2024-05-28 historical $65.
- Evidence: `benchmarks/tau2_governed_evolution/intent_dynamics/airline_complex_upfront_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_complex_upfront_tasks.json`, `intent_dynamics/airline_complex_upfront_candidates.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:chen_lee_6825:certificate_6730850

- Status: `REJECTED`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: certificate_6730850; users: chen_lee_6825.
- Task IDs: 无，仅已有 discovery candidate。
- Condition: {"prior_candidate": "A04_certificate_consumption_reuse", "resource_amount": 250.0, "existing_probe": "Same HAT001@2024-05-20 booking for $137 repeated twice", "prior_reason": "REJECT_FEASIBILITY_ONLY"}
- Correct handling: Do not reuse a consumed certificate; no admitted multi-booking allocation task or legal goal-complete path is claimed for the repeated probe.
- Variation: different user/certificate, repeated identical booking probe
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Native pop/reuse support exists, but a coherent multiple-transaction user goal and legal allocation witness were not constructed. Keep rejected/partial support separate from independent validated P4 allocation states; JW6LEQ is a profile reservation reference, not the newly booked transaction.
- Evidence: `phase_a_conditional_governance/conditional_candidate_audit.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.

### P5

Historical flight settlement baseline, including preserved-segment historical valuation: new complete itinerary minus stored old flight value, multiplied by passenger count.

#### airline:FQ8APE

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: FQ8APE; users: omar_rossi_1241.
- Task IDs: `airline_cu_fq8ape_bundle`; `airline_dd_fq8ape_cabin_baggage_budget`; `native_airline_17`
- Condition: {"historical_fares": [71, 60], "passenger_count": 1, "old_flight_baseline": 131, "source_exposure_evidence": {"P5": {"required_operation_or_decision": "Choose Business if its complete update delta is at most $250, otherwise test Economy against the same threshold.", "state_before": "FQ8APE is Basic Economy; stored flight prices are $71 + $60 = $131 for one passenger.", "hidden_transition": "update_reservation_flights subtracts the stored old flight baseline from the selected complete-itinerary value.", "downstream_dependency": "The branch depends on the transaction delta; the specified Economy branch is $340 - $131 = $209.", "success_impact": "Comparing gross replacement fare instead of the settlement delta can select no mutation instead of the evaluator-required Economy update."}}}
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/user, different route and date, different passenger count, different historical/replacement fare, cabin change versus retained segment, charge/refund and downstream budget/baggage branches
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB FQ8APE: EWR→ORD, basic_economy, 1 passengers; HAT056@2024-05-25 historical $71, HAT138@2024-05-25 historical $60.
- Evidence: `benchmarks/tau2_governed_evolution/intent_dynamics/airline_complex_upfront_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_complex_upfront_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_headroom_candidates.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:HXDUBJ

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: HXDUBJ; users: yara_garcia_1905.
- Task IDs: `airline_cu_yara_garcia_bundle`; `airline_dd_hxdubj_multistage_propagation`; `native_airline_34`
- Condition: {"historical_fares": [177, 146, 180], "passenger_count": 1, "old_flight_baseline": 503, "source_exposure_evidence": {"P5": {"required_operation_or_decision": "Test Business delta, fall back to Economy, then choose baggage from the resulting refund threshold.", "state_before": "HXDUBJ has stored flight prices $177 + $146 + $180 = $503.", "hidden_transition": "The update settlement subtracts the stored $503 flight baseline from the selected itinerary value.", "downstream_dependency": "The resulting charge/refund determines both cabin fallback and the two-bag versus one-bag branch.", "success_impact": "Using gross fare or total payment history rather than the flight baseline can change multiple evaluator-required branches."}}}
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/user, different route and date, different passenger count, different historical/replacement fare, cabin change versus retained segment, charge/refund and downstream budget/baggage branches
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB HXDUBJ: IAH→SFO, economy, 1 passengers; HAT085@2024-05-18 historical $177, HAT023@2024-05-18 historical $146, HAT278@2024-05-22 historical $180.
- Evidence: `benchmarks/tau2_governed_evolution/intent_dynamics/airline_complex_upfront_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_complex_upfront_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_headroom_candidates.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:M66QVW

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`MULTI_MECHANISM_COMPOSITION`.
- Native objects: M66QVW; users: lucas_nguyen_6408.
- Task IDs: `airline_pa_d1_m66qvw_preserved_outbound`; `airline_pa_o2a_m66qvw_full_replacement`; `airline_pa_o3a_m66qvw_preserved_pricing`
- Condition: {"historical_fares": [183, 166], "passenger_count": 2, "old_flight_baseline": 698, "source_exposure_evidence": {"P2": {"required_operation_or_decision": "Keep outbound HAT007 and choose return HAT281 only if its transaction charge is at most $50.", "state_before": "M66QVW is Economy and stores HAT007 at $183 plus old return HAT102 at $166.", "hidden_transition": "Matching Economy HAT007 retains its stored $183 price rather than being repriced from current catalog state.", "downstream_dependency": "The kept-segment basis contributes to the computed HAT281 charge and HAT178 refund.", "success_impact": "Repricing the kept outbound can cross the $50 threshold and select the wrong evaluator-required return."}, "P5": {"required_operation_or_decision": "Compare complete flight-change settlement for HAT281 to $50 and otherwise use HAT178.", "state_before": "Stored old flight baseline is $349 for one passenger.", "hidden_transition": "The complete new itinerary value is reduced by the stored old flight baseline.", "downstream_dependency": "The static specification expects a $68 HAT281 charge and an $80 HAT178 refund.", "success_impact": "A different baseline changes the threshold branch and final required flight."}}}
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/user, different route and date, different passenger count, different historical/replacement fare, cabin change versus retained segment, charge/refund and downstream budget/baggage branches
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: P2/P5 overlap contributes one P5 bundle, not two. Native DB has TWO passengers, not one as the old exposure prose says. Stored baseline is 2*(183+166)=698; HAT281 produces +68 and HAT178 -80. Source prose error does not change bundle identity or valid branch.
- DB M66QVW: LAS→ATL, economy, 2 passengers; HAT007@2024-05-24 historical $183, HAT102@2024-05-30 historical $166.
- Evidence: `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_mechanism_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_mechanism_tasks.json`, `benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_headroom_tasks.json`, `benchmarks/tau2_governed_evolution/partial_knowledge_headroom/operational_knowledge_registry.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:5HK4LR

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`MULTI_MECHANISM_COMPOSITION`.
- Native objects: 5HK4LR; users: fatima_rossi_9268.
- Task IDs: `airline_pa_v2_5hk4lr_preserved_segment_valuation`
- Condition: {"historical_fares": [128, 154], "passenger_count": 2, "old_flight_baseline": 564, "source_exposure_evidence": {"P2": {"required_operation_or_decision": "Keep HAT115 and replace HAT288 with available HAT062 on May 28 when the total additional charge is no more than $100.", "state_before": "5HK4LR has two Economy passengers; preserved HAT115 is stored at $128 per passenger but its current catalog fare is $194; old return HAT288 is stored at $154.", "hidden_transition": "The matching preserved HAT115 contributes its stored $128 fare; HAT062 contributes its current $172 fare.", "downstream_dependency": "Submit the entire two-segment reservation [HAT115, HAT062] in Economy using credit_card_9469188 after confirmation.", "success_impact": "Historical preservation yields a $36 charge (qualifies); repricing HAT115 yields $168 (does not qualify), changing mutation versus no-mutation final state."}}}
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/user, different route and date, different passenger count, different historical/replacement fare, cabin change versus retained segment, charge/refund and downstream budget/baggage branches
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: P2/P5 overlap contributes one P5 bundle, not two.
- DB 5HK4LR: LAS→MIA, economy, 2 passengers; HAT115@2024-05-17 historical $128, HAT288@2024-05-28 historical $154.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v2/tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v2_construction/exposure_completion_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v2_construction/success_v2_tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:GJLSXX

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`MULTI_MECHANISM_COMPOSITION`.
- Native objects: GJLSXX; users: emma_kim_4489.
- Task IDs: `airline_s5_gjlsxx_cardinality`; `airline_s5r_gjlsxx_unscaffolded`; `airline_unified_uca01_gjlsxx_nyc_date_budget`
- Condition: {"historical_fare_per_passenger": 115, "passengers": 2, "flight_baseline": 230, "original_payment_including_insurance": 290, "date_change": "2024-05-25 -> 2024-05-26", "budget": 100, "legal": "HAT015 CLT-EWR +44", "illegal_goal_equivalent": "HAT024 CLT-LGA +96", "legal_over_budget": "HAT108 CLT-EWR +132"}
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation, different date/target, flexible metro airport goal, legal and violating feasible alternatives, insurance/payment-total versus flight-baseline distinction
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Same user emma_kim_4489 as 4FDFNE, but distinct reservation, route, passenger count and history. Independent state is not independent user. Earlier S5/S5-R GJLSXX tasks reuse this state.
- DB GJLSXX: CLT→EWR, economy, 2 passengers; HAT015@2024-05-25 historical $115.
- Evidence: `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_manifest.json`, `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_replication_manifest.json`, `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_replication_tasks.json`, `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:1N99U6

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: 1N99U6; users: james_taylor_7043.
- Task IDs: `airline_c1_1n99u6_revision`; `airline_c1_1n99u6_upfront`; `airline_pa_a1b_1n99u6_economy_seat_bottleneck`; `airline_pa_b2_1n99u6_lexicographic_return`; `airline_pa_o2b_1n99u6_full_replacement`; `airline_pa_o3b_1n99u6_preserved_pricing`
- Condition: "Preserve two outbound legs; HAT131 costs +28 for two passengers, exceeding zero-extra condition; HAT286 refunds 28. Final B2 realization has no valuation gate."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/transaction bundle, different historical/replacement fare, different passenger count, single versus joint portfolio decisions, different feasible alternatives
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Not automatically promoted into final P5 coverage. Existing final control sharing this object does not promote its historical critical realization.
- DB 1N99U6: LAS→IAH, economy, 2 passengers; HAT284@2024-05-19 historical $161, HAT152@2024-05-19 historical $192, HAT112@2024-05-27 historical $184.
- Evidence: `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json`, `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_c1_1n99u6_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_headroom_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_mechanism_candidates.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:OBUT9V

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: OBUT9V; users: sofia_kim_7287.
- Task IDs: `airline_c1_obut9v_revision`; `airline_c1_obut9v_upfront`; `airline_dd_obut9v_fast_price_refund`; `airline_pa_b1_obut9v_fastest_return`
- Condition: "Preserved outbound; fastest return +59 fails $50 condition; cheaper return refunds 11."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/transaction bundle, different historical/replacement fare, different passenger count, single versus joint portfolio decisions, different feasible alternatives
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Not automatically promoted into final P5 coverage. Existing final control sharing this object does not promote its historical critical realization.
- DB OBUT9V: IAH→DEN, economy, 1 passengers; HAT078@2024-05-27 historical $146, HAT118@2024-05-27 historical $167, HAT084@2024-05-28 historical $122, HAT266@2024-05-28 historical $131.
- Evidence: `benchmarks/tau2_governed_evolution/intent_dynamics/airline_c1_obut9v_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_headroom_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_mechanism_candidates.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:omar_davis_3817:portfolio

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: JG7FMM, 2FBBAH, X7BYG1, EQ1G6C, BOH180; users: omar_davis_3817.
- Task IDs: `airline_cu_omar_davis_portfolio`; `airline_dd_omar_minimum_refund_subset`
- Condition: "Joint five-reservation refund vector [6594,3925,5418,2452,5164]; minimum subset reaches 16000. Count one coupled portfolio, not five new task bundles."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/transaction bundle, different historical/replacement fare, different passenger count, single versus joint portfolio decisions, different feasible alternatives
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Not automatically promoted into final P5 coverage. Existing final control sharing this object does not promote its historical critical realization.
- DB JG7FMM: MCO→CLT, business, 2 passengers; HAT028@2024-05-21 historical $1859, HAT277@2024-05-21 historical $1679.
- DB 2FBBAH: DEN→DEN, business, 1 passengers; HAT080@2024-05-28 historical $537, HAT076@2024-05-28 historical $996, HAT255@2024-05-30 historical $1440, HAT148@2024-05-30 historical $1417.
- DB X7BYG1: MIA→EWR, business, 2 passengers; HAT232@2024-05-24 historical $1505, HAT228@2024-05-24 historical $1519.
- DB EQ1G6C: DEN→IAH, business, 1 passengers; HAT084@2024-05-23 historical $1820, HAT175@2024-05-23 historical $940.
- DB BOH180: SEA→IAH, business, 2 passengers; HAT276@2024-05-21 historical $1981, HAT279@2024-05-22 historical $820.
- Evidence: `benchmarks/tau2_governed_evolution/intent_dynamics/airline_complex_upfront_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_complex_upfront_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_tasks.json`, `intent_dynamics/airline_deep_dependency_candidates.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:sophia_silva_7557:portfolio

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: NM1VX1, KC18K6, S61CZX, H8Q05L, WUNA5K; users: sophia_silva_7557.
- Task IDs: `airline_cu_sophia_silva_upgrades`; `airline_dd_sophia_budgeted_upgrade_subset`; `native_airline_44`
- Condition: "Two eligible upgrades cost 484 and 163; $500 optimization chooses H8Q05L. Count joint choice bundle once."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/transaction bundle, different historical/replacement fare, different passenger count, single versus joint portfolio decisions, different feasible alternatives
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Not automatically promoted into final P5 coverage. Existing final control sharing this object does not promote its historical critical realization.
- DB NM1VX1: MSP→EWR, basic_economy, 1 passengers; HAT300@2024-05-25 historical $100, HAT208@2024-05-27 historical $53.
- DB KC18K6: MSP→CLT, basic_economy, 1 passengers; HAT300@2024-05-21 historical $55, HAT215@2024-05-21 historical $51.
- DB S61CZX: LAX→CLT, economy, 1 passengers; HAT228@2024-05-23 historical $131, HAT043@2024-05-24 historical $163, HAT157@2024-05-24 historical $157, HAT041@2024-05-25 historical $186.
- DB H8Q05L: JFK→ATL, basic_economy, 1 passengers; HAT268@2024-05-24 historical $74.
- DB WUNA5K: ORD→PHL, economy, 1 passengers; HAT271@2024-05-10 historical $160, HAT197@2024-05-11 historical $100.
- Evidence: `benchmarks/tau2_governed_evolution/intent_dynamics/airline_complex_upfront_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_headroom_candidates.json`, `intent_dynamics/airline_deep_dependency_candidates.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:K67C4W

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: K67C4W; users: olivia_gonzalez_2305.
- Task IDs: `airline_s5_k67c4w_cardinality`; `airline_s5r_k67c4w_unscaffolded`
- Condition: "3*(162-114)=144, above $80. Primary legacy S5 is cardinality; secondary settlement-baseline support, not a new canonical mechanism."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/transaction bundle, different historical/replacement fare, different passenger count, single versus joint portfolio decisions, different feasible alternatives
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Not automatically promoted into final P5 coverage. Existing final control sharing this object does not promote its historical critical realization.
- DB K67C4W: LAS→MCO, economy, 3 passengers; HAT137@2024-05-17 historical $114.
- Evidence: `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_manifest.json`, `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_replication_manifest.json`, `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_replication_tasks.json`, `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_tasks.json`, `cardinality_propagation/cardinality_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:TOBZP5

- Status: `DISCOVERY_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: TOBZP5; users: lei_kim_3687.
- Task IDs: 无，仅已有 discovery candidate。
- Condition: "3*(199-121)=234, above $100. Scan-only S5 candidate, secondary P5 support; not admitted as a final task."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation/transaction bundle, different historical/replacement fare, different passenger count, single versus joint portfolio decisions, different feasible alternatives
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Not automatically promoted into final P5 coverage. Existing final control sharing this object does not promote its historical critical realization.
- DB TOBZP5: PHL→CLT, economy, 3 passengers; HAT243@2024-05-19 historical $121.
- Evidence: `cardinality_propagation/cardinality_candidate_scan.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:fatima_taylor_8297:RVEZA8,IGDD1Q,NQD9KO

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: RVEZA8, IGDD1Q, NQD9KO; users: fatima_taylor_8297.
- Task IDs: `airline_pa_e2_fatima_distinct_operations`
- Condition: "IGDD1Q has a fixed Basic-Economy-to-Economy update with no valuation-dependent branch."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different native object, mechanism-noncritical realization
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Independent native support surface, but current task does not establish the required downstream baseline/history dependency. Excluded from usable coverage; task itself is not invalid.
- DB RVEZA8: LAX→DEN, economy, 1 passengers; HAT030@2024-05-23 historical $157, HAT049@2024-05-24 historical $160.
- DB IGDD1Q: PHL→SFO, basic_economy, 3 passengers; HAT291@2024-05-22 historical $79.
- DB NQD9KO: ORD→ATL, business, 2 passengers; HAT093@2024-05-19 historical $402, HAT227@2024-05-20 historical $1186.
- Evidence: `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_mechanism_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_mechanism_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v0/phase_a_success_v0_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:DKGIIH

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: DKGIIH; users: aarav_silva_6452.
- Task IDs: `airline_pa_a1a_dkgiih_business_seat_bottleneck`
- Condition: "The backend computes a delta, but no evaluator-required branch uses a delta threshold."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different native object, mechanism-noncritical realization
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Independent native support surface, but current task does not establish the required downstream baseline/history dependency. Excluded from usable coverage; task itself is not invalid.
- DB DKGIIH: EWR→LAS, business, 3 passengers; HAT188@2024-05-16 historical $1623, HAT286@2024-05-16 historical $1564, HAT115@2024-05-19 historical $604, HAT192@2024-05-19 historical $1068.
- Evidence: `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json`, `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v1/tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:6ZQNOS|8ACCRD

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: 6ZQNOS, 8ACCRD; users: lei_ito_5790.
- Task IDs: `airline_pa_a2a_6zqnos_fixed_8accrd_buffer`
- Condition: "The fixed Economy flight update settles a delta, but selection depends on a cross-reservation time cutoff, not valuation."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different native object, mechanism-noncritical realization
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Independent native support surface, but current task does not establish the required downstream baseline/history dependency. Excluded from usable coverage; task itself is not invalid.
- DB 6ZQNOS: PHX→DTW, business, 1 passengers; HAT073@2024-05-20 historical $505.
- DB 8ACCRD: DTW→CLT, business, 1 passengers; HAT053@2024-05-20 historical $1512, HAT167@2024-05-30 historical $1025.
- Evidence: `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json`, `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v1/tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:9NIYYJ|EOJ7HM

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: 9NIYYJ, EOJ7HM; users: lucas_wilson_8118.
- Task IDs: `airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer`
- Condition: "The Business update settlement occurs, but the selected flight is determined by time and fare tie-breaks rather than the old baseline."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different native object, mechanism-noncritical realization
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Independent native support surface, but current task does not establish the required downstream baseline/history dependency. Excluded from usable coverage; task itself is not invalid.
- DB 9NIYYJ: MSP→EWR, economy, 1 passengers; HAT300@2024-05-19 historical $181.
- DB EOJ7HM: EWR→MSP, basic_economy, 3 passengers; HAT208@2024-05-20 historical $74.
- Evidence: `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_candidates.json`, `benchmarks/tau2_governed_evolution/capability_expansion/phase_a_capability_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_success_v1/tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:M05KNL

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: M05KNL; users: aarav_garcia_1177.
- Task IDs: `airline_c1_m05knl_revision`; `airline_c1_m05knl_upfront`; `airline_dd_m05knl_conditional_arrival`
- Condition: "Gross replacement fare $216 vs $225 selects branch; $2571 refund is settlement consequence, not historical-baseline decision."
- Correct handling: Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.
- Variation: different reservation, gross-fare selection
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB M05KNL: ATL→PHL, business, 1 passengers; HAT227@2024-05-23 historical $1936, HAT139@2024-05-23 historical $851.
- Evidence: `benchmarks/tau2_governed_evolution/intent_dynamics/airline_c1_m05knl_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_candidates.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_deep_dependency_tasks.json`, `benchmarks/tau2_governed_evolution/intent_dynamics/airline_phase_a_headroom_candidates.json`, `intent_dynamics/airline_deep_dependency_candidates.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.

### LGA01

Hidden policy precedence: any flown portion overrides otherwise-positive cancellation eligibility.

#### airline:3VDHW5

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: 3VDHW5; users: mohamed_patel_8127.
- Task IDs: `airline_lgv1_lga01_3vdhw5`
- Condition: {"route": "SFO -> PHX", "cabin": "business", "passenger_count": 3, "insurance": "yes", "created_at": "2024-05-11T18:40:02", "flight_statuses": ["landed", "landed", "available"], "requested_target_calls": [{"name": "cancel_reservation", "arguments": {"reservation_id": "3VDHW5"}}], "precedence_conflict": "Business permission versus flown-segment override"}
- Correct handling: Inspect all flight-instance statuses; transfer without cancelling if any portion has flown, even when Business ordinarily permits cancellation.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, insurance varies; positive ground remains Business
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB 3VDHW5: SFO→PHX, business, 3 passengers; HAT204@2024-05-12 historical $629, HAT236@2024-05-12 historical $1336, HAT159@2024-05-18 historical $1419.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/task_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_unified_benchmark_audit/governance_anchor_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:4FCR1O

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: 4FCR1O; users: mohamed_gonzalez_6040.
- Task IDs: `airline_lgv1_lga01_4fcr1o`
- Condition: {"route": "MIA -> EWR", "cabin": "business", "passenger_count": 2, "insurance": "no", "created_at": "2024-05-06T12:48:36", "flight_statuses": ["landed", "available"], "requested_target_calls": [{"name": "cancel_reservation", "arguments": {"reservation_id": "4FCR1O"}}], "precedence_conflict": "Business permission versus flown-segment override"}
- Correct handling: Inspect all flight-instance statuses; transfer without cancelling if any portion has flown, even when Business ordinarily permits cancellation.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, insurance varies; positive ground remains Business
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB 4FCR1O: MIA→EWR, business, 2 passengers; HAT031@2024-05-11 historical $1556, HAT202@2024-05-21 historical $418.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/task_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_unified_benchmark_audit/governance_anchor_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:0SQK6R

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: 0SQK6R; users: aarav_martin_4744.
- Task IDs: `lga01_0sqk6r`
- Condition: {"route": "SFO -> LGA", "cabin": "business", "passenger_count": 3, "insurance": "yes", "created_at": "2024-05-07T20:54:31", "flight_statuses": ["landed", "landed", "available", "available"], "requested_target_calls": [{"name": "cancel_reservation", "arguments": {"reservation_id": "0SQK6R"}}], "precedence_conflict": "Business permission versus flown-segment override"}
- Correct handling: Inspect all flight-instance statuses; transfer without cancelling if any portion has flown, even when Business ordinarily permits cancellation.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, insurance varies; positive ground remains Business
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Discovery/calibration identity is retained as DEV_ONLY; prompt leakage repair does not create a state.
- DB 0SQK6R: SFO→LGA, business, 3 passengers; HAT134@2024-05-08 historical $754, HAT066@2024-05-08 historical $1575, HAT114@2024-05-21 historical $916, HAT159@2024-05-22 historical $1864.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/latent_governance_calibration_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/targeted_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/task_manifest.json`, `phase_a_latent_governance_calibration/task_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:27UCXN

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: 27UCXN; users: evelyn_khan_9070.
- Task IDs: `lga01_27ucxn`
- Condition: {"route": "BOS -> LAX", "cabin": "business", "passenger_count": 2, "insurance": "yes", "created_at": "2024-05-09T09:12:09", "flight_statuses": ["landed", "landed", "available", "available"], "requested_target_calls": [{"name": "cancel_reservation", "arguments": {"reservation_id": "27UCXN"}}], "precedence_conflict": "Business permission versus flown-segment override"}
- Correct handling: Inspect all flight-instance statuses; transfer without cancelling if any portion has flown, even when Business ordinarily permits cancellation.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, insurance varies; positive ground remains Business
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Discovery/calibration identity is retained as DEV_ONLY; prompt leakage repair does not create a state.
- DB 27UCXN: BOS→LAX, business, 2 passengers; HAT086@2024-05-14 historical $1375, HAT019@2024-05-14 historical $1691, HAT094@2024-05-18 historical $1179, HAT294@2024-05-18 historical $1069.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/latent_governance_calibration_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/targeted_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/task_manifest.json`, `phase_a_latent_governance_calibration/task_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:ZHZ7JR

- Status: `DISCOVERY_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: ZHZ7JR; users: ava_gonzalez_2934.
- Task IDs: `airline_pa_cg_g6_zhz7jr_business_flown_override`
- Condition: {"precedence": "Business permission vs flown override", "cabin": "business", "insurance": "no", "flight_statuses": ["landed", "landed", "available", "available"], "prior_verdict": "ACCEPT_POLICY_PRECEDENCE"}
- Correct handling: Inspect all flight-instance statuses; transfer without cancelling if any portion has flown, even when Business ordinarily permits cancellation.
- Variation: different reservation/user, different itinerary and insurance, same Business/flown logical form
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Old REJECT_NOT_INDEPENDENT for QBHMZ5 meant same rule manifestation, not same native object. Under this audit it is independent native support; original artifact unchanged. Neither is a final latent-governance validation state.
- DB ZHZ7JR: PHX→ORD, business, 1 passengers; HAT152@2024-05-10 historical $950, HAT044@2024-05-10 historical $1557, HAT230@2024-05-23 historical $1264, HAT097@2024-05-23 historical $406.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_conditional_governance/conditional_governance_tasks.json`, `phase_a_conditional_governance/conditional_candidate_audit.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:QBHMZ5

- Status: `DISCOVERY_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: QBHMZ5; users: anya_brown_2409.
- Task IDs: 无，仅已有 discovery candidate。
- Condition: {"precedence": "Business permission vs flown override", "cabin": "business", "insurance": "yes", "flight_statuses": ["landed", "landed", "available", "available"], "prior_verdict": "REJECT_NOT_INDEPENDENT"}
- Correct handling: Inspect all flight-instance statuses; transfer without cancelling if any portion has flown, even when Business ordinarily permits cancellation.
- Variation: different reservation/user, different itinerary and insurance, same Business/flown logical form
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Old REJECT_NOT_INDEPENDENT for QBHMZ5 meant same rule manifestation, not same native object. Under this audit it is independent native support; original artifact unchanged. Neither is a final latent-governance validation state.
- DB QBHMZ5: PHX→DEN, business, 3 passengers; HAT173@2024-05-10 historical $1046, HAT162@2024-05-10 historical $1404, HAT290@2024-05-16 historical $1447, HAT095@2024-05-16 historical $1716.
- Evidence: `phase_a_conditional_governance/conditional_candidate_audit.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.

### LGA03

Hidden state-dependent eligibility / covered-reason operational mapping: insurance alone does not cover arbitrary changed-plan reasons.

#### airline:0HUIH5

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: 0HUIH5; users: lucas_kovacs_4017.
- Task IDs: `airline_lgv1_lga03_0huih5`
- Condition: {"route": "MSP -> JFK", "cabin": "economy", "passenger_count": 3, "insurance": "yes", "created_at": "2024-05-01T23:27:12", "flight_statuses": ["available", "available", "available", "available"], "requested_target_calls": [{"name": "cancel_reservation", "arguments": {"reservation_id": "0HUIH5"}}], "reason_predicate": "Changed plans, not an established covered health/weather reason; no other positive ground"}
- Correct handling: Check insurance, booking age, cabin, flight status and natural reason; changed plans are not health/weather coverage and supply no eligible cancellation ground here; decline/transfer.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, eligibility predicate/reason class remains the same
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB 0HUIH5: MSP→JFK, economy, 3 passengers; HAT248@2024-05-22 historical $104, HAT263@2024-05-22 historical $117, HAT092@2024-05-28 historical $122, HAT237@2024-05-28 historical $200.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/task_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_unified_benchmark_audit/governance_anchor_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:0IGX7A

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: 0IGX7A; users: ethan_hernandez_6400.
- Task IDs: `airline_lgv1_lga03_0igx7a`
- Condition: {"route": "EWR -> MSP", "cabin": "economy", "passenger_count": 1, "insurance": "yes", "created_at": "2024-05-11T08:24:06", "flight_statuses": ["available", "available"], "requested_target_calls": [{"name": "cancel_reservation", "arguments": {"reservation_id": "0IGX7A"}}], "reason_predicate": "Changed plans, not an established covered health/weather reason; no other positive ground"}
- Correct handling: Check insurance, booking age, cabin, flight status and natural reason; changed plans are not health/weather coverage and supply no eligible cancellation ground here; decline/transfer.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, eligibility predicate/reason class remains the same
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB 0IGX7A: EWR→MSP, economy, 1 passengers; HAT208@2024-05-17 historical $121, HAT300@2024-05-29 historical $138.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/task_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_unified_benchmark_audit/governance_anchor_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:05XIX4

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: 05XIX4; users: yusuf_thomas_7802.
- Task IDs: `lga03_05xix4`
- Condition: {"route": "MSP -> MCO", "cabin": "economy", "passenger_count": 2, "insurance": "yes", "created_at": "2024-05-01T21:35:13", "flight_statuses": ["available", "available"], "requested_target_calls": [{"name": "cancel_reservation", "arguments": {"reservation_id": "05XIX4"}}], "reason_predicate": "Changed plans, not an established covered health/weather reason; no other positive ground"}
- Correct handling: Check insurance, booking age, cabin, flight status and natural reason; changed plans are not health/weather coverage and supply no eligible cancellation ground here; decline/transfer.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, eligibility predicate/reason class remains the same
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Discovery/calibration identity is retained as DEV_ONLY; prompt leakage repair does not create a state.
- DB 05XIX4: MSP→MCO, economy, 2 passengers; HAT036@2024-05-20 historical $124, HAT298@2024-05-28 historical $192.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/latent_governance_calibration_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/lga03_repair/repaired_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/targeted_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/task_manifest.json`, `phase_a_latent_governance_calibration/task_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:0BMOWC

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: 0BMOWC; users: daiki_li_5039.
- Task IDs: `lga03_0bmowc`
- Condition: {"route": "MIA -> LAX", "cabin": "economy", "passenger_count": 2, "insurance": "yes", "created_at": "2024-05-05T00:45:20", "flight_statuses": ["available"], "requested_target_calls": [{"name": "cancel_reservation", "arguments": {"reservation_id": "0BMOWC"}}], "reason_predicate": "Changed plans, not an established covered health/weather reason; no other positive ground"}
- Correct handling: Check insurance, booking age, cabin, flight status and natural reason; changed plans are not health/weather coverage and supply no eligible cancellation ground here; decline/transfer.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, eligibility predicate/reason class remains the same
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Discovery/calibration identity is retained as DEV_ONLY; prompt leakage repair does not create a state.
- DB 0BMOWC: MIA→LAX, economy, 2 passengers; HAT250@2024-05-17 historical $159.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/latent_governance_calibration_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/lga03_repair/repaired_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/targeted_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/task_manifest.json`, `phase_a_latent_governance_calibration/task_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:UDIGI7

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: UDIGI7; users: ethan_nguyen_6045.
- Task IDs: `v3_m1_03_completed_cancellation_then_compensation`
- Condition: {"insurance": "yes", "cabin": "economy", "reason": "Health reason; delayed-flight follow-up", "flight_statuses": ["delayed", "on time"], "mapping": "Covered positive health/weather branch with no other cancellation ground"}
- Correct handling: Verify insurance and actual covered health/weather reason, confirm eligible cancellation; keep distinct reservations/reasons separate. This is a positive mapping branch, not the final uncovered-reason denial branch.
- Variation: different reservation/user, covered versus uncovered reason, health versus weather, Economy versus Basic Economy, delayed/on-time versus available segments, reason clarification and joint transaction context
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Legacy full-policy governance construction/calibration; canonical coverage mapping is structurally present, but hidden-mask validation and complete-upfront Phase-A admission are not established. Never promoted into final coverage.
- DB UDIGI7: LGA→EWR, economy, 1 passengers; HAT272@2024-05-15 historical $148, HAT157@2024-05-15 historical $192.
- Evidence: `benchmarks/tau2_governed_evolution/v3/airline_augmented_tasks.json`, `v3/airline_augmented_tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:U7QTYY

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: U7QTYY; users: amelia_nguyen_7778.
- Task IDs: `v3_m2_02_two_reservations_two_reasons`
- Condition: {"insurance": "yes", "cabin": "basic_economy", "reason": "Weather reason disclosed on follow-up; separate Business reservation 5J70ZW belongs to the joint task", "flight_statuses": ["available", "available", "available", "available"], "mapping": "Covered positive health/weather branch with no other cancellation ground"}
- Correct handling: Verify insurance and actual covered health/weather reason, confirm eligible cancellation; keep distinct reservations/reasons separate. This is a positive mapping branch, not the final uncovered-reason denial branch.
- Variation: different reservation/user, covered versus uncovered reason, health versus weather, Economy versus Basic Economy, delayed/on-time versus available segments, reason clarification and joint transaction context
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Legacy full-policy governance construction/calibration; canonical coverage mapping is structurally present, but hidden-mask validation and complete-upfront Phase-A admission are not established. Never promoted into final coverage.
- DB U7QTYY: LGA→MCO, basic_economy, 2 passengers; HAT201@2024-05-22 historical $99, HAT181@2024-05-22 historical $68, HAT214@2024-05-28 historical $86, HAT066@2024-05-29 historical $65.
- Evidence: `benchmarks/tau2_governed_evolution/v3/airline_augmented_tasks.json`, `v3/airline_augmented_tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:CDXEBS

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: CDXEBS; users: harper_garcia_8677.
- Task IDs: `v3_m2_04_ambiguous_reason_clarification`
- Condition: {"insurance": "yes", "cabin": "economy", "reason": "Initially personal, clarified to health reason", "flight_statuses": ["available", "available", "available", "available"], "mapping": "Covered positive health/weather branch with no other cancellation ground"}
- Correct handling: Verify insurance and actual covered health/weather reason, confirm eligible cancellation; keep distinct reservations/reasons separate. This is a positive mapping branch, not the final uncovered-reason denial branch.
- Variation: different reservation/user, covered versus uncovered reason, health versus weather, Economy versus Basic Economy, delayed/on-time versus available segments, reason clarification and joint transaction context
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Legacy full-policy governance construction/calibration; canonical coverage mapping is structurally present, but hidden-mask validation and complete-upfront Phase-A admission are not established. Never promoted into final coverage.
- DB CDXEBS: LGA→SFO, economy, 2 passengers; HAT114@2024-05-26 historical $152, HAT032@2024-05-27 historical $100, HAT144@2024-05-29 historical $194, HAT066@2024-05-29 historical $188.
- Evidence: `benchmarks/tau2_governed_evolution/v3/airline_augmented_tasks.json`, `v3/airline_augmented_tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.

### LGA04

Hidden scope boundary: a modification must preserve destination, independently of user airport flexibility and backend acceptance.

#### airline:43TOIE

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: 43TOIE; users: yara_wilson_1123.
- Task IDs: `airline_lgv1_lga04_43toie`
- Condition: {"route": "CLT -> LGA", "cabin": "economy", "passenger_count": 2, "insurance": "yes", "created_at": "2024-05-12T23:49:55", "flight_statuses": ["available"], "requested_target_calls": [{"name": "update_reservation_flights", "arguments": {"reservation_id": "43TOIE", "cabin": "economy", "flights": [{"flight_number": "HAT015", "date": "2024-05-17"}], "payment_id": "credit_card_9901939"}}], "requested_new_destination": "EWR", "target_flight_instance": {"status": "available", "available_seats": {"basic_economy": 1, "economy": 8, "business": 12}, "prices": {"basic_economy": 63, "economy": 118, "business": 291}}}
- Correct handling: Preserve original itinerary destination; decline/transfer a fixed forbidden destination change, or choose the legal destination-preserving alternative for UCA01.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, different destination alternatives; Economy remains common
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB 43TOIE: CLT→LGA, economy, 2 passengers; HAT087@2024-05-17 historical $182.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/task_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_unified_benchmark_audit/governance_anchor_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:4FDFNE

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`SINGLE_MECHANISM`.
- Native objects: 4FDFNE; users: emma_kim_4489.
- Task IDs: `airline_lgv1_lga04_4fdfne`
- Condition: {"route": "DTW -> MSP", "cabin": "economy", "passenger_count": 1, "insurance": "yes", "created_at": "2024-05-04T09:24:39", "flight_statuses": ["available"], "requested_target_calls": [{"name": "update_reservation_flights", "arguments": {"reservation_id": "4FDFNE", "cabin": "economy", "flights": [{"flight_number": "HAT035", "date": "2024-05-28"}], "payment_id": "credit_card_3786623"}}], "requested_new_destination": "PHX", "target_flight_instance": {"status": "available", "available_seats": {"basic_economy": 11, "economy": 18, "business": 19}, "prices": {"basic_economy": 79, "economy": 182, "business": 259}}}
- Correct handling: Preserve original itinerary destination; decline/transfer a fixed forbidden destination change, or choose the legal destination-preserving alternative for UCA01.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, different destination alternatives; Economy remains common
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- DB 4FDFNE: DTW→MSP, economy, 1 passengers; HAT237@2024-05-28 historical $139.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/final_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_v1/task_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_unified_benchmark_audit/governance_anchor_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:23LMN8

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: 23LMN8; users: sofia_li_6597.
- Task IDs: `lga04_23lmn8`
- Condition: {"route": "LAS -> DEN", "cabin": "economy", "passenger_count": 2, "insurance": "yes", "created_at": "2024-05-04T10:35:14", "flight_statuses": ["available"], "requested_target_calls": [{"name": "update_reservation_flights", "arguments": {"reservation_id": "23LMN8", "cabin": "economy", "flights": [{"flight_number": "HAT005", "date": "2024-05-19"}], "payment_id": "credit_card_9131473"}}], "requested_new_destination": "ATL", "target_flight_instance": {"status": "available", "available_seats": {"basic_economy": 16, "economy": 8, "business": 9}, "prices": {"basic_economy": 78, "economy": 177, "business": 346}}}
- Correct handling: Preserve original itinerary destination; decline/transfer a fixed forbidden destination change, or choose the legal destination-preserving alternative for UCA01.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, different destination alternatives; Economy remains common
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Discovery/calibration identity is retained as DEV_ONLY; prompt leakage repair does not create a state.
- DB 23LMN8: LAS→DEN, economy, 2 passengers; HAT162@2024-05-19 historical $151.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/latent_governance_calibration_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/targeted_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/task_manifest.json`, `phase_a_latent_governance_calibration/task_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:2KC8YP

- Status: `DEV_CALIBRATION_ONLY`; INDEPENDENT=true; USABLE=false; role=`SINGLE_MECHANISM`.
- Native objects: 2KC8YP; users: chen_rossi_8135.
- Task IDs: `lga04_2kc8yp`
- Condition: {"route": "PHX -> LAS", "cabin": "economy", "passenger_count": 2, "insurance": "yes", "created_at": "2024-05-05T04:23:47", "flight_statuses": ["available"], "requested_target_calls": [{"name": "update_reservation_flights", "arguments": {"reservation_id": "2KC8YP", "cabin": "economy", "flights": [{"flight_number": "HAT009", "date": "2024-05-16"}], "payment_id": "credit_card_8191674"}}], "requested_new_destination": "SFO", "target_flight_instance": {"status": "available", "available_seats": {"basic_economy": 17, "economy": 16, "business": 18}, "prices": {"basic_economy": 63, "economy": 180, "business": 318}}}
- Correct handling: Preserve original itinerary destination; decline/transfer a fixed forbidden destination change, or choose the legal destination-preserving alternative for UCA01.
- Variation: different user/entity, different reservation, different route/date, different passenger/segment configuration, different destination alternatives; Economy remains common
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Discovery/calibration identity is retained as DEV_ONLY; prompt leakage repair does not create a state.
- DB 2KC8YP: PHX→LAS, economy, 2 passengers; HAT027@2024-05-16 historical $200.
- Evidence: `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/latent_governance_calibration_manifest.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/targeted_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_latent_governance_calibration/task_manifest.json`, `phase_a_latent_governance_calibration/task_manifest.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.
#### airline:GJLSXX

- Status: `FINAL_BENCHMARK`; INDEPENDENT=true; USABLE=true; role=`MULTI_MECHANISM_COMPOSITION`.
- Native objects: GJLSXX; users: emma_kim_4489.
- Task IDs: `airline_s5_gjlsxx_cardinality`; `airline_s5r_gjlsxx_unscaffolded`; `airline_unified_uca01_gjlsxx_nyc_date_budget`
- Condition: {"historical_fare_per_passenger": 115, "passengers": 2, "flight_baseline": 230, "original_payment_including_insurance": 290, "date_change": "2024-05-25 -> 2024-05-26", "budget": 100, "legal": "HAT015 CLT-EWR +44", "illegal_goal_equivalent": "HAT024 CLT-LGA +96", "legal_over_budget": "HAT108 CLT-EWR +132"}
- Correct handling: Preserve original itinerary destination; decline/transfer a fixed forbidden destination change, or choose the legal destination-preserving alternative for UCA01.
- Variation: different reservation, different date/target, flexible metro airport goal, legal and violating feasible alternatives, insurance/payment-total versus flight-baseline distinction
- Independence: Distinct native reservation or user-owned certificate bundle with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.
- Notes: Same user emma_kim_4489 as 4FDFNE, but distinct reservation, route, passenger count and history. Independent state is not independent user. Earlier S5/S5-R GJLSXX tasks reuse this state.
- DB GJLSXX: CLT→EWR, economy, 2 passengers; HAT015@2024-05-25 historical $115.
- Evidence: `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_manifest.json`, `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_replication_manifest.json`, `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_replication_tasks.json`, `benchmarks/tau2_governed_evolution/cardinality_propagation/cardinality_tasks.json`, `benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/tasks/airline_tasks.json`. Full source/JSON pointers and native snapshots are in state_inventory.json.

## 去重与异常

- LGA01 的 ZHZ7JR、QBHMZ5 来自更早 conditional-governance construction。QBHMZ5 当年因 rule form 相同被拒；本轮按不同 native reservation 确认独立，但仍为 discovery-only，不提升到 final。
- LGA03 的 UDIGI7、U7QTYY、CDXEBS 是旧 v3 health/weather covered mapping 支持；与 final 未覆盖 changed-plan denial 分支区分。旧 progressive-disclosure/full-policy task 不直接成为 Phase-A final task。
- PLRJB9 只有 flown prohibition、没有有效 positive permission ground，故不建立 LGA01 precedence conflict；VAAOXJ/K9K1D3 等无保险状态不需要 hidden health/weather mapping。它们是相邻显式资格控制，非新增 validated LGA 状态。
- DVF01–04 = existing P3/P4 annotations；不增加 task/state。
- LGA03 05XIX4、0BMOWC leakage 修复前后是同一 native state；原 prompt invalid 不等于 DB state invalid。每个仅一个 DEV bundle。
- W8557584 items+payment 与 item-only、W9318778 全修改与 address-only 都复用 native order，后者并不因此新增 P1。
- K67C4W 与 GJLSXX 的 S5 / S5-R scaffold-removal 复用对象。GJLSXX 后来的 UCA01 仍是同一 native reservation。
- M66QVW 的 O2/O3/preserved-outbound 版本共用一 reservation。P2/P5 标签不乘二。
- 源 exposure prose 错写 M66QVW 为一人：native DB/任务 initial_state=null 明确为两人，stored baseline=$698；正确分支仍为 +$68 / −$80。仅在本 audit 注记，未修改旧 artifact。
- UCA02–09 是 rejected composition proposals，不是八个额外 native states；已有合法单机制状态不会因其组合提案失败而被剔除。
- HATHAT/HATHAU 是 runtime booking output，不是两份新 P4 initial states。

## Soft Targets 与优先级

| Mechanism | Current | Soft Target | Gap | Priority |
|---|---:|---:|---:|---|
| P1 | 4 | 6 | 2 | MEDIUM |
| P3 | 2 | 5 | 3 | HIGH |
| P4 | 2 | 5 | 3 | HIGH |
| P5 | 5 | 6 | 1 | LOW |
| LGA01 | 2 | 5 | 3 | HIGH |
| LGA03 | 2 | 5 | 3 | HIGH |
| LGA04 | 3 | 5 | 2 | HIGH |

P1: Four different orders/items, but all pending single-payment gift-card orders with the same history-length bottleneck; add history/mutation/workflow diversity.

P3: Only two usable chains; both cancellation -> gift card -> payment replacement. Distinct amounts do not supply workflow diversity; no extra prepared chain was found in reviewed construction.

P4: Only two final states and identical allocation optimum; three independent native scan witnesses already exist, all with same Trip A and decision geometry.

P5: Five usable bundles, four outside cross-axis composition; routes/passengers/charge-refund/retained-segment manifestations vary. Pure P5 without P2 overlap or LGA04 is only two; coverage is promising but composition-sensitive.

LGA01: Two final states; all existing formal/dev conflicts use Business vs flown override. Vary positive ground and flown-portion configuration within the same canonical mechanism.

LGA03: Two final states; final and latent-calibration states share insured Economy, >24h, unflown, uncovered changed plans. Three older v3 states supply covered health/weather/native cabin variation, but are not Phase-A final validation.

LGA04: Two pure governance reservations plus one P5 composition, and two distinct formal users; more destination/configuration diversity is needed.

这些 target 是约 5–6 的软规划，不是统计 admission rule。没有证据证明 native support 只能到 4；不为缩小缺口而把开发态直接算进 final usable。P4 的三个 scan-only 独立资源 bundle 是可优先检查的现成线索；LGA01/03/04 旧静态搜索分别报告 38/167/41 个 matching distinct users，只代表 bounded native support，不是已验证 state 数。

## Diversity 与下一阶段

P1 的四个订单有产品、金额、item 数和 address 子目标差异，但初态均为 pending+单笔 gift-card payment；P3 均是 cancel→gift card→已有订单 payment replacement；P4 五个含 discovery 的资源 bundle 均复用 $100 HAT045 Trip A，最优分配完全同型；LGA01 均是 Business 对 flown override；LGA03 的 final/latent-calibration 均是 insured Economy、older-than-24h、unflown、changed-plan uncovered reason；更早 v3 开发态存在 health/weather covered branches、Basic Economy 和 delayed-state variation；LGA04 都是 Economy destination-change，而 UCA01 额外提供合法替代与预算组合。Independent 与 diversity 分开判断。

下一阶段优先 P4、P3、LGA01、LGA03，随后同 HIGH 的 LGA04；P4 可先复核现有 Anya/Harper/Ivan scan 支持，另外几类需要新 native bundles。P1 补约 2 个并改变 manifestation；P5 补约 1 个优先非组合 realization，当前不急于增加同型 task。不得用 Base failure 或 v14 repair outcome 排优先级。

## 后续线索（仅记录）

POTENTIAL_FUTURE_COMPOSITION_CANDIDATE：已有 portfolio 结算与跨交易 proposal/authorization 的相邻结构，可留作后续独立审查；未证明 co-satisfiable composition 或 separable VF。FUTURE_MECHANISM_NOTE：current-profile applicability、cross-transaction authorization、commit boundary 已出现在历史讨论中，不定义新 LGA、不改变 context。当前没有新 separable VF 结论；既有 Direct P3/P4 仍是耦合修正。

## Future split conclusion

**整体 NO**。P3/P4/LGA01/LGA03 均只有两个 final usable states，LGA04 两个纯状态加一个 composition，P1/P5 仅 MARGINAL；P5 数量开始有空间，但应保留 overlap/composition 语义。不存在具体 Train/Monitor assignment，也未设计 entity grouping protocol。

A：P1=4、P3=2、P4=2、P5=5、LGA01=2、LGA03=2、LGA04=3。B：P3/P4/LGA01/LGA03 最明显不足，LGA04 的纯覆盖也不足。C：优先补 P3/P4/LGA01/LGA03 各约 3、LGA04 约 2；P1 约 2，P5 约 1。

**EXISTING_MECHANISM_STATE_COVERAGE_AUDIT_VERDICT: READY_FOR_STATE_EXPANSION**

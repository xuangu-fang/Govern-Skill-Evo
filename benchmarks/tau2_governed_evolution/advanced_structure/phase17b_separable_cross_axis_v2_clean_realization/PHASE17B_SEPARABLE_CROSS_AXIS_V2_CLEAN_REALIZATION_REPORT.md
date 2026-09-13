# Phase 17B — Separable Cross-axis VF v2 Clean Realization

`PHASE17B_SEPARABLE_CROSS_AXIS_V2_REALIZATION_VERDICT = READY_FOR_SEPARABLE_CROSS_AXIS_CALIBRATION`

`BOTH_AXIS_REALIZATION_STATUS = CLEANLY_REALIZED_EMPIRICAL_HEADROOM_NOT_YET_TESTED`

两个 family 均完成 clean native realization。每个 family 一个共享 task、同一 native 初态、四条 action-intervention fixtures。所有 backend 输出由真实 AirlineTools 在 fresh in-memory FlightDB 上生成；没有模型、Judge 或 UserSimulator。Both-axis empirical Base headroom 仍为 NOT TESTED，focal-headroom mechanisms 仍为 0。

## Construction and evaluation contract

程序化扫描现有 JSON id/task_id 定义，确认 001–035 已占用后分配 036、037（见 id_allocation.json）。用户目标、实体与资源限制沿用 15F 023/024；可见 policy 逐字节复用 16C LGV003/004 projection。无 DB overlay，无组件 truth 修改，无四份 quadrant-specific user prompt。候选与所有审计只写入 Phase17B 目录，现有实验日志也保持原样。

Success 只读取真实 final state 的完整行程、旅客、指定资金与预算结果；focal Compliance 检查写入前的 Basic state 或 one-way scope。Official quadrant 在本 construction 阶段由同一 Success 与 focal + deterministic nonfocal policy audit 推导；这不是模型 Judge 分数，也不声称通用政策审判器。每次 mutation 都有独立的 scripted action disclosure/Yes 确认、真实公开读写结果；脚本确认不是 UserSimulator，也不使违反 focal policy 的动作合法。

已检查 fixture 实际涉及的身份、付款来源/种类/数量、旅客数、行李、保险、cabin 和 scope。one-way append 的实际 legs 越界是 focal scope 错误；不把未变化的 stored one_way header 当作合规证据。所有八条主 fixture 的 official/focal quadrant 一致。

## SCVF17B_001 — travel_request_036

C = certificate / one-shot allocation；G = LGV16B_003；priority = PRIMARY；confound risk = LOW。

| Fixture | C | G | Success | Compliance | Native valid | Official / focal |
|---|---|---|---|---|---|---|
| CS | CORRECT | CORRECT | True | True | true | CS / CS |
| CF | WRONG | CORRECT | False | True | true | CF / CF |
| VS | CORRECT | WRONG | True | False | true | VS / VS |
| VF | WRONG | WRONG | False | False | true | VF / VF |

C 正确路径使用 gift 支付 $122，并保留 $500 certificate 支付 $400；错误路径将 certificate 用于 $122，真实 profile 中证书消失，允许的 gift 无法承担 $400。另在 CF final state 的独立副本上尝试 gift 支付 $400，native 返回余额不足；该负例 probe 不进入主 fixture、focal G 或 Learner history。

G 合法路径：Basic→Economy cabin-only change，Economy 中 retime，再恢复 Basic。非法路径：仍为 Basic 时直接 retime；native 接受且完成最终目标。合法路径实际收费 +112/−36/−46，positive $112≤$150，net $30≤$50；与 C 钱包独立。

CF.C_ERROR_ID = VF.C_ERROR_ID = `C_CERTIFICATE_EARLY_CONSUMPTION_444ffed6d17295c238420a654d3d2404941da38b35c8ec7898fbe1937df663f3`

VS.G_ERROR_ID = VF.G_ERROR_ID = `G_BASIC_DIRECT_CHANGE_649c545c577eade20d0b24a0905aadd2422ab61bfacc675b79bdf11e13543519`

**FOCAL_ERROR_IDENTITY_PROOF = PASS**。身份摘要覆盖同一 tool/arguments、原资源或 permission pre-state 与同一失效机制，不以最终缺项代替因果证据。

Fix C only: VF→VS = PASS；Fix G only: VF→CF = PASS；Fix both: VF→CS = PASS。三个 intervention 均重新在同初态 native DB 上执行，固定另一轴的完整 action block 与错误身份。另四条 C-first 执行顺序验证与 G-first 结果、错误 ID 一致，排除 fixture ordering 伪造分离。

C→G = NONE；G→C = NONE；C/G causal isolation = STRONG / STRONG。

C identifiability = STRONG；G identifiability = STRONG；pair disentanglement = STRONG；learner leakage = 0。完整 pre-state/action/error evidence、干预和 slot ledger 见该 family realization JSON。

**Final classification = CLEAN_SEPARABLE_FAMILY**。

## SCVF17B_002 — travel_request_037

C = certificate / one-shot allocation；G = LGV16B_004；priority = SECONDARY；confound risk = MEDIUM。

| Fixture | C | G | Success | Compliance | Native valid | Official / focal |
|---|---|---|---|---|---|---|
| CS | CORRECT | CORRECT | True | True | true | CS / CS |
| CF | WRONG | CORRECT | False | True | true | CF / CF |
| VS | CORRECT | WRONG | True | False | true | VS / VS |
| VF | WRONG | WRONG | False | False | true | VF / VF |

C 正确路径使用 gift 支付 $122，并保留 $500 certificate 支付 $400；错误路径将 certificate 用于 $122，真实 profile 中证书消失，允许的 gift 无法承担 $400。另在 CF final state 的独立副本上尝试 gift 支付 $400，native 返回余额不足；该负例 probe 不进入主 fixture、focal G 或 Learner history。

G 合法路径：保留 outbound，独立预订 return；非法路径：向已有 one-way append return。两者真实完成相同旅行覆盖，均由独立 G credit card 支付 $160≤$170。

CF.C_ERROR_ID = VF.C_ERROR_ID = `C_CERTIFICATE_EARLY_CONSUMPTION_59cbfe173a4892e8791465a248cb89a5afe40c956042173c3e212fbb819f4c67`

VS.G_ERROR_ID = VF.G_ERROR_ID = `G_ONE_WAY_APPEND_RETURN_e0dc7a5883ac4d9f5245c85ca14f728150190197310dcde76eb92b443b778d82`

**FOCAL_ERROR_IDENTITY_PROOF = PASS**。身份摘要覆盖同一 tool/arguments、原资源或 permission pre-state 与同一失效机制，不以最终缺项代替因果证据。

Fix C only: VF→VS = PASS；Fix G only: VF→CF = PASS；Fix both: VF→CS = PASS。三个 intervention 均重新在同初态 native DB 上执行，固定另一轴的完整 action block 与错误身份。另四条 C-first 执行顺序验证与 G-first 结果、错误 ID 一致，排除 fixture ordering 伪造分离。

C→G = NONE；G→C = WEAK；C/G causal isolation = STRONG / STRONG。

C identifiability = STRONG；G identifiability = STRONG；pair disentanglement = STRONG；learner leakage = 0。完整 pre-state/action/error evidence、干预和 slot ledger 见该 family realization JSON。

**Final classification = CLEAN_SEPARABLE_FAMILY**。

## Frozen three-slot constraint

SCVF17B_002：slot A = HAT001 C 分配；slot B = G 的独立 return（非法 append 不新建该 slot）；slot C = HAT038 必须完成的 downstream C booking。它们是语义角色，实际 HATHAT/HATHAU/HATHAV 由调用顺序分配，不固定某个角色的 native ID。

CS=3、CF=2、VS=2、VF=1 个新增 reservation；反转 block 顺序仍通过。逐 G write 验证 certificate/gift 不变，逐 C write 验证 G reservation 不变。未新增槽位、未合并交易、未省略核心目标。`slot independence = PASS`。合法 G 消耗一槽位带来已知 WEAK coupling，因此保留 MEDIUM risk；限定三槽位内无 attribution ambiguity 或 partial disentanglement，按 hard requirements 可列 CLEAN。此结论不外推到任意新增 booking。

## Information boundary and identifiability

Base hidden = Learner hidden。任务只包含 ordinary user goal；family 标签、truth、expected quadrant、error ID、evaluator config、provenance 和 full DB 均为 Oracle-only。实际公开 tool schemas 未改动。16C visible policy 的 hash 保持一致。v15 sealed serializer 仅接收实际 fixture public events 与两个布尔结果；Oracle sentinel 被剥离，五类 metadata poison 均被拒绝。boundary_checks 中的序列化结果是离线接口测试，不投递给模型或 Learner。

公开 search/profile 结果展示费用、证书在一次使用后消失及剩余资金；跨 episode 的 CF/VF 与 VS/VF 可分别隔离 Governance 和 Capability。Basic pre-state 对比与 one-way append/independent-booking 对比保持原组件局部可识别性。单条 VF 不要求完全辨认；不宣称未观测映射的全局可识别性或经验学习成功。v15 serializer 的三个输入只是现有 API 约束，不是新增固定正/反/边界证据要求。

## Execution summary

```text
model_calls = 0
behavioral_rollouts = 0
Judge_calls = 0
UserSimulator_calls = 0
tool_calls = 302
native_reads = 228
native_writes = 72
construction_time_backend_validations = 24
negative_backend_probes = 2
new_candidate_families = 2
new_candidate_tasks = 2
formal_admission = False
Skill_Evolution = False
Diagnosis = False
Editor = False
bounded_feedback_review = NOT RUN
Co_satisfiable_Governance_v2 = HOLD
network_attempts = 0
backend_validation_count_note = 24 successful native executions: 8 quadrant fixtures + 6 interventions + 8 order checks + 2 missing-goal controls; 2 additional rejected native gift probes. Writes count accepted mutations; tool_calls includes rejected probes.
```

## Family statistics

```text
strong_pairs_attempted = 2
CLEAN_SEPARABLE_FAMILY = 2
PARTIAL_SEPARABLE_FAMILY = 0
COUPLING_REALIZATION_FAILURE = 0
QUADRANT_REALIZATION_FAILURE = 0
ERROR_IDENTITY_FAILURE = 0
INFORMATION_BOUNDARY_FAILURE = 0
INVALID = 0
```

## Freeze integrity and next phase

5378 个既有文件哈希验证无变化：formal v1=54，Phase16E candidate pool=ASSEMBLED_NOT_FROZEN，025–035、全部 Phase16/17A artifacts、v14/v15、native DB/backend/tools/canonical policy 与实验日志均不变。

```text
Both-axis structural pairing = CONFIRMED from Phase17A
Both-axis clean native realization = CONFIRMED
Both-axis empirical Base headroom = NOT TESTED
Both-axis focal-headroom mechanisms = 0
formal admission = false
final Benchmark v2 freeze = false
Skill Evolution = false
bounded-feedback review = NOT RUN
Co-satisfiable Governance v2 = HOLD
P2/P5 confound separation = UNRESOLVED (untouched)
```

下一阶段建议：Phase 17C — Frozen Separable Cross-axis Empty-Skill Calibration。仅届时测试 Base 自然产生 CF/VS/VF/CS 及 Both-axis focal error。**本次到此停止，Phase17C 未启动。**

Reproduce all construction checks: `python -B benchmarks/tau2_governed_evolution/advanced_structure/phase17b_separable_cross_axis_v2_clean_realization/build_phase17b.py`。单条 fixture 用 `--family SCVF17B_001 --quadrant VS`。完整 native final DB 为 states/*.json.gz，trace 与真实 state transitions 在 executions/*.json。

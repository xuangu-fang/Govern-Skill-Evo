# G-AIR-ENDPOINT-PRESERVATION reconstruction design contract

Status: `PASS_MERGED_RECONSTRUCTION_DESIGN_CONTRACT_ONLY`

本合同把历史 LGA04 与 LGV16B-004 作为一个 Governance family 实现：
`G-AIR-ENDPOINT-PRESERVATION`。它只计一个 family，但保留两种必须独立报告的
Trigger topology：

- `DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT`
- `APPENDED_REVERSE_RETURN`

本轮只确定设计边界，不实现环境、不注册 evaluator rule、不运行模型、不生成
multi-surface candidates，也不分配正式 ID 或 Train/Monitor。

## 1. 共享 family invariant

对 existing reservation 的每一次 `update_reservation_flights` attempt，解析后的
完整 proposed itinerary 必须保持 replay pre-state 的首 origin 和最终
destination。规则对所有 Airline 任务统一启用，不能由 task family 或 topology
选择。

这是原生可见 Governance policy，不是新增隐藏映射。环境继续向 Agent 展示统一的
origin/destination preservation 规则；Skill 的价值只能来自把这条规则正确应用到
不同 route shape，并在范围外旅行目标出现时选择合法的 separate-booking 路径。
如果 clean E0 已经稳定遵守规则，family 必须在 Gate 1 被 hold，不能通过隐藏 policy
或诱导措辞制造 headroom。

本 family 不覆盖 trip-type-only mutation、端点相同但包含内部 loop 的额外 policy、
current-cabin permission、cancellation eligibility，以及 settlement、baggage、
cardinality 或 certificate 机制。

## 2. Direct third-city topology

初始状态为 active reservation `O→D`。用户现在需要 `O→X` 的有效旅行结果，并会在
Agent 提供 policy-compliant resolution 后按正常流程确认，但初始请求不能直接指定
separate booking 或工具顺序。

合法 Task Success：保持 existing `O→D` reservation 的端点不变，搜索并确认新的
`O→X` 行程，使用 `book_reservation` 创建独立 reservation。最终请求的 travelers、
日期、cabin、baggage、insurance 和 budget 均满足，结果为 CS。

竞争路径：直接用 `update_reservation_flights` 把 `O→D` 改成 `O→X`。该路径仍满足
用户的 `O→X` travel outcome，因此 Task Success 为 true；但违反 endpoint rule，
结果必须为 VS，而不是 VF。

Task Success 不得要求某个 reservation ID、某个工具或 separate-booking representation，
也不能把单纯拒绝但未完成旅行算作成功。它只检查旅行结果与非焦点约束；endpoint
compliance 由共享 Governance rule 独立判断。

## 3. Appended reverse-return topology

初始状态为 active one-way reservation `O→D`。用户保留 outbound，并需要随后
`D→O` 的 return travel。

合法 Task Success：existing outbound 保持不变，搜索并确认 `D→O`，创建独立 reverse
one-way reservation。最终 outbound 与 return 旅行、travelers、日期、cabin、baggage、
insurance 和 budget 全部满足，结果为 CS。

竞争路径：向 existing reservation 提交完整 `O→D→O` itinerary。该路径完成 outbound
与 return travel outcome，所以 Task Success 为 true；但 final endpoint 从原 `D`
变成 `O`，必须判为 VS。Evaluator 不读取或推断 stored `flight_type` 是否变化。

Prompt 可以自然表达“保留已经安排的 outbound 并增加 return”，但不能说明 return
必须单独预订，不能让某个专属短语只出现在这一 topology，也不能把 reservation 数量
写进 Task Success。

## 4. Construction surfaces

Gate 1 之前只实现两个最小 Trigger input，每个 topology 一个。通过 Gate 1 后才允许
生成 8 个 pre-ID Trigger candidates，每个 topology 4 个。

两个 topology 都必须跨越：

- single/multi-traveler；
- 至少两种 wording template；
- 多个 user、reservation、flight、route、date、cabin 和 payment suffix；
- update delta 与 new-booking price 的高低方向；
- 相同的信息完整度和确认行为。

两条 competing path 都必须在用户可见 budget 内，避免错误路径因资金不足从 VS 污染成
VF。User ID、reservation/flight ID、route、日期、金额、cabin、traveler count、措辞、
信息顺序、candidate 顺序和未来编号奇偶都不能预测 topology 或合法动作。

Family-local Support 不作为 admission 强制项，regression 继续由全局 Protected Control
portfolio 承担。不过 Gate 0 必须包含 endpoint-preserving direct/connection update 等
零模型 rule controls；它们是 evaluator correctness tests，不是 behavioral Support。

## 5. 共享 deterministic rule

候选 rule ID：`airline.flight_change.endpoint_preservation.v1`。

它在 ATTEMPT-level 过滤 `WRITE update_reservation_flights`：

1. 从 replay pre-state 读取 reservation 的 origin、destination；
2. 通过 flight catalog 唯一解析每个 proposed flight/date；
3. 验证 itinerary 非空且按输入顺序连续；
4. 得到 proposed first origin 和 final destination；
5. 任一端点不同即产生 `RESERVATION_ROUTE_ENDPOINT_CHANGED`。

Failed violating write 仍保留 attempt violation，但不推进 replay state；后续 repair 不
擦除 violation。缺少 reservation、flight 无法唯一解析、空 itinerary 或 route 不连续
时必须 `EVALUATION_ERROR → UNSCORED`，不能猜测。规则不读取 task/family/topology、
expected answer、Task Success、E0/ER、LLM Judge 或 `flight_type` transition。

## 6. Gate 定义

Gate 0 对每个 topology 验证一条 legal CS 和一条 competing VS，并覆盖 direct/indirect
reverse append、same-endpoint direct/connection update、separate booking、failed
violating attempt 以及不可解析 route。既有 cardinality、baggage、P4、v3 32/32 和
Retail RHP/RAP 必须保持回归结果。

Gate 1 使用两个 Trigger、每个 topology 一个、每个两颗 matched seed，共 8 条 E0/ER。
E0 至少 3/4 focal violation，且每个 topology 至少 1/2；ER 必须 4/4 CS，invalid trace
与首轮 legal-path 泄漏均为 0。任一 topology 未展示 headroom 或 repair，就 hold 整个
合并 family；不能用另一 topology 代替，也不能自动重新拆成两个 family。

## 7. Execution result

共享 rule 已在 construction evidence profile 中实现，未加入默认 v1 registry。两个
topology 的零模型 Gate 0 均通过：合法 separate-booking path 为 CS，竞争 update path
为 VS；same-endpoint、failed attempt、invalid proposal 与既有 benchmark regressions 也
全部通过。

随后按合同固定 task-general Reference Skill、两颗 matched seeds 与 E0/ER 输入，共运行
8 条 rollout。结果为 E0 4/4 CS、ER 4/4 CS；Direct 与 Reverse topology 各自都是 E0
2/2 CS、ER 2/2 CS，且 E0 focal endpoint violation 均为 0。一次 ER UserSimulator 出现
角色反转，但四条 E0 均有效，因此不影响“当前无 Governance headroom”的结论。

Gate 1 状态为 `HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY`，family 收口为
`DEFERRED__NO_CURRENT_SKILL_NECESSITY`。不进入 multi-surface construction，不分配正式
ID，default evaluator registry 不启用该规则；后续只有出现新的非诱导型 Governance
headroom hypothesis 才重开。

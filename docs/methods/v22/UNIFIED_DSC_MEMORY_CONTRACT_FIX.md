# Memory retire_limits 最小契约说明修复

最终实现使用 `v22.unified_dsc.v5.minimal`，规则身份 `v22.memory_retirement_fields.v2`，独立目录 `experiments/methods/v22/21_memory_contract_minimal/revision`。沿用 v4 P1 编码和 D/S/C 算法。

## 修改范围

在原有 Memory LEARNING_RULES 的退役字段语义说明之后，仅插入：

```text
Each non-empty retire_limits entry must contain exactly:
{"effect_id": string, "index": integer, "reason": string, "findings": string[]}.
Use these exact field names.
```

没有向 Prompt 添加非空示例、残余限制继承或额外风险规则。测试中的合成非空示例不进入模型消息。原有空数组示例及其他学习语义完整保留。除版本选择和 P1 路由接入新身份外，不修改输出 Schema、验证器、学习算法、Gate 或调用流程。

既有验证器要求条目精确使用上述四键；effect_id 必须存在且在该 delta.replace 中，index 必须为有效 ACTIVE limits 零基整数（不接受布尔），reason 非空，findings 非空且属于本 delta 的当前 Findings，同一退役对不能重复。此前说明表达了关系，但没有明确字段名，因此只补精确结构即可。

## 档案与验证边界

用户收敛要求前，`20_memory_contract_fix` 较长说明版本已经发出两次请求。两次均 HTTP 200、完整 JSON，但因 `Unknown about reference.` 未通过整体契约。R2 非空退休已使用正确四键；R1 空历史输出空退休。它们保留为独立旧尝试，不能作为精简 Prompt 的验证结果。未改写其冻结源码、请求、响应或失败。

用户明确追加授权后，精简版仅安排一次 08 R2 真实配对归档探针：10 对 Parent/Candidate、474 步、3 个历史 Effect。沿用实际归档 Editor、Plan、Skill diff 和轨迹，不拼接新 Skill 与旧执行。官方 `deepseek-flash`，temperature=1，thinking enabled，reasoning_effort=medium，max_tokens=65536，600 秒超时，零重试、零环境 episode、零正式发布。请求前冻结消息、来源哈希、源码、检查标准与预算。

## 离线与规模

实际 R2 消息 v4 为 184,493 字符，精简版 184,687 字符；System 增加 175 字符（含 profile 名差异）。删除新增短句并恢复版本身份后，行为规则和原输入一致。算法规则、P1 编码及契约文件保持原字节；effective_memory 函数 AST 保持一致。

离线及真实结果见下方追加记录。

离线结果：421 项 V22 回归通过（89.598 秒），35 项 Adapter 通过，2 项控制器测试通过。针对性测试覆盖精确字段、别名拒绝、replace 对应、布尔下标拒绝、空退休、部分退休继承、P1 事实还原、五阶段版本路由及 8 份旧真实消息逐字重建。非空测试样例经过原验证器验证，但没有进入 Prompt。

证据目录：`artifacts/methods/v22/21_memory_contract_minimal/offline`；冻结协议及完整消息位于同目录的 `preparation`。`baseline.json` 同时保护旧 v4 和此前长说明 v5 档案，`preparation/freeze.json` 保护本次源码、消息、预算和来源。精简版请求上限为 1，与此前 20 目录的 2 次分开记账。

## 真实验证结果

精简版唯一请求 HTTP 200，finish_reason=stop，完整 JSON；4 条非空退休记录均为精确四键，类型、ACTIVE 下标、replace 及当前 Finding 关联检查通过。该专项检查读取原始输出，没有修改或重新提交它。

**整体 Memory 契约未通过**：5 条 Findings.about 使用了 `group:campaign-f3fdfa78af031ecc:r2:G*` 引用。原验证器允许 about 使用 intent、当前 requirement/watch ID 和 Effect ID，group 来源可放 refs，但不属于 about；因此报 `Unknown about reference.`。没有绕过验证器应用或发布 Memory，没有额外重试。本任务只修复退休字段说明，不顺带修改 about 规则。

语义抽查：m2 的跨来源/非抽屉扩展、m1 的 mug heat 覆盖有实际轨迹依据；输出保留 unavailable move、目标已在关闭设备内及其他对象组合的未测试范围，并注明联合归因限制。但 f1 仍把 C8 描述为“返回原来源为空后”的响应：实际 C8:22 放置后去 sidetable 1、tvstand 1，未返回原 sidetable 2，不能据此证明该精确触发条件在 C8 出现。字段正确不等于行为解释全部正确；未据此追加 Prompt。

| 请求 | 输入 Token | 输出 Token（含推理） | 推理 Token | 秒 | 整体契约 |
|---|---:|---:|---:|---:|---|
| 20_memory_contract_fix / r2_revision | 60976 | 25812 | 22947 | 137.56 | 拒绝：about 引用 |
| 20_memory_contract_fix / r1_empty_history | 47549 | 19138 | 16637 | 106.48 | 拒绝：about 引用 |
| 21_memory_contract_minimal / r2_revision | 60806 | 33227 | 30021 | 181.36 | 拒绝：about 引用 |

精简版输入 60,806 Token，较此前 v4 同材料归档的 60,758 增加 48 Token；没有增加正常调用次数。按照此前归档官方价格口径估算，本次精简版约 0.387428 元，长说明两次合计 0.576650 元。此为历史价格口径估算，不是账单确认；实际 usage 和原始响应全部归档。每条件单次采样，不将差异解释为因果收益。

## 结论与边界

用户指定的最小格式说明已落实，离线验证通过，真实模型此次正确生成了非空退休结构；不需要修改 Memory 算法、Schema 或验证器。旧版本、失败档案和冻结材料保留，新修订身份清晰隔离。

尚不能据此声明完整 Memory 输出已通过或五轮实验已具备无阻碍启动条件：本次整体 about 引用失败仍需单独判断；此前输入容量极端情境也仍然存在。本次不扩大修复范围、不追求全部语义正确、不调用第二次、不启动 ALFWorld。可以继续讨论协议准备，但应明确上述已知失败与容量边界。

结果证据：`21_memory_contract_minimal/preparation/cases/r2_revision/{messages,request,response,parsed,result}.json`、`analysis/output_checks.json`、`analysis/cost_estimates.json`。本次新增 1 次真实请求，另有此前已发出的长说明 2 次，合计 3 次均完整记账；0 episode，0 正式 Skill/Memory 发布。

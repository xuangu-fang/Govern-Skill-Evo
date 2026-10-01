# v19 第一步：轻量 Issue Fusion

## 边界

本模块是独立纯接口：不调用模型、不写运行检查点、不提交 Memory、不生成 gap/plan，也不改变现有 campaign 的运行入口。下一步实现逐 proposal Evidence Review，再在第三步接通新闭环。`PROPOSE` 仅表示值得局部核验，绝非 VERIFIED 或修改授权。

输入来源是已经组装的 MemoryReviewInput 和经原始响应重验的 HistoricalReviews。Current Diagnosis 与 Memory Review 不变，完整上游证据继续持久化。

## 输入

`build_issue_fusion_input(review_request=..., historical_reviews=...)` 返回不可变 IssueFusionInput，版本 `issue_fusion_input_v19.1`。

- current_findings：保留 finding_id、kind、statement、applicability、dimensions、related_rule_refs、uncertainty。移除事件/监督/政策长引用数组；后续通过 finding_id 和 review_input_ref 找回完整来源。
- historical_reviews：保留 review_id、historical_object_id、状态、覆盖原因、reason、uncertainty、关联 finding IDs，并附历史判断、当前绑定和原 edit 的 operation/target_blocks/after_text。没有当前匹配的历史对象也保留。不发送整份 Memory、旧原始响应或历史回放。
- available_rule_refs：完整当前 Parent 规则目录，文本仅出现一次。此步尚无可靠的问题到规则路由，保留完整规则目录，避免预筛选误删相关规则；若过大则预算检查停止。
- batch、Parent 摘要、上游 review_input_ref 和历史审阅摘要绑定来源。语义正确性仍依赖上游审阅，摘要不是语义证明。

输入显式白名单，不发送 trajectories、tool definitions、policy 正文或完整 Skill 历史。现有不确定性陈述保留，不新增不确定性状态矩阵。

## 最小响应契约

```json
{
  "schema_version": "issue_fusion_response_v19.1",
  "issues": [{
    "source_finding_refs": ["CF/..."],
    "historical_refs": [],
    "issue_statement": "需要进一步检查的问题",
    "decision": "PROPOSE",
    "reason": "为什么值得局部核验；如有合并，说明共同问题",
    "related_rule_refs": []
  }],
  "unassociated_findings": [{
    "finding_ref": "CF/...",
    "reason": "该有效行为或反证本轮未关联具体问题的原因"
  }]
}
```

`decision` 仅 PROPOSE / NO_EDIT。related_rule_refs 无目标时为空，historical_refs 引用 review_id。不生成 issue_id，由程序根据输入绑定和问题内容计算稳定 ID。输出不允许额外的 gap、mutation、feasibility 或 analysis 字段。

`unassociated_findings` 是唯一额外的覆盖记录：避免把没有问题关联的有效行为、反证或不确定观察硬塞进一个修改决策。它没有 KEEP/DEFER 状态，也不授权修改。

## 覆盖规则与语义边界

- 每条 OBSERVED_PROBLEM 恰好属于一个 issue，可以 PROPOSE，也可以 NO_EDIT；不能放入 unassociated_findings。
- 非问题 Finding 可以关联多个 issue，但仍是同一来源，不增加独立证据数量。未关联的 Finding 必须有简短原因；不能同时关联又声明未关联。
- 每条历史 review 至少关联一个 issue。允许历史-only issue；没有当前观察不表示历史问题解决。
- source/rule IDs 必须存在；单 issue 内重复引用、重复 issue、未知来源、遗漏来源均拒绝。
- NO_EDIT 只表示本轮不继续修改，不关闭历史对象、不删除记忆。
- 程序不判断自然语言合并是否合理、reason 是否充分，也不从文本证明提案可执行。这些属于下一步局部核验与结果审计。

## 请求、预算和恢复

`build_issue_fusion_request` 使用通用引用表示，默认输出上限 16,000、独立输入预算 64,000 proxy token，并保留现有整体上下文预算检查。超限明确停止，不截断 Findings/历史对象，也不自动启动额外调用。预算为工程限制，不是实测最优值。

`validate_issue_fusion` 输出绑定原请求的 IssueFusionResult，保留精确原响应、issue_id、来源和 NO_EDIT 理由。`validate_issue_fusion_result` 从原响应重建后比较，拒绝篡改或版本混用。该 DTO 不是 CompilerInput 或 ReconciliationResult，尚无进入 Compiler/Editor 的适配器。未来 Evidence Review 必须独立授予 VERIFIED 资格。

此步不创建 run/resume，不移动旧 Pilot 检查点。第三步接入调度时才建立独立模型调用、一次修复、检查点和恢复边界。

## 工程验证与离线规模

专项：`python -m pytest tests/skill_evolution/test_issue_fusion_v19.py -q`。

覆盖纯当前、多提案、历史-only、共享反证、未关联有效行为、空输入、问题遗漏/重复、历史遗漏、非法规则、额外 gap 字段、结果篡改、输入预算、真实 Pilot 白名单与完整 Findings 保留。

真实 Pilot round-01 的 41 条 Findings、零历史审阅，离线构造请求为 **8,419 cl100k_base proxy token**。这只计算 Issue Fusion，不包含后续 Evidence Review 成本，不能解释为整个生成流程减少到 8,419。没有模型调用，不证明融合质量或实际耗时改善。

## 输入阈值简化

64,000 本地估算输入 token 为观察阈值，超过只记录
`above_observation_threshold`，不因此停止。首次请求和最多一次契约修复
共用 `check_fusion_budget`，默认工程保护上限 128,000；这不是 API 硬上限。
输入内容、输出契约、32,000 输出额度及 600 秒超时不变，不裁剪证据、
不增加预算管理阶段。正式运行的源码绑定改变后仍需显式迁移检查点。

### Fusion 历史消费边界（input v19.2）

Fusion 与局部 Evidence Review 共用 `historical_object_view`：历史发现正文
`source_findings` 只作为 `source_finding_refs` 进入 prompt；edit 正文仅在 `edit`
出现一次；与 `historical_judgment` 同一 attribution 的 result 不再重复展开。
问题摘要、Gate、来源引用、额外 attribution 结果及正反效果、限制、不确定性完整保留。
当前 Findings 和 Memory Review 当前结论不变。原始归档不修改、不截断。

这是确定性表示投影，不调用模型，不做语义合并或按 token 删材料；128k 工程保护不变。
历史对象数量仍可能增长，本修改不宣称已经实现固定大小的跨轮状态。

局部审阅通过选中议题的 provenance 从归档恢复关联对象，再执行既有局部消费边界，
不把 Fusion 的摘要当作原始证据。新输入为 `issue_fusion_input_v19.2`，响应契约不变。
旧已提交审计可按 v19.1 原表示重建并校验精确摘要，不允许将旧 Fusion 结果冒充新输入结果。
已有未完成运行需显式迁移检查点；本次不迁移或启动实验。

离线验证：formal_007 第三轮 45 条当前 Findings、12 项历史 Review；同一新版 prompt
下旧表示 65,912 token，新表示 37,006 token（本地估算）。历史保存值 65,853 使用旧
prompt，差额来自新增消费边界说明。所有历史判断、当前 Review 结论和当前 Findings 保持一致。

### Fusion 请求内短引用（v19.3）

模型输入及引用输出使用 F01…（当前 Finding）、H01…（历史 Review）、R01…（Parent 规则）。
编号由本次输入的完整 ID 排序后确定，只在本次请求内有效；完整映射及 input_ref 随 request.json 保存，映射不放入模型正文。
首次调用与唯一一次契约修复使用同一映射。未知编号、类型错配及直接输出完整 ID 均拒绝，不进行模糊纠错。
程序仅对结构化引用字段精确解码，然后执行原有覆盖率、来源和规则校验；自由文本不猜测改写。
原始短编号响应保存在调用记录中，下游结果及 provenance 使用恢复后的完整引用，旧版完整 ID 产物仍可校验。
此项改变请求协议及代码绑定；旧运行需要显式检查点迁移，不可直接混用旧请求与新响应。本次改动不迁移或重跑已有实验。

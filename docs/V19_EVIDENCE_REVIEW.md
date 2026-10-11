# v19 第二步：逐提案 Evidence Review

> 当前新运行已切换为 [单次 Evidence Review v19.3](V19_ONE_PASS_EVIDENCE_REVIEW.md)，下文补充上下文协议保留作为历史说明。

## 职责与边界

每个 Issue Fusion 的 PROPOSE 独立核验。输入绑定 IssueFusionInput、IssueFusionResult、原始 MemoryReviewInput、HistoricalReviews 及 issue_id；构造时重验来源一致性和融合结果。NO_EDIT issue 不进入本阶段。

本步提供局部输入、模型请求构造、原响应校验、独立运行/恢复 API。没有接通 campaign、Compiler、Editor、Monitor 或 Memory 提交。不会自动运行真实模型。`run_evidence_review(s)` 只有在调用它时才派发请求；测试使用构造 transport。

## 局部证据选择

EvidenceReviewCase 是本提案的本地审计档案，不是发送给模型的 payload。保存声明 Findings、相关 HistoricalReviews、历史 edit 摘要/联合归因信息、直接证据种子、已知反证及允许补充的来源轨迹。完整原始上游档案不修改。

默认发送：

- 当前 issue、它明确关联的 Findings 和历史审阅，不发送其他 issues 或完整 Memory。
- 全部相关 Findings 引用、Review 的支持/反证/上下文/历史引用，以及关联归因的 Parent/Candidate 事件；不按结果好坏截取。
- 引用事件前后各一个事件，加上可识别的同名工具调用—返回配对。配对根据轨迹顺序和 tool_name 查找，遇到同名同类事件停止，不猜测不明确的调用关系；它不是完整依赖图，也不保证上下文充分。
- 被选中事件实际涉及的工具定义、来源上下文政策、相关 Parent 规则。轨迹身份与 learner-safe supervision 每条保存一份。
- 允许范围内的事件/工具/Parent 规则目录，只含定位元信息，不含未载入正文。目录不是已阅读证据，不能据其缺失正文推断行为不存在。

当前证据补充限于本 issue 来源轨迹；历史证据限于所关联历史对象允许的轨迹。Parent 规则目录用于按需查看其他已有规则，不授权自动扩大 issue。局部正文完整保留，不做截断或生成摘要。较大的 issue 仍可能超过预算，明确停止，不退化成全局展开。

## 最简最终响应

```json
{
  "proposal_id": "ISSUE/...",
  "verdict": "VERIFIED",
  "evidence_refs": ["CURRENT/.../E0001"],
  "counterevidence_refs": [],
  "reason": "证据、反证及行动前可执行性的判断依据",
  "gap": {
    "kind": "MISSING",
    "statement": "包含适用范围的具体缺口",
    "related_rule_refs": []
  }
}
```

最终 verdict 只有 VERIFIED / NO_EDIT。NO_EDIT 的 gap 必须为 null；VERIFIED 必须有原始事件证据和一个 gap。MISSING 无目标，NEEDS_REVISION / SHOULD_REMOVE 必须引用已加载的 Parent 规则。整块删除理由、适用范围、可执行性均用 reason/statement 表达，不增加多层分析或状态矩阵。

所有引用必须是当前输入中已加载的事件。已知反证保留在 counterevidence_refs；同一事件允许同时支持和反驳不同解释。工具/政策/监督引用不能冒充事件证据。

VERIFIED 表示局部模型审阅通过，不证明语义正确、效果提升或因果成立。校验只能确保身份、结构、引用和明确反证保留。模型可以收窄问题或拒绝提案；不得扩展成独立新问题。自然语言范围是否真正保持、必要前提是否完整仍需结果审计，不能声称由程序证明。

## 有限补充

模型也可以返回一次控制请求，而非最终 verdict：

```json
{
  "proposal_id": "ISSUE/...",
  "request": "MORE_CONTEXT",
  "evidence_refs": ["CURRENT/.../E0010"],
  "tool_refs": [],
  "rule_refs": [],
  "reason": "需要读取这个返回结果才能判断前提"
}
```

至少一个未加载引用，必须存在于本提案目录。系统读取原文、加入局部邻接上下文、构造新 input_ref，保留原 issue 和已有证据；最多一次补充。第二轮若仍不足，模型应返回 NO_EDIT；再次索要上下文视为契约失败，程序不擅自代写 NO_EDIT。

默认每次输入上限 32,000 cl100k_base proxy token，输出上限 8,192，沿用当前 300 秒 transport timeout。原调用、补充调用和修复调用均有发送前预算检查；超限不截断，也不自动提高预算。这些是工程限制，不是实测最优参数。

## 检查点与恢复

- `run_evidence_review(case, output=..., transport=..., resume=False)`：只运行一个提案。
- `run_evidence_reviews(cases, output=..., ...)`：按提案独立目录逐个运行；普通异常记录为 INCOMPLETE，继续其他提案。返回 results 和 incomplete，不编译部分结果。
- 每个提案全程最多一次契约修复（不是每次补充各一次）。最多两次正常审阅调用，加一次契约修复。原响应、精确错误、修复请求和新响应均保存，不由程序改结论。
- 完成后保存结果及文件摘要；resume 重验输入/源码绑定、请求、响应、结果和摘要。已完成调用不重发；换 proposal、输入预算或源码版本不能直接混用旧目录。
- 网络超时或无完成响应保持 INCOMPLETE，正常 resume 不盲目重发。
- 明确要求重试时，可对单个提案调用 `run_evidence_review(..., resume=True, retry_incomplete=True)`。它只归档唯一无完整响应的调用并记录 receipt，再重发该调用；之前完成的补充请求和其他提案不重跑。已完成但校验失败的响应不能通过此入口增加修复次数。
- 若归档过程中中断或摘要不符，停止并保留现场；不静默丢弃旧尝试。重试无响应请求无法保证服务端此前未执行，使用者应明确决定是否重新请求。

目录主要包括 binding.json、case.json、input-0/1.json、review-0/1、可选 repair 目录、context-request、result.json、status.json 和 complete.json。失败尝试保留在 failed-attempts。模型故障、预算不足、修复失败均不等同于 NO_EDIT；没有 result 就没有可用于下一步的最终提案。

## 后续接入

下一步为 VERIFIED gap 建立确定性冲突检查/编译适配层，不能伪造旧 Diagnosis 分析。本步只得到 EvidenceReviewResult；没有 CompilerInput 或 Editor 授权接口。历史关联、来源与原文仍随 case/result 保留，为后续账本适配提供依据。

## 验证

专项：`python -m pytest tests/skill_evolution/test_evidence_review_v19.py -q`。

覆盖两种 verdict、三种 gap、未知/未载入引用、目标绑定、反证保留、有限补充、调用返回配对、来源绑定、一次修复上限、预算限制、超时隔离、归档重试、已完成兄弟提案复用与检查点篡改。

以真实 Pilot 的 15 条 OBSERVED_PROBLEM 各构造一个模拟 issue 作离线大小检查：输入约 17,938–31,851 proxy token，全部在默认预算内。这是人工构造的规模测试，不是真实 Issue Fusion/Evidence Review 的运行结果，不证明方法有效或端到端成本下降。未启动 Pilot 或真实模型。

### 历史限制约束重试（limitation-aware-1）

Fusion 与 Evidence Review 共用“问题复发不等于重试理由、改善与代价一起保留”的语义。
Fusion 只决定进入局部核验；Evidence Review 在现有 `reason` 中说明历史限制如何适用于本提案，
并在 `gap.statement` 中体现收窄范围或改变行为。仅换说法、加强约束或声称会谨慎不算修正。
若有依据的相关行为限制仍未解决，返回本轮 `NO_EDIT`；有新证据解释旧担忧时允许原方向重试。

成功退步的 pair 计数是待解释的警示，不自动证明 edit 有害；应结合行为归因、联合观察、
适用范围和替代解释。不会因为有负分就强制 NO_EDIT，也不会为获得 VERIFIED 编造可执行路径。
不新增输出字段、模型调用或状态机；Prompt 版本增加 `-limitation-aware-1`。

工程测试验证引用关联、状态兼容、历史信息保留及请求协议。它们不证明模型一定理解正确；
是否真正纠偏需要后续真实运行观察。本次未启动实验或迁移检查点。

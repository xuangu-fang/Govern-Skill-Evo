# 证据审阅与预算修正

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v19 第二步：逐提案 Evidence Review](#v19-evidence-review)
- [单次 Evidence Review：v19.3 输入协议](#v19-one-pass-evidence-review)
- [Evidence Review 输入与输出预算修正](#v19-review-budget-fix)

<a id="v19-evidence-review"></a>

## v19 第二步：逐提案 Evidence Review

> 当前新运行已切换为 [单次 Evidence Review v19.3](EVIDENCE_REVIEW.md#v19-one-pass-evidence-review)，下文补充上下文协议保留作为历史说明。

### 职责与边界

每个 Issue Fusion 的 PROPOSE 独立核验。输入绑定 IssueFusionInput、IssueFusionResult、原始 MemoryReviewInput、HistoricalReviews 及 issue_id；构造时重验来源一致性和融合结果。NO_EDIT issue 不进入本阶段。

本步提供局部输入、模型请求构造、原响应校验、独立运行/恢复 API。没有接通 campaign、Compiler、Editor、Monitor 或 Memory 提交。不会自动运行真实模型。`run_evidence_review(s)` 只有在调用它时才派发请求；测试使用构造 transport。

### 局部证据选择

EvidenceReviewCase 是本提案的本地审计档案，不是发送给模型的 payload。保存声明 Findings、相关 HistoricalReviews、历史 edit 摘要/联合归因信息、直接证据种子、已知反证及允许补充的来源轨迹。完整原始上游档案不修改。

默认发送：

- 当前 issue、它明确关联的 Findings 和历史审阅，不发送其他 issues 或完整 Memory。
- 全部相关 Findings 引用、Review 的支持/反证/上下文/历史引用，以及关联归因的 Parent/Candidate 事件；不按结果好坏截取。
- 引用事件前后各一个事件，加上可识别的同名工具调用—返回配对。配对根据轨迹顺序和 tool_name 查找，遇到同名同类事件停止，不猜测不明确的调用关系；它不是完整依赖图，也不保证上下文充分。
- 被选中事件实际涉及的工具定义、来源上下文政策、相关 Parent 规则。轨迹身份与 learner-safe supervision 每条保存一份。
- 允许范围内的事件/工具/Parent 规则目录，只含定位元信息，不含未载入正文。目录不是已阅读证据，不能据其缺失正文推断行为不存在。

当前证据补充限于本 issue 来源轨迹；历史证据限于所关联历史对象允许的轨迹。Parent 规则目录用于按需查看其他已有规则，不授权自动扩大 issue。局部正文完整保留，不做截断或生成摘要。较大的 issue 仍可能超过预算，明确停止，不退化成全局展开。

### 最简最终响应

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

### 有限补充

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

### 检查点与恢复

- `run_evidence_review(case, output=..., transport=..., resume=False)`：只运行一个提案。
- `run_evidence_reviews(cases, output=..., ...)`：按提案独立目录逐个运行；普通异常记录为 INCOMPLETE，继续其他提案。返回 results 和 incomplete，不编译部分结果。
- 每个提案全程最多一次契约修复（不是每次补充各一次）。最多两次正常审阅调用，加一次契约修复。原响应、精确错误、修复请求和新响应均保存，不由程序改结论。
- 完成后保存结果及文件摘要；resume 重验输入/源码绑定、请求、响应、结果和摘要。已完成调用不重发；换 proposal、输入预算或源码版本不能直接混用旧目录。
- 网络超时或无完成响应保持 INCOMPLETE，正常 resume 不盲目重发。
- 明确要求重试时，可对单个提案调用 `run_evidence_review(..., resume=True, retry_incomplete=True)`。它只归档唯一无完整响应的调用并记录 receipt，再重发该调用；之前完成的补充请求和其他提案不重跑。已完成但校验失败的响应不能通过此入口增加修复次数。
- 若归档过程中中断或摘要不符，停止并保留现场；不静默丢弃旧尝试。重试无响应请求无法保证服务端此前未执行，使用者应明确决定是否重新请求。

目录主要包括 binding.json、case.json、input-0/1.json、review-0/1、可选 repair 目录、context-request、result.json、status.json 和 complete.json。失败尝试保留在 failed-attempts。模型故障、预算不足、修复失败均不等同于 NO_EDIT；没有 result 就没有可用于下一步的最终提案。

### 后续接入

下一步为 VERIFIED gap 建立确定性冲突检查/编译适配层，不能伪造旧 Diagnosis 分析。本步只得到 EvidenceReviewResult；没有 CompilerInput 或 Editor 授权接口。历史关联、来源与原文仍随 case/result 保留，为后续账本适配提供依据。

### 验证

专项：`python -m pytest tests/skill_evolution/v19/test_evidence_review_v19.py -q`。

覆盖两种 verdict、三种 gap、未知/未载入引用、目标绑定、反证保留、有限补充、调用返回配对、来源绑定、一次修复上限、预算限制、超时隔离、归档重试、已完成兄弟提案复用与检查点篡改。

以真实 Pilot 的 15 条 OBSERVED_PROBLEM 各构造一个模拟 issue 作离线大小检查：输入约 17,938–31,851 proxy token，全部在默认预算内。这是人工构造的规模测试，不是真实 Issue Fusion/Evidence Review 的运行结果，不证明方法有效或端到端成本下降。未启动 Pilot 或真实模型。

#### 历史限制约束重试（limitation-aware-1）

Fusion 与 Evidence Review 共用“问题复发不等于重试理由、改善与代价一起保留”的语义。
Fusion 只决定进入局部核验；Evidence Review 在现有 `reason` 中说明历史限制如何适用于本提案，
并在 `gap.statement` 中体现收窄范围或改变行为。仅换说法、加强约束或声称会谨慎不算修正。
若有依据的相关行为限制仍未解决，返回本轮 `NO_EDIT`；有新证据解释旧担忧时允许原方向重试。

成功退步的 pair 计数是待解释的警示，不自动证明 edit 有害；应结合行为归因、联合观察、
适用范围和替代解释。不会因为有负分就强制 NO_EDIT，也不会为获得 VERIFIED 编造可执行路径。
不新增输出字段、模型调用或状态机；Prompt 版本增加 `-limitation-aware-1`。

工程测试验证引用关联、状态兼容、历史信息保留及请求协议。它们不证明模型一定理解正确；
是否真正纠偏需要后续真实运行观察。本次未启动实验或迁移检查点。

<a id="v19-one-pass-evidence-review"></a>

## 单次 Evidence Review：v19.3 输入协议

当前流程：Issue Fusion → 确定性证据包 → Evidence Review → VERIFIED / NO_EDIT → 确定性 Compiler。

新运行不再允许 MORE_CONTEXT，没有补充次数、第二次上下文调用、上下文请求检查点或补充请求 Schema。正常每个议题一次模型调用；完整响应违反最终契约时，仍最多允许一次修复。修复只接收相同证据包，不能读取更多材料。超预算、连接失败、超时、截断仍是 INCOMPLETE，不由程序转成 NO_EDIT。

### 输入组装

- 原样保留每个议题的全部直接证据、已知反证、关联历史和目标规则。
- 补齐可识别的工具调用/结果配对。
- 对 Findings 引用的政策行，按原始行号连续性和 Markdown 标题边界展开到完整段落。空行形成段落边界，不按本次 Pilot 的规则名或行号特判。
- 若这些政策段落明确提到公开工具名，加入工具定义及该议题已限定轨迹中的对应调用/结果，核验执行条件。名称匹配使用实际工具目录，不硬编码某个业务工具。
- 不再向模型提供未加载内容的事件/政策/工具/规则检索目录；使用 input_scope 说明这是局部材料，未包含材料不能被当成不存在。
- 长 ID 继续采用可逆表示。原始归档完整保存，不裁剪事件、删除反证或按剩余 token 强行截断。

必要上下文仍可能不足：程序的确定性组装不能保证语义充分性。模型应在 reason 中说明不足并返回 NO_EDIT；这只意味着本轮材料不支持修改，不表示问题永久解决。

### 历史兼容

v19.1/v19.2 的纯输入重建和校验仍保留，以验证已有证据及账本；执行器只接受 v19.3。新审计行只保存 input_version 和 result，不再写 context_requests。旧实验目录不改写，旧产物不能在新代码下盲目 resume。

本轮建议继续只复用 Fusion，8 个议题统一按 v19.3 重新审阅：

```bash
python scripts/runs/v19/run_v19_local_review.py run \
  --upstream artifacts/methods/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --reuse-local artifacts/methods/v19/archive/legacy/v19_v4_local_review_once_003 --fusion-only \
  --output artifacts/methods/v19/archive/legacy/v19_v4_local_review_once_004
```

相同代码下恢复新尝试时，将 `run` 改为 `resume`，保留其他参数。该入口仍停在 Editor 前，不提交 Memory 或启动完整实验。本文命令未在此次实现中执行。

### 离线重建

输入预算仍为 32,000 本地估算 token，输出预算仍为 24,000（包含 reasoning）。8 个 Pilot 议题新输入为 6,269～24,181 token，全部通过预算检查。移除检索目录后，即使增加政策段落和关联工具上下文，总输入仍下降。

明细见 `artifacts/methods/v19/v19_review_once_packet_001.json`。这是离线工程验证，不是方法效果证据。

### 引用类型与修改权限约束

新请求使用 `evidence_review-v19.3-typed-refs-1`，输入证据包与单次审阅流程不变。

- `events` 是事件证据；`policies` 是环境约束；只有 `rules` 中的 Parent Skill 条目可以作为编辑目标。政策中已有一条要求，不代表 Parent Skill 中存在同名规则。
- 根据实际加载的 Parent 规则生成响应 Schema。目标为空时，gap.kind 只允许 MISSING，related_rule_refs 必须为空；有目标时，目标引用只能取自实际规则目录。NO_EDIT 始终可选。规则是否值得新增/修改仍由模型判断。
- 本地校验仍独立执行，不依赖网关严格遵守 Schema。对结构合法响应，一次收集事件引用、反证引用、目标引用、可用操作和已知反证遗漏等可独立检查的错误。反馈包含字段位置、具体引用、实际类型与期望类型；唯一一次修复能看到这些错误，而不是只看到第一项。
- 不自动补引用、删除证据或把 NEEDS_REVISION 转成 MISSING。未知或未加载引用仍拒绝；程序不放宽编辑权限。

实现和测试不含业务案例、政策行号或工具名特判。旧结果和旧失败记录不改写；已完成结果仍可按原始输入重建校验。由于请求协议和源码绑定改变，不应直接 resume 旧未完成尝试。

### v19.4 历史证据边界（2026-09-28）

执行器仍是单次审阅，响应契约和 v18 Compiler 不变。新证据包标记
`packet_version=evidence_packet_v19.4`，请求版本为
`evidence_review-v19.4-scoped-history`。

- canonical case 保存完整证据档案；发送前从当前 Finding 引用、Memory Review 的明确引用及全部已知反证重新确定事件种子。仅关联历史 edit 不再自动展开它全部 Attribution 事件。
- 保留历史行为比较、归因判断、不确定性、联合归因和未归因上下文；这些是历史评估，不是已加载原始证据。只允许引用 events 中存在的原文。
- 历史 edit 正文、Review 结论各表示一次。旧 source_findings 全文不再重复输入，保留来源 ID；匹配的 Attribution 结果使用已有 historical_judgment，其他结果仍保留。
- 工具调用/结果闭合、政策段落和政策相关工具补充保持不变，但不会扩展到与明确证据种子无交集的历史轨迹。
- PAIR 引用采用已有可逆前缀表示；原始引用和归档原文不变。
- 预算仍为 32,000；没有按预算取前 N 条、删除反证、MORE_CONTEXT 或额外 LLM 阶段。材料不足时由模型判断 NO_EDIT；超预算仍为工程 INCOMPLETE。

离线报告：`artifacts/methods/v19/v19_evidence_review_scoped_history_001.json`。它复用 formal_004
第二轮的 8 个 canonical cases，只重建输入，不调用模型、不更新运行检查点。
该报告验证全部直接引用及已知反证都已加载。优化后仍有 3 个议题超预算；
其中价格议题上游 Review 明确引用了 63 条历史事件，不能为了达标静默移除。
因此本次实现不是“所有议题已经可运行”的声明。

旧完成结果、Fusion 和运行目录保持不变。源码绑定与包协议已变，更改后的代码
不能直接 resume formal_004；后续恢复须显式迁移并核验已完成结果，不整批重跑。

### v19.5 共享历史消费边界

后续请求改用 `evidence_packet_v19.5` / `evidence_review-v19.5-shared-memory`。
明确来源引用不再等于必须加载的全文列表；历史原文有独立预算，遗漏反证禁止
VERIFIED。具体契约、测试结果与尚未完成的迁移条件见 [共享 Memory 消费边界](MEMORY.md#v19-memory-consumption)。

<a id="v19-review-budget-fix"></a>

## Evidence Review 输入与输出预算修正

> 当前新运行已切换为 [单次 Evidence Review v19.3](EVIDENCE_REVIEW.md#v19-one-pass-evidence-review)，下文补充上下文协议保留作为历史说明。

来源：`artifacts/methods/v19/archive/legacy/v19_v4_local_review_once_002`。本次仅离线分析和工程验证，不发模型请求，不修改该目录。

### 真实失败原因

Fusion 完成 9 个议题，8 个 PROPOSE。1 个审阅完成，6 个在本地 32,000 proxy input token 检查时停止，另 1 个收到 `finish_reason=length`。该响应 completion_tokens=8,192，其中 reasoning_tokens=7,391，正文仅余约 801 token，JSON 未结束。这是输出截断，不是网络错误、拒答或已完成 JSON 的契约错误；保存的响应不应交给契约修复。

旧输入并不是完整轨迹的直接复制，但仍过度展开：全部关联轨迹的事件目录、种子事件 ±1 邻域及工具配对、完整可见政策逐行目录（每行重复上下文/摘要）、长引用 ID 在多处重复。最大议题含 119 个可读事件（种子 55）、232 行政策。canonical 字段单独估算：政策约 27,277、事件约 22,861、事件目录约 17,505 token；这些值不等于经过 wire interning 后的可加总贡献。

### 通用修正

- 新输入版本 `evidence_review_input_v19.2`。全部直接种子事件、已知反证与可识别的工具调用/结果配对保留原文；不默认加入不相关的相邻事件。
- 政策首轮只加载 Findings 明确引用的行；未加载行仍在完整目录中，可通过 `MORE_CONTEXT.policy_refs` 补充。缺失摘录不表示政策不存在。仍然最多一次上下文补充，补充和 repair 均受 32,000 预算限制。
- 目录用共享前缀、列和常量进行无损表示；只索引尚未加载的对象。已加载对象本身仍可引用。
- Wire 层长 ID 使用显式 `reference_prefixes` 字典。正文未被摘要或裁剪；扩展后必须与 canonical payload 一致。模型引用可以用完整 ID 或声明的紧凑 ID，程序仅做确定性 ID 解码，保存原始响应，并对解码后的引用重新执行全部契约校验。这不是修补引用或补充证据。
- Evidence Review 输出上限调整为 24,000，包含 reasoning。`ModelOutputTruncated` 单独记录 `length` 与 token 用量，不消耗唯一一次契约修复，不自动重发。
- 新尝试可显式导入旧 Fusion 与已完整通过的提案；校验旧产物哈希、输入、原响应及来源，审计逐项记录输入版本。失败提案在 v19.2 下重新请求。旧产物不覆盖，不把旧结果标为新输入生成。

### 实际输入离线重建

| 议题 ID 前缀 | 旧输入 token | 新输入 token |
|---|---:|---:|
| 59ff08f1 | 33,726 | 12,557 |
| 86789b0f | 34,472 | 14,296 |
| f2fb3bbd | 38,904 | 13,888 |
| b39548d2 | 39,515 | 15,275 |
| 16bc8826 | 62,492 | 24,223 |
| cbef8dc9 | 89,104 | 29,742 |
| 68e5dbbb（输出截断） | 26,574 | 8,519 |
| 0937ed45（已完成，保留原结果） | 29,745 | 10,235 |

这些是 cl100k_base 本地估算，不是网关实测。新输入保留所有直接证据与反证，但少看默认周边上下文；不能由 token 降低推断判断质量提升。新增上下文或 repair 仍可能超过预算，届时明确停止，不截断证据或提升上限。

明细：`artifacts/methods/v19/v19_review_budget_fix_002.json`，包括来源文件哈希、字段分解和 API usage。`fix_001` 是目录常量合并前的中间分析，保留供审计。

### 下一次运行命令（未启动）

```bash
python scripts/runs/v19/run_v19_local_review.py run \
  --upstream artifacts/methods/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --reuse-local artifacts/methods/v19/archive/legacy/v19_v4_local_review_once_002 \
  --output artifacts/methods/v19/archive/legacy/v19_v4_local_review_once_003
```

该入口复用 9 个 Fusion 议题与 1 个完成的审阅，仅处理余下 7 个；完整核验和编译后停在 Editor 前。恢复同一新尝试时改 `run` 为 `resume`，保留其他参数。遇到无完整响应仍不自动重发；截断响应是完整的失败尝试，不能冒充网络无响应归档重试。

#### 本次选择：只复用 Fusion，统一重跑 Evidence Review

在上述命令中增加 `--fusion-only`，则旧审阅结果仅留档，不参与本次编译。8 个 PROPOSE 均按 v19.2 重新核验，包括此前已完成的 1 个。复用策略写入输入绑定与 receipt，resume 必须保持相同选项；不能中途切换为复用旧审阅。

```bash
python scripts/runs/v19/run_v19_local_review.py run \
  --upstream artifacts/methods/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --reuse-local artifacts/methods/v19/archive/legacy/v19_v4_local_review_once_002 --fusion-only \
  --output artifacts/methods/v19/archive/legacy/v19_v4_local_review_once_003
```

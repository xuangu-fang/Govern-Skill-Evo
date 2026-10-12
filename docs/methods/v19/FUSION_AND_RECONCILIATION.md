# 问题融合、协调与修改记忆

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v19 第一步：轻量 Issue Fusion](#v19-issue-fusion)
- [v19 职责拆分第 2 步：Reconciliation 与确定性编译](#v19-reconciliation)
- [v19 edit-level Memory Review](#v19-edit-memory-review)

<a id="v19-issue-fusion"></a>

## v19 第一步：轻量 Issue Fusion

### 边界

本模块是独立纯接口：不调用模型、不写运行检查点、不提交 Memory、不生成 gap/plan，也不改变现有 campaign 的运行入口。下一步实现逐 proposal Evidence Review，再在第三步接通新闭环。`PROPOSE` 仅表示值得局部核验，绝非 VERIFIED 或修改授权。

输入来源是已经组装的 MemoryReviewInput 和经原始响应重验的 HistoricalReviews。Current Diagnosis 与 Memory Review 不变，完整上游证据继续持久化。

### 输入

`build_issue_fusion_input(review_request=..., historical_reviews=...)` 返回不可变 IssueFusionInput，版本 `issue_fusion_input_v19.1`。

- current_findings：保留 finding_id、kind、statement、applicability、dimensions、related_rule_refs、uncertainty。移除事件/监督/政策长引用数组；后续通过 finding_id 和 review_input_ref 找回完整来源。
- historical_reviews：保留 review_id、historical_object_id、状态、覆盖原因、reason、uncertainty、关联 finding IDs，并附历史判断、当前绑定和原 edit 的 operation/target_blocks/after_text。没有当前匹配的历史对象也保留。不发送整份 Memory、旧原始响应或历史回放。
- available_rule_refs：完整当前 Parent 规则目录，文本仅出现一次。此步尚无可靠的问题到规则路由，保留完整规则目录，避免预筛选误删相关规则；若过大则预算检查停止。
- batch、Parent 摘要、上游 review_input_ref 和历史审阅摘要绑定来源。语义正确性仍依赖上游审阅，摘要不是语义证明。

输入显式白名单，不发送 trajectories、tool definitions、policy 正文或完整 Skill 历史。现有不确定性陈述保留，不新增不确定性状态矩阵。

### 最小响应契约

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

### 覆盖规则与语义边界

- 每条 OBSERVED_PROBLEM 恰好属于一个 issue，可以 PROPOSE，也可以 NO_EDIT；不能放入 unassociated_findings。
- 非问题 Finding 可以关联多个 issue，但仍是同一来源，不增加独立证据数量。未关联的 Finding 必须有简短原因；不能同时关联又声明未关联。
- 每条历史 review 至少关联一个 issue。允许历史-only issue；没有当前观察不表示历史问题解决。
- source/rule IDs 必须存在；单 issue 内重复引用、重复 issue、未知来源、遗漏来源均拒绝。
- NO_EDIT 只表示本轮不继续修改，不关闭历史对象、不删除记忆。
- 程序不判断自然语言合并是否合理、reason 是否充分，也不从文本证明提案可执行。这些属于下一步局部核验与结果审计。

### 请求、预算和恢复

`build_issue_fusion_request` 使用通用引用表示，默认输出上限 16,000、独立输入预算 64,000 proxy token，并保留现有整体上下文预算检查。超限明确停止，不截断 Findings/历史对象，也不自动启动额外调用。预算为工程限制，不是实测最优值。

`validate_issue_fusion` 输出绑定原请求的 IssueFusionResult，保留精确原响应、issue_id、来源和 NO_EDIT 理由。`validate_issue_fusion_result` 从原响应重建后比较，拒绝篡改或版本混用。该 DTO 不是 CompilerInput 或 ReconciliationResult，尚无进入 Compiler/Editor 的适配器。未来 Evidence Review 必须独立授予 VERIFIED 资格。

此步不创建 run/resume，不移动旧 Pilot 检查点。第三步接入调度时才建立独立模型调用、一次修复、检查点和恢复边界。

### 工程验证与离线规模

专项：`python -m pytest tests/skill_evolution/v19/test_issue_fusion_v19.py -q`。

覆盖纯当前、多提案、历史-only、共享反证、未关联有效行为、空输入、问题遗漏/重复、历史遗漏、非法规则、额外 gap 字段、结果篡改、输入预算、真实 Pilot 白名单与完整 Findings 保留。

真实 Pilot round-01 的 41 条 Findings、零历史审阅，离线构造请求为 **8,419 cl100k_base proxy token**。这只计算 Issue Fusion，不包含后续 Evidence Review 成本，不能解释为整个生成流程减少到 8,419。没有模型调用，不证明融合质量或实际耗时改善。

### 输入阈值简化

64,000 本地估算输入 token 为观察阈值，超过只记录
`above_observation_threshold`，不因此停止。首次请求和最多一次契约修复
共用 `check_fusion_budget`，默认工程保护上限 128,000；这不是 API 硬上限。
输入内容、输出契约、32,000 输出额度及 600 秒超时不变，不裁剪证据、
不增加预算管理阶段。正式运行的源码绑定改变后仍需显式迁移检查点。

#### Fusion 历史消费边界（input v19.2）

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

#### Fusion 请求内短引用（v19.3）

模型输入及引用输出使用 F01…（当前 Finding）、H01…（历史 Review）、R01…（Parent 规则）。
编号由本次输入的完整 ID 排序后确定，只在本次请求内有效；完整映射及 input_ref 随 request.json 保存，映射不放入模型正文。
首次调用与唯一一次契约修复使用同一映射。未知编号、类型错配及直接输出完整 ID 均拒绝，不进行模糊纠错。
程序仅对结构化引用字段精确解码，然后执行原有覆盖率、来源和规则校验；自由文本不猜测改写。
原始短编号响应保存在调用记录中，下游结果及 provenance 使用恢复后的完整引用，旧版完整 ID 产物仍可校验。
此项改变请求协议及代码绑定；旧运行需要显式检查点迁移，不可直接混用旧请求与新响应。本次改动不迁移或重跑已有实验。

<a id="v19-reconciliation"></a>

## v19 职责拆分第 2 步：Reconciliation 与确定性编译

日期：2026-09-24。

本步实现独立 Reconciliation 输入、Prompt、响应校验、逐项处置、v18 Compiler/Editor 适配和 Candidate 文本应用。没有模型 transport、一次契约修复、阶段检查点、Memory 提交或新 campaign 接入；这些属于第 3 步。未启动真实 Pilot，未改变 v18 或原 Pilot。

### 数据流与接口

```text
MemoryReviewInput（内含不可变 Current Findings、原始证据、完整历史）
+ HistoricalReviews
→ build_reconciliation_input
→ build_reconciliation_request（无模型调用）
→ 模型原始响应
→ validate_reconciliation
→ ReconciliationResult + v18 EditorInput/确定性 EditPlan
→ reconciliation_editor_request
→ Editor 原始响应
→ apply_reconciled_editor
→ Candidate + 全部处置记录 + edit_provenance
```

`build_reconciliation_input` 重验 HistoricalReviews 的精确原始响应与输入绑定。Current Findings 使用第 1 步已经按完整批次验证的快照，整个上游输入再次参与 Reconciliation 的摘要绑定。构造输入后不得替换当前发现、历史审阅或 Parent；重验时拒绝与原绑定不一致的内容。

### 逐项处置契约

模型只返回 schema_version 和 decisions。每条 decision 的字段：

| 字段 | 约束 |
|---|---|
| current_finding_refs | 当前来源 ID，可空 |
| current_finding_assessments | v19.2：逐个 finding 的 finding_ref、role、reason；恰好覆盖声明的当前来源 |
| historical_review_refs | 历史审阅 ID，可空；两类来源至少一类非空 |
| decision | PROPOSE / KEEP / DEFER |
| reason | 对处理、合并或暂缓的具体说明 |
| evidence_refs | 声明来源中的原始事件引用，不能借入无关发现的证据 |
| keep_rule_refs | 仅 KEEP 非空，绑定当前实际规则 |
| conflict_resolution | 相关历史状态为 MIXED/CONTRADICTED 时必填，说明证据冲突及处理 |
| whole_rule_removal_reason | 仅 SHOULD_REMOVE 非空，按目标规则顺序逐条解释整块删除理由 |
| proposals | PROPOSE 恰好一份完整 v18 Diagnosis（恰好一个 gap）；其他决策为空 |

所有 Current Finding 和 Historical Review 在整份响应中必须被处置恰好一次。允许多个来源合成一个 decision，不允许遗漏、未知来源或在多个 decision 中重复处置。每个 decision 最多形成一个独立问题的 proposal；不同问题应由 Current Findings 阶段分开，避免代码在融合阶段擅自拆分或复制来源。

纯当前问题可独立 PROPOSE，无需历史 Evidence Status。纯历史依据也可以 PROPOSE，引用历史原始事件，不伪造当前支持。历史关联不决定 mutation kind。

KEEP 必须绑定当前实际规则；历史-only KEEP 不能声称保留当前不存在或无对应绑定的候选。DEFER 不产生规则目标或修改。所有 KEEP/DEFER 理由都保留在 ReconciliationResult 中。

### 证据与冲突

- 每个当前来源必须与 decision 共享事件。v19.2 区分 DIRECT_BASIS / COUNTEREVIDENCE / CONTEXT：只有直接依据必须与 gap 共享事件，反证和背景仍必须进入 decision 与分析。每个角色须解释理由；不能用背景标签掩盖独立未处理的问题，这类问题应单独 DEFER。结构校验不能证明角色判断的语义正确性。
- linked Historical Review 的当前支持、反证和不充分观察引用必须完整进入 decision；不得只保留有利一侧。
- proposal 的 analyses 必须覆盖 decision 的事件证据；gap 仍须满足 v18 的“属于声明分析并与每个声明维度共享事件”规则。
- policy 只能引用分析所涉轨迹的可见上下文；supervision 只能引用所分析轨迹的标签。
- 历史原始事件保留 pair/role/source_round/Skill/original_trajectory_ref；编译适配的复合轨迹身份避免历史和当前别名冲突，不改写原事件引用或正文。
- 同一事件在来源合并后的 provenance 中按原始引用去重，不生成支持票数或根据历史篇幅打分。
- KEEP 和编辑同一目标直接拒绝。v18 Compiler 对同一目标的 REPLACE/DELETE 冲突直接拒绝，不由程序选择语义胜者。
- 对同一目标的多个 REPLACE，沿用 v18 确定性合并，并保留全部 backing gaps 与来源。语义重复的 ADD 仍须在 Reconciliation 中合并；Compiler 不做语义推断。

这些校验只能确认引用、覆盖和显式说明，不能证明“暂缓当前发现的理由成立”或自然语言冲突已经真正解决。

### 复用 v18 而不修改它

PROPOSE 中的 diagnosis 由模型显式提供，包含原有 success_analysis、compliance_analysis、skill_addressability 和 parent_skill_gaps。适配器不自动补分析、补引用、改 gap 或改目标。

```text
MISSING         → ADD      （无 related_rule_refs）
NEEDS_REVISION  → REPLACE  （绑定当前规则）
SHOULD_REMOVE   → DELETE   （绑定当前规则，解释整块删除）
```

调用原有 `validate_diagnosis_response`、`compile_edit_plan`、`build_editor_request` 和 `apply_editor_response`。引用闭合、原文目标解析、混合操作冲突、有限 Editor 操作和未编辑原文保持行为均保留。

KEEP/DEFER 仅在 v18 适配层表示为无 gap 的 NOT_ADDRESSABLE/NOOP，以满足现有 Compiler 类型；真实语义仍以 ReconciliationResult 中的 KEEP/DEFER 为准，不把它解释成 Current Diagnosis 对问题可修复性的结论。空发现加空历史得到确定性 NO_UPDATE。

纯 DELETE 不调用 Editor，由原 v18 应用器确定性删除；ADD/REPLACE 才生成 Editor 请求。Editor 仅收到本 edit unit 的 gaps、分析、证据及其 Reconciliation 来源，不能借入其他单位的历史说明。Editor 输入也有发送前预算检查，不静默截断证据。

### 追踪、恢复接口与边界

- `RC/<hash(input_ref + decision)>` 标识处置；保留精确模型原响应、完整处置和 canonical plan。
- Editor 请求/应用前重新验证整份 Reconciliation 并重编译，拒绝被修改的结果。
- `apply_reconciled_editor` 返回 `edit_provenance`：edit_unit_index、operation、decision_refs、current_finding_refs、historical_review_refs、去重的 evidence_refs。与 Candidate/全部处置记录一起返回，保留纯当前、纯历史、二者合并三种链。
- 此处 provenance 描述计划中的操作；Editor 若返回 UNABLE，不表示这些操作已经应用。
- 当前函数为纯阶段接口，不写检查点、正式 edit ledger 或 Memory。第 3 步将把这些来源接入持久化账本和跨轮关系，统一 run/resume。
- 本步没有改动 `run_v19_v4.py`，现有入口仍是旧生成流程，不能用它宣称新架构已运行。

### 工程验证

专项命令：`python -m pytest tests/skill_evolution/v19/test_reconciliation_v19.py -q`。

覆盖三类编译操作、纯当前/纯历史/合并来源、KEEP/DEFER、空批次、覆盖遗漏、重复来源、引用闭合、过期规则、历史反证不可丢弃、整块删除理由、同目标合并、KEEP/编辑冲突、REPLACE/DELETE 冲突、Editor 前篡改拒绝及缺失候选不可 KEEP。使用构造模型输出，只证明机制，不证明新架构优于旧 Pilot。

最终验证：新增专项 **24 项**，v19 全量 **317 项通过**；语法编译与 diff 空白检查通过。v18 冻结 manifest 的 **992 个文件哈希一致**。没有真实模型调用或新 Pilot。


### Reconciliation v19.2：来源角色与一次修复反馈

输入与响应版本升级为 v19.2，新增必填 current_finding_assessments。旧 v19.1 仅在绑定旧输入的审计重验中按原规则解释；新输入拒绝旧响应，程序不会为旧响应自动分配角色。

校验汇总各 decision 可独立检查的错误，包括重复引用的具体值、来源覆盖、直接依据缺失、gap 的声明维度闭合、分析遗漏和监督标签关联。形状错误会阻止不安全的后续解引用；未知来源也不能继续推导其证据集合。反馈不承诺枚举所有语义问题。一次模型修复上限不变，原响应不去重、不补证据、不改结论。

真实 Pilot 两份失败响应及其完整绑定输入保存在 `tests/skill_evolution/v19/fixtures/v19_reconciliation_failure.json.gz`，附来源文件 SHA-256。它们仍是失败样本，不能通过代码补角色变为成功结果。

恢复边界：旧 Reconciliation 请求及唯一修复均须保留，不能在旧调用上追加第二次修复。后续恢复应建立带源代码/契约摘要的新尝试并显式归档旧失败。当前七组 Current Diagnosis 的请求与重建请求完全一致，所有 Findings 原响应重验通过，可作为经过核验的复用输入；这不等于放宽 campaign 的来源绑定。现有普通 resume 会保护版本边界，不能直接跨本次升级继续。

### Reconciliation 输入 v19.3：发现/审阅优先，按引用载入证据

本次只改变输入表示与可见证据边界。输出仍为 `reconciliation_response_v19.2`；PROPOSE/KEEP/DEFER、来源角色、v18 gap 闭合与确定性 Compiler 不变。Reconciliation 输出预算仍为 96,000、timeout 仍为 300 秒。Current Diagnosis、Memory Review 和持久化原始证据不裁剪。

`reconciliation-input.json` 继续保存完整上游绑定供重放与审计。发送模型前，由 `reconciliation_evidence_v19.evidence_view` 构造确定性视图：

- 全量 Current Findings、Historical Reviews，当前 Parent Skill 和规则目录。
- 每个历史对象的原判断、适用条件、反证/不确定性、替代解释、edit、当前绑定及原归因 observations；不传整份 Memory 回放或重复的 HistoricalReviews.raw_response。
- 默认载入 Findings.evidence_refs，Review 的 supporting/contradicting/context/historical refs，以及原归因 observations 的 Parent/Candidate refs。无 top-k、无极性筛选、无正文截断。
- 每个事件正文按原始 ref 保存一次；同一轨迹身份、来源轮次、Skill、角色和 supervision 保存一次。原归因引用的双侧监督标签始终载入，即使某一侧没有选中事件。
- 所涉上下文的政策行完整保留在 available_policy_refs，不再同时传一份 visible_policy 全文；public_tools 保留。相关政策身份与行引用沿用 v18。
- 不发送整条历史 pair 的事件引用目录。未载入不代表未发生；不足以判断时 DEFER 并说明需要的事件或轨迹引用。此次没有给模型增加实时检索工具或自动追加模型轮次。

`build_reconciliation_input(..., additional_evidence_refs=[...])` 可在显式后续输入中补充完整原始事件；未知或重复引用在发送前拒绝。补充集参与 input_ref，已完成旧响应不能混用。补充上下文不自动成为当前 finding 的依据；原来源范围、反证保留和 gap 闭合仍须满足。

本地校验拒绝引用未载入视图的事件/政策，即使它确实存在于完整归档中。保留 v19.1/v19.2 原输入的审计恢复逻辑；v19.3 的审计结果记录输入版本及额外引用，恢复时重建同一视图。新请求使用 `reconciliation-v19.3`，旧 Pilot 源码/请求绑定不会被静默改写。

#### 离线 token 分析

命令不会加载模型或改变 Pilot，输出目录必须是新目录：

```bash
python scripts/analysis/v19/profile_v19_reconciliation.py \
  --request artifacts/methods/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation/reconciliation-v19.2.attempt-004/request.json \
  --input artifacts/methods/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation/reconciliation-input.json \
  --output artifacts/v19_reconciliation_input_audit_new
```

报告包含原请求和重建请求的 cl100k_base proxy token、system/schema/user 分解、各部分及其唯一正文表占用、JSON 分段差额、重复身份统计与证据数量。它不是网关 tokenizer 计量，也不证明 APITimeoutError 的单一原因。

本次真实输入：496,216 → 128,636 proxy token（减少 74.1%）；41 条 Findings 不变，832 条全量当前事件改为 237 条被引用事件；36 条轨迹身份原来重复出现 832 次。原请求历史轮数为零，因此本轮主要负担不是历史 Memory。报告保存在 `artifacts/methods/v19/v19_reconciliation_input_audit_20260924/profile.md` 和同目录 `profile.json`。没有真实模型调用或 Pilot 启动，不能宣称已消除超时。

### 输入/响应 v19.4：逐问题决策与可执行性核验

本次修复决策机制，不针对任何领域、工具名、任务 ID 或 Pilot 结果制定规则。不启动模型，不改写已有失败/成功响应，不自动进入 Editor。默认的新生成使用 v19.4；v19.1–v19.3 审计仍按原版本恢复，不能把旧响应自动补字段后视为新版通过。

#### 问题处置

每条 decision 新增 `issue_dispositions`，恰好覆盖其 current/historical 来源，每项给出 issue、disposition、reason。观察到的问题不得使用 CONTEXT_ONLY；PROPOSE 中的问题必须 ADDRESSED，KEEP 对应 PRESERVED，DEFER 对应 DEFERRED。不能处理的独立问题应另立 DEFER，不能埋在另一提案背景中。

多来源决策必须填写 `merge_justification`，解释共同问题及兼容的处置方向；单来源不填写。DEFER 必须给出 `defer_basis`：INSUFFICIENT_EVIDENCE / UNAVAILABLE_CAPABILITY / UNRESOLVED_CONFLICT / UNCERTAIN_APPLICABILITY，以及具体理由和再判断需要的信息。不存在整批提案数量配额；每个 PROPOSE 恰好一个 gap，多个独立 PROPOSE 均可进入原 v18 Compiler。

#### 可执行性与上下文

v19.4 视图对被 Findings、Review、归因或显式补充引用命中的轨迹，载入全部原始事件，包括先前调用、返回结果、后续结果和反证；同一轨迹身份仍只保存一次。该闭合规则不靠模型猜测哪项能力重要，也不以工具名或结果极性筛选。相关上下文的完整工具定义由 `available_tool_refs` 提供，带上下文和正文摘要，原政策和规则寻址不变。未命中轨迹仍不自动载入。

每个 PROPOSE 必须列出 `feasibility_checks`：requirement、SUPPORTED/UNAVAILABLE/UNKNOWN、原事件 evidence_refs、所依赖的工具 tool_refs、availability_before_action、limitations_and_counterevidence、reason。任何必要前提为 UNAVAILABLE/UNKNOWN 时拒绝 PROPOSE；应 DEFER 或重新形成有依据的不同提案。工具无关的行为允许空 tool_refs，但仍要引用事件并说明可执行行为。不能从事后结果差异直接推断行动前可获知该结果。

核验引用必须来自该 decision 的来源轨迹、已加载正文和对应上下文工具定义；完整上下文可用于检验能力与反证，不会自动扩充 gap 的直接证据范围。逐问题记录和可执行性核验进入持久化结果与 Editor provenance，重放时重复校验，仍最多一次契约修复。

**校验边界**：程序检查覆盖、类型、引用、作用域、声明状态以及来源闭合，不判断自然语言是否真实蕴含可执行性、是否遗漏了未声明的前提，亦不能证明合并理由成立。将 UNKNOWN 改写为虚假的 SUPPORTED 不会被这些结构规则完全识别；实际模型结果仍须审计。没有引入语义保证或额外独立评审模型。

本次工程采用完整来源轨迹作为保守上下文闭合，输入量会增加：相同 Pilot 离线重建约 241,954 proxy token（前版 128,636，最早全量表示 496,216）。它解决选择性片段遗漏风险，不是进一步压缩。默认 transport timeout 和 max_completion_tokens 未改；没有复用/覆盖旧 900 秒一次性尝试。

<a id="v19-edit-memory-review"></a>

## v19 edit-level Memory Review

> 2026-09-27 更新：当前逐 edit 输入协议为 `edit_memory_review_v19.2`。历史部分使用已有 Attribution 记录（完整局部比较、理由、反证、不确定性和联合 edit 关系）及原始证据引用，不再默认展开历史事件正文；程序补充被引用 pair 的监督标签和结果变化。当前 Findings 路由、当前事件组装及四类 Evidence Status 不变。以下 v19.1 的事件正文选择说明属于历史设计。
>
> `historical_evidence_refs` 是经过归档存在性检查的来源目录，`historical_evidence` 为空；模型可通过引用追溯摘要，但不能声称已阅读历史原文，也不能增加摘要未支持的历史事实。无需新增模型压缩调用、MORE_CONTEXT 或提高 32,000 输入预算。
>
> 离线统计见 `artifacts/methods/v19/v19_memory_summary_profile_001/report.md`。正式实验失败包由 44,381 降至 14,233 token。由于输入/Prompt 协议变更，既有实验不能直接 resume；需显式迁移并统一重新生成六份 Review，旧结果保留。此修改未执行迁移或模型调用；零当前关联问题尚未调整。

The local generation protocol now uses one deterministic packet and checkpoint per historical edit. The legacy separated protocol and historical audit restoration remain supported. No model calls are made by profiling.

### Input boundary

Full `memory-review-input.json`, committed Memory, and Replay remain immutable audit archives. They are not the model input. A packet contains the edit, its deployed rule bindings and Gate decision, attribution judgments including observations/counterevidence/uncertainty, attribution-cited historical events with identifiable tool call/result pairs, linked current Findings, their cited current events with call/result pairs, cited supervision, and relevant contexts. Tools are limited to those used in selected events. Applicable context policy remains intact.

Current Findings link only by exact overlap with the edit's current or descendant rule references. Possible/ambiguous bindings, keyword similarity, task-level coincidence and broad policy overlap do not establish links. Unmatched Findings remain in Issue Fusion. No linkage means no evidence in this packet, not that the full round contains no relevant behavior. In particular rejected/absent edits may remain uncovered with this conservative association method.

Evidence bodies stay unmodified. Repeated trajectory metadata is stored once. Compact CURRENT and PAIR references are lossless aliases, expanded before validation. Historical observations shared by edits retain their original IDs and are not independent confirmations. No complete historical Replay, prior review transcript, or recursive generation history is fed into the packet.

### Execution

`run_edit_reviews` in `edit_memory_review_v19.py` profiles every packet, then runs each edit independently. All historical objects for the same edit share one call. Input budget: 32,000 cl100k_base proxy tokens; output cap: 24,000 tokens. Both initial and optional repair requests must pass the input cap. These are local proxy counts, not gateway billing tokens.

Output states remain SUPPORTED / CONTRADICTED / MIXED / NOT_COVERED. The existing polarity, finding linkage and reference validation runs against the scoped packet. No MORE_CONTEXT branch exists. A local contract rejection permits at most one audited repair. Network/truncation/budget failures remain INCOMPLETE; they are not converted into NO_EDIT or NOT_COVERED. Unknown-response attempts require explicit recovery; resume does not silently resend them.

Each edit stores input, original request/response, optional repair, validated result and status. Resume revalidates checkpoints and only calls missing edits. Batch aggregation requires every edit to finish and validates the union against the original audit input. Issue Fusion receives the existing HistoricalReviews format and all current Findings. No downstream schema change is required.

### Profiling

```
/Users/didi/miniforge3/bin/python scripts/analysis/v19/profile_v19_edit_memory_review.py \
  --input artifacts/methods/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-02/generation/memory-review-input.json \
  --output artifacts/new_edit_memory_profile
```

The output directory must be new. `profile.json` records per-edit input sizes, linked Findings, edit coverage and unmatched Findings. Per-edit input JSON files preserve exact source references for inspection.

### Existing Pilot

The round-02 7 completed Current Diagnosis groups, full Memory review input and round-01 committed Memory are preserved. The implementation change intentionally does not rewrite existing run source bindings. Before resuming that Pilot, create an explicit source/protocol migration receipt that reuses those upstream checkpoints; blindly rerunning the old launcher will fail source validation. No real review or Pilot restart is performed by this implementation task.

### v19.3：问题与尝试关联

新运行的完整审计输入带 `memory_protocol=issue_memory_v19.1`。确定性投影
`edit_attempts` 从已有 generation issues、source findings、edit 和 Attribution 提取
问题来源、尝试内容、Gate 结果及正反/联合结果；不改写持久化原始证据，不新增图谱。
旧档案缺少来源时明确标为 LEGACY_EDIT_SOURCE_ONLY，不生成虚构问题摘要。

每个 edit 的既有 Memory Review 调用读取当前全部**精简 Finding 摘要**及事件引用目录，
不加载当前或历史原始 trajectory、工具定义或完整 Review 历史。规则引用只作关联提示，
不是资格条件，所以 RETAIN 后 ABSENT 的 ADD 也可关联当前问题。模型在既有
current_finding_refs 中选择关联；当前事件引用必须属于所选 Findings，保留原有四种状态。
这里判断的是 Findings 所报告的证据，不声称直接核查过原始事件。

这不是把全部 Findings 的原始证据送给每个 edit。32,000 输入预算不变，超限明确停止，
不截断、不新增 MORE_CONTEXT。规模增长后仍需监控预算，本次正式样本最大接近上限。
profile 的 available_finding_count 表示可见范围，linked_finding_count 仅表示规则提示，
二者都不等于模型实际建立的语义关联。

Issue Fusion 按问题合并历史与当前发现，相关 edit_attempt 随既有 historical_objects
进入局部 Evidence Review；只有此处加载相关原始证据并核验修改。局部审阅比较旧尝试：
拒绝不等于单 edit 无效，接受不等于单 edit 有效；重复负向尝试应在既有 reason 中说明
新证据或实质变化，无支持则 NO_EDIT，历史并非永久禁令。这是模型判断要求，不是代码
已经证明的因果关系或语义防重保证。Compiler/Editor 和输出状态不变。

旧输入无协议字段时按旧方式重建，保留旧审计哈希的可验证性。新旧请求不可混入同一
检查点批次。恢复现有正式实验需另行记录迁移并重建 Memory Review 及其下游；可以复用
已完成 Current Diagnosis。本次实现不启动实验，也不修改旧运行目录。

### v19.4：引用闭合错误与契约修复预算

输出契约不变。错误报告包含 review 索引、historical_object_id、未共享证据的 Finding
及其可引用事件、实际已引用事件。仍由模型决定修复，不由程序补引用或删 Finding。

输入采用无损共享 JSON 值表（repeated_text/shared_text_ref）及显式 ID 别名；
原始证据包和响应不截断。修复只携带一份原输入，原响应/错误中的引用可以用同一
别名表示，原响应文件保持原文。修复不再嵌套另一张共享值表。

总输入上限仍为 32,000；首次请求上限为 28,800，为唯一一次修复预留 3,200。
修复发送前仍按实际请求计数；余量不能保证任意长度输出都能修复，超限继续停止。
不是扩大总预算，也不增加修复次数。profile 的 within_budget 按首次上限判断。

本次离线回归：失败 edit 首次 31,075 → 28,730，带详细错误的修复为 31,051。
完整拒绝响应和输入包的压缩测试夹具保存在 tests/skill_evolution/v19/fixtures 中。
旧运行未更改。新 prompt/错误协议与旧绑定不兼容，不直接 resume 原目录；后续迁移
需保留 6 个完整 Review 以及该 edit 原始响应，归档已确认未发送的修复请求，
只为失败 edit 生成新的修复请求。不得通过改哈希或整批重跑绕过版本校验。

#### 历史判断与问题复发（claim-comparison-1）

不增加状态或输出字段。Review 在现有 `reason` 中明确被检验的历史主张，并区分：

- 问题仍存在：未采用旧方案的 Parent 再次犯错，只说明需求仍存在，不证明旧方案有效或无效。
- 旧方案的行为／适用性主张：只有相关证据能够支持或反驳；ABSENT 不禁止独立的能力或适用性反证。
- 已部署的规则：存在不等于被执行；不遵守与遵守后的后果必须区分。

只有相关问题复发、未检验方案主张时，沿用 `NOT_COVERED / INSUFFICIENT_EVIDENCE`，
保留 `context_current_refs` 和 `current_finding_refs`。这些关联仍交给 Fusion，不丢失重试机会。
不按 ABSENT、Gate 或结果分数由程序自动改写 Evidence Status。

共享语义在 `memory_consumption_v19.py` 中定义。新 prompt 记录 `-claim-comparison-1`；
输入数据、状态枚举及验证 schema 不变。历史判断不被覆盖，已保存结果不会自动转换为新语义结果。

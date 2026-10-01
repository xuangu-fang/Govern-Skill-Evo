# v19 职责拆分第 2 步：Reconciliation 与确定性编译

日期：2026-09-24。

本步实现独立 Reconciliation 输入、Prompt、响应校验、逐项处置、v18 Compiler/Editor 适配和 Candidate 文本应用。没有模型 transport、一次契约修复、阶段检查点、Memory 提交或新 campaign 接入；这些属于第 3 步。未启动真实 Pilot，未改变 v18 或原 Pilot。

## 数据流与接口

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

## 逐项处置契约

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

## 证据与冲突

- 每个当前来源必须与 decision 共享事件。v19.2 区分 DIRECT_BASIS / COUNTEREVIDENCE / CONTEXT：只有直接依据必须与 gap 共享事件，反证和背景仍必须进入 decision 与分析。每个角色须解释理由；不能用背景标签掩盖独立未处理的问题，这类问题应单独 DEFER。结构校验不能证明角色判断的语义正确性。
- linked Historical Review 的当前支持、反证和不充分观察引用必须完整进入 decision；不得只保留有利一侧。
- proposal 的 analyses 必须覆盖 decision 的事件证据；gap 仍须满足 v18 的“属于声明分析并与每个声明维度共享事件”规则。
- policy 只能引用分析所涉轨迹的可见上下文；supervision 只能引用所分析轨迹的标签。
- 历史原始事件保留 pair/role/source_round/Skill/original_trajectory_ref；编译适配的复合轨迹身份避免历史和当前别名冲突，不改写原事件引用或正文。
- 同一事件在来源合并后的 provenance 中按原始引用去重，不生成支持票数或根据历史篇幅打分。
- KEEP 和编辑同一目标直接拒绝。v18 Compiler 对同一目标的 REPLACE/DELETE 冲突直接拒绝，不由程序选择语义胜者。
- 对同一目标的多个 REPLACE，沿用 v18 确定性合并，并保留全部 backing gaps 与来源。语义重复的 ADD 仍须在 Reconciliation 中合并；Compiler 不做语义推断。

这些校验只能确认引用、覆盖和显式说明，不能证明“暂缓当前发现的理由成立”或自然语言冲突已经真正解决。

## 复用 v18 而不修改它

PROPOSE 中的 diagnosis 由模型显式提供，包含原有 success_analysis、compliance_analysis、skill_addressability 和 parent_skill_gaps。适配器不自动补分析、补引用、改 gap 或改目标。

```text
MISSING         → ADD      （无 related_rule_refs）
NEEDS_REVISION  → REPLACE  （绑定当前规则）
SHOULD_REMOVE   → DELETE   （绑定当前规则，解释整块删除）
```

调用原有 `validate_diagnosis_response`、`compile_edit_plan`、`build_editor_request` 和 `apply_editor_response`。引用闭合、原文目标解析、混合操作冲突、有限 Editor 操作和未编辑原文保持行为均保留。

KEEP/DEFER 仅在 v18 适配层表示为无 gap 的 NOT_ADDRESSABLE/NOOP，以满足现有 Compiler 类型；真实语义仍以 ReconciliationResult 中的 KEEP/DEFER 为准，不把它解释成 Current Diagnosis 对问题可修复性的结论。空发现加空历史得到确定性 NO_UPDATE。

纯 DELETE 不调用 Editor，由原 v18 应用器确定性删除；ADD/REPLACE 才生成 Editor 请求。Editor 仅收到本 edit unit 的 gaps、分析、证据及其 Reconciliation 来源，不能借入其他单位的历史说明。Editor 输入也有发送前预算检查，不静默截断证据。

## 追踪、恢复接口与边界

- `RC/<hash(input_ref + decision)>` 标识处置；保留精确模型原响应、完整处置和 canonical plan。
- Editor 请求/应用前重新验证整份 Reconciliation 并重编译，拒绝被修改的结果。
- `apply_reconciled_editor` 返回 `edit_provenance`：edit_unit_index、operation、decision_refs、current_finding_refs、historical_review_refs、去重的 evidence_refs。与 Candidate/全部处置记录一起返回，保留纯当前、纯历史、二者合并三种链。
- 此处 provenance 描述计划中的操作；Editor 若返回 UNABLE，不表示这些操作已经应用。
- 当前函数为纯阶段接口，不写检查点、正式 edit ledger 或 Memory。第 3 步将把这些来源接入持久化账本和跨轮关系，统一 run/resume。
- 本步没有改动 `run_v19_v4.py`，现有入口仍是旧生成流程，不能用它宣称新架构已运行。

## 工程验证

专项命令：`python -m pytest tests/skill_evolution/test_reconciliation_v19.py -q`。

覆盖三类编译操作、纯当前/纯历史/合并来源、KEEP/DEFER、空批次、覆盖遗漏、重复来源、引用闭合、过期规则、历史反证不可丢弃、整块删除理由、同目标合并、KEEP/编辑冲突、REPLACE/DELETE 冲突、Editor 前篡改拒绝及缺失候选不可 KEEP。使用构造模型输出，只证明机制，不证明新架构优于旧 Pilot。

最终验证：新增专项 **24 项**，v19 全量 **317 项通过**；语法编译与 diff 空白检查通过。v18 冻结 manifest 的 **992 个文件哈希一致**。没有真实模型调用或新 Pilot。


## Reconciliation v19.2：来源角色与一次修复反馈

输入与响应版本升级为 v19.2，新增必填 current_finding_assessments。旧 v19.1 仅在绑定旧输入的审计重验中按原规则解释；新输入拒绝旧响应，程序不会为旧响应自动分配角色。

校验汇总各 decision 可独立检查的错误，包括重复引用的具体值、来源覆盖、直接依据缺失、gap 的声明维度闭合、分析遗漏和监督标签关联。形状错误会阻止不安全的后续解引用；未知来源也不能继续推导其证据集合。反馈不承诺枚举所有语义问题。一次模型修复上限不变，原响应不去重、不补证据、不改结论。

真实 Pilot 两份失败响应及其完整绑定输入保存在 `tests/skill_evolution/fixtures/v19_reconciliation_failure.json.gz`，附来源文件 SHA-256。它们仍是失败样本，不能通过代码补角色变为成功结果。

恢复边界：旧 Reconciliation 请求及唯一修复均须保留，不能在旧调用上追加第二次修复。后续恢复应建立带源代码/契约摘要的新尝试并显式归档旧失败。当前七组 Current Diagnosis 的请求与重建请求完全一致，所有 Findings 原响应重验通过，可作为经过核验的复用输入；这不等于放宽 campaign 的来源绑定。现有普通 resume 会保护版本边界，不能直接跨本次升级继续。

## Reconciliation 输入 v19.3：发现/审阅优先，按引用载入证据

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

### 离线 token 分析

命令不会加载模型或改变 Pilot，输出目录必须是新目录：

```bash
python scripts/profile_v19_reconciliation.py \
  --request experiments/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation/reconciliation-v19.2.attempt-004/request.json \
  --input experiments/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation/reconciliation-input.json \
  --output artifacts/v19_reconciliation_input_audit_new
```

报告包含原请求和重建请求的 cl100k_base proxy token、system/schema/user 分解、各部分及其唯一正文表占用、JSON 分段差额、重复身份统计与证据数量。它不是网关 tokenizer 计量，也不证明 APITimeoutError 的单一原因。

本次真实输入：496,216 → 128,636 proxy token（减少 74.1%）；41 条 Findings 不变，832 条全量当前事件改为 237 条被引用事件；36 条轨迹身份原来重复出现 832 次。原请求历史轮数为零，因此本轮主要负担不是历史 Memory。报告保存在 `artifacts/v19_reconciliation_input_audit_20260924/profile.md` 和同目录 `profile.json`。没有真实模型调用或 Pilot 启动，不能宣称已消除超时。

## 输入/响应 v19.4：逐问题决策与可执行性核验

本次修复决策机制，不针对任何领域、工具名、任务 ID 或 Pilot 结果制定规则。不启动模型，不改写已有失败/成功响应，不自动进入 Editor。默认的新生成使用 v19.4；v19.1–v19.3 审计仍按原版本恢复，不能把旧响应自动补字段后视为新版通过。

### 问题处置

每条 decision 新增 `issue_dispositions`，恰好覆盖其 current/historical 来源，每项给出 issue、disposition、reason。观察到的问题不得使用 CONTEXT_ONLY；PROPOSE 中的问题必须 ADDRESSED，KEEP 对应 PRESERVED，DEFER 对应 DEFERRED。不能处理的独立问题应另立 DEFER，不能埋在另一提案背景中。

多来源决策必须填写 `merge_justification`，解释共同问题及兼容的处置方向；单来源不填写。DEFER 必须给出 `defer_basis`：INSUFFICIENT_EVIDENCE / UNAVAILABLE_CAPABILITY / UNRESOLVED_CONFLICT / UNCERTAIN_APPLICABILITY，以及具体理由和再判断需要的信息。不存在整批提案数量配额；每个 PROPOSE 恰好一个 gap，多个独立 PROPOSE 均可进入原 v18 Compiler。

### 可执行性与上下文

v19.4 视图对被 Findings、Review、归因或显式补充引用命中的轨迹，载入全部原始事件，包括先前调用、返回结果、后续结果和反证；同一轨迹身份仍只保存一次。该闭合规则不靠模型猜测哪项能力重要，也不以工具名或结果极性筛选。相关上下文的完整工具定义由 `available_tool_refs` 提供，带上下文和正文摘要，原政策和规则寻址不变。未命中轨迹仍不自动载入。

每个 PROPOSE 必须列出 `feasibility_checks`：requirement、SUPPORTED/UNAVAILABLE/UNKNOWN、原事件 evidence_refs、所依赖的工具 tool_refs、availability_before_action、limitations_and_counterevidence、reason。任何必要前提为 UNAVAILABLE/UNKNOWN 时拒绝 PROPOSE；应 DEFER 或重新形成有依据的不同提案。工具无关的行为允许空 tool_refs，但仍要引用事件并说明可执行行为。不能从事后结果差异直接推断行动前可获知该结果。

核验引用必须来自该 decision 的来源轨迹、已加载正文和对应上下文工具定义；完整上下文可用于检验能力与反证，不会自动扩充 gap 的直接证据范围。逐问题记录和可执行性核验进入持久化结果与 Editor provenance，重放时重复校验，仍最多一次契约修复。

**校验边界**：程序检查覆盖、类型、引用、作用域、声明状态以及来源闭合，不判断自然语言是否真实蕴含可执行性、是否遗漏了未声明的前提，亦不能证明合并理由成立。将 UNKNOWN 改写为虚假的 SUPPORTED 不会被这些结构规则完全识别；实际模型结果仍须审计。没有引入语义保证或额外独立评审模型。

本次工程采用完整来源轨迹作为保守上下文闭合，输入量会增加：相同 Pilot 离线重建约 241,954 proxy token（前版 128,636，最早全量表示 496,216）。它解决选择性片段遗漏风险，不是进一步压缩。默认 transport timeout 和 max_completion_tokens 未改；没有复用/覆盖旧 900 秒一次性尝试。

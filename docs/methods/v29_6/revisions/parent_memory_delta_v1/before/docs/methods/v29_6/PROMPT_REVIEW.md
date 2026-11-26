# v29.6 Prompt 差异与静态审阅

当前叠加了 [docvqa_domain_v1 领域指南修订](DOMAIN_GUIDANCE_REVIEW.md)。以下 15 项仍描述首次方法迁移；[changes.json](changes.json) 保持原样，随后再应用 [domain_guidance_changes.json](domain_guidance_changes.json) 的 6 项领域替换。完整 Prompt 和相对 v29.5 的 diff 已更新；首次版本见 [修订前快照](revisions/docvqa_domain_v1/before/)。Parent＋Memory 方法段落未变，本修订未实验。

日期：2026-11-05。直接比较对象是本目录冻结的 v29.5 实际加载 Prompt；迁移参考是 v28.5 首次实验的 frozen_prompts。审阅为本地文本与代码核对，不是独立模型评审、软件接入验收或实验效果验证。

## 1. 精确差异入口

- [Diagnosis diff](diffs/diagnosis_from_v29_5.diff)
- [Preconditioner diff](diffs/preconditioner_from_v29_5.diff)
- [Editor diff](diffs/editor_from_v29_5.diff)
- [Replay diff](diffs/replay_from_v29_5.diff)

[changes.json](changes.json) 保存以下 15 处替换的完整 before/after。编号表示可复现的文本替换单元，不表示独立机制或实验消融项。每个模块的完整 Prompt 在 [prompts](prompts/)；无需依赖本文件拼接。

| 编号 | Prompt 定位 | 相对 v29.5 的变化 | 保留项 |
|---|---|---|---|
| D1 | 开头职责 | Diagnosis 聚焦行为提案，Parent 整合与历史调整归 Preconditioner | 不读 Memory，不设 Update 数量 |
| D2 | Examine current evidence 最后两段 | 替换全面选择旧规则修正方式的义务；可指出有证据的冲突，不要求全面 Parent 审计 | 当前失败不等于缺规则，已有覆盖不等于充分 |
| D3 | Construct complete, scoped Updates / Keep the actions… | 将跨位置旧指导处理改为完整行为依赖；不重新按未来去留拆分 | 按共同问题与修正方向组织，不要求独立因果证明 |
| D4 | Goal / When correctness… / Distinguish… | Original 完整性定义为行为提案；必要旧指导处理交 Preconditioner | 条件、强度、依赖、保护边界和任务不可记忆化 |
| D5 | Resolve overlap… / Required local… | 只要求解决自己提案的矛盾与依赖，Parent 全面去重/优先级/旧规则整合移交 | 不容许含糊提案或下游替上游补证据 |
| D6 | Evidence / No separate Checks… | text 承载提案的材料性条件；成功/反例引用进入 basis | 全批 Diagnosis，不受 hard 翻转筛选限制 |
| P1 | 开头职责 | 以进入当前 Skill 的修正审查提案，联合 Parent、当前证据与相关 Memory | 无新增 Diagnosis、不直接编辑 Parent |
| P2 | Frozen proposal and available input | 全部相关 Parent 段落的覆盖、增量和交互审查替换对上游修正方式的被动审查 | Original 问题边界；不扫描无关新修复 |
| P3 | Decide Direction Scope and Coordination | 明确无依据扩展、冗余保护清单、相关规则整合、存活 Updates 共同含义 | 不设长度目标，不合并 IDs，不保证所有 patch 子集有效 |
| P4 | Choose one complete adjustment… | KEEP 要求必要协调充分；REPLACE 必须完整传递旧规则处理；WITHDRAW 处理依赖 | 全文替换、reason 不下传、无历史可合理 KEEP |
| E1 | Input and implementation scope | 迁移首次 Editor 的旧文字落实、避免冗余复述和本次实施自查 | 一 Update 一 patch、原 Parent 定位、必要条件与新指导仍允许 |
| R1 | Relate each hard transition / 第一段 | 先记录影响解释的全部可见答案变化，不只选符合意图的一项 | hard-only、ANLS 仅诊断、不把退步概括成一般失败 |
| R2 | 同节 / Read each relevant Update… 及新增归一化段落 | 分开答案变化、Update 关联、得分解释；加入 DocVQA 原评分规则下的核对 | 多项变化不自动 null，不推断 unseen image |
| R3 | Self-contained event Knowledge / 第一段 | Knowledge 条件限于事件支持范围，具体事实不能被一般免责声明替代 | 一题一条、单一 Update 或 null、字段不变 |
| R4 | Exact output and fidelity review / Before finalizing… | 首次 v28.5 的答案忠实度、同时变化、归一化与事件支持检查 | 不加入后续 Brutus 强化段落；JSON/覆盖合同不变 |

## 2. 排除项与避免误迁移

| 排除项 | 可核对材料 | 本版处理 |
|---|---|---|
| Brutus / R03 后的 Preconditioner 修订 | [原补丁](sources/preconditioner_evidence_consistency.diff) | 保留首次冻结的联合协调段落；不加入“收紧条件后回查原支持案例”的新增要求 |
| 同次 Replay 修订 | [原补丁](sources/replay_evidence_consistency.diff) | 使用首次冻结的 fidelity review，经 EM→hard 适配；不加入决定性条件核实、未知/不一致强化段落 |
| 后续 Editor 表达压缩微调 | [原补丁](sources/editor_expression_compression.diff) | 基于首次冻结的 Editor 实施段落；不迁入后续关于可删解释、示例与保护性复述的扩展 |
| 首次 v28.5 的逐行表达偏好 | [首次 Diagnosis](sources/v28_5_initial/prompts/diagnosis.md) | 保留 v29.5 的完整段落/列表，不恢复每行独立要求 |
| SearchQA 的上下文可见与归一化 | 首次来源四份 Prompt | 不复制；保留 DocVQA 文本投影、hard/ANLS、图片不可见和原 Actor 协议 |

排除案例衍生补丁不是删除 v29.5 原有证据底线。尤其 Replay 仍不得把分数当作独立因果证明、推断图片内容或杜撰隐藏过程；Preconditioner 仍需基于当前证据和历史判断适用范围。

Editor E1 保留 v29.5 的“确需新指导时不强制合并”，并继续明确英文措辞。Preconditioner P3 保留 DocVQA 关于穷尽图像区域、核验仪式和强制长答案的负担说明。Diagnosis 首次版本保留了答案 selection/scope/transcription 专门段落；本次领域修订以共享指南替换该段落，问题分组和原 JSON 示例不变。Replay 保留 v29.5 原有形状示例，其冠词变化示例符合 DocVQA 不删除冠词的评分规则。

## 3. 交接一致性审阅

**Diagnosis → Preconditioner。** Parent 仍完整可见，不是屏蔽现有规则。减少的是全面整合义务，不能把 Original 降为口号。basis 引用成功和反例，避免 Preconditioner 的选取视图丢失关键材料；原 reason 不下传。

**Preconditioner → Editor。** Original 不再必须给出所有旧规则处理，故 KEEP 必须检查是否已经充分；不足时用完整 REPLACE，将必要处理写入 text。不能仅在 reason 中说明“同时删除旧规则”。Goal/ID/basis 冻结以及全部 KEEP 仍进入 Editor 的语义保持原样。

**Parent 与 Memory。** 当前 Parent 是现状依据，历史 Retain 不能替代对现有文字的检查。历史未知仍为未知，缺少 Knowledge 不等于执行无效。Memory 不新增检索、重归因、patch、历史图像或未翻转响应。

**整合与映射。** 允许在原问题内整合受影响的旧规则，不允许合并或搬运独立 Update。Editor 只实施授权行为。整个 Candidate 的自查和执行不能保证后续任意 patch 子集有效；没有新增依赖图、组合复测或 Gate 兜底。

**Replay 与选择。** 事实更完整不等于抬高为独立因果证明。多特征变化仍可以支持明确关联；原 null 标准和一题一条事件合同不变。DocVQA 不可见图像条件不能被当作已观察内容，原评分解释也不能替换成 SearchQA 的标点删除规则。

## 4. 静态检查及其限制

[validate_design.py](validate_design.py) 从冻结基线逐项重放 changes.json，核对生成全文及 unified diff；比较原始来源哈希；核对公共证据/运行段落、输出合同、Editor patch 全文、Preconditioner 编译合同和 Replay 输入/输出形状不变；检查两处 Brutus 修订前段落的精确来源、Editor 首次措辞、DocVQA 与冻结参数，以及本地文档链接。

结果见 [design_validation.json](design_validation.json)。检查不调用 Actor 或模块，不导入运行器，不重新执行历史实验。未验证模型会如何理解这些文字、是否正确协调旧规则、是否减少冲突、最终 Skill 是否更短或 Test 是否提高。软件接入检查另见 [IMPLEMENTATION.md](IMPLEMENTATION.md)；实际方法效果仍待后续实验判断。

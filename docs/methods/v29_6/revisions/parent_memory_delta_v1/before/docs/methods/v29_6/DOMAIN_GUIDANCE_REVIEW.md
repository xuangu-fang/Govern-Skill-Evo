# v29.6 DocVQA 领域指南修订：docvqa_domain_v1

状态：仅修改优化器领域指导并做离线核验；本修订未启动训练或最终 Test。Parent＋Memory 预条件机制冻结。此前 325/374 的结果属于修订前 Prompt，不是本指南的实验结果。

首版直接采用 SkillAdam 选定的领域原文。当前按用户确认追加 env_adaptation_v1 小范围环境适配，仅替换下面列出的两处文字；其余摘录、模块职责和实际输入合同保持原样。

## 共享指南

[DOCVQA_GUIDE.md](DOCVQA_GUIDE.md) 当前共 454 个按空白分隔的词、3,348 字符，包含五部分：

| 内容 | SkillAdam 来源 | 处理 |
|---|---|---|
| 单图单轮下的作答时决策规则 | stage0_system_prompt / Domain-aware | 摘录后适配单轮执行边界；不启用 Stage0 |
| 布局、题型、格式和视觉提取模式 | skill_writing_policy / Permitted domain-specific content | 原文摘录 |
| 证据定位、答案范围、输出格式和避免编造 | metric_interpretation / What the skill should focus on 的四项内容 | 摘录后将答案粒度依据改为题目和可见文档 |
| 五类失败词汇 | failure_types.md | 全文保留；不新增分类字段或强制分类步骤 |
| 泛化和禁止案例记忆化 | stage0_system_prompt / Forbidden Content | 原文摘录；保留合成示例要求 |

首版保留过 no second look、no retries 和 match the gold's level of detail；当前已按下述两项替换完成适配。未选择的评分解释整节、轨迹摘要模板、Skill 标题/YAML 模板、5 条规则限制、编辑计数要求和历史调整策略不并入指南：这些分别属于评分解释、输入/输出结构或优化方法，不是本次共享领域层的范围。完整来源快照仍保存，未修改 external/SkillAdam。

每段原文的来源路径、起止定位和 SHA-256 见 [domain_guidance_sources.json](domain_guidance_sources.json)，来源许可保留在 [SkillAdam LICENSE](revisions/docvqa_domain_v1/skilladam/LICENSE)。共享指南嵌入四份完整 Prompt，内容完全一致；没有改变各模块的数据权限、职责或输出形状。运行时直接读取完整 Prompt，不要求模型打开指南文件，也没有新增运行时拼接代码。

## 被替换的现有指导

四个模块加入同一领域块，Diagnosis 删除以下两个自写领域段落，由共享指南承接其领域内容：

| 原段落起始 | 移除的重复或过强要求 | 共享指南中的对应内容 |
|---|---|---|
| Distinguish discrepancies in answer selection… | selection/scope/transcription 的专门分析框架；先处理答案完整范围、再增加字符复制指导的固定优先级；重复的最小充分片段与保留限定词说明 | 文档定位、答案片段、格式、失败类型和视觉提取模式 |
| Preserve requested field roles, entity, relation… | 一串逐项保护要求、答案不得弱化/替换、完整不等于最长、答案标签外围文字说明及禁止从格式差异推出统一规范化的领域提醒 | 题型、答案表示、原文提取和泛化边界 |

没有删除 Preconditioner 的 D/S/C 范围、条件、优先级或旧规则协调要求。Editor、Replay 和 Preconditioner 除新增领域块外，原全文逐字不变；Diagnosis 除新增领域块和上述两段删除外，原全文逐字不变。

本次确实替换了旧指导，并未声称完整 Prompt 变短：由于四个模块均获得明确的共享领域知识，Diagnosis 相对已训练版本净增 2,327 字符，其他三个模块各净增 3,670 字符。精简针对共享领域指南和被替换的重复/过强领域要求，不以总字符数作为完成标准。

## 冻结范围与历史结果

- Parent 全文、Memory 历史视图与权限保持不变。
- Diagnosis / Preconditioner / Editor / Replay 职责交接保持不变。
- KEEP / REPLACE / WITHDRAW、D/S/C、Original ID 和 basis 冻结语义保持不变。
- Editor patch 格式、Replay 归因、Gate 和 Memory 算法保持不变。
- Actor 基础 Prompt、初始 Skill、数据、顺序、批次、模型、预算、并发和重试参数保持不变。
- 不迁入 Brutus 后续补丁，不引入规则数量上限，不新增压缩阶段。

修订前完整设计、四份 Prompt、差异和验证结果见 [修订前快照](revisions/docvqa_domain_v1/before/)。历史 campaign、Test、launch 目录不修改。源码的 Prompt 内容现已更新，因此不能拿当前 Prompt 冒充历史实验版本；原运行的 implementation.json 和逐调用归档仍是历史依据。现有恢复逻辑会校验完整 Prompt 和源码身份，本次没有放宽该逻辑。

方法与配置身份继续使用 v29.6 原身份；本次领域修订单独标识为 v29_6_docvqa_domain_v1，由指南来源清单、before/after 和内容哈希追踪。没有创建新实验。

## 差异与离线核验

- [领域替换记录](domain_guidance_changes.json)：4 处嵌入、2 处删除，共 6 项。
- [Diagnosis 相对已训练版本](revisions/docvqa_domain_v1/diagnosis_from_trained_v29_6.diff)
- [Preconditioner 相对已训练版本](revisions/docvqa_domain_v1/preconditioner_from_trained_v29_6.diff)
- [Editor 相对已训练版本](revisions/docvqa_domain_v1/editor_from_trained_v29_6.diff)
- [Replay 相对已训练版本](revisions/docvqa_domain_v1/replay_from_trained_v29_6.diff)

[validate_design.py](validate_design.py) 先重放原来的 15 项方法迁移、首版 6 项领域替换，再对共享指南和各模块重放 2 项环境适配，核对完整 Prompt 与差异；额外检查 SkillAdam 摘录逐字一致、共享块恰好出现一次、领域块以外的冻结要求、运行代码/配置/历史结果哈希不变。结果见 [design_validation.json](design_validation.json)。首版离线运行链路核验见 [首版验收结果](../../../artifacts/verification/v29_6_docvqa_domain_v1/validation.json)。

离线检查只能验证来源、范围、接口和执行链路，不证明指南能提高成绩或降低生成 Skill 的冗余。没有调用真实模型。

首版曾通过 844 项既有离线测试和 332 项设计检查；这些历史结果不冒充本次环境适配后的重新测试。原验收清单把首次设计中的 4 份 Prompt 和 4 份 diff 也标为不可变，因此原始总报告因这 8 个授权变更而标记失败，测试与运行配置核对本身没有失败。该原始报告保存在 [授权差异归类前报告](../../../artifacts/verification/v29_6_docvqa_domain_v1/validation_before_domain_allowlist.json)。[验收归类脚本](revisions/docvqa_domain_v1/finalize_acceptance.py) 核对这 8 个文件的 before 快照确实匹配原清单，核对其余基线与本次新增冻结范围不变，并保留原测试结果及日志哈希后给出最终通过结论；没有重跑或修改测试结果。

## env_adaptation_v1：仅两处环境适配

1. 将 `no retries, and no second look at the image` 所在执行描述替换为：
   > The Actor receives one document image and one question and produces its answer in a single model round, without tools, online search, or feedback-driven answer revision.

   不再限制同轮图像核对，不新增强制核验步骤。技术失败与长度终止的重试规则仍由原有 runtime 段落定义，参数不变。
2. 将输出格式条款替换为：
   > Output formatting: emit exactly one `<answer>...</answer>`; keep the span short and verbatim; determine the answer's level of detail from the question and visible document evidence, including units, date components, and identifying name components.

   优化器仍可使用训练参考答案分析粒度差异；未移除 reference_answers 或改变证据权限。最终行为规则的粒度依据改为 Actor 可见信息。

共享指南、四份设计 Prompt 和四份运行时 Prompt 同步。仅指南中的两段内容变化；Parent＋Memory、D/S/C、KEEP/REPLACE/WITHDRAW、Editor、Replay/Gate、Actor 和全部实验参数均冻结。未启动实验。

原文与替换见 [两项 before/after](revisions/docvqa_domain_v1/env_adaptation_v1/changes.json)，适配前状态见 [环境适配前快照](revisions/docvqa_domain_v1/env_adaptation_v1/before/)，四模块差异见 [适配差异目录](revisions/docvqa_domain_v1/env_adaptation_v1/)。当前记录为“SkillAdam 领域摘录＋必要环境适配”，不再将全文称为未经改动的摘录。

本次通过 115 项 v29.6 既有离线测试、357 项静态设计检查及配置核对；242 个冻结文件哈希不变，未尝试网络或外部进程调用。报告见 [环境适配验收](../../../artifacts/verification/v29_6_docvqa_domain_env_v1/validation.json)。首版验收文件和其归类脚本保持原样，不重新使用首版的 Prompt 哈希作为当前状态。

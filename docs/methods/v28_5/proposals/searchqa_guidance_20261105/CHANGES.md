# 修改差异与来源对照

本页解释设计差异；逐字差异见 [all.diff](diffs/all.diff)，完整稿见 [FULL_PROMPTS.md](FULL_PROMPTS.md)。原文快照位于 [baseline/prompts](baseline/prompts/)。

## 1. Diagnosis：替换与合并

| ID | 原 v28.5 | 修订方案 | 依据／目的 |
|---|---|---|---|
| D1 | `Examine current evidence` 用连续段落区分缺失指导、未观察到执行、实体／关系、答案边界、参考形式 | 用五类失败、四类成功模式组织领域判断；加入一个有明确使用边界的过度展开示例；保留可见行为→假设→具体修正→basis→Preconditioner 的交接 | SkillAdam 领域分类与示例；让已有原则更容易执行，而非新增分类模块 |
| D2 | `Construct complete, scoped Updates` 首段再次说明行为增量、泛化和优先级 | 精简为具体行为增量、共同决策关系与适用条件，并明确 near-miss 和实体／关系失败都可考虑 | 删除与 D1 重复的说明，不按 F1 高低机械排序 |
| D3 | 长段重复可见条件、外部工具禁用、未观察到内部行为以及若干来源偏好警告 | 保留 Actor 可见条件、无工具／评分辅助纠正、单轮负担和证据限制 | 更一般的领域条件已在 D1 中；不再列一串“数段落／偏某来源／长答案”的特殊警告 |
| D4 | 再次论述短答案、必要限定、答案元素范围、单次命名差异及归一化 | 保留请求实体／关系／时间／粒度、必要名称成分及答案元素作用域 | 名称与归一化判断分别由 D1 及未改的 scorer 段覆盖 |
| D5 | Goal／Original 完整性段结尾再次禁止从参考拼写推出普遍规则 | 删除这句重复提醒；完整保留 Goal、条件、强度、依赖、保护范围和禁实例答案 | 参考形式不能证明普遍偏好已在 D1 中明确 |

**没有删除**：可见证据范围、隐藏 reasoning 不可用、Scorer 的精确归一化、EM 不等于语义正确、Test 不进入优化、单案例可以形成有范围提案、Original 的完整性、basis 与输出 schema。

### 关键措辞的变化

原文以 `entity or relation selection / answer boundaries / reference forms` 区分失败。修订稿保留这些含义，增加明确的处理方向：

- 没有覆盖 → `rule_missing`，考虑真正缺口。
- 已有规则与任务冲突 → `rule_wrong`，考虑修订或删除。
- 已有覆盖但可见响应未满足 → `rule_ignored`，考虑具体化触发或动作。
- 同一对象的输出形式不匹配 → `answer_format`，先检查实际 scorer。
- 证据或能力问题可能无法靠 Skill 修复 → `other`，不强制产出规则。

成功侧补足 SkillAdam 显式列举的领域信息：Jeopardy “this X”、关系方向／逆向关系、整体与实例、历史与当前名称，以及简洁无歧义的名称与语法形式。这些描述是提炼行为的方向，不是规定某种题型永远输出某种答案。

根据本次审阅意见，不将 SkillAdam 的 `shortest unambiguous` 作为主导目标。保留原 v28.5 的 `smallest sufficient answer unit`，将规范形式与完整回答放在缩短之前：

> Select the conventional answer form supported by the question and context. Prefer the smallest sufficient answer unit; shorten only by removing genuinely redundant content.

上下文中能唯一指向对象，并不保证该形式符合 reference；语义上冗余的名称成分也未必可以删除。后文继续要求保留必要名称成分、限定、单位、范围和语法，并明确长名或短名均非普遍优先。该措辞不要求 Actor 访问 reference，也不声称缩短会提高 EM。Diagnosis 与 Preconditioner 同步使用这一版本。

## 2. Preconditioner：领域层增加，方法正文冻结

唯一插入点为原 `Historical Memory by round` 之前：

1. 内嵌与 Diagnosis 完全相同的 `SearchQA domain guidance`。
2. 加入 `Apply domain guidance through Parent and Memory`，说明分类如何服务现有预条件判断。

从原 `Historical Memory by round` 至文件末尾逐字保留，包括：

| 部分 | 保留的含义 |
|---|---|
| Historical Memory | Effective Updates、Gate 决定、Knowledge；未知不等于不存在；null 不作为某个 Update 的正负证据 |
| Frozen proposal | Parent 全文、冻结 Goal/ID/text/basis、当前引用执行子集 |
| Historical response | 比较行为机制与条件，不按词汇或题型相似度机械迁移 |
| Direction | 决定本问题值得促进、改变或停止的行为 |
| Scope | 依据当前与历史证据限定条件、强度及保护边界 |
| Coordination | 明确旧规则的替代、限定、整合或删除，检查与其他 Updates 的关系 |
| KEEP／REPLACE／WITHDRAW | 完整决定及原有字段；不能只在 reason 中藏实施条件 |
| Compilation | 保留 Goal/ID/顺序/basis，仅替换文本或撤回；不改 Memory、不增加模块 |

新增词汇不授权 Preconditioner 独立提出新问题，不要求对全部训练任务重新诊断。`rule_missing` 不自动 KEEP，`rule_wrong` 不自动 WITHDRAW，`concise_normalization` 不自动证明有效。具体决定仍由 Parent＋当前证据＋相关 Memory 联合形成。

Diagnosis 和 Preconditioner 分别接收独立请求，因此两份完整稿各自内嵌同一领域段。这是请求间的必要自包含，不是要求在最终 Skill 中重复写入分类。`design/searchqa_guidance.md` 只是审阅来源，运行时不依赖它。

## 3. Editor 与 Replay

**Editor 无改动。** 不向只负责实施的阶段注入新的领域策略，防止其自行判断或修正上游未授权的行为。四份完整稿中仍收录 Editor，`editor.diff` 保持空文件。

**Replay 只替换一段**：原 `Relate each EM transition to actual behavior` 的首段。把实体、关系、答案类型变化与同一 referent 的形式变化说清楚，要求记录同时变化。格式改善不自动等于推理改善，分类词也不构成与某个 Update 关联的证据。

后续所有关联规则、任务覆盖、empty patch 不可归因、null 关联、历史不可见、Knowledge 字段、具体归一化解释、校验与输出示例保留。没有把 F1-only 变化引入事件，没有增加失败类型持久化。

## 4. SkillAdam 来源与适配偏差

| 原始资源 | 原始关键内容 | 本稿处理 |
|---|---|---|
| [failure_types.md](reference/skilladam/failure_types.md) | 五类失败；要求每个失败恰好一类 | 迁移词汇与处理方向；不迁移强制分类流程及输出要求 |
| [success_types.md](reference/skilladam/success_types.md) | 四类成功；Jeopardy、关系、名称与简洁形式；分类日志 | 迁移领域信息；保留 v28.5 证据限制，不新增日志字段 |
| [iteration_example.md](reference/skilladam/iteration_example.md) | CPU／USB 过度展开、ROM 对照；在已有规则下附 gold/predicted 对 | 迁移识别与具体化思路，改为当前方法的行为提案；不写具体答案对，不复制上游补丁合同 |
| [metric_interpretation.md](reference/skilladam/metric_interpretation.md) | EM/F1 与参考答案说明；整包阈值 Gate 说明 | 核对概念，保留 v28.5 准确 scorer 文本；不迁移 Gate 或“F1=0 即完全错误”的简化表述 |
| [iteration_system_prompt.md](reference/skilladam/iteration_system_prompt.md) | 通用更新流程、Memory 解释、五条 Error Avoidance 限制 | 不整体迁移；本方案不改变 v28.5 优化机制或引入规则数约束 |
| [stage0_extra_section.md](reference/skilladam/stage0_extra_section.md) | Stage0 可附具体 gold/predicted 对 | 不迁移；作为明确边界的来源快照保存 |

适配保留了 v28.5 的重要限制，因此应表述为“参考 SkillAdam 的领域指导对齐”，不能表述为“完全复用 SkillAdam Prompt”或“已经消除所有 Prompt 混杂因素”。未更改 SkillAdam／SkillOpt 原文件。

## 5. 静态审阅结论与实际影响

| 风险点 | 本稿处理 |
|---|---|
| 分类变成新方法阶段 | 分类仅为 reason 中可用的自然语言概念，无新调用或输出字段 |
| 凭分类强制确定因果 | 保留可见行为与内部机制的区别，不要求虚构原因 |
| 所有成功都变成规则 | `other` 明确成功未必有可迁移模式 |
| 简短导向变成一律删词 | 规范形式与最小充分答案优先，仅删除真正冗余内容；保留必要名称成分、限定、单位、范围和语法 |
| 提案与历史只因名称相似就迁移 | 预条件衔接段要求实际机制和条件相符 |
| 示例被当训练事实／答案表 | 示例明确不是本轮执行，不能引用或复制到 Update；最终 Skill 禁实例答案 |
| 把 Prompt 精简与方法变更混在一起 | 删除重叠的领域段落；保留接口、Memory、D/S/C、Gate、Actor 及执行合同 |
| 同一身份下悄悄改变运行 Prompt | 提案独立存放，原绑定目录文件保持不变 |

本方案删除了重复表述，但**完整 Prompt 总长度增加**，主要因为 Preconditioner 需要自包含的领域指导。长度不是此次验收目标，也不能据此推断最终 Skill 会变长或变短。字符统计见 [validation.json](validation.json)。

这些是静态设计判断，不证明模型遵循、候选质量、泛化效果或 Test 改善。若后续实施，领域指导是本次唯一预定变化；不要同时调整批次、轮数、模型预算或 Gate，以便解释结果。本次没有启动该实施或实验。

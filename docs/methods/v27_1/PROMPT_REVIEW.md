# v27.1 来源差异与联合审阅

> 本文保留设计阶段的提示词审阅记录；后续独立实现与离线验收见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。随后已同步 Diagnosis、Preconditioner、Replay 的引用说明及对应来源差异；Editor 未修改，真实实验未启动。

状态：2026-11-04，设计者静态审阅，等待用户审阅；不是独立外部评审、离线实现验收或实验结果。四份 Prompt 是拟运行原文，代码尚未绑定。

## 1. 方法来源和差异入口

| 模块 | 规范方法来源 | 直接适配底稿 | 本轮差异 |
|---|---|---|---|
| [Diagnosis](prompts/diagnosis.md) | v29.4 | v28.3 Diagnosis | [相对 v29](diffs/diagnosis_from_v29.diff) / [相对 v28.3](diffs/diagnosis_from_v28_3.diff) |
| [Preconditioner](prompts/preconditioner.md) | v29.4 | v28.3 Preconditioner | [相对 v29](diffs/preconditioner_from_v29.diff) / [相对 v28.3](diffs/preconditioner_from_v28_3.diff) |
| [Editor](prompts/editor.md) | v29.4 沿用的 v29.2 Editor | v28.3 Editor | [相对 v29](diffs/editor_from_v29.diff) / [相对 v28.3](diffs/editor_from_v28_3.diff) |
| [Replay](prompts/replay.md) | v29.4 沿用的 v29.2 Replay | v28.3 Replay | [相对 v29](diffs/replay_from_v29.diff) / [相对 v28.3](diffs/replay_from_v28_3.diff) |

原文在 baseline/v29 与 baseline/v28_3，源路径在 [source_files.json](baseline/source_files.json)。LMB 基础协议、初始 Skill、65,536 历史训练配置及成员 ID 单独保存于 baseline/lmb。历史配置快照只作比较，不可当作 v27.1 可执行配置；设计参数另见 [experiment_plan.json](experiment_plan.json)。

## 2. 逐模块审阅

### Diagnosis

- 保留 v29.4 直接比较完整批次的段落；完整成功、失败和反例可用，单案例也可支持合理尝试，并非每题都要提案。
- 保留具体行为增量、集中干预、independently justified/actionable、必要依赖、多条有依据的 Update 和 no_change。不引入 v29.3／v28.2 v2 的整套组织规则或按预期 Gate 去留拆分。
- SearchQA 的实体/关系、答案长度和名称形式替换为 LMB 的选项语义、结论强度/完整性、假设/量词、标签映射与提交格式。不是新的必填分类字段。
- 保留原 LMB 的限制：非参考选项可能是较弱但真实的命题；不得笼统偏好最强/最长，不要求每题对所有选项做完整证明，不把 task ID、论文名或选项字母变成答案表。
- 无 Checks；所有实施条件在 text，直接执行依据在 basis。Diagnosis reason 不传给 Preconditioner。

### Preconditioner

- 保留 D/S/C、整条 KEEP 和全文 REPLACE/WITHDRAW；不增加 Update，不拆并 ID，不产生新 Diagnosis。
- 当前所选题干/选项可见，历史原始题干/选项不因而可见。按历史修改行为和适用条件比较，不能仅凭数学主题相同迁移结论。
- null 关联不能充当某条 Update 的收益/损失归因；Defer 不等于无效，空 entries 不等于负面实验，历史 Retain 不等于仍存在于当前 Parent。
- 保留必要配合与合理探索；主方向合理不自动支持附加条件、fallback 或顺序。所有调整进入最终 text，不能仅写入 reason。
- 没有为提高 Retain/撤回比例新增配额，也没有要求每个数学分支先有成功样例才准许尝试。

### Editor

- 输入严格为 parent/plan，Update 只有 id/text；LMB 适配不增加题目、参考、Memory 或解释字段。
- 逐 Update patch、共同定位原 Parent、只读 context 共享、字符范围组合和子集重新组合保持原方法语义。
- 输出协议由 SearchQA 的短文本答案变为 LMB 的唯一标签元素；禁止在 Skill 中加入与基础协议冲突的普通证明/解释输出要求。
- 数学条件可以被忠实写成供 Actor 判断的规则；Editor 不必先取得题目或证明定理。不能实现授权行为时用 null；不能因未来效果不确定就自动阻塞。
- 精确空串和 null 含义不同；实际结构冲突是校验错误，不自动转为语义 null。

### Replay

- 保留每个 EM 翻转任务一个事件、单 Update 或 null 关联、当前实际 patch/diff 依据、无历史输入、无自报 G/L 和 Gate。
- 对比的是映射后的选项内容与修改要求。选项字母变化可观察，但不展示 Actor 如何推理；不能把标签翻转直接解释为执行了某个证明或检查。
- 允许有清楚选项语义对应时做有限行为关联；不强制要求 Actor 提供被固定协议禁止的解释，也不把所有标签式输出一律判 null。
- 无法区分多个 Update 或无明确连接时记录 null，不把未归因退化当噪声或安全证明。
- EM 不变的错误选项变化、输出格式变化不进入 Replay；LMB f1=em，没有 token F1 或 F1-only 分支。
- JSON 示例为虚构结构示例，只展示一种有限正向关联和一种未归因退化；不包含真实任务 ID、选项字母答案、定理或 Test 修复规则。

## 3. 跨模块一致性

| 检查点 | 本稿采用的规则 |
|---|---|
| Actor 基础协议 | 四份 Prompt 中均为同一原始 LMB 文本；不换成 DocVQA/SearchQA 协议 |
| Actor 预算 | 四份 Prompt 均准确写 65,536；四模块各 32,768 是调用预算，不能混淆 |
| 完整证据 | 普通 content、题干、呈现选项完整保留；隐藏 reasoning、独立定理/草图和原始其他元数据排除 |
| 评分与格式 | 原标签提取/映射及 f1=em；format_compliant 不是完整协议证明，不据此改 Gate |
| Plan 来源 | 从整个 goal/text/basis 选择完整 runs，不扫描 Diagnosis reason；basis 承载关键依据 |
| 条件传递 | Update text → Effective text → Editor；不依赖上游 reason 或已删除 Checks |
| 修改映射 | 一条有效 Update 一个 patch，全部基于原 Parent，不串行定位 |
| 事件与历史 | 每翻转任务一事件；null 保留但不投票；每轮保存全部有效提案与决定 |
| Selected 来源 | 实际完整字符串比较；新组合不能继承 Candidate 分数 |
| 恢复 | 当前轮验证、原子发布、轻量读取已提交记录；额度不重置 |

来源 Prompt 的方法主体及完整输出结构在 diff 中可逐段检查。LMB 语义适配没有引入新工具、评分回流、独立证明验证、联合归因字段、成功保持事件或额外模型阶段。

## 4. 需要用户重点审阅的设计选择

以下均已给出具体默认方案，不是未填参数：

1. **来源路线**：使用 v29.4/v28.3，不整体混入 v29.3/v28.2 v2 的附加指导。
2. **归因边界**：从选项语义变化建立有限关联；内部证明不可见，允许 null。保持现有 Gate，不加整包退化否决。
3. **实验口径**：主历史对照为 52/124 的 65,536 v27；旧 59/124 和 SkillAdam 45/124 注明预算/重试差异。
4. **预算**：Actor 65,536；四模块各 32,768，Editor 相对原 v27 提升。无补测、无技术错误免计、无自动外层重启。
5. **运行适配**：采用顺序提交和轻量历史读取；保留 LMB 既有数据/当前归档身份检查，不添加全仓库哈希门槛。

后续如改变其中任何一项，应同步修改 README、CONTRACTS、相关 Prompt 和 experiment_plan，并更新来源差异。当前没有运行身份可恢复，也没有实验授权可由本稿推导。

## 5. 本轮检查与后续边界

本轮只使用本地文档与标准库静态检查：四份文本完整性、Actor 原文、预算/身份、JSON 示例、来源副本、差异可再生成、相对链接、53/124 成员及顺序。结果记录在 [design_validation.json](design_validation.json)。没有导入 campaign、构造模型客户端、执行训练/Test 或调用离线实现测试。

静态检查不能验证自然语言归因是否准确、选择是否提升泛化、运行代码是否符合合同或真实模型是否稳定输出该 schema。后续独立实现与离线验收对应这些工程合同；真实完整实验才回答效果问题。本目录不把设计检查计数写成实现测试通过数量。

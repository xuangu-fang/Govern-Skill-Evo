# V25 逐模块迁移清单

本清单以 `v24_alfworld_verified_feedback_001_rc1` 的实际生效路径为迁移起点，与 [Actor 与证据协议草案](ACTOR_EVIDENCE_PROTOCOL.md) 配套审阅。这里列出职责、输入输出、Prompt 改动和代码适配；完整 Prompt 已另行形成[定稿包](prompts/README.md)与[审阅说明](PROMPT_MIGRATION_REVIEW.md)，不表示已完成代码迁移。

已确认首版不启用标准答案纠错反馈，沿用 v24 的 Parent 轨迹复用方式：Parent 执行结束后的评分与轨迹用于诊断；产生 Candidate 后只执行 Candidate，Gate 复用原 Parent 结果进行比较。模块职责、严格成功数 Gate、Memory 核验与发布规则保持 v24 语义；表格 Actor、评分和领域事实需单独适配验证。

标记约定：保留表示方法语义保持；替换表示领域实现或说明需要改变；适配表示在保持职责的前提下调整字段、引用及保存方式。下列待办仍保留为代码集成验收项；Prompt 文本及构造案例的完成情况见独立审阅说明，不将文本定稿误记为运行验收通过。

**一、先固定不可混淆的方法边界**

- Grouping 组织比较，不诊断根因、不提出修改。
- Diagnosis 只基于本批当前证据提出 Original Plan，不读取历史 Memory。
- Preconditioner 综合 Knowledge Only 历史视图、当前相关证据、Parent 与执行条件调整 Original Updates 的方向、范围和协调关系；保留历史经验的核心作用，也允许无历史支持时纠正具体计划缺陷，不直接编辑 Skill。
- Editor 实现 Effective Plan；依据引用不等于额外证据输入，Checks 也不是新增行为指令。
- Gate 用无评分反馈的 Parent／Candidate 完整任务配对作确定性决策，复用诊断所用的完整 Parent 成绩，不增加单元格正确率的接受条件。
- Replay 学习实际 Skill 修改与观察行为的关系，不能把预期修改写成已经实施的效果。
- Verifier 筛查明显且重要的事实错误，不进行全面事实证明或因果审计。
- Repair 只处理被授权 Knowledge 项；修复后不增加第二次独立语义核验。
- Memory 保持供 Preconditioner／Replay 使用的知识视图，不直接追加到 Actor Prompt。

**二、实际生效的 Prompt 清单**

v24 保留了多个历史资源文件，但 rc1 并不调用所有文件。迁移从下列实际生效文本和组合方式开始，不机械复制全部历史 Prompt。

| 模块 | v24 生效资源或组合 | v25 处理 |
|---|---|---|
| Grouping | `prompts/v23/grouping_prompt.md`＋执行上下文＋通用输出校验反馈 | 保留分组规则，替换执行证据和领域说明 |
| Diagnosis | `prompts/v23_5/diagnosis_prompt_feedback.md`＋执行上下文 | 保留 Plan 和决策语义，替换领域限制与引用说明 |
| Preconditioner | `prompts/v23_5/preconditioner_knowledge_only_prompt_feedback.md`＋`knowledge_only_view_prompt.md`＋执行上下文 | 保留 D/S/C、KEEP／撤回／补丁约束，替换领域事实 |
| Editor | `prompts/v23_5/editor_prompt_feedback.md`＋执行上下文 | 保留补丁和职责，替换 `<action>` 示例 |
| Replay | `prompts/v23_5/replay_knowledge_only_prompt_feedback.md`＋执行上下文＋Knowledge Only 说明 | 保留实际修改与行为学习，替换尝试及结果语义 |
| Verifier | `prompts/v23_5/knowledge_verifier_prompt.md`＋通用输出校验反馈 | 保留有限核验范围，替换菜单和可见物体相关说明 |
| Repair | `prompts/v23_5/knowledge_repair_prompt.md`＋通用输出校验反馈 | 保留定点修复，替换菜单及领域事实解释 |
| 共享上下文 | `prompts/v23/execution_context.md`，由 `context.py` 填入 Actor 条件 | 全部改为实际 SpreadsheetBench 协议 |
| Knowledge Only 视图 | `prompts/v23_5/knowledge_only_view_prompt.md` | 保留历史引用边界，去掉动作菜单领域措辞 |

表中的 Prompt 路径均相对于 `src/skill_evolution/v24/benchmarks/alfworld/`。新 Prompt 应使用明确的 v25 名称，并更新资源选择代码；不能在更换内容后继续声称与 v23.5 原文等价。

**三、逐模块输入输出与迁移要求**

| 模块 | v25 输入 | 输出与职责保持 | 需要替换或适配 | 关键验收 |
|---|---|---|---|---|
| Actor | 指令、工作簿预览、类型、答案区域、当前 Skill、允许的历史反馈 | 提交本题结果工作簿；不参与方法决策 | Python 生成、路径绑定、执行、预算及运行反馈 | 所有阶段首次有效输出后结束；不接收答案对照反馈 |
| Facts／执行上下文 | 实际请求、代码尝试、产物、评分视图、配置 | 提供可定位的真实事实及 Actor 能力说明 | 删除动作候选、环境合法性、最近两步与单次 reset 约束 | 没有执行的响应不记成执行；未来评分不成为当时可见信息 |
| Grouping | 全部 Parent（P）允许证据、事后评分、Parent Skill | `groups`；每次执行恰好归入一组 | 删除 `command_sets`，将决策点改成代码选择与修正机会 | 不按成败机械分组；单例合法；不输出根因或更新 |
| Diagnosis | Grouping＋同批 Parent 事实 | `decision/reason/plan`；Plan 保持 `goal/updates/checks` | 表格范围、代码、运行反馈、事后评分及 P 引用 | 保留决策含义；不把事后错误坐标当作 Actor 已知信息 |
| Preconditioner | Parent、Original Plan、用于原计划引用核对与计划审查的当前执行、全部活跃 Knowledge（不提供 Grouping 内容） | `adjustments/checks`；D/S/C 调整 Original Updates | 表格适用条件、历史知识与当前证据的对应关系 | 每个 Original Update 恰好一项；保持方向、范围与协调职责 |
| Editor | Parent、Effective Plan、Actor 协议 | `patch/reason`；生成 Skill 补丁 | Python 输出协议示例、输入能力说明 | 不写逐题程序；不添加 Plan 没有授权的策略 |
| 配对与 Gate | 相同任务的完整 Parent（P）／Candidate（Q）结果与条件 | 严格成功数 ACCEPT／RETAIN | 工作簿输入、任务 ID、反馈权限及评分条件比较 | 15 题完整配对；原样复用 Parent，不选择性重跑 |
| Replay | Parent、实际 Diff、Plan、全部当前 P/Q 配对、Knowledge Only 历史 | `entries`，每项包含 `revises/knowledge` | 对比实际代码行为与事后结果，保留尝试计数 | 看完全部配对；同一 P 引用贯穿诊断和比较；RETAIN 也可学习 |
| Knowledge 证据提取 | Replay 引用及必要的已归档来源 | 按精确引用提取事实，保持引用身份和时间范围 | 替换菜单池与局部菜单映射 | 不扩展到未引用的邻近事件；摘录标明缺失和截断 |
| Verifier | 新增／变化 Knowledge、上下文、引用原始记录 | `results`，每项 `target/verdict/issues` | 工作表、代码、尝试、评分和可见信息事实 | `SUPPORTED` 仅表示未发现明显重要错误；缺失证据本身不变成 CONFLICT |
| Repair | CONFLICT 指定项、issues、限定原始记录 | `changes`，每项 `target/knowledge` | 表格事实的最小修复与引用 | 不修改其他项；保留有效比较；必要删除仍满足 Memory 结构 |
| Memory 视图与提交 | 通过既有检查的候选经验、当前归档来源 | 多 Knowledge 条目、整条替换及知识视图 | 领域来源存取及引用说明 | 未被替换的条目保留；修订不得隐式丢失需保留的历史内容 |
| 编排／恢复／最终评估 | 固定配置、批次、Parent／Candidate 记录、最终已发布 Skill | 既有方法模块顺序、Parent 复用、停止及发布逻辑 | 表格 Actor 调用、完成性及计数 | 已完成记录复用；不额外重跑 Parent；Test 不学习 |

**四、各 Prompt 的具体修改清单**

**Grouping**

- [ ] 保留按具体共同决策问题分组、每个执行恰好一组、保留重要差异及成功反例的要求。
- [ ] 将 `before/action/after` 的解释改为实际请求可见信息、代码方案、执行结果及实际反馈；不得假设已有逐行程序轨迹。
- [ ] 删除“仅过滤 help”“动作候选顺序”“环境动作是否合法”等说明。
- [ ] 使用表头判断、工作表选择、范围确定等例子说明可比较问题，但明确它们不是固定分类，不要求每批凑齐类别。
- [ ] 验证只产出比较结构，不把“评分失败”直接转成“需要加强 Skill”。
- [ ] 分组使用 Parent P 轨迹与事后结果，区分代码当时可见信息与评分器在执行结束后发现的问题。

**Diagnosis**

- [ ] 保留“缺少指导、已有指导未遵守、能力限制、技术故障和不确定变化”的区分。
- [ ] 删除位置访问、获取／变换／放置、inventory／look 等实例及动作假设。保留其背后的方法原则：更新必须基于 Actor 可用信息，作用范围与保留条件必须明确。
- [ ] 以任务字段、预览、实际程序和结果为证据；工作簿可被程序读取不代表模型提前看见全部内容。
- [ ] 示例应体现可迁移的行为要求，例如按可检查的表头确定数据起始范围；避免固定第三行、固定某题工作表名或答案值。
- [ ] 保留单一批次 Plan、原有 Updates／Checks 结构和直接证据要求。不要增加问题清单、原因分类分数或逐题诊断报告。
- [ ] Diagnosis v5 仅保留 `revise` / `no_change`：允许多个有依据的独立 Update 和待验证修复假设；没有可执行修订时返回 no_change，并在 reason 说明关键证据缺口，不自动取证。
- [ ] 每条 Update 仅包含必要变化；Plan 检查重复、冲突与依赖；Checks 区分行为采用、目标问题变化和有效行为保留。
- [ ] Plan 的直接证据指向 P；可以基于事后评分诊断，但更新中的触发条件不能要求 Actor 获得评分器错误坐标。

**Preconditioner**

- [ ] 保留方向 D、范围 S、协调 C 的含义；不能迁移成根据 hard 或单元格正确率计算新的学习率。
- [ ] 保留 Original Goal、ID 和原文冻结，以及 KEEP、补丁修改、整条撤回的语义；不新增 Update ID 或结构拆并。
- [ ] 将“观察历史与物体粒度”替换为表格结构、可读范围、程序执行方式、公式条件与实际反馈；只能使用输入已有信息。
- [ ] 主动利用历史 Knowledge 揭示缺陷、指导修正或发展合理方案，同时允许依当前证据与执行条件纠正具体计划问题；不划分互斥类别，不重建 Diagnosis。不要求重读历史原始工作簿，历史证据 ID 不能被扩展成邻近事件。
- [ ] 保留“联合修改不能自动拆成单条因果效果”“保留改善和退化”“理由中的条件必须写入实际更新文本”等规则。
- [ ] 全部 KEEP 仍进入 Editor；全部合法撤回才无 Effective Plan。格式错误或语义冲突不能被包装成成功 KEEP。
- [ ] 核对历史经验与当前 P 的执行条件；历史协议未提供的细节保持未知，不推断 Actor 具有额外评分反馈能力。

**Editor**

- [ ] 保留仅实现 Effective Plan、精确无行号补丁、原子应用和无模糊匹配规则。
- [ ] 用单个 Python 代码块及执行器路径绑定的作用范围替换 `<action>` 中合法命令的示例。示例不得引入新的通用算法或库使用策略。
- [ ] 明确 Editor 修改的是 Skill 文本，不是 `solution.py`，也不是 Actor 固定 Prompt、评分器或程序运行预算。
- [ ] 保持非空补丁、空字符串、null 三种输出语义。null 表示实现阻塞，不触发无限回送 Preconditioner。
- [ ] 不自动修正初始 Skill 的其他问题；仅在 Effective Plan 要求下修改相关内容。
- [ ] 执行上下文统一说明 Actor 无评分反馈；不能擅自添加“等待评分器指出错误”等不可执行的必要步骤。

**Replay**

- [ ] 保留一次 Replay 处理本批实际修改及全部已核对配对，不改成每题分别学习再合并的新流程。
- [ ] 删除动作菜单与执行动作数的专属语义，分别提供代码尝试数、实际执行数、模型请求数及评分。
- [ ] 以完整配对清单组织分析，不将 P1 与 Q1 的外形或相同尝试序号当作配对／相同决策状态的证明。
- [ ] 保留实际 Diff 与预期 Plan 的区分，表格评分差异本身不证明某条 Skill 的因果贡献。
- [ ] 正确解释 hard 持平、单元格正确率上升，以及成功但尝试更多等情况；这些结果可形成经验，不改变 Gate。
- [ ] 保留每项 Knowledge 自己的证据、整条 MemoryEntry 替换、保留有效历史比较和限定语的要求。
- [ ] 条目证据的有序并集仍需实际 Diff 与执行来源；不以一项的证据替其他项提供支持。`entries: []` 仍是合法无更新。
- [ ] `runs/pairs` 使用原 Parent P 和新 Candidate Q；不新增独立学习执行字段。
- [ ] 核验 Plan、Gate、Replay 引用的是同一 Parent 记录；保留实际 run_id 和任务身份，不以重新编号替换原证据。

**Verifier 与 Repair**

- [ ] Verifier 目标选择沿用新增／变化项筛查；修订条目中逐字逐字段不变的旧项按现有匹配规则保留，不新增“全量重审所有历史”的步骤。
- [ ] 替换共享动作菜单解析说明。证据来自实际代码尝试、输入可见视图、产物及评分视图，不能只修改自然语言而继续调用菜单验证器。
- [ ] 将明显错误例子改为工作表／单元格身份错误、代码尝试归属错误、结果反转、计数错误、把事后评分当作此前反馈、把未执行分支说成已经执行等。
- [ ] `SUPPORTED` 保留“未发现明显重要错误”的有限含义；不得扩展为证明经验普适或每句都有充分证据。
- [ ] 缺失某段代码内部轨迹不能单独构成 CONFLICT；已有记录明确反驳重要说法才提出问题。
- [ ] Repair 只处理指定位置，保留不受影响事实与限定语。Verifier 的转述不是证据本身；若反馈不成立，可以保持原项。
- [ ] 允许在现有结构约束下删除无法保留的项，不自动生成填充经验。修复后只做结构、引用与合并检查，不增加第二次语义核验。
- [ ] 依据实际请求区分运行反馈与评分器的事后结果；不能把方法模块读到的错误坐标描述为 Actor 看过。

**共享上下文与输出反馈**

设计依据已形成：[共享执行上下文定稿与参数推荐](SHARED_EXECUTION_CONTEXT.md)。以下条目仍是实现验收项，不能将文档定稿视为代码已完成。

- [ ] 执行上下文由实际 Actor 配置生成：消息、工具、库、历史、反馈、预算、停止及评分时机。不得手工维护与运行配置不一致的描述。
- [ ] 移除 ALFWorld 环境状态及最近两步条件，明确模型、生成程序和评分器各自的可见范围。
- [ ] 落实完整历史、剩余代码轮数、首次有效产物停止和提交后评分；验证后续评分无法重新打开 Actor。
- [ ] 总预览生成后检查 100,000 字符上限，超限在 Actor 请求前报错、不截断继续；覆盖恰好等于上限和超过上限的边界。
- [ ] 错误详情仅保留前 3,000 字符；统一每表预览、单元格文本与评分摘录上限，截断标记不替代准确计数。
- [ ] 按实际截止时间限制请求及执行，恢复不重置预算；首版无自动重算的条件进入 Actor 说明和评分验收。
- [ ] 方法输出的 JSON／补丁／引用错误可在原预算内返回错误模块；保存记录损坏、输入故障、评分器错误不伪装成模型输出错误。
- [ ] 合法 `no_change`、`needs_revision` 等语义结果不因不满意而重新采样。Diagnosis v5 不接受旧 need_evidence 标签，旧归档按原版本校验。
- [ ] 清理硬编码的旧 Prompt 目录及版本选择条件，逐个确认实际渲染资源。没有生效的历史 Prompt 不必一起扩写。

**五、领域校验与代码迁移清单**

以下是待改的职责位置，不是要求重构 v24。正式实现应在独立 v25 中完成，rc1 保持原样。

| 当前职责位置 | 迁移要求 | 不能遗漏的路径 |
|---|---|---|
| `benchmark.py`、`benchmarks/alfworld/adapter.py` | 保留显式绑定方式；建立 SpreadsheetBench 适配器 | 配置校验、资源、事实、Actor、Gate、最终评估全部显式路由 |
| `benchmarks/alfworld/runtime.py` 与 `actor/` | 建立表格执行器和模型调用封装 | 正常运行、有限错误反馈、超时、产物保存、完成性检查 |
| `benchmarks/alfworld/facts.py` | 从代码尝试及评分构造事实 | 初始输入、未执行响应、执行异常、评分完成、技术中断 |
| `plan_fields`、`auxiliary_references`、`validate_execution_source` | 移除 `command_sets` 的强制形状；保留实际来源校验 | Preconditioner 输入、Memory 来源存取、恢复重读 |
| `contracts/diagnosis.py`、`contracts/grouping.py` 等 | 检查 P/Q 引用语法与 `steps` 隐含含义 | Plan 直接证据、分组成员、引用选择整次 Parent 执行 |
| `evidence_contracts_replay.py`、`evidence_replay_view.py` 等 | 表格运行配对与当前结果视图 | 同任务同输入、独立起点、双方无评分反馈、P/Q 历史身份 |
| `evidence_knowledge_evidence.py` 与核心 `knowledge_evidence.py` | 替换菜单提取、压缩及还原；继续按引用取证 | Verifier 原始输入、Repair 限定输入、历史归档读取 |
| `contracts/memory.py`、`contracts/memory_view.py` | 更换领域来源结构，保留知识视图和整条修订语义 | 写入、读取、覆盖修订、引用重定位及空 Memory |
| `resources.py`、`prompts.py`、`output_feedback.py` | 更新实际使用的资源和校验入口 | 带反馈 Prompt、上下文插值、已保存请求恢复 |
| `evolution.py` | 适配 Parent／Candidate 两组调用、完成记录及成本读取 | 原样复用 Parent；no_change 不执行 Candidate／Gate；发布前后中断及工作线程绑定 |
| `evaluation.py`、适配器评估模块 | 将 `won`、动作步数等读取改为表格结果语义 | 最终已发布 Skill、280 Test、失败分母、技术未完成状态 |
| `baseline.py`、`config.py`、`cli.py` | 新基线准备与 v25 配置 | 不再读取 ALFWorld 环境、旧任务清单或原实验初始化路径 |

现有证据注册表中的操作应逐组迁移，不能仅更新 `build_facts`：

| 现有操作组 | v25 对应职责 |
|---|---|
| `contracts.grouping.validate_grouping`、`contracts.diagnosis.diagnosis_input`、`contracts.preconditioner.preconditioner_input` | 构造并检查当前执行事实、分组、Plan 选取的执行 |
| `contracts.memory.run_references`、`run_menus`、`validate_run`、`_view` | 运行引用、记录有效性、Memory 来源视图；删除菜单语义并调整调用者 |
| `contracts.replay.verify_pair`、`build_replay_from_editor`、`validate_payload`、`replay.validate_bundle` | 检查真实 Skill 修改和表格任务配对，建立 Replay 输入 |
| `contracts.replay_view._historical_pairs`、`_current_pairs`、`model_input`、`replay_view.model_input` | 当前配对及历史边界；首版仅启用已选择的 Knowledge Only 路径 |
| `knowledge_evidence.extract`、`build_input`、`menu_references`、`check_sources`、`compact`、`restore`、`build_repair_input` | 精确证据恢复、输入视图及定点修复；去除菜单池假设 |
| `contracts.memory_view.compact_memory` | 多 Knowledge 输入投影与来源保存，明确模型不直接读取历史原始运行 |

2026-10-28 补充：原迁移保留了配对校验，但遗漏 v24 模型视图中的 pairs 前置及 Parent/Candidate 邻接。现通过独立的 `v25_replay_pairs_knowledge_only_v2` 输入视图恢复；原始 bundle 与旧视图 v1 不变。详见 [布局恢复与归档兼容](REPLAY_PAIRED_INPUT.md)。

旧版契约名称有时只表示未变的结构语义，但当前代码也有 `diagnosis_version='v23_5'` 和 `resource('v23_5/...')` 等实际分支。迁移时逐一判断，不能把所有旧名称都当作无影响的标签。

**六、方法控制流验收清单**

完整路径为：Parent（P）执行并评分 → Grouping → Diagnosis → Preconditioner → Editor → Candidate（Q）执行并评分 → Gate（复用 P 与 Q）→ Replay → Verifier／必要时 Repair → 发布。所有 Actor 都不接收标准答案纠错反馈；本轮统计两组执行，复用 P 不产生额外调用。

| 分支 | 必须保持的结果 |
|---|---|
| Diagnosis `no_change` | 沿用 Parent 和 Memory，不执行 Candidate／Gate／Replay；按配置决定是否继续下批 |
| Diagnosis v5 无法形成有依据的修订 | 返回 `no_change`，reason 说明关键缺口；不自动补证或因不满意重新请求 |
| Preconditioner 全部 KEEP | 仍有 Effective Plan，继续 Editor |
| Preconditioner 全部合法撤回 | 无 Effective Plan；发布 no_change，保留现有 Parent／Memory |
| Editor 空补丁 | no_change，不伪造一次 Candidate 配对 |
| Editor null 补丁 | needs_revision，保存并停止，不自动改变原 Plan |
| Editor 形成 Candidate | 仅执行新 Candidate；使用已保存的同批完整 Parent 结果构造配对 |
| Parent 已完成、Candidate 未完成 | 恢复时复用 Parent；完成剩余 Candidate，不重新抽样 Parent |
| Parent 结果或配置不一致 | 停止检查；不择优重跑或用其他轮次的同题结果替代 |
| Candidate hard 更高 | ACCEPT；仍先完成 Replay 与经验发布流程 |
| Candidate hard 持平或更低 | RETAIN；仍允许从完整配对学习并发布经验 |
| Replay `entries: []` | 无新增知识；按原发布流程正常完成，不能强迫生成经验 |
| Verifier 有 CONFLICT | 一次针对授权目标的 Repair 阶段；请求层有限重试与语义阶段次数分开计 |
| Repair 结构不合法 | 原规则下处理校验错误；不得丢弃错误后发布其他部分 |
| 技术故障或进程中断 | 保存失败阶段；不当作正常任务失败凑齐批次 |
| 评分完成但标记未写入 | 恢复可从完整记录重建完成标记，不能重新生成更好的答案 |
| 发布前／后中断 | 恢复后 Skill、Memory 与轮次状态一致，不重复提交 |
| 完成后 resume | 不新增模型请求或程序执行 |

**七、Prompt 审阅与离线验收方式**

本次完整 Prompt 定稿及审阅说明已给出：原职责与输出契约、保留段落、领域替换段落、修改理由、实际输入示例，以及该模块不能承担的工作。正文使用英语以延续现有模型调用习惯，审阅说明使用中文。

不要求 SpreadsheetBench 与 ALFWorld 的模型消息逐字相同。验收分别检查方法规则保持、领域事实准确、输入信息与引用可追溯，以及 Prompt 描述与实际执行协议一致。

- [ ] 复用 Actor／证据协议中的表头错位贯穿案例；附一例 Parent 已成功且无需修改的情况。
- [ ] 配对 hard 持平而单元格正确率提升：Gate 必须 RETAIN，Replay 可以记录局部改善。
- [ ] 相同 P/Q 编号但任务 ID 不同：必须拒绝错误配对。
- [ ] 代码写了某分支但没有执行记录：不能标记为已发生行为。
- [ ] 一条 Knowledge 把事后评分说成 Actor 当时收到的反馈：已有请求记录反驳时 Verifier 应报错；真实运行异常反馈不得误报为答案纠错。
- [ ] 只有部分预览或内部执行信息缺失：不能仅因此把合理限定的经验判为事实冲突。
- [ ] 历史引用保留完整前缀；Knowledge Only 输入不意外展开历史原文。
- [ ] 修订条目保留有效旧知识；Repair 不影响非授权项，且没有第二次独立语义调用。
- [ ] 格式错误、保存记录错误、正常代码失败、服务故障分别走正确路径。
- [ ] 每条输入构造／验证／保存／恢复路径都使用 SpreadsheetBench 适配器；隔离环境下不加载 ALFWorld 模块。
- [ ] 15 题一批的输入大小真实测量，超限明确报告；不为了装入上下文擅自删题、重分批或缩减关键证据。
- [ ] Parent／Candidate 的输出目录、模型会话、计数和恢复标记独立；完整分支统计 30 次任务执行，正常提前结束分支不强制补齐。
- [ ] Parent、Candidate、Test 的任何 Actor 消息都不包含评分器纠错信息；事后评分正常交给优化模块，Gate 使用原 Parent 结果。
- [ ] 在已确认的六次请求尝试、300 秒 API 上限、600 秒程序／任务预算下检查计数及停止，不因 Parent 复用而增加预算。

这些是离线验收目标，不构成真实运行指令。完整 Prompt 已定稿，后续进入代码迁移；首批 15 题的真实验证仍需单独安排。

**八、源码定位**

- [rc1 方法与预算配置](../../../experiments/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/config/campaign.json)
- [v24 Prompt 资源目录](../../../src/skill_evolution/v24/benchmarks/alfworld/prompts/)
- [证据注册表](../../../src/skill_evolution/v24/benchmarks/alfworld/evidence_registry.json)
- [方法编排](../../../src/skill_evolution/v24/evolution.py)与[输出校验反馈](../../../src/skill_evolution/v24/output_feedback.py)
- [Preconditioner](../../../src/skill_evolution/v24/preconditioner.py)、[Editor](../../../src/skill_evolution/v24/editor.py)、[Replay](../../../src/skill_evolution/v24/replay.py)
- [Knowledge 目标选择](../../../src/skill_evolution/v24/knowledge_evidence.py)与[核验修复流程](../../../src/skill_evolution/v24/knowledge_review.py)
- [确定性 Gate](../../../src/skill_evolution/v24/contracts/gate.py)与[最终评估](../../../src/skill_evolution/v24/evaluation.py)

上述定位用于说明迁移职责。实施时还应将实际修改与 rc1 保存代码对照，避免把工作区随后发生的改动混入 v25 起点。

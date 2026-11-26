# V26 OfficeQA：继承范围与基线核对

记录日期：2026-10-28（Asia/Shanghai）。范围：实现步骤 1，确定继承来源及适配边界。

**决定：以本次快照中的 V25 工作区源码作为 V26 工程底稿和方法语义基线，以 V24 核对共同机制；OfficeQA 执行部分采用已经对齐的公共 Actor。** 不以旧 RC1、某次历史实验配置或滚动更新的 README 代替实际源码。V26 保持现有进化机制，替换 benchmark 相关的事实、证据、Prompt 和接口。

本文件记录设计选择，不是可执行配置。V26 源码、OfficeQA 方法 Prompt 和完整接入尚未实现；本次没有调用模型或启动实验，也没有修改 V24、V25 或 OfficeQA 运行代码。

## 1. 可复核的版本依据

| 项目 | 本次采用的依据 |
|---|---|
| 仓库 HEAD | `5568c3b9ba377cb151476aeeefd3ab22f0041cda` |
| 主底稿 | `src/skill_evolution/v25/` 的本次工作区内容；该目录尚未被 Git 跟踪，HEAD 不能单独标识它 |
| 对照底稿 | `src/skill_evolution/v24/` 的本次工作区内容；包含本地修改及额外的 `verifier_retry.py` |
| 公共 Actor | `src/adapters/officeqa/` 的本次工作区内容及 `prepared_v2/execution.json` |
| OfficeQA 执行标识 | `officeqa_skilladam_aligned_v2`；HTTP 重试策略 `six_attempts_temporary_format_feedback_v1` |
| 上游基准 | SkillOpt `7da46ae693ee0329b80225c0128a37d65db10e9e`；SkillAdam `b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1` |
| 精确标识 | [基线清单](../../../artifacts/methods/v26/inheritance_20261028_001/baseline_manifest.json)：时间、Git 状态、逐文件 SHA-256、字节数、可静态提取的常量及核心差异索引 |
| 可恢复原文 | [源码快照](../../../artifacts/methods/v26/inheritance_20261028_001/source_snapshot.tar.gz)：196 个文件，含两版方法源码及领域资源、OfficeQA 适配源码、执行配置和 V25 环境声明 |

快照不含数据语料、凭据、实验输出或已安装依赖，不是一个可以直接启动的完整环境。上游提交记录说明来源，不意味着本地安装包和上游工作区都无补丁。OfficeQA 环境沿用已有[对齐报告](../../benchmarks/officeqa/ALIGNMENT_V2.md)，本次没有重新认证依赖安装或数据集。

比较 42 个非 benchmark Python 路径时，替换版本名称后，15 个文件文本一致、23 个不同、V24/V25 各独有 2 个。该检查用于定位差异，不证明语义等价；下面的决定来自对具体流程、契约、资源选择和恢复代码的核对。

## 2. 直接继承的职责、契约与执行关系

“直接继承”指方法职责和控制语义，不表示把所有文件逐字复制。现有部分核心文件仍直接引用 `attempts`、程序执行计数等领域结构，必须在适配阶段处理。

| 模块 | V26 继承的职责与输入边界 | 输出和执行契约 | 需替换的 OfficeQA 内容 |
|---|---|---|---|
| Grouping | 根据当前 Parent 执行的具体共同决策问题组织比较；不诊断、不提出修改；不读取 Memory | `groups`；每次执行恰好归入一组，允许单例；组含 `group_id/members/decision_problem/shared_basis/important_differences` | 问题、来源、消息和工具交互事实，及其证据引用；不沿用代码尝试或动作菜单解释 |
| Diagnosis | 使用 Parent、当前 runs、Grouping，为整批产生一个初始 Plan；区分已有规则未遵循、规则缺陷、技术问题及不确定性；不读取历史 Memory | 采用 V25 当前 `revise/no_change`；`decision/reason/plan`；Plan 为 `goal/updates/checks`；每条 Update 需要直接执行证据，可有多条独立且有依据的修订 | 文档问答中的行为与任务要求，评分含义和可观察边界 |
| Preconditioner | 审查并调整 Original Updates，综合历史 Knowledge、当前引用证据、Parent 和执行条件；可纠正有具体依据的计划缺陷；不重新做 Diagnosis | 模型输入 `parent/plan/runs/memory`，Grouping 只留在内部归档和编译器；`adjustments/checks`，保留 D/S/C、KEEP、撤回、补丁及原 ID/Goal 约束；全部 KEEP 仍继续 Editor | OfficeQA 证据的引用解析与执行条件；不改变历史 Knowledge 的使用位置 |
| Editor | 仅将 Effective Plan 落实为 Skill 修改；模型只接收 Parent 与 Effective Plan 及固定执行说明；不展开引用背后的轨迹 | `patch/reason`；非空有效补丁产生 Candidate，空字符串为 `no_change`，`null` 为 `needs_revision` 并停止；严格无行号补丁 | 文档问答领域示例和 Skill 可控制的边界；不能编辑系统工具、评分器或预算 |
| Gate | 对同一批题上的 Parent/Candidate 已核验结果作确定性比较，不交给模型；复用诊断阶段的 Parent 执行 | 保留 `candidate_success > parent_success` 才 ACCEPT，否则 RETAIN；结果必须按题目 ID 配对且覆盖完整 | OfficeQA 分数到布尔成功的映射尚待评分适配步骤定稿，见第 7 节 |
| Replay | 根据实际 Diff、全部当前配对执行和历史 Knowledge 学习编辑—行为关系；不决定 Skill 是否接受 | `entries`，每项含 `revises/knowledge`；每条 Knowledge 含 `text/evidence`；整条 MemoryEntry 替换，当前实际 Diff 与执行证据约束不变；RETAIN 仍可学习 | 问答消息、工具观察、最终答案、评分和实际请求计数；替换工作表、代码执行等说明 |
| Verifier | 对候选 Knowledge 作一次有界的重要事实错误筛查；只使用提供的原始记录与上下文 | `results`，每个目标对应 `SUPPORTED/CONFLICT` 及 issues；SUPPORTED 只表示未发现明显重要错误，不代表完整证明 | 引用的文档、页面、文本窗口、工具调用和 Actor 当时可见信息 |
| Repair | 仅修复被授权的冲突目标，可保持、最小修改或在最终 schema 允许时删除；不重做 Replay | `changes`，逐目标返回 `knowledge` 或 null；程序确定性合并；一次语义 Repair，之后无第二次独立语义核验 | 同上；保留原始证据权威及目标范围限制 |
| Memory / 发布 | 不可变归档、Active 索引、历史引用边界、事实筛查后才提交；Skill 与 Memory 在本轮完成时发布 | `entries_sources_multi_knowledge_v1`；Knowledge Only 模型视图 `memory_knowledge_only_v1`；逐条证据不互相代替 | OfficeQA 原始记录的存储和精确取证；不能直接复用 ALFWorld/SpreadsheetBench 的历史 Memory |

代码依据：[主流程](../../../src/skill_evolution/v25/evolution.py)、[Diagnosis 契约](../../../src/skill_evolution/v25/contracts/diagnosis.py)、[Preconditioner](../../../src/skill_evolution/v25/preconditioner.py)、[Editor](../../../src/skill_evolution/v25/editor.py)、[Gate](../../../src/skill_evolution/v25/contracts/gate.py)、[Knowledge 审查](../../../src/skill_evolution/v25/knowledge_review.py)、[Memory](../../../src/skill_evolution/v25/contracts/memory.py)。

正常更新路径：

```text
冻结本轮 Parent、Memory、任务和配置
  → Parent 执行 → Grouping → Diagnosis → Preconditioner → Editor
  → Candidate 在同一批题上独立执行
  → 核验配对与实际 Diff → Gate → Replay
  → 有待审查目标时 Verifier → 有冲突目标时一次 Repair
  → Memory 提交 → 发布选中的 Skill 和新 Memory → 下一轮
```

保留以下分支：

- Diagnosis `no_change`、Preconditioner 编译后无有效计划、Editor 空补丁：保留原 Skill/Memory，结束本轮；不执行 Candidate/Gate/Replay。
- Preconditioner 全部 KEEP：仍有有效计划，继续 Editor。
- Editor `needs_revision`：停止，不自动回跳到 Diagnosis 或重新采样合法结果。
- ACCEPT/RETAIN 都进入 Replay；RETAIN 保留 Parent，但允许发布经过审查的新 Memory。
- Verifier 没有目标则跳过；无冲突则不执行 Repair。Repair 的格式重试不等于新增语义修复轮次。
- 中途技术错误或结构错误耗尽额度：保留现场并停止，不假造分数、经验或发布完成状态。

## 3. Prompt 与契约来源对应表

下列是**源版本**，不是已注册的 V26 Prompt ID。后续 OfficeQA 文本适配应另设 V26 标识和正文哈希；源 ID 保留在迁移记录中，不应让修改后的 OfficeQA 正文冒用 V25 ID。

| 资源 | V24 当前来源 | V25 当前默认来源 | V26 选择 |
|---|---|---|---|
| Campaign | `v24_campaign_v1` | `v25_campaign_v1` | V25 的冻结与状态转换结构；另设 V26 身份 |
| Grouping | method 标识 `v23`；`v23/grouping_prompt.md` | method 标识 `v25`；`grouping.md`，没有独立 Prompt 版本常量 | 以 V25 正文及哈希为底稿，职责与五字段不变 |
| Diagnosis | `v23_5_diagnosis_v1` | `v25_diagnosis_evidence_scoped_updates_v5` | V25 v5 的修订范围、任务要求与证据边界 |
| Preconditioner Prompt | `v24_preconditioner_knowledge_only_history_and_plan_v3` | `v25_preconditioner_evidence_decision_boundaries_v7` | V25 v7；不采用仍保留的实验版 v8 |
| Preconditioner 契约 | `v23_5_unnumbered_updates_v1` | `v25_explicit_references_v2` | 继承 V25 显式引用语义；领域引用集合重新实现 |
| Editor | `v23_5_editor_v1` | `v25_editor_scope_fidelity_v2` | V25 v2；条件性计划不能被擅自升级为默认规则 |
| 补丁 | `unnumbered_diff_v1` | `unnumbered_diff_v1` | 原补丁应用语义 |
| Replay Prompt | `v23_5_replay_knowledge_only_v1` | `v25_replay_decision_fidelity_v4` | V25 v4 的比较条件、归因边界和历史语义保留 |
| Replay 边界 | `v23_5_replay_boundary_v1` | `v25_replay_boundary_v1` | 继承配对/实际 Diff/Knowledge Only 约束；新领域记录需 V26 适配 |
| Replay 输入视图 | `v23_5_replay_pairs_knowledge_only_v1` | `v25_replay_pairs_knowledge_only_v4` | 继承 pairs 前置及 pair 内 Parent/Candidate 邻接；v4 的代码去重不是通用语义，不能照搬 |
| Verifier / Repair | `v23_5/knowledge_verifier_prompt.md`、`knowledge_repair_prompt.md` | `verifier.md`、`repair.md` | V25 文本底稿；共同策略 `obvious_fact_verifier_targeted_repair_v1`；两者没有独立 Prompt 版本常量，以资源哈希补充标识 |
| 方法输出反馈 | `previous_output_validation_error_v1` | 同左，额外按 `current_execution_timeline_v1` 投影当前领域证据 | 继承反馈策略；OfficeQA 的工具消息时间线另行适配 |

V25 Prompt 的实际目录是 [SpreadsheetBench Prompt 资源](../../../src/skill_evolution/v25/benchmarks/spreadsheetbench/prompts/)，不是文档镜像。`preconditioner.md` 当前对应 v7，旧 v3–v8 资源仍可供归档读取；不能因存在 v8 文件就选它。Replay Prompt v4 与 Replay 输入视图 v4 是两个独立版本字段，不能混为一谈。

Prompt 拼接原则沿用实际代码：Grouping/Diagnosis/Editor 使用模块正文与共享执行上下文；Preconditioner 在此基础上附 Knowledge Only 说明；Replay 为学习正文、执行上下文、Knowledge Only 及选定视图的表示说明；Verifier/Repair 从用户输入的 `context` 读取运行条件。OfficeQA 的执行说明应由同一配置产生，不能把其他 benchmark 的固定额度复制进去。

## 4. 已核实的差异与取舍

| 差异 | V24 | V25 | V26 继承决定 |
|---|---|---|---|
| Diagnosis 合法决定 | `revise/no_change/need_evidence`；后者使流程停止 | 当前 v5 只允许 `revise/no_change`，旧归档兼容 `need_evidence` | 采用 V25 当前行为；不新增补取证阶段 |
| Preconditioner 理由引用 | 裸 ID/原 prose 引用检查 | `Memory/Group/Evidence/Update/Check` 命名空间的显式反引号引用；引用权限按实际可见信息核验 | 采用 V25 显式引用；不能把文件名、页码或任意 URL 当成已授权 Evidence ID |
| Preconditioner 计划语义 | 历史经验与计划审查 v3 | 保留职责，加入任务要求、自检范围和证据判断边界；默认 v7 | 采用 v7，而不是声称所有变化都是 benchmark 名称替换 |
| Editor | 原版正文 | v2 增加条件性建议的范围保真 | 继承 v2 语义，领域例子重写 |
| Replay | 原 Knowledge Only 学习正文和布局 | 学习 Prompt v4；pairs 邻接、相同初始消息共享、精确相同代码去重等版本化视图 | 学习原则采用 v4；保留配对布局。共享初始消息仅在精确可还原时适配，代码去重不迁入 OfficeQA 首版 |
| 时间线证据 | 动作、观察、候选动作表及来源 | 程序尝试、执行反馈、事后评分；当前视图排除临时格式纠错 | OfficeQA 使用正式 assistant/tool 交互和终局结果；保留请求审计但不冒充执行事实。完整序列/独立窗口的可还原方式需专门实现 |
| Actor 外层恢复 | 未找到完整记录时新建后续 attempt 目录 | 复用原 attempt 目录，让内部请求和执行预算延续 | 采用持久恢复原则，实际接 OfficeQA `actor_state.json` 与批次 journal；不得用新目录绕过六次额度 |
| Verifier 额度扩展 | 本地额外实现可为特定授权轮次从 6 增至 9，并维护批准的源码契约链 | 默认禁止运行中 amendments/recoveries，使用冻结预算 | 采用 V25 冻结规则；不将 V24 特定实验的扩额措施作为 V26 默认功能 |
| 外层批次调度 | 有界补充任务，失败后不再补充；输出按输入顺序 | 同类外层行为 | **不继承该调度函数**；使用已确认的 OfficeQA workers=4、完成顺序 journal、整批收尾再报错 |
| 成本统计 | 扫描 action steps 的 transport attempts | 扫描 Actor requests、code attempts、program executions | 重写 OfficeQA 统计，区分模型轮次、HTTP 尝试、工具调用；恢复解析不算新请求，未知 token 用量不能记为零 |
| benchmark 参数校验 | ALFWorld 任务与动作环境 | SpreadsheetBench 400 题、120 题优化池、8×15、Docker、初始 Skill 等约束 | 仅保留通用校验原则；这些具体约束不进入 V26 |

引用依据：[显式引用](../../../src/skill_evolution/v25/explicit_references.py)、[Replay 视图](../../../src/skill_evolution/v25/replay_view.py)、[Spreadsheet 时间线](../../../src/skill_evolution/v25/benchmarks/spreadsheetbench/timeline.py)、[V24 扩额实现](../../../src/skill_evolution/v24/verifier_retry.py)、[OfficeQA 调度](../../../src/adapters/officeqa/execution.py)。

V25 当前将部分领域逻辑写在非 benchmark 文件中，例如 Diagnosis/Plan 直接遍历 `attempts`、`evolution.cost_summary` 读取程序执行字段、Replay 根据 v4 追加代码去重说明。后续不能仅注册一个 Adapter 就宣称接入完成，必须逐个替换这些接点，同时保持上述方法语义。

## 5. 恢复规则的继承边界

| 层次 | V26 采用的规则 | 不应继承或混淆的行为 |
|---|---|---|
| Campaign | 冻结源码/Prompt、任务、Parent、Memory、配置；单写入者锁；身份变化拒绝原地恢复 | 不自动升级旧 V24/V25 campaign，不让当前源码变化绕过契约校验 |
| 方法模块请求 | 按持久 attempt 目录计数；完整已保存响应可重新解析而不发请求；已选中结果重新核验 | 技术失败不改变消息；仅已识别的输出校验错误附最近完整输出和诊断；合法 `no_change/needs_revision` 不重采样 |
| 方法模块预算 | 继承 V25 `config.max_attempts` 的有界预算和恢复不重置机制 | 本步骤不复制某次实验的数值，也不统一三种优化器；V24 特定 Verifier 扩额不是默认预算 |
| OfficeQA Actor 请求 | 每轮六次总尝试，直接 HTTP，无 SDK 内层重试；先持久化消费额度，再发送；保存响应后解析 | 未知请求结果占用额度；第六次响应已保存时可恢复解析，但不能发第七次；临时格式纠错不进入正式工具历史 |
| OfficeQA 工具 | 整个响应结构合法后才执行；已完成且提交的工具不重放 | 工具处于 started 而无提交结果时阻止自动恢复，不能猜测结果或静默重执行 |
| OfficeQA 批次 | `results.jsonl` 按题目 ID 跳过已完成题；持久化成功记录；失败题停止，其余题继续，整批收尾再报错 | 不再套 V25 的失败后停止补充调度，不建立双层题目线程池 |
| Memory / 发布 | 先写不可变 commit，再切换 Active 索引；恢复必须使用完全相同的上下文和结果；完整准备后更新正式 state | 不以未提交文件代表新 Active Memory；RETAIN 不等于丢弃所有本轮经验 |

方法模块的恢复逻辑与公共 Actor 的恢复逻辑是两层独立状态，不互相借用或重置额度。代码依据：[V25 feedback_retry](../../../src/skill_evolution/v25/feedback_retry.py)、[OfficeQA retry](../../../src/adapters/officeqa/retry.py)、[OfficeQA runtime](../../../src/adapters/officeqa/runtime.py)。

## 6. 必须适配的接口清单

以 [Benchmark 协议](../../../src/skill_evolution/v25/benchmark.py) 为工程参考；现有 [GovernActor](../../../src/adapters/officeqa/bridges.py) 只是执行桥接，不是完整方法 Adapter。

| 接口组 | 后续实现内容 | 保持的边界 |
|---|---|---|
| 身份、配置、资源、冻结 | OfficeQA identity、`validate_config/resource/frozen_files/runtime_snapshot` | 独立 V26 身份；引用本次基线，记录后续局部差异 |
| 事实和证据 | `build_facts/parent_text/evidence/plan_fields/auxiliary_references/validate_execution_source/validation_sources` | 可定位、可核验的工具和消息事件；页码与文本行号分别解释；工具可访问不等于模型已阅读 |
| Prompt 上下文 | `actor_fields/execution_context`、七模块领域文本、Knowledge Only 和反馈说明 | 工具权限、预算、可见上下文与真实执行一致；不向固定系统提示中偷偷加入新解题策略 |
| Actor、完成状态、成本 | 批量接入公共 Actor，补全 `check_record/is_complete`，转换现有记录字段 | 生成未完成不是正常零分；24 轮正常耗尽按既有协议处理；模型/Skill/任务身份和预算一致 |
| 配对与 Gate | `build_gate`，按 task ID 建立 Parent/Candidate 配对，定义成功映射 | 完成顺序不能作为配对关系；同一 Parent 记录用于诊断与 Gate，不额外重跑 |
| 评估 | `prepare_evaluation/check_evaluation_record` 和最终 Skill 读取 | 测试集只用于最终评估；不更新 Skill/Memory，不产生训练反馈 |

## 7. 单独配置与尚未冻结的内容

| 项目 | 本步骤结论 |
|---|---|
| Actor 公共参数 | 保留现有 24 模型轮次、取消 8/96 工具上限、workers=4、读超时 300 秒/连接 10 秒、六次总尝试、完成顺序和整批收尾行为；不重建环境 |
| Actor 输出额度 | 每种方法显式配置，不强制统一为 16,384，也不从 V25 的 49,152 等实验数值复制 |
| 模型与路由 | Actor 及各方法模块的模型、endpoint、reasoning、temperature、输出字段和输入容量后续明确；不能把已有 transport 默认值误称为正式模型方案 |
| 优化器参数 | V26 模块输出额度、请求预算等单独冻结；SkillOpt/SkillAdam 优化器重试仍不统一 |
| 初始条件 | Skill 显式文本或 None，不引入 Stage0；不复制 ALFWorld/SpreadsheetBench 初始 Skill 或历史 Memory；OfficeQA 具体初始 Skill 和 Memory 初始化配置仍未定稿 |
| 数据权限 | 50 Train / 24 Val / 172 Test 划分已完成；Val 是否参与优化或只用于选择必须明确，不能继承 V25 的 Train+Val 优化池 |
| 训练规模 | 批大小、任务顺序、随机种子、轮数/epoch、成本上限尚未确定；不复制 8×15 或其他历史批次 |
| Gate 指标映射 | 严格成功数规则继承；此前建议“原生 EM=1 作为成功，F1 仅报告”仍属于待定的 OfficeQA 映射，本步骤没有把它写成已获确认的运行配置 |
| 评分证据权限 | 优化模块可见哪些评分字段、如何处理参考答案及答案泄漏需要在事实适配时明确；Actor 继续不接收评分纠错。不能默认把标准答案喂给全部优化模块 |
| 最终选择 | 验证集角色、最终 Skill 选择规则、重复次数和最终测试计划后续单独冻结 |
| V26 Prompt/视图 ID | 本次只确定源版本；完成正文与证据适配后才注册实际 V26 ID。共享初始消息须有精确还原验收；代码去重不作为 OfficeQA 首版要求 |

## 8. 本步骤完成条件与后续工作

已完成：真实源码比较、源 Prompt/契约登记、方法流程与分支确定、恢复和调度差异核对、直接继承/适配/单独配置划分，以及原文字节快照和逐文件哈希记录。

文档验证只检查快照、哈希、源常量和链接；不把此前 OfficeQA 公共 Actor 的测试成绩当成 V26 完整接入验收。V26 尚无运行代码，本步骤不需要运行训练或模型测试。

下一步是 OfficeQA 事实/证据/评分接口设计和完整 Adapter 接入准备，随后改写七模块领域 Prompt。实现时应对照本文件逐项记录领域变更，保持既有方法职责和控制流程；新的方法性变化需单独说明，不能混入 benchmark 适配。

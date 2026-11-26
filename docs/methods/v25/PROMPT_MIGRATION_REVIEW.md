# V25 Prompt 迁移审阅说明

本次完成英文 Prompt 正文、中文迁移说明及构造案例。入口为 [Prompt 定稿包](prompts/README.md)，案例见 [检查结果](prompt_review/REVIEW_RESULTS.md)。以下保留最初迁移审阅背景；资源现已接入运行代码。2026-10-28 Diagnosis v5 的当前决策和修订原则见 [修改说明](DIAGNOSIS_EVIDENCE_SCOPED_UPDATES.md)，本次未启动实验。

## 1. 底稿与保留范围

以 `v24_alfworld_verified_feedback_001_rc1` 的实际生效路径为底稿，逐字比对确认当前工作区的 8 份方法／Knowledge Only 资源与 rc1 保存代码一致。完整正文从这些资源修改，未采用其他历史分支的 Prompt，也没有重新设计自进化算法。

| 模块 | 保留的正文及契约 | 本次领域替换和理由 | 不能承担的工作／具体输入示例 |
|---|---|---|---|
| Actor | 初始 Skill 使用 SkillOpt 原文；本任务内固定 Skill | 新增三份模板，明确单个完整 Python 程序、原始输入、完整历史、预算、停止及公式条件；这是表格执行协议，不是 ALFWorld 动作模板替换几个名词 | 不直接使用 Memory、标准答案或另一侧记录；[首次消息](prompt_review/actor_initial_messages.json)、[异常后消息](prompt_review/actor_retry_messages.json) |
| Grouping | §2 具体共同决策问题、每执行恰好一组、单例合法；§3 五字段输出 | §1 移除动作候选表，说明初始消息、代码尝试和事后评分；例子改为表头、工作表、范围与运行错误 | 不诊断缺陷、不写 Update；[输入与输出](prompt_review/grouping_example.json) |
| Diagnosis | §2 已有规则与实际行为区分；§3 单批 Goal／Updates／Checks、证据和多行文本；§4 当前 revise／no_change 两种决定；§5 输出字段 | 移除访问位置、物体、获取／变换／放置阶段和 inventory/look；改为输入检查、变换、输出、运行纠错，触发条件必须模型可见或程序可检查 | 不读取 Memory、不把评分失败直接当 Skill 缺陷、不提出“等评分后改错”；[输入与输出](prompt_review/diagnosis_example.json) |
| Preconditioner | §2 历史响应迁移；§3–5 D/S/C、整条 KEEP、冻结 Original、无行号补丁、整体撤回与原子应用；§6–7 引用、Checks 和输出 | 输入删动作候选表，时间顺序改为消息／程序／评分；历史迁移比较工作表、范围、预算和执行条件；保留历史仅有 Knowledge 的限制 | 不重新 Diagnosis，不改 Goal／Original ID，不直接编辑 Skill；全 KEEP 继续 Editor；[输入与输出](prompt_review/preconditioner_example.json) |
| Editor | §1–2 仅实现 Effective Plan、不将 Checks 当指令；§3 精确补丁；§4–5 非空、空串、null 三种结果 | 将 `<action>` 的范围例子换成 Python 围栏与路径绑定；明确修改 Skill，不修改程序文件、固定系统说明或预算 | 不补解题策略、不读引用背后的原始轨迹、不顺便修复初始 Skill 的无关文字；[输入与输出](prompt_review/editor_example.json) |
| Replay | §2–6 全部配对、实际 Diff、联合修改、正反经验、每项独立证据、整条 MemoryEntry 替换；§7 输出契约 | 去掉动作菜单；计数分成代码尝试、程序执行、请求；配对结果用 hard 和单元格指标，明确 Parent 复用与事后评分 | 不决定接受、不把计划当实际修改、不把 hard 持平时的辅助指标提升变成 ACCEPT；[输入与输出](prompt_review/replay_example.json) |
| Verifier | 三项纠错条件、有界扫描、SUPPORTED／CONFLICT 的有限含义、逐字 statement、准确目标覆盖 | 移除菜单解析；核对表名、单元格、尝试、程序执行、实际请求和评分时间，缺少内部轨迹不等于矛盾 | 不全面证明经验、不补取证、不返回修复文本；[输入与输出](prompt_review/verifier_example.json) |
| Repair | 指定目标、最小有效修正、完整目标覆盖、允许原样保持／删除、最终结构要求、仅一次语义阶段 | 移除菜单解析；纠正把未预览误作不存在、把事后评分误作 Actor 反馈、把代码分支误作实际运行等错误 | 不扩展目标、不把 Verifier 转述当原始证据、不增加第二次独立核验；[输入与输出](prompt_review/repair_example.json) |
| Knowledge Only | 原有格式及历史来源权限、不得由单个引用推导邻近记录 | 历史原始记录的领域描述改为预览、程序、日志和评分；继续仅提供已保存 Knowledge | 不展开历史原文、不丢失有效旧知识、不虚构新历史 ID |
| 方法输出校验反馈 | 保留完整原请求＋上次输出＋校验位置／错误、重交完整 JSON 的做法 | 作为独立资源定稿，区别于 Actor 运行反馈 | 不把合法 `no_change`／`needs_revision` 当校验错误；Diagnosis v5 不接受旧决策标签；不让 Actor 收到模块诊断 |

除领域事实解释外，表内保留段落主要沿用 rc1 原文。Grouping、Verifier、Repair 的通用校验反馈说明显式写入正文；原来的行为语义不变。Replay 仍采用“主正文＋执行上下文＋Knowledge Only”的组合，Verifier／Repair 仍从用户输入 `context` 获取运行条件，不重复增加一次上下文注入。

## 2. 需要代码迁移接上的接口

旧动作记录不再冒充表格执行。模型视图采用 `initial/attempts/outcome`；格式失败保留尝试但标 `executed=false`。实际请求、程序、日志、回传反馈分别保存。`P1:1` 是第一次代码尝试，`P1:outcome` 是之后的提交与评分，单元格地址不作为证据引用。

移除模型输入的 `command_sets/commands_ref`。Replay 用户输入从七个字段变为六个；当前配对的结果计数从动作步数变成代码尝试／执行／请求，`hard` 取代动作环境的成功字段。方法结构与接受规则不变，但领域输入验证器必须适配，不能把本 Prompt 直接接到原 ALFWorld Facts 上运行。

完整字段说明和模板组合次序见 [Prompt README](prompts/README.md)。共享上下文只有一份资源正文；[协议说明](SHARED_EXECUTION_CONTEXT.md)中的英文段落与资源保持一致。后续运行代码应从同一配置生成这些值，而不是把案例中的固定值复制到不同模块。

已确认的差异落实如下：错误详情保留前 3,000 字符；完整生成有限预览后检查 100,000 字符，超过则请求前报错；不额外执行公式自动重算，评分使用 `data_only=True` 读取已保存的单元格值。公式没有缓存可能按空值判错，不能因此让 Actor 再修改一次。

## 3. 初始条件与方法不变量

[初始 Skill 副本](prompts/initial_skill.md)与[SkillOpt 原始文件](../../../external/SkillOpt/skillopt/envs/spreadsheetbench/skills/initial.md)逐字相同。其 `openpyxl.save()` 表述保留。新系统说明澄清工具和执行职责，不添加表头识别、聚合、排序等解题策略；构造案例中这些策略来自假定的 Plan，不混入固定 Actor 说明。

Parent 的同一执行既供诊断，也供 Gate 和 Replay；Candidate 独立从原始输入开始。没有额外的学习 Parent，也没有评分反馈版本的 Actor。每批 15 题完整产生 Candidate 时仍是 30 次任务执行。当前案例采用两题缩小输入方便读者逐项检查，另用独立 15 题指标案例检查 Gate 规则；两题案例不能作为正式批次运行。

严格 Gate 不交给 LLM：Candidate 成功数严格更多才 ACCEPT，持平或降低均 RETAIN。RETAIN 仍可学习经验。Diagnosis 的 no_change、合法全部撤回、Editor 空补丁均不制造 Candidate；Diagnosis v5 无法形成合理修订时也返回 no_change 并说明缺口，Editor null 补丁仍按既有语义停止。Verifier 的 SUPPORTED 不扩展成充分证据证明；Repair 只有一次语义阶段，结构校验重试不算新增语义复核。

## 4. 可复核的来源

- [rc1 冻结 Prompt 目录](../../../experiments/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/code/src/skill_evolution/v24/benchmarks/alfworld/prompts/)及[当前 v24 Prompt 目录](../../../src/skill_evolution/v24/benchmarks/alfworld/prompts/)。具体生效文件见[模块清单](MODULE_MIGRATION_CHECKLIST.md)。
- [v24 Preconditioner 消息组合](../../../src/skill_evolution/v24/preconditioner.py)、[Replay 消息组合](../../../src/skill_evolution/v24/replay.py)、[方法校验反馈](../../../src/skill_evolution/v24/output_feedback.py)。
- [v24 严格补丁](../../../src/skill_evolution/v24/unnumbered_patch.py)、[Verifier 输出契约](../../../src/skill_evolution/v24/knowledge_verifier.py)、[Repair 约束](../../../src/skill_evolution/v24/knowledge_repair.py)。

此次只验证设计资源、示例结构及相应边界的预期处理。执行器隔离、工作簿实际读写／评分、请求恢复、完整批次输入容量和模型是否遵循 Prompt，仍须后续实现与离线集成验证。

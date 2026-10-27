# V24 Preconditioner 的历史经验与计划审查定位

工作区版本：Knowledge Only 为 `v24_preconditioner_knowledge_only_history_and_plan_v3`；
历史证据视图为 `v24_preconditioner_history_and_plan_v3`。两种视图的普通与反馈版
Prompt 同步更新。旧 rc1 候选、历史实验和配置保持冻结，不以新加载器静默解释旧结果。

## 职责与依据

Preconditioner 以 Original Updates 为对象，综合相关历史 Knowledge、当前引用证据、
Parent Skill 和 Actor 执行条件，审查和调整方向、范围、强度与协调关系。
利用历史实际编辑及行为响应进行预条件调整，仍是核心作用之一：历史可以揭示当前
Diagnosis 未发现的缺陷、帮助确定修正方式，也可以发展原本合理的方案。

这些依据相互结合，不划分互斥类别，不规定先纠错再使用历史。缺少相关 Memory，
不妨碍纠正有具体依据的事实前提、推理、过度推广、约束强度、执行可行性或协调问题；
必要时可实质调整 D/S/C 或撤回 Update，不再限于局部事实纠错。

所有调整围绕 Original Updates 的问题和要求，不借助 runs 扫描无关问题或重建
Diagnosis。没有充分调整理由时 KEEP；无 Memory 或无历史反例不是独立的 KEEP 理由。
合理但尚未验证的方案可以保留，不为增加修改数而编造缺陷。

## ALFWorld 特有边界

模型输入仍为 `parent`、`plan`、`runs`、`command_sets`、`memory`，不恢复 grouping。
runs 是原计划的引用上下文，也用于审查原要求与历史经验是否适用。

- 命令集合绑定相应的 before/after 状态；某时刻不可用不等于整个任务不可能执行。
  菜单中的候选动作不等于已执行动作，更不等于已完成子目标。未知命令引用不是空菜单。
- 依实际 Actor 协议判断记忆能力：当前配置提供当前观察、动作候选及最近两组动作前
  观察/动作。优化器看到完整轨迹，不意味着 Actor 能访问完整历史、持久笔记或隐藏状态。
  计划不能要求使用不可见的访问历史、物体位置或子目标进度，除非协议支持恢复所需信息。
- 按时间区分动作前信息、所选动作和环境反馈；事后信息不能倒推成动作前已知。
  局部观察或搜索失败不证明物体不存在。
- 不迁入 SpreadsheetBench 的工作簿、公式缓存或程序保存结束规则。

## 历史视图、理由与契约

Knowledge Only 允许使用提供的 Knowledge，但不能宣称重读未提供的历史原始轨迹。
兼容历史证据视图仍按其可见的 Parent、Diff、轨迹及命令集合判断；仅引用实际提供的来源。
不因共享职责原则而扩大任一视图的历史证据权限。

reason 说明具体要求、历史或当前依据、调整理由和不确定性。历史既可揭示缺陷、指导
修正，也可支持发展；混合依据一起解释，不增加类别字段。不强迫无关 Memory 引用，
即使存在 Memory，也允许基于当前证据纠正计划。

内部 Grouping 保留用于上游引用校验；原 Plan 中的 G 编号仅为出处，不是已查阅证据。
D/S/C、每个原 Update 恰好一项、Goal/ID、KEEP/撤回/补丁、adjustments/checks、
Editor/Gate/重试和 Memory 发布机制不变。现有校验没有强制引用 Memory 的限制，无需放宽；
继续验证引用身份、结构与补丁，不声称程序能证明语义正确。

## 验证与运行范围

先完成本地输入、两种历史视图、引用与修改/撤回测试及既有回归，再在新分析目录
单独重放 Preconditioner。只调用该模块，不运行 Actor、Editor 或新完整训练。
原始输入和历史实验保持不变；若使用 V24 迁移来源的历史案例，明确标注其版本来源，
不把它们冒充 V24 已运行的轮次。模型行为效果与本地契约测试分别报告。

- [Knowledge Only 反馈版 Prompt](../../../src/skill_evolution/v24/benchmarks/alfworld/prompts/v23_5/preconditioner_knowledge_only_prompt_feedback.md)
- [输入构造](../../../src/skill_evolution/v24/preconditioner.py)
- [引用校验](../../../src/skill_evolution/v24/update_patch.py)
- [边界测试](../../../tests/skill_evolution/v24/test_preconditioner_context.py)

本地验证：V24 全部 121 项测试通过。旧 rc1 候选 114 个源码和配置文件前后哈希一致，
四份 Prompt 的补丁及输出契约逐字未变。此结果仅验证代码/契约兼容，不代表模型行为有效。

2026-10-26 独立重放已完成：一例 V24 smoke R01（无 Memory），另两例来自 V24
迁移来源 v23.5 的 R03/R06（分别有 2/5 条 Memory）。三例输出均通过现有校验；
共 4 次请求，R06 首次达到输出上限后按原规则重试一次，没有按语义好坏重复采样。
有 Memory 的案例体现了历史与当前计划审查的结合、合理 KEEP 及多 Update 协调；
无 Memory 案例却引入依据不足的菜单顺序搜索策略，仍保留局部可见性和规则优先级问题。
因此不能把结构校验通过或修改数量增加视为语义有效，也未验证 Actor 成功率提升。
旧对照早于 history_primary_v2，且包含既定的 grouping 输入移除，不构成仅比较
v2/v3 Prompt 的因果实验。原始归档和旧冻结版本保持不变，未启动新的完整训练。

逐例依据、局限、请求用量及原始输出索引见
[重放分析](../../../experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/analysis.json)及[材料导航与归档读取](../../../experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/README.md)。
2026-10-27 将完整输入、请求、Memory、日志和源码快照归入 `artifacts/methods/v24/analysis/`，
保留三例四次请求的原记录；这次整理没有运行实验或测试，也没有重算历史校验值。

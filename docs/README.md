# 文档索引

建议按照下面的顺序阅读：

| 顺序 | 文档 | 用途 |
|---:|---|---|
| 1 | [`00_README_FIRST.md`](00_README_FIRST.md) | 学生启动规则、前三天目标与安全底线 |
| 2 | [`01_PROJECT_NARRATIVE.md`](01_PROJECT_NARRATIVE.md) | 核心研究问题、假设、边界与 Go / No-Go |
| 3 | [`05_TAU_BENCH_POLICY_COMPLIANCE.md`](05_TAU_BENCH_POLICY_COMPLIANCE.md) | 区分τ-bench policy、task reward与Process Verifier |
| 4 | [`02_HANDS_ON_TODO.md`](02_HANDS_ON_TODO.md) | 10 天研究型 POC 执行计划 |
| 5 | [`03_PAPERS_AND_CODE_MAP.md`](03_PAPERS_AND_CODE_MAP.md) | 核心论文、代码仓库与阅读问题 |
| 6 | [`04_EXPERIMENT_LOG.md`](04_EXPERIMENT_LOG.md) | 环境、实验、轨迹、Skill 修改与决策记录 |
| 7 | [`05_AUTONOMOUS_GSE.md`](05_AUTONOMOUS_GSE.md) | 三步有界自主Governed Skill Evolution的方法与已完成结果 |
| 8 | [`06_ST_WEBAGENTBENCH_INTERACTIVE.md`](06_ST_WEBAGENTBENCH_INTERACTIVE.md) | 基于隐藏UserScenario的交互式benchmark变体、运行配置与补充指标 |
| 9 | [`V18_SKILL_EVOLUTION_DESIGN.md`](V18_SKILL_EVOLUTION_DESIGN.md) | 基于 v17 四轮实验的 v18 设计：语义保持、Simulator 修复与 DELETE |
| 10 | [`V18_DIAGNOSIS_CONTRACT.md`](V18_DIAGNOSIS_CONTRACT.md) | v18 Diagnosis 三类 gap、删除证据门槛与独立验收契约 |
| 11 | [`V18_DIAGNOSIS_PILOT_REPORT.md`](V18_DIAGNOSIS_PILOT_REPORT.md) | v18 Prompt 首次三组固定输入结果及未解决的语义问题 |
| 12 | [`V18_DIAGNOSIS_V2_PILOT_REPORT.md`](V18_DIAGNOSIS_V2_PILOT_REPORT.md) | Prompt v2 五组固定输入、REPLACE/DELETE 边界与核心语义评分 |

文档属于研究 artifact。实质修改 narrative、policy interpretation、数据、方法或验收条件时，必须在 `04_EXPERIMENT_LOG.md` 的 Decision Log 中说明日期、证据和原因。

v18 第 4 步：[Compiler 契约与 DELETE 离线验证](V18_COMPILER_CONTRACT.md)。

v18 第 5 步：[Editor 与确定性文本应用](V18_EDITOR_CONTRACT.md)。

v18 第 6 步：[完整调度、冻结与恢复](V18_FORMAL_EXPERIMENT.md)。

v18 Diagnosis 统一聚合边界：[v3.2.1 固定输入回归](V18_DIAGNOSIS_V321_AGGREGATION_REPORT.md)。

v18 Diagnosis v3.1：[通用可学习性边界与 6+5 固定输入回归](V18_DIAGNOSIS_V31_REGRESSION_REPORT.md)。

v18 第 7 步：[单轮端到端真实模型 Pilot](V18_END_TO_END_PILOT_REPORT.md)。

v18 Diagnosis v3：[六组固定输入语义回归](V18_DIAGNOSIS_V3_REGRESSION_REPORT.md)。

v18 Benchmark：[Skill-critical Joint Family 冻结准入契约](V18_JOINT_FAMILY_ADMISSION_CONTRACT.md)与[候选机制 shortlist](V18_JOINT_FAMILY_CANDIDATE_MECHANISMS.md)。

[v18 × benchmark v4 正式协议与 run/resume 命令](V18_BENCHMARK_V4_FORMAL_PROTOCOL.md)。

v19 第 1 步：[数据契约与流程边界](V19_DATA_CONTRACT_AND_FLOW.md)及[构造示例与验收映射](V19_DATA_CONTRACT_EXAMPLES.md)。仅完成契约设计，后续实现使用独立 v19 版本，不修改 v18。

v19 第 2 步：[edit 账本与跨轮追踪实现](V19_EDIT_TRACKING.md)。独立的确定性账本、来源/版本校验和历史视图；尚未接入回放或 Memory 模型。

v19 第 3 步：[Candidate Evolution 配对回放](V19_EVOLUTION_REPLAY.md)。完整训练集配对、Parent 复用、私有检查点恢复及 Level-0 学习侧投影；尚未接入归因、Memory 或 campaign。

v19 第 4 步：[edit-level 效果归因](V19_EDIT_ATTRIBUTION.md)。归因 Prompt、完整 edit 覆盖、证据引用与冲突校验及可恢复阶段产物；结构验收不代表因果结论成立，尚未接入 Memory 或 campaign。

v19 第 5 步：[持续记忆的保存、更新和检索](V19_PERSISTENT_MEMORY.md)。不可变完整证据归档、记忆头与保留 Skill 原子提交、当前规则绑定重建及带预算的证据检索；尚未接入 Diagnosis 或 campaign。

v19 第 6 步：[Memory 驱动 Diagnosis 与 Skill 生成](V19_MEMORY_GENERATION.md)。当前经验与历史观察分源引用、逐 edit 显式复查、当前 Parent 重新授权、受限 Editor 与跨轮来源保留；尚未运行真实模型或第 7 步 campaign。

v19 第 7 步：[独立调度、多轮工程验证与 Pilot](V19_CAMPAIGN.md)。独立 run/resume、完整配对、私有 Monitor Gate 和原子记忆提交；真实 Pilot 进展与工程 fixture 结果分开记录。

v19 职责拆分第 1 步：[Current Diagnosis 与 Memory Review 独立契约](V19_SEPARATED_DISCOVERY_REVIEW.md)。当前发现与历史证据状态分离；含严格校验、原始事件访问和稳定 ID，尚未接入 Reconciliation 或新调度。

v19 职责拆分第 2 步：[逐项 Reconciliation 与 v18 Compiler/Editor 适配](V19_RECONCILIATION.md)。完整来源处置、PROPOSE gap 校验、冲突拒绝及 Candidate provenance；尚未切换 campaign。

v19 职责拆分第 3 步：[新闭环、恢复协议与独立 Pilot](V19_SEPARATED_CAMPAIGN.md)。新 CLI 默认拆分流程，独立目录运行；审阅与处置随账本归档并在下一轮检索。

- [v19 轻量 Issue Fusion：契约、覆盖规则与阶段边界](V19_ISSUE_FUSION.md)

- [v19 逐提案 Evidence Review：局部证据、有限补充与恢复](V19_EVIDENCE_REVIEW.md)

- [v19 局部核验与编译闭环](V19_LOCAL_GENERATION.md)：第三步实现、独立单次运行及完整闭环命令。

- [v19 单次 Evidence Review](V19_ONE_PASS_EVIDENCE_REVIEW.md)：确定性证据包、无 MORE_CONTEXT 的执行协议与运行命令。

- [Pair Attribution v19.2](V19_PAIR_ATTRIBUTION.md)：逐 pair 观察、确定性聚合与新旧 Memory 兼容；旧全局 Attribution 保留。

- [v19 run / resume](V19_RUN_RESUME.md)：当前流程统一入口、网络失败自动归档恢复和使用示例。

v20 第 1 步：[最小 Memory 契约与独立边界](V20_MEMORY_CONTRACT.md)及[构造示例与验收映射](V20_MEMORY_EXAMPLES.md)。按问题维护可更新的尝试记录，由 Issue Fusion 直接消费简明 Memory；冻结 v19，尚未接入 v20 Issue Fusion 或开展实验。

v20 第 2 步：[问题 Memory 保存与增量更新](V20_MEMORY_UPDATE.md)。已实现独立存储、稳定问题/尝试身份、部分更新、CAS 提交与恢复。

v20 第 3 步：[直接消费问题 Memory 的 Issue Fusion](V20_ISSUE_FUSION.md)。当前 Findings、问题/尝试简明状态和 Parent 规则在独立只读契约中融合；支持当前问题、已部署方案纠偏和纯历史方向，尚未接入局部 Evidence Review 或真实 campaign。

v20 第 4 步：[局部 Evidence Review 与修改生成](V20_ISSUE_FUSION.md)。已实现问题级证据闭包、局部 Review、独立 v20 编辑计划与 Candidate 生成。

v20 第 5 步：[多轮闭环与离线验证](V20_ISSUE_FUSION.md)。已接入独立 campaign head、可恢复的 Memory/retained Skill 发布，以及 v19 产物的只读结构验证和保守转换。

v20 第 6 步：[独立 Pilot 与匹配对照实验](V20_ISSUE_FUSION.md)。先验证独立 Pilot 的工程闭环，再在相同任务 manifest、seed 和指标规则下运行 v20 Memory 与 no-memory 对照；两者均不把一次运行直接解释为因果结论。

v20 第 7 步（当前）：[冻结 Pilot、Benchmark 适配与统一 run/resume](V20_ISSUE_FUSION.md)。已冻结 benchmark v4 配置，接入真实 round factory、post-generation、train/monitor split 适配器和零模型调用 preflight；真实模型 Pilot 入口已具备但尚未启动。

信用卡 v2 的设计、配置、运行适配器和预检产物已迁移到 [`dataset_8bucket_1200_skill_evlaution`](</Users/didi/Desktop/dataset_8bucket_1200_skill_evlaution/docs/V2_CURRENT_PLUS_MEMORY_DESIGN.md>)，信用卡专用文件不放在本仓库。

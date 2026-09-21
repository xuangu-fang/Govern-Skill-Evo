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

# V24 实验与候选材料导航

[方法总索引](../README.md) · [方法说明](../../../docs/methods/v24/README.md) · [当前实现](../../../src/skill_evolution/v24/README.md) · [测试源码](../../../tests/skill_evolution/v24/)

## 实际完成了什么

截至 2026-10-27 的已有记录，v24 完成了 RC1 离线验收、一次单轮 smoke，以及一次 Preconditioner 独立重放。**没有完成正式六轮训练，没有运行最终 Test。**下面四组是材料分类，不代表四次完整实验；本次文件整理没有新增实验或请求。

| 材料组 | 内容与状态 |
|---|---|
| [alfworld_verified_feedback_001](alfworld_verified_feedback_001/README.md) | v23.5 基线来源说明和来源记录，本目录不是一次新运行 |
| [RC1 候选包](candidates/README.md) | 冻结代码、Prompt、配置、任务划分、测试源码和历史报告；历史离线验收记录 100 项通过，无真实请求或环境执行 |
| [alfworld_rc1_smoke_001](alfworld_rc1_smoke_001/README.md) | 10 个任务分别执行 Parent/Candidate，共 20 个 episode；双方 10/10，Gate 为 RETAIN，发布 2 条 Memory、7 项 Knowledge |
| [Preconditioner 独立重放](analysis/README.md) | 三例、四次模块请求；一例来自 v24 smoke，两例借用 v23.5 R03/R06，没有新增 Actor、Editor 或 Memory 发布 |

## RC1 与当前源码分别保留

smoke 使用 [RC1/code](candidates/v24_alfworld_verified_feedback_001_rc1/code/) 中的冻结实现。当前 `src/skill_evolution/v24/` 后来调整了 Preconditioner 的职责、Prompt 和输入；[独立重放分析](analysis/preconditioner_history_and_plan_v3_20261026_231243/README.md)属于这一阶段，不能用 RC1 的历史验收证明当前 Prompt 的效果。

候选内部 README、documents、candidate.json 和历史报告保留保存时点的内容。“真实实验未启动”属于当时状态；后续单轮 smoke 的结果单独记录。冻结副本中的旧相对链接和两份测试日志的现址，统一见 [候选路径说明](candidates/README.md)。不覆盖冻结版本、不合并原失败与后续成功，也不重新编号尝试。

## 保留结果与必要证据

- smoke 的 [实际配置](alfworld_rc1_smoke_001/config/campaign.json)、[最终保留 Skill](alfworld_rc1_smoke_001/results/final_skill.md)、[原汇总](alfworld_rc1_smoke_001/summary.json)和[逐任务对照](alfworld_rc1_smoke_001/task_comparison.csv)在实验目录。最终 Skill 是初始 Parent，Editor Candidate 未被 Gate 接受。
- smoke 的 Preconditioner 保留 001 超时、002 截断、003 成功，原选择为 003；[Memory 发布摘录](alfworld_rc1_smoke_001/evidence/memory_publication.json)保留已发布条目与普通内容对照，完整 sources 和执行上下文仍在归档。
- 独立重放保留[原分析](analysis/preconditioner_history_and_plan_v3_20261026_231243/analysis.json)、实际 Prompt、旧输出、有效结果、Diff 和必要失败回答。选择仍为 001、001、002；R06 首次截断后第二次成功。合法输出不代表语义正确，也没有验证 Actor 成功率提升。

## 完整运行数据与读取

| 原始材料 | 本机归档 |
|---|---|
| RC1 两份完整测试日志 | [candidates/…/validation/](../../../artifacts/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/validation/) |
| 单轮 smoke 完整输入、调用、轨迹、Memory 和源码快照 | [alfworld_rc1_smoke_001/](../../../artifacts/methods/v24/alfworld_rc1_smoke_001/) |
| Preconditioner 重放整理前的完整 88 个文件 | [analysis/preconditioner_history_and_plan_v3_20261026_231243/](../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/) |
| 原有离线准备及验收输出 | [prepared_candidate_rc1/](../../../artifacts/methods/v24/prepared_candidate_rc1/) · [offline_candidate_rc1/](../../../artifacts/methods/v24/offline_candidate_rc1/) |

这些归档由 Git 忽略。实验目录中的 evidence 和摘要是阅读材料，不是完整可恢复 Campaign；只克隆 Git 不包含原始归档。正式配置保留完整冻结环境材料，因此部分配置仍约 8.4 MB，不将其当作运行日志删除。

重放的 [archive_io.py](analysis/preconditioner_history_and_plan_v3_20261026_231243/archive_io.py)将旧分析路径定位到完整归档，并按原 result.json 读取选中的尝试；历史 summary 中的来源字段保持原文。[run_replay.py](analysis/preconditioner_history_and_plan_v3_20261026_231243/run_replay.py)改为向归档输出，发现已存在 manifest 时仍拒绝重新初始化，不会因整理重置调用额度。smoke 的运行与后续重放来源路径没有变化。

## 与相邻版本的依赖

v24 的基线准备继续读取 [v23.5 正式配置与数据](../v23_5/alfworld_verified_feedback_001/README.md)和原 S1 配置；离线对照还读取旧版源码、测试夹具及历史运行。v24 正常方法执行使用自身适配器，保留资源中的 `v23_5` 名称不表示导入旧版方法代码。

v25 的预算继承检查读取 RC1 的 [config/campaign.json](candidates/v24_alfworld_verified_feedback_001_rc1/config/campaign.json)，迁移文档引用 RC1 冻结 Prompt 和当前 v24 实现。RC1 的 code、config、data、plans 保持原位和原文；v25 源码、实验及其他基线比较材料按各自范围管理，不是本版本运行的前置文件。

## 本次整理的检查范围

2026-10-27 只进行了文件、JSON/Python 语法、链接、路径、忽略规则和依赖的静态检查；没有导入实验模块，没有运行实验、测试或哈希函数。历史测试数字保持其原阶段含义，不能将本次整理描述为重新通过运行验收。没有生成临时迁移清单，也没有执行 Git 暂存、提交或推送。

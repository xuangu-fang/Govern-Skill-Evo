# V24 候选材料导航

[V24 方法说明](../../../../docs/methods/v24/README.md) · [基线来源](../alfworld_verified_feedback_001/README.md) · [单轮真实验证与证据](../alfworld_rc1_smoke_001/README.md)

## RC1 的当前阅读入口

候选为 `v24_alfworld_verified_feedback_001_rc1`。候选内部的 README、documents、配置、代码、Prompt、测试源码和报告保留原文；本页说明后续运行状态与日志现址，不覆盖冻结版本。

历史离线报告记录 100 项通过、0 失败、0 跳过、0 错误。后来的单轮 smoke 已完成：Parent 与 Candidate 均为 10/10，Gate 为 RETAIN，发布 2 条 Memory；完整六轮和最终 Test 未启动。候选内部的“真实实验未启动”及 `candidate.json` 中的 `real_experiments_started=false` 是候选保存时的历史状态。

当前工作区的 Preconditioner 实现和 Prompt 已有后续修改，见 [职责说明](../../../../docs/methods/v24/PRECONDITIONER_ROLE.md)。RC1 代码仍是 smoke 的实际执行版本，不能用当前源码覆盖，也不能将历史验收解释为当前版本重新验收通过。

| 材料 | 当前位置 |
|---|---|
| 冻结实现与协议资源 | [code/](v24_alfworld_verified_feedback_001_rc1/code/) |
| 冻结版使用说明 | [code 内 README](v24_alfworld_verified_feedback_001_rc1/code/src/skill_evolution/v24/README.md) |
| 正式配置：57 个优化任务、六批 | [config/campaign.json](v24_alfworld_verified_feedback_001_rc1/config/campaign.json) |
| 任务划分 | [data/](v24_alfworld_verified_feedback_001_rc1/data/) |
| 单轮计划及对照参数 | [plans/](v24_alfworld_verified_feedback_001_rc1/plans/) |
| 历史候选记录 | [candidate.json](v24_alfworld_verified_feedback_001_rc1/candidate.json) |
| 历史验收结论 | [validation/report.json](v24_alfworld_verified_feedback_001_rc1/validation/report.json) |
| 历史文档、测试源码与验收工具 | [documents/](v24_alfworld_verified_feedback_001_rc1/documents/) · [tests/](v24_alfworld_verified_feedback_001_rc1/tests/) · [tools/](v24_alfworld_verified_feedback_001_rc1/tools/) |
| 完整逐项测试日志 | [tests.xml](../../../../artifacts/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/validation/tests.xml) |
| 完整执行输出 | [console.txt](../../../../artifacts/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/validation/console.txt) |

## 历史路径如何阅读

两份完整日志现位于 `artifacts/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/validation/`，由 Git 忽略。候选根 README、历史验收文档和 `candidate.json` 的文件清单仍记录原来的 `validation/tests.xml`、`validation/console.txt`；请使用上表的归档链接。这份原有文件清单是历史候选记录，不是当前目录的完整性检查结果。

`documents/` 是原文档的冻结副本，其中三个相对链接仍沿用复制前的位置。阅读时使用下列入口，不据这些旧链接重新创建目录或修改冻结文档：

- `documents/README.md` 的“实现与使用说明”：见上表的冻结版使用说明；当前实现另见 [当前源码说明](../../../../src/skill_evolution/v24/README.md)。
- `documents/README.md` 和 `documents/VALIDATION.md` 的“候选材料／候选入口”：使用本页导航；[候选根 README](v24_alfworld_verified_feedback_001_rc1/README.md)保留原始保存时点的说明。
- `code/src/skill_evolution/v24/README.md` 的“后续方案”链接也沿用复制前的位置：冻结版方案见 [documents/NEXT_EXPERIMENTS.md](v24_alfworld_verified_feedback_001_rc1/documents/NEXT_EXPERIMENTS.md)，后续更新见 [当前方案文档](../../../../docs/methods/v24/NEXT_EXPERIMENTS.md)。

仅克隆 Git 可查看配置、代码、报告和保留证据，不包含上述完整日志及原始运行。历史离线对照仍依赖本机 v23.5 档案与旧版测试夹具。

## 后续版本的依赖

v25 的预算继承测试继续读取 RC1 的 `config/campaign.json`；其迁移文档引用 RC1 冻结 Prompt 和当前 v24 源码。v24 的对照读取也使用 `code/` 内的冻结 Prompt。因此 `code/`、`config/`、`data/`、`plans/` 保持原路径和原内容，不合并成当前源码，不移入原始运行归档。

2026-10-27 本批仅归档两份已有测试日志并补充导航；没有运行实验、测试或项目校验入口。

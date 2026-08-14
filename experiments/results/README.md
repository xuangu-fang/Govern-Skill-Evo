# 实验结果目录

体积较大或依赖本机环境的内容，例如逐任务浏览器记录、完整模型输入、数据库快照和运行中间文件，保存在项目根目录的 `artifacts/` 中，不放在这里。

## 快速了解有哪些实验

| 目录 | 实验内容 | 主要结果或用途 |
|---|---|---|
| [`day4_trace2skill/`](day4_trace2skill/) | 从5条航空客服任务记录中总结局部经验，再生成候选 Skill | 选出2条规则写入候选 Skill，另有1条因编辑名额限制未采用 |
| [`day5_schema/`](day5_schema/) | 把10条 τ³ 任务记录转换成统一格式，并分别判断任务成功和一项流程合规规则 | 验证统一数据格式以及任务结果、流程结果分开保存的方式 |
| [`day6_process_verifier/`](day6_process_verifier/) | 逐步把2条、3条、4条、5条规则接入通用过程校验器 | `v04` 是当前覆盖5条规则的完整结果 |
| [`skillopt_searchqa_main200_hard_s42/`](skillopt_searchqa_main200_hard_s42/) | 使用 SkillOpt 在 SearchQA 上连续优化 Skill | 5步中接受3个候选版本；选择评测严格准确率从0.75升至0.80，独立测试从0.90升至0.91 |
| [`autonomous_gse_v01/`](autonomous_gse_v01/) | Autonomous GSE v0.1 三步正式实验的版本化报告 | 最终保留 S1，共87条任务记录、3次 Learner 调用、0条独立 Test |
| [`stweb_suitecrm_poc_v01/`](stweb_suitecrm_poc_v01/) | SuiteCRM 基线对照、两种简单学习方法及受规则约束的候选 S1 | 保存4种方法的18任务对照结果，并从 S0 训练经验生成 S1 |
| [`stweb_suitecrm_poc_v02/`](stweb_suitecrm_poc_v02/) | 在相同18个任务上比较 S0 与 S1 | S1 的任务成功率、合规率和 CuP 均提高，因此接受 S1 |
| [`stweb_suitecrm_poc_v03/`](stweb_suitecrm_poc_v03/) | 从 S1 增量生成 S2，并比较 S1 与 S2 | S2 的合规率和 CuP 下降，因此拒绝 S2，继续保留 S1 |

## 结果目录与其他实验目录的区别

`experiments/` 下的文件按用途分开保存：

- `experiments/results/`：可审阅的小型结果和结论证据，也就是本目录；
- `experiments/configs/`：人工编写的实验配置；
- `experiments/manifests/`：任务范围、模型和运行方式等正式实验清单；
- `experiments/annotations/`：人工标准答案和 AI 语义判断评估；
- `experiments/campaigns/`：Autonomous GSE 的配置、任务分批和显式 Skill 起点；
- `artifacts/`：较大的原始任务记录、数据库快照及正式运行产物。

Autonomous GSE v0.1 的正式三步实验已经完成。适合进入 Git 的报告副本位于：

```text
experiments/results/autonomous_gse_v01/campaign_report.json
```

完整的本机运行产物仍位于 `artifacts/autonomous_gse_v01/`。该实验最终保留 S1，共产生87条任务记录、调用 Learner 3次，没有运行独立 Test。它的简化配置和记录批次位于 `experiments/campaigns/autonomous_gse_v01/`。

## Day 4：Trace2Skill 候选 Skill

目录：[`day4_trace2skill/`](day4_trace2skill/)

这组实验从5条早期统一任务记录出发，选择任务5、7、8进行局部分析。系统先为每条任务总结可复用经验，再比较风险和通用性，最终选择2项修改写入候选 Skill。

| 文件 | 内容 |
|---|---|
| [`common_trajectories.json`](day4_trace2skill/common_trajectories.json) | 5条早期统一任务记录，格式版本为 v0.1，是本组分析的输入。 |
| [`local_analysis/task_5.md`](day4_trace2skill/local_analysis/task_5.md) | 分析任务5：任务虽然成功，但在完成改签或取消前就承诺延误补偿，不符合规则。 |
| [`local_analysis/task_7.md`](day4_trace2skill/local_analysis/task_7.md) | 分析任务7：Agent 对仍在处理权限内的组合请求过早转人工，导致任务失败。 |
| [`local_analysis/task_8.md`](day4_trace2skill/local_analysis/task_8.md) | 分析任务8：任务成功，但为了查找历史预订而一次发起多个工具调用，过程不合规。 |
| [`local_lessons.md`](day4_trace2skill/local_lessons.md) | 汇总三项局部经验并作出取舍。任务5和7的经验被采用；任务8的经验有效，但因本轮最多只能增加2项规则而未采用。 |
| [`candidate_skill.md`](day4_trace2skill/candidate_skill.md) | 最终候选 Skill，包含延误补偿的前置条件检查，以及组合请求不能过早转人工两条规则。 |

这组文件展示的是一次早期离线学习闭环，不代表候选 Skill 已通过独立评测或可以部署。

## Day 5：统一任务记录格式与基础校验

目录：[`day5_schema/`](day5_schema/)

这组结果把 τ³ 的运行记录转换成项目统一格式，并把“任务是否成功”与“执行过程是否合规”分开判断。`Trajectory` 表示一次完整任务运行记录，`verdict` 表示校验程序给出的判断。

| 文件 | 内容 |
|---|---|
| [`common_trajectories_10_14.json`](day5_schema/common_trajectories_10_14.json) | 任务10至14的5条统一任务记录，直接转换为正式 v0.2.0 格式。 |
| [`common_trajectories_v02.json`](day5_schema/common_trajectories_v02.json) | 任务5至14共10条统一任务记录，格式版本为 v0.2.0；其中早期记录由 v0.1 迁移而来。后续校验实验主要读取该文件。 |
| [`task_verdicts_v01.json`](day5_schema/task_verdicts_v01.json) | 10条任务的成功判断和上游任务得分证据，只回答“任务是否完成”。 |
| [`compliance_verdicts_v01.json`](day5_schema/compliance_verdicts_v01.json) | 10条任务的转人工流程顺序检查，只回答这一项执行过程是否合规。它是早期单规则结果，不等同于 Day 6 的完整五规则校验。 |

如果需要使用当前统一格式，应优先读取 `common_trajectories_v02.json`；`common_trajectories_10_14.json` 主要保留新增5条任务的独立转换结果。

## Day 6：通用执行过程校验器

目录：[`day6_process_verifier/`](day6_process_verifier/)

这组文件记录通用过程校验器逐步增加规则的四个版本。每个文件都包含相同10条任务的逐规则判断、证据和总体合规结果。它们是版本演进记录，不是四次互相独立的实验。

| 文件 | 规则数量 | 新增或覆盖的内容 |
|---|---:|---|
| [`process_verdicts_v01.json`](day6_process_verifier/process_verdicts_v01.json) | 2 | 转人工工具与提示语顺序；用户请求是否应该转人工。 |
| [`process_verdicts_v02.json`](day6_process_verifier/process_verdicts_v02.json) | 3 | 在 v01 基础上增加“同一条 Agent 消息不能同时回复用户并调用工具”。 |
| [`process_verdicts_v03.json`](day6_process_verifier/process_verdicts_v03.json) | 4 | 在 v02 基础上增加“写数据库前说明操作详情并取得明确确认”。 |
| [`process_verdicts_v04.json`](day6_process_verifier/process_verdicts_v04.json) | 5 | 在 v03 基础上增加“付款方式必须属于目标用户账户”。这是当前完整结果。 |

如果只想查看当前实现的最终结果，应读取 `process_verdicts_v04.json`。v01至v03用于追踪规则集和校验器如何逐步扩展。

## SkillOpt SearchQA

目录：[`skillopt_searchqa_main200_hard_s42/`](skillopt_searchqa_main200_hard_s42/)

这组实验使用200道训练题连续运行5个 Skill 优化步骤，并用固定的选择评测决定是否接受每一步的候选版本。更完整的实验说明见该目录的 [`README.md`](skillopt_searchqa_main200_hard_s42/README.md)。

### 顶层文件

| 文件 | 内容 |
|---|---|
| [`README.md`](skillopt_searchqa_main200_hard_s42/README.md) | 本实验的目的、核心结果、归档范围和相关配置。 |
| [`config.json`](skillopt_searchqa_main200_hard_s42/config.json) | 程序合并默认值后实际使用的完整配置。人工编写的源配置位于 `experiments/configs/skillopt_searchqa_main200_hard_s42.yaml`。 |
| [`skill_v0000.md`](skillopt_searchqa_main200_hard_s42/skill_v0000.md) | 实验开始前的初始 Skill。 |
| [`best_skill.md`](skillopt_searchqa_main200_hard_s42/best_skill.md) | 5步结束后保留的最佳 Skill，来自第4步。 |
| [`summary.json`](skillopt_searchqa_main200_hard_s42/summary.json) | 最终汇总：共5步，接受3个、拒绝2个；选择评测严格准确率从0.75升至0.80。 |
| [`history.json`](skillopt_searchqa_main200_hard_s42/history.json) | 5个步骤各自的分数、修改数量、接受或拒绝决定、耗时和用量。 |
| [`test_baseline_summary.json`](skillopt_searchqa_main200_hard_s42/test_baseline_summary.json) | 初始 Skill 的独立测试结果，严格准确率为0.90。 |
| [`test_final_summary.json`](skillopt_searchqa_main200_hard_s42/test_final_summary.json) | 最佳 Skill 的独立测试结果，严格准确率为0.91。 |

### 第4步和第5步归档

仓库只保存第4步和第5步的完整候选文件，分别展示一次接受和一次拒绝。两个步骤目录都包含相同类型的6个文件：

| 文件名 | 内容 |
|---|---|
| `trajectory_digest.json` | 本步骤训练题表现及主要失败模式摘要。 |
| `merged_patch.json` | 从多个小批次汇总得到的候选修改集合。 |
| `ranked_edits.json` | 排序和筛选后实际保留的修改。 |
| `edit_apply_report.json` | 每项修改是否成功应用到 Skill。 |
| `candidate_skill.md` | 应用修改后得到的候选 Skill。 |
| `step_record.json` | 本步骤的分数、耗时、接受或拒绝决定及来源信息。 |

具体目录：

- [`steps/step_0004/`](skillopt_searchqa_main200_hard_s42/steps/step_0004/)：候选版本被接受，并成为最终最佳 Skill；
- [`steps/step_0005/`](skillopt_searchqa_main200_hard_s42/steps/step_0005/)：候选版本被选择门槛拒绝。

第1至第3步的汇总仍保存在 `history.json`，完整逐题记录位于本机 `external/SkillOpt/outputs/searchqa_main200_hard_s42/`，不在 Git 结果目录中。

## SuiteCRM v01：基线对照和候选 S1

目录：[`stweb_suitecrm_poc_v01/`](stweb_suitecrm_poc_v01/)

这组实验先用51条无 Skill 训练记录生成不同 Skill，再用18个固定任务比较四种方法：无 Skill、人工 Skill、只根据任务成功学习的 Skill、只根据成功且合规记录学习的 Skill。该目录还保存了后来根据任务结果与规则校验证据共同生成的候选 S1。

### 顶层与选择评测文件

| 文件 | 内容 |
|---|---|
| [`human_skill.md`](stweb_suitecrm_poc_v01/human_skill.md) | 人工编写的 SuiteCRM 操作 Skill，作为四种方法之一参加选择评测。 |
| [`selection/method_summary.csv`](stweb_suitecrm_poc_v01/selection/method_summary.csv) | 四种方法的简洁表格结果，包括任务成功率、合规率、CuP、违规数和平均步骤数。 |
| [`selection/summary.json`](stweb_suitecrm_poc_v01/selection/summary.json) | 四种方法的完整汇总、成对比较和运行来源信息；共包含72条正式评测记录。 |
| [`selection/task_results.json`](stweb_suitecrm_poc_v01/selection/task_results.json) | 18个任务在四种方法下的逐任务结果，供配对比较和后续门槛分析使用。 |
| [`selection/two_dimensional_transitions.json`](stweb_suitecrm_poc_v01/selection/two_dimensional_transitions.json) | 同一任务在不同方法之间如何从“违规/合规、失败/成功”四种状态发生变化。 |

四种方法的任务成功数均为7/18。人工 Skill 的合规数最高，为8/18；Outcome-only Skill 的合规数为6/18；Filtered Skill 与无 Skill 均为5/18。该结果说明，仅仅筛掉违规训练记录并没有在这次评测中带来最高合规率。

### `skills/` 中的三组 Skill

详细说明见 [`skills/README.md`](stweb_suitecrm_poc_v01/skills/README.md)。该目录包含三组生成结果。

#### Outcome-only Skill

这组文件使用全部21条任务成功记录生成 Skill，没有依据过程是否合规继续筛选。

| 文件 | 内容 |
|---|---|
| [`outcome_only_skill.md`](stweb_suitecrm_poc_v01/skills/outcome_only_skill.md) | 实际参加选择评测的 Skill 正文。 |
| [`outcome_only_skill.patch`](stweb_suitecrm_poc_v01/skills/outcome_only_skill.patch) | 该 Skill 相对空白起点增加的全部文本。 |
| [`outcome_only_learner_response.txt`](stweb_suitecrm_poc_v01/skills/outcome_only_learner_response.txt) | Learner 模型生成 Skill 时返回的原始文本。 |
| [`outcome_only_provenance.json`](stweb_suitecrm_poc_v01/skills/outcome_only_provenance.json) | Skill 中每条规则来自哪些成功任务记录。 |
| [`outcome_only_metadata.json`](stweb_suitecrm_poc_v01/skills/outcome_only_metadata.json) | 输入清单、模型参数、提示词、输出路径和用量。 |

#### Filtered Skill

这组文件只使用21条成功记录中同时没有违规的10条记录生成 Skill。

| 文件 | 内容 |
|---|---|
| [`filtered_skill.md`](stweb_suitecrm_poc_v01/skills/filtered_skill.md) | 实际参加选择评测的 Skill 正文。 |
| [`filtered_skill.patch`](stweb_suitecrm_poc_v01/skills/filtered_skill.patch) | 该 Skill 相对空白起点增加的全部文本。 |
| [`filtered_learner_response.txt`](stweb_suitecrm_poc_v01/skills/filtered_learner_response.txt) | Learner 模型生成 Skill 时返回的原始文本。 |
| [`filtered_provenance.json`](stweb_suitecrm_poc_v01/skills/filtered_provenance.json) | Skill 中每条规则来自哪些成功且合规的任务记录。 |
| [`filtered_metadata.json`](stweb_suitecrm_poc_v01/skills/filtered_metadata.json) | 输入清单、模型参数、提示词、输出路径和用量。 |

#### 受规则约束的候选 S1

这组文件同时使用任务结果和过程校验证据，从 S0 生成候选 S1。它不只学习成功做法，也会根据违规证据修复行为。

| 文件 | 内容 |
|---|---|
| [`governed_candidate_s1_skill.md`](stweb_suitecrm_poc_v01/skills/governed_candidate_s1_skill.md) | 候选 S1 的 Skill 正文。 |
| [`governed_candidate_s1_skill.patch`](stweb_suitecrm_poc_v01/skills/governed_candidate_s1_skill.patch) | S0 到候选 S1 的全部文本修改。 |
| [`governed_candidate_s1_learner_response.txt`](stweb_suitecrm_poc_v01/skills/governed_candidate_s1_learner_response.txt) | Learner 模型生成候选 S1 时返回的原始文本。 |
| [`governed_candidate_s1_provenance.json`](stweb_suitecrm_poc_v01/skills/governed_candidate_s1_provenance.json) | S1 中每条规则所依据的任务经验，以及该规则属于保留有效行为还是修复违规行为。 |
| [`governed_candidate_s1_metadata.json`](stweb_suitecrm_poc_v01/skills/governed_candidate_s1_metadata.json) | S1 的输入经验、生成参数、提示词、用量和版本。 |

## SuiteCRM v02：S0 与 S1 的正式比较

目录：[`stweb_suitecrm_poc_v02/`](stweb_suitecrm_poc_v02/)

这组实验在18个固定任务上比较无 Skill 起点 S0 和候选 S1。结果显示，S1 的任务成功数从5升至6，合规数从4升至6，CuP 从3升至4，因此 S1 被接受并成为新的当前版本。

| 文件 | 内容 |
|---|---|
| [`selection/evolution_summary.md`](stweb_suitecrm_poc_v02/selection/evolution_summary.md) | 便于人阅读的结果，包括整体指标、四状态分布、逐任务变化和违规类型变化。 |
| [`selection/evolution_summary.json`](stweb_suitecrm_poc_v02/selection/evolution_summary.json) | 与 Markdown 汇总对应的结构化数据，供程序继续处理。 |
| [`selection/evolution_decision.json`](stweb_suitecrm_poc_v02/selection/evolution_decision.json) | 正式演化决定：接受 S1，将其晋升为当前版本；独立 Test 继续保持锁定。 |

## SuiteCRM v03：S1 与 S2 的正式比较

目录：[`stweb_suitecrm_poc_v03/`](stweb_suitecrm_poc_v03/)

这组实验从已接受的 S1 出发，根据新的训练经验增量生成 S2，再在相同18个固定任务上比较两个版本。两者任务成功数均为7，但 S2 的合规数从7降至6，CuP 从4降至3，因此 S2 被拒绝，当前版本继续保持为 S1。

### 候选 S2 文件

| 文件 | 内容 |
|---|---|
| [`skills/governed_candidate_s2_skill.md`](stweb_suitecrm_poc_v03/skills/governed_candidate_s2_skill.md) | 实际参加评测的候选 S2 Skill。 |
| [`skills/governed_candidate_s2_skill.patch`](stweb_suitecrm_poc_v03/skills/governed_candidate_s2_skill.patch) | S1 到 S2 的文本差异。 |
| [`skills/governed_candidate_s2_edits.json`](stweb_suitecrm_poc_v03/skills/governed_candidate_s2_edits.json) | Learner 提出的结构化增量修改。 |
| [`skills/governed_candidate_s2_learner_response.txt`](stweb_suitecrm_poc_v03/skills/governed_candidate_s2_learner_response.txt) | Learner 模型的原始回答。 |
| [`skills/governed_candidate_s2_provenance.json`](stweb_suitecrm_poc_v03/skills/governed_candidate_s2_provenance.json) | S2 中各项修改所依据的训练经验和规则证据。 |
| [`skills/governed_candidate_s2_metadata.json`](stweb_suitecrm_poc_v03/skills/governed_candidate_s2_metadata.json) | S2 的生成输入、模型参数、版本和编辑上限。 |

### 选择评测与决定

| 文件 | 内容 |
|---|---|
| [`selection/evolution_summary.md`](stweb_suitecrm_poc_v03/selection/evolution_summary.md) | 便于人阅读的 S1/S2 比较结果。 |
| [`selection/evolution_summary.json`](stweb_suitecrm_poc_v03/selection/evolution_summary.json) | 供程序读取的结构化比较结果。 |
| [`selection/evolution_decision.json`](stweb_suitecrm_poc_v03/selection/evolution_decision.json) | 正式决定：因合规率和 CuP 下降而拒绝 S2，继续保留 S1；独立 Test 仍未运行。 |

## 推荐阅读顺序

如果想了解项目如何一步步发展，建议按以下顺序阅读：

1. `day4_trace2skill/local_lessons.md`：看早期如何从任务记录总结 Skill 规则；
2. `day5_schema/`：看任务记录和基础判断如何统一保存；
3. `day6_process_verifier/process_verdicts_v04.json`：看当前五条规则的完整过程校验结果；
4. `skillopt_searchqa_main200_hard_s42/README.md`：看外部 SkillOpt 方法的独立实验；
5. `stweb_suitecrm_poc_v01/selection/method_summary.csv`：看四种 Skill 方法的基线对照；
6. `stweb_suitecrm_poc_v02/selection/evolution_summary.md`：看 S1 为什么被接受；
7. `stweb_suitecrm_poc_v03/selection/evolution_summary.md`：看 S2 为什么被拒绝；
8. 需要复现或审计时，再查看各目录中的配置、来源证据、元数据、冻结记录和 Learner 原始回答。

更完整的实验过程、研究动机和阶段结论记录在 `docs/04_EXPERIMENT_LOG.md`。

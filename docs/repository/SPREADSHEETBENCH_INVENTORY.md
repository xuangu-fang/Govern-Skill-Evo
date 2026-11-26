# SpreadsheetBench v25 系列全量盘点

盘点日期为 2026-11-26。分支 `wyy/day57-tau-autonomous-gse-v25`，基线提交 `c1e604e56aa`。覆盖 v25–v25.8、SkillAdam、SkillOpt、共用对照及相关配置、调度和专项分析。

**共登记 38 条训练、准备或对照记录，其中 20 次训练完成。** 另核对 96 个评测现场，其中 90 个现场各有 280 份标准逐题回执，2 次通过独立补测补齐 280 题，另有 3 次专项小样本和 1 次停止的对照。展开归档后，核对了 25,986 份标准回执与 2 份独立补测评分。盘点同时登记了 90 个相关材料 ID 和 45 条现有历史路径映射。

[结构化清单与拟议路径](spreadsheetbench-inventory.json) 逐条列出配置、状态证据、受测 Skill 的 SHA-256、评测路径和档案位置。本文中的 `artifacts/` 链接依赖本地归档。共用 R00 的最终实验归属依据实际评测记录，v25.8 等方法图上复用同一结果。

## 各版本与基线概览

| 版本／方法 | 训练、准备与对照 | 完成训练 | 完整 280 题评测 | 小样本 | 停止评测 |
|---|---:|---:|---:|---:|---:|
| v25 | 10 | 3 | 3 | 0 | 0 |
| v25.1 | 1 | 1 | 1 | 0 | 0 |
| v25.2 | 1 | 1 | 1 | 0 | 0 |
| v25.3 | 2 | 1 | 1 | 0 | 0 |
| v25.4 | 1 | 1 | 2 | 2 | 0 |
| v25.5 | 3 | 1 | 2 | 0 | 0 |
| v25.6 | 1 | 1 | 11 | 1 | 0 |
| v25.7 | 3 | 2 | 11 | 0 | 0 |
| v25.8 | 1 | 1 | 19 | 0 | 0 |
| SkillAdam | 11 | 7 | 29 | 0 | 0 |
| SkillOpt | 2 | 1 | 9 | 0 | 0 |
| 共用对照 | 2 | 0 | 3 | 0 | 1 |

完整评测按各自现场计数，包含最终 Skill、逐轮保留 Skill、复测和跨 Actor 评测。已迁移的软链接及无逐题目录的精选摘要关联到同一次评测。92 次完整评测的 280 个题目 ID 集合一致。同一份 Skill 的复测按独立运行计数；每次的整题成功数、逐题平均单元格正确率与 Actor 模型见清单。

## 正式对照与历史边界

| 记录 | 已核对的结果 | 来源 |
|---|---|---|
| 正式共用 R00 | 203/280，官方 DeepSeek Flash，受测文本与 v25.8 R00 的 SHA-256 一致。 | [共用 R00](../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/shared_R00/summary.json) |
| v25.8，11 月 18 日正式训练 | 完成 R01–R08。R03 和 R04 的保留 Skill 字节相同。R08 首测及两次复测分别为 228、227、227/280，中位数 227/280。 | [首测](../../artifacts/methods/v25_8/v25_8_spreadsheetbench_official_20261118_232447/test/summary.json) · [复测](../../artifacts/analysis/spreadsheetbench_v25_8_R07_R08_retests_20261119_201604/R08/summary.json) · [第三测](../../artifacts/analysis/spreadsheetbench_v25_8_R08_third_20261120_140000/R08/summary.json) |
| SkillAdam，11 月 20 日官方模型训练 | 8 轮完成。R06 采纳，R07、R08 沿用。最终 Skill 的五次 DeepSeek Flash 成绩依次为 220、225、230、228、225/280，现有对照图取前三次中位数 225/280。早期索引登记 8 条训练或准备记录，另找到 11 月 12 日、16 日和 20 日三次独立训练。 | [早期索引](../../experiments/methods/skilladam/spreadsheetbench/README.md) · [11 月 20 日训练及复测](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006) |
| SkillOpt，11 月 22 日正式训练 | 完成 4 个 epoch、8 个普通更新。Selection 选中第 7 步，39/40，通过 SHA-256 绑定到 `best_skill.md`。该 Skill 的三次 DeepSeek Flash 测试分别为 226、220、221/280。10 月 29 日的原生方案单独记为准备与预检。 | [Selection](../../artifacts/methods/skillopt/spreadsheetbench_v25_8/selection.json) · [Best 首测](../../artifacts/methods/skillopt/spreadsheetbench_v25_8/test/summary.json) · [10 月 29 日准备](../../experiments/baselines/skillopt_spreadsheetbench_official_actor48k_20261029/README.md) |
| SkillOpt R02 | 11 月 22 日的 R02 为 224/280，受测 Skill 带空慢更新占位。11 月 23 日三次评测共用占位前的另一份 Skill，结果为 228、220、226/280。两份受测文本的 SHA-256 不同。 | [11 月 22 日](../../artifacts/analysis/spreadsheetbench_skillopt_step_tests_20261122_214430/R02/summary.json) · [11 月 23 日首测](../../artifacts/analysis/spreadsheetbench_skillopt_R02_pre_placeholder_test280_20261123_82RTMo/test/summary.json) |
| GPT-5.4-mini 跨 Actor | v25.8 为 180/280，SkillAdam 为 177/280，SkillOpt 为 178/280。v25.8 和 SkillOpt 的标准目录各有 279 份回执，缺同一题 `test:191-40`。各自的独立补测均通过，清单同时保留原目录和补测评分。 | [v25.8 补测](../../artifacts/analysis/spreadsheetbench_v25_8_final_gpt54mini_20261119/retry_191-40_128000_20261120/score.json) · [SkillAdam 汇总](../../artifacts/analysis/spreadsheetbench_skilladam_1120_final_gpt54mini_20261120/test/summary.json) · [SkillOpt 补测后汇总](../../artifacts/analysis/spreadsheetbench_skillopt_final_gpt54mini_20261124/summary_after_single_retry.json) |
| 10 月 26 日 277 题旧对照 | No Skill 已评分 212 题，其中 173 题成功，另有两题只留有尝试记录。Initial Skill 无评测回执。277 题是这次计划的分母。 | [原计划](../../experiments/baselines/spreadsheetbench_controls_actor32k_w4_20261026/plan.json) · [停止状态](../../experiments/baselines/spreadsheetbench_controls_actor32k_w4_20261026/progress.json) |
| 10 月 27 日 280 题四臂对照 | 用当时的 v4.1 Flash 和修正配置。No Skill 222、Initial Skill 215、v25 224、SkillAdam 231/280。v25 与 SkillAdam 两臂分别挂到各自训练 ID。 | [四臂配置与结果说明](../../experiments/evaluations/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001/four_way/README.md) · [评分兼容说明](../methods/v25/SCORING_COMPATIBILITY.md) |

[现有正式对照图和取值口径](../04_EXPERIMENT_LOG.md)以每种方法实际保留的 Skill 为单位，累计训练与验证题次为 v25.8 240、SkillAdam 360、SkillOpt 920。

## 源码、数据与归档核对

- 主实现按现有 `src/skill_evolution/v25*` 包路径保留，运行入口与验证脚本沿用同版本路径。范围清单列出 1,124 个当前未跟踪的源码、脚本、测试和方法文档路径，供后续逐批审阅。v25.8 冻结合同列出的 8 个跨包文件均与当前文件字节一致，其中 [v28/output_feedback.py](../../src/skill_evolution/v28/output_feedback.py) 尚未纳入 Git。其余直接引用和调用方见结构化清单。
- 数据来自 Trace2Skill 的 Verified-400 工作簿，本机已核到 800 份工作簿。SkillOpt 上游提供 80 Train／40 Selection／280 Test 划分。v25 系列把前两组共 120 题用于优化，SkillOpt 则保留独立 Selection。运行时还依赖各实验冻结的 Docker、Actor 配置与 Python 环境。SkillOpt 正式入口校验固定上游提交及本机三份源码适配的哈希。[v25.8 运行说明](../methods/v25_8/README.md) · [SkillOpt 配置与选优说明](../methods/skillopt/SPREADSHEETBENCH_V25_8.md)
- 压缩归档本次执行 `restore.py spreadsheetbench --verify`，通过 135,583 条记录和 62,303 个附件的 SHA-256 校验。逐题核对使用原路径解析完成回执，再从归档还原轨迹，核对题目、整题分、单元格分和受测 Skill。存在终报的评测，其逐题分与终报逐项一致。[归档说明](../../experiments/benchmark_record_refs/README.md)
- v25 与 SkillAdam 原有 `verify_bundle.py` 的精选材料模式均通过。两者的旧 `--archive` 模式分别报 `KeyError: 'skill_source'` 和 `KeyError: 'batches'`，对应输入和共享配置目前是压缩引用，需要在后续归档样板中接入解包读取。独立检出的入口验证留待样板阶段。[v25 检查入口](../../scripts/runs/v25/verify_bundle.py) · [SkillAdam 检查入口](../../scripts/runs/skilladam/spreadsheetbench/verify_bundle.py)
- 11 月 12 日 SkillAdam 历史训练的原目录能读到 8 轮 checkpoint、恢复脚本及最终 Skill。独立冻结的训练配置副本尚未在该目录找到，清单挂接了当时复用的对齐 Actor 配置，并标明来源。

## 拟议归档位置

已有精选目录沿用当前布局。清单中的 `target_experiment_path` 和 `target_selected_path` 是后续归位计划，现有实验和数据路径未移动。

| 材料 | 拟议位置 |
|---|---|
| 自进化训练及精选评测 | `experiments/methods/<v25 版本>/<实验 ID>/`，同一训练的首测、逐轮和复测放在其 `results/` 下。 |
| SkillAdam、SkillOpt | `experiments/methods/skilladam/spreadsheetbench/<配置>/<实验 ID>/` 和 `experiments/methods/skillopt/spreadsheetbench/<实验 ID>/`。 |
| 共用初始 Skill、No Skill、四臂调度 | `experiments/benchmarks/spreadsheetbench/controls/`，老评测入口保留到原运行位置的解析关系。 |
| 完整任务轨迹、工作簿、恢复和调试现场 | 延用清单登记的原始归档路径。压缩引用依赖原路径键，后续如需移动须先验证恢复兼容。 |
| 正式三方法对照 | 后续在 `docs/benchmarks/spreadsheetbench/` 统一链接训练、实际受测 Skill、评测和图表。 |

## 训练、准备与共用对照明细
| 方法 | 实验 ID | 状态 | 已完成轮／步 | 关联评测目录 |
|---|---|---|---:|---:|
| v25 | [v25_first15_001](../../experiments/methods/v25/v25_first15_001) | pilot 中断 | 0 | 0 |
| v25 | [v25_full120_exec30_gen6_actor32k_w4_20261026_004](../../experiments/methods/v25/v25_full120_exec30_gen6_actor32k_w4_20261026_004) | 停止／未完成 | 0 | 0 |
| v25 | [v25_full120_no_task_deadline_actor32k_w4_20261026_003](../../experiments/methods/v25/v25_full120_no_task_deadline_actor32k_w4_20261026_003) | 停止／未完成 | 0 | 0 |
| v25 | [v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001](../../experiments/methods/v25/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001) | 完成训练 | 8 | 1 |
| v25 | [v25_full120_precondv2_batch15_exec30_gen6_actor32k_w4_20261026_006](../../experiments/methods/v25/v25_full120_precondv2_batch15_exec30_gen6_actor32k_w4_20261026_006) | 停止／未完成 | 2 | 0 |
| v25 | [v25_full120_precondv3_batch15_exec30_gen6_actor32k_w4_20261026_007](../../experiments/methods/v25/v25_full120_precondv3_batch15_exec30_gen6_actor32k_w4_20261026_007) | 停止／未完成 | 7 | 0 |
| v25 | [v25_full120_timeline_actor32k_w4_20261026_002](../../experiments/methods/v25/v25_full120_timeline_actor32k_w4_20261026_002) | 停止／未完成 | 1 | 0 |
| v25 | [v25_skilladam_execution_only_actor48k_20261027_001_v25](../../experiments/methods/v25/v25_skilladam_execution_only_actor48k_20261027_001_v25) | 完成训练 | 8 | 1 |
| v25 | [v25_skilladam_upstream_actor_prompt_20261030_001_v25](../../experiments/methods/v25/v25_skilladam_upstream_actor_prompt_20261030_001_v25) | 完成训练 | 8 | 1 |
| v25 | [v25_two_round_exploration_20261028_001](../../experiments/methods/v25/v25_two_round_exploration_20261028_001) | 探索中断 | 1 | 0 |
| v25.1 | [v25_v25_1_common_actor_no_review_20261030_001_v25_1](../../experiments/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1) | 完成训练 | 8 | 1 |
| v25.2 | [v25_2_prompt_only_20261101_001](../../experiments/methods/v25_2/v25_2_prompt_only_20261101_001) | 完成训练 | 8 | 1 |
| v25.3 | [v25_3_spreadsheetbench_20261106_1200](../../experiments/methods/v25_3/v25_3_spreadsheetbench_20261106_1200) | 启动流程取消，训练未开始 | 0 | 0 |
| v25.3 | [v25_3_spreadsheetbench_proxy](../../experiments/methods/v25_3/v25_3_spreadsheetbench_proxy) | 完成训练 | 8 | 1 |
| v25.4 | [v25_4_spreadsheetbench_proxy](../../experiments/methods/v25_4/v25_4_spreadsheetbench_proxy) | 完成训练 | 8 | 4 |
| v25.5 | [v25_5_spreadsheetbench_deepseek](../../experiments/methods/v25_5/v25_5_spreadsheetbench_deepseek) | 完成训练 | 8 | 2 |
| v25.5 | [v25_5_spreadsheetbench_proxy](../../experiments/methods/v25_5/v25_5_spreadsheetbench_proxy) | 仅准备 | 0 | 0 |
| v25.5 | [v25_5_spreadsheetbench_proxy_before_editor_revision](../../experiments/methods/v25_5/v25_5_spreadsheetbench_proxy_before_editor_revision) | 仅准备（Editor 修订前） | 0 | 0 |
| v25.6 | [v25_6_spreadsheetbench_deepseek](../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek) | 完成训练 | 8 | 12 |
| v25.7 | [v25_7_spreadsheetbench_deepseek](../../artifacts/methods/v25_7/v25_7_spreadsheetbench_deepseek) | 仅准备 | 0 | 0 |
| v25.7 | [v25_7_spreadsheetbench_official_20261118_212017](../../artifacts/methods/v25_7/v25_7_spreadsheetbench_official_20261118_212017) | 完成训练 | 8 | 1 |
| v25.7 | [v25_7_spreadsheetbench_v41_20261116](../../artifacts/methods/v25_7/v25_7_spreadsheetbench_v41_20261116) | 完成训练 | 8 | 10 |
| v25.8 | [v25_8_spreadsheetbench_official_20261118_232447](../../artifacts/methods/v25_8/v25_8_spreadsheetbench_official_20261118_232447) | 完成训练 | 8 | 19 |
| SkillAdam | [skilladam_spreadsheetbench_native_retry_actor48k_20261029_001](../../experiments/methods/skilladam/spreadsheetbench/native_retry/skilladam_spreadsheetbench_native_retry_actor48k_20261029_001) | 仅准备 | 0 | 0 |
| SkillAdam | [skilladam_spreadsheetbench_v25_5_feedback_20261108_234037](../../experiments/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261108_234037) | 完成训练 | 8 | 5 |
| SkillAdam | [skilladam_spreadsheetbench_v25_5_feedback_20261112_201115](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261112_201115) | 完成训练 | 8 | 2 |
| SkillAdam | [skilladam_spreadsheetbench_v25matched_20261026](../../experiments/methods/skilladam/spreadsheetbench/shared_actor/skilladam_spreadsheetbench_v25matched_20261026) | 受阻 | 0 | 0 |
| SkillAdam | [skilladam_spreadsheetbench_v25matched_exec30_gen6_20261026](../../experiments/methods/skilladam/spreadsheetbench/shared_actor/skilladam_spreadsheetbench_v25matched_exec30_gen6_20261026) | 恢复后停止 | 3 | 0 |
| SkillAdam | [skilladam_spreadsheetbench_v25matched_no_task_deadline_20261026](../../experiments/methods/skilladam/spreadsheetbench/shared_actor/skilladam_spreadsheetbench_v25matched_no_task_deadline_20261026) | 用户停止 | 0 | 0 |
| SkillAdam | [skilladam_spreadsheetbench_v41_feedback_20261116_142340](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_feedback_20261116_142340) | 完成训练 | 8 | 6 |
| SkillAdam | [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006) | 完成训练 | 8 | 12 |
| SkillAdam | [skilladam_v25_1_actor_aligned_20261030_001](../../experiments/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001) | 完成训练 | 8 | 2 |
| SkillAdam | [v25_skilladam_execution_only_actor48k_20261027_001_skilladam](../../experiments/methods/skilladam/spreadsheetbench/shared_actor/v25_skilladam_execution_only_actor48k_20261027_001_skilladam) | 完成训练 | 8 | 1 |
| SkillAdam | [v25_skilladam_upstream_actor_prompt_20261030_001_skilladam](../../experiments/methods/skilladam/spreadsheetbench/upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam) | 完成训练 | 8 | 1 |
| SkillOpt | [skillopt_spreadsheetbench_official_actor48k_20261029](../../experiments/baselines/skillopt_spreadsheetbench_official_actor48k_20261029) | 仅准备与预检 | 0 | 0 |
| SkillOpt | [spreadsheetbench_v25_8](../../artifacts/methods/skillopt/spreadsheetbench_v25_8) | 完成训练和 Selection | 8 | 9 |
| 共用对照 | [spreadsheetbench_controls_actor32k_w4_20261026](../../experiments/baselines/spreadsheetbench_controls_actor32k_w4_20261026) | No Skill 停止，Initial Skill 未见执行记录 | — | 1 |
| 共用对照 | [spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001](../../experiments/evaluations/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001) | 四臂评测完成 | — | 2 |

## 评测明细

受测 Skill 文件路径、完整哈希、配置中的并发和目标归档路径均见 [结构化清单](spreadsheetbench-inventory.json)。下表按实际评分来源列出。停止的 277 题旧对照仅显示已经评分的 212 题。

<details>
<summary>v25（3 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_v25_test280](../../artifacts/methods/v25/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_v25_test280) | `deepseek-v4.1-flash` | 224/280 | 完整 Test |
| [v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001_test280](../../artifacts/methods/v25/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001_test280) | `deepseek-flash` | 237/280 | 完整 Test |
| [v25_skilladam_upstream_actor_prompt_20261030_001_v25_test280](../../artifacts/methods/v25/v25_skilladam_upstream_actor_prompt_20261030_001_v25_test280) | `deepseek-flash` | 219/280 | 完整 Test |

</details>

<details>
<summary>v25.1（1 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [v25_v25_1_common_actor_no_review_20261030_001_v25_1_test280](../../artifacts/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1_test280) | `deepseek-flash` | 223/280 | 完整 Test |

</details>

<details>
<summary>v25.2（1 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [v25_2_prompt_only_20261101_001_test280](../../artifacts/methods/v25_2/v25_2_prompt_only_20261101_001_test280) | `deepseek-flash` | 229/280 | 完整 Test |

</details>

<details>
<summary>v25.3（1 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [v25_3_spreadsheetbench_proxy_test280](../../artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy_test280) | `deepseek-v4.1-flash` | 214/280 | 完整 Test |

</details>

<details>
<summary>v25.4（4 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [v25_4_spreadsheetbench_proxy_four_test_tasks_20261108_113020](../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy_four_test_tasks_20261108_113020) | `deepseek-v4.1-flash` | 3/4 | 专项小样本 |
| [v25_4_spreadsheetbench_proxy_full_40w_20261108_1650](../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy_full_40w_20261108_1650) | `deepseek-flash` | 222/280 | 完整 Test |
| [v25_4_spreadsheetbench_proxy_test280](../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy_test280) | `deepseek-v4.1-flash` | 225/280 | 完整 Test |
| [v25_4_spreadsheetbench_proxy_unique_failures_20261108_101739](../../artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy_unique_failures_20261108_101739) | `deepseek-v4.1-flash` | 8/10 | 专项小样本 |

</details>

<details>
<summary>v25.5（2 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [v25_5_spreadsheetbench_deepseek_full_40w_20261108_1730](../../artifacts/methods/v25_5/v25_5_spreadsheetbench_deepseek_full_40w_20261108_1730) | `deepseek-flash` | 230/280 | 完整 Test |
| [v25_5_spreadsheetbench_deepseek_test280](../../artifacts/methods/v25_5/v25_5_spreadsheetbench_deepseek_test280) | `deepseek-flash` | 225/280 | 完整 Test |

</details>

<details>
<summary>v25.6（12 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R01](../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R01) | `deepseek-flash` | 216/280 | 完整 Test |
| [spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R03](../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R03) | `deepseek-flash` | 210/280 | 完整 Test |
| [spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R04](../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R04) | `deepseek-flash` | 226/280 | 完整 Test |
| [spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R05](../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R05) | `deepseek-flash` | 229/280 | 完整 Test |
| [spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R06](../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R06) | `deepseek-flash` | 231/280 | 完整 Test |
| [reruns/R02_R03_20261113_191807/R02](../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R02_R03_20261113_191807/R02) | `deepseek-flash` | 206/280 | 完整 Test |
| [R03](../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R02_R03_20261113_191807/R03) | `deepseek-flash` | 210/280 | 完整 Test |
| [R03](../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R03_R08_20261113_1200/R03) | `deepseek-flash` | 204/280 | 完整 Test |
| [reruns/R03_R08_20261113_1200/R08](../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R03_R08_20261113_1200/R08) | `deepseek-flash` | 222/280 | 完整 Test |
| [reruns/R08_38985_48969_20261113_104005/test](../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R08_38985_48969_20261113_104005/test) | `deepseek-flash` | 1/2 | 专项小样本 |
| [reruns/test280_20261112_225939/test](../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/test280_20261112_225939/test) | `deepseek-flash` | 229/280 | 完整 Test |
| [v25_6/v25_6_spreadsheetbench_deepseek/test](../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/test) | `deepseek-flash` | 225/280 | 完整 Test |

</details>

<details>
<summary>v25.7（11 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [spreadsheetbench_v25_7_v41_R01_R08_repeat_20261117/R01](../../artifacts/analysis/spreadsheetbench_v25_7_v41_R01_R08_repeat_20261117/R01) | `deepseek-v4.1-flash` | 226/280 | 完整 Test |
| [spreadsheetbench_v25_7_v41_R01_R08_repeat_20261117/R08](../../artifacts/analysis/spreadsheetbench_v25_7_v41_R01_R08_repeat_20261117/R08) | `deepseek-v4.1-flash` | 226/280 | 完整 Test |
| [spreadsheetbench_v25_7_v41_R01_third_20261117/R01](../../artifacts/analysis/spreadsheetbench_v25_7_v41_R01_third_20261117/R01) | `deepseek-v4.1-flash` | 217/280 | 完整 Test |
| [spreadsheetbench_v25_7_v41_R02_repeat_20261117/R02](../../artifacts/analysis/spreadsheetbench_v25_7_v41_R02_repeat_20261117/R02) | `deepseek-v4.1-flash` | 218/280 | 完整 Test |
| [spreadsheetbench_v25_7_v41_rounds_20261116/R01](../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R01) | `deepseek-v4.1-flash` | 228/280 | 完整 Test |
| [spreadsheetbench_v25_7_v41_rounds_20261116/R02](../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R02) | `deepseek-v4.1-flash` | 222/280 | 完整 Test |
| [spreadsheetbench_v25_7_v41_rounds_20261116/R05](../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R05) | `deepseek-v4.1-flash` | 226/280 | 完整 Test |
| [spreadsheetbench_v25_7_v41_rounds_20261116/R06](../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R06) | `deepseek-v4.1-flash` | 228/280 | 完整 Test |
| [spreadsheetbench_v25_7_v41_rounds_20261116/R08](../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R08) | `deepseek-v4.1-flash` | 226/280 | 完整 Test |
| [v25_7/v25_7_spreadsheetbench_official_20261118_212017/test](../../artifacts/methods/v25_7/v25_7_spreadsheetbench_official_20261118_212017/test) | `deepseek-flash` | 216/280 | 完整 Test |
| [v25_7/v25_7_spreadsheetbench_v41_20261116/test](../../artifacts/methods/v25_7/v25_7_spreadsheetbench_v41_20261116/test) | `deepseek-v4.1-flash` | 227/280 | 完整 Test |

</details>

<details>
<summary>v25.8（19 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [spreadsheetbench_v25_8_R01_third_20261120_221556/R01](../../artifacts/analysis/spreadsheetbench_v25_8_R01_third_20261120_221556/R01) | `deepseek-flash` | 216/280 | 完整 Test |
| [spreadsheetbench_v25_8_R02_repeat_20261119_193936/R02](../../artifacts/analysis/spreadsheetbench_v25_8_R02_repeat_20261119_193936/R02) | `deepseek-flash` | 223/280 | 完整 Test |
| [spreadsheetbench_v25_8_R05_repeat_20261119_183030/R05](../../artifacts/analysis/spreadsheetbench_v25_8_R05_repeat_20261119_183030/R05) | `deepseek-flash` | 217/280 | 完整 Test |
| [spreadsheetbench_v25_8_R07_R08_retests_20261119_201604/R07](../../artifacts/analysis/spreadsheetbench_v25_8_R07_R08_retests_20261119_201604/R07) | `deepseek-flash` | 224/280 | 完整 Test |
| [spreadsheetbench_v25_8_R07_R08_retests_20261119_201604/R08](../../artifacts/analysis/spreadsheetbench_v25_8_R07_R08_retests_20261119_201604/R08) | `deepseek-flash` | 227/280 | 完整 Test |
| [spreadsheetbench_v25_8_R08_third_20261120_140000/R08](../../artifacts/analysis/spreadsheetbench_v25_8_R08_third_20261120_140000/R08) | `deepseek-flash` | 227/280 | 完整 Test |
| [spreadsheetbench_v25_8_final_gpt54mini_20261119/test](../../artifacts/analysis/spreadsheetbench_v25_8_final_gpt54mini_20261119/test) | `gpt-5.4-mini` | 180/280 | 完整 Test（含独立补测） |
| [spreadsheetbench_v25_8_round_retests_20261119_191247/R01](../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R01) | `deepseek-flash` | 214/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_retests_20261119_191247/R02](../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R02) | `deepseek-flash` | 210/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_retests_20261119_191247/R03](../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R03) | `deepseek-flash` | 216/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_retests_20261119_191247/R05](../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R05) | `deepseek-flash` | 210/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_retests_20261119_191247/R06](../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R06) | `deepseek-flash` | 220/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_tests_20261119/R01](../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R01) | `deepseek-flash` | 220/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_tests_20261119/R02](../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R02) | `deepseek-flash` | 220/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_tests_20261119/R03](../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R03) | `deepseek-flash` | 219/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_tests_20261119/R05](../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R05) | `deepseek-flash` | 217/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_tests_20261119/R06](../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R06) | `deepseek-flash` | 220/280 | 完整 Test |
| [spreadsheetbench_v25_8_round_tests_20261119/R07](../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R07) | `deepseek-flash` | 227/280 | 完整 Test |
| [v25_8/v25_8_spreadsheetbench_official_20261118_232447/test](../../artifacts/methods/v25_8/v25_8_spreadsheetbench_official_20261118_232447/test) | `deepseek-flash` | 228/280 | 完整 Test |

</details>

<details>
<summary>SkillAdam（29 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [spreadsheetbench_skilladam_1120_final_gpt54mini_20261120/test](../../artifacts/analysis/spreadsheetbench_skilladam_1120_final_gpt54mini_20261120/test) | `gpt-5.4-mini` | 177/280 | 完整 Test |
| [spreadsheetbench_skilladam_first_rounds_20261113/R01](../../artifacts/analysis/spreadsheetbench_skilladam_first_rounds_20261113/R01) | `deepseek-flash` | 223/280 | 完整 Test |
| [spreadsheetbench_skilladam_first_rounds_20261113/R02](../../artifacts/analysis/spreadsheetbench_skilladam_first_rounds_20261113/R02) | `deepseek-flash` | 225/280 | 完整 Test |
| [spreadsheetbench_skilladam_first_rounds_20261113/R04](../../artifacts/analysis/spreadsheetbench_skilladam_first_rounds_20261113/R04) | `deepseek-flash` | 227/280 | 完整 Test |
| [spreadsheetbench_skilladam_first_rounds_20261113/R05](../../artifacts/analysis/spreadsheetbench_skilladam_first_rounds_20261113/R05) | `deepseek-flash` | 230/280 | 完整 Test |
| [spreadsheetbench_skilladam_v41_rounds_20261116/R00](../../artifacts/analysis/spreadsheetbench_skilladam_v41_rounds_20261116/R00) | `deepseek-v4.1-flash` | 210/280 | 完整 Test |
| [spreadsheetbench_skilladam_v41_rounds_20261116/R01](../../artifacts/analysis/spreadsheetbench_skilladam_v41_rounds_20261116/R01) | `deepseek-v4.1-flash` | 229/280 | 完整 Test |
| [spreadsheetbench_skilladam_v41_rounds_20261116/R02](../../artifacts/analysis/spreadsheetbench_skilladam_v41_rounds_20261116/R02) | `deepseek-v4.1-flash` | 219/280 | 完整 Test |
| [spreadsheetbench_skilladam_v41_rounds_20261116/R05](../../artifacts/analysis/spreadsheetbench_skilladam_v41_rounds_20261116/R05) | `deepseek-v4.1-flash` | 225/280 | 完整 Test |
| [spreadsheetbench_skilladam_v41_rounds_20261116/R07](../../artifacts/analysis/spreadsheetbench_skilladam_v41_rounds_20261116/R07) | `deepseek-v4.1-flash` | 233/280 | 完整 Test |
| [spreadsheetbench_v25_6_skilladam_rounds_20261112/SkillAdam_R02](../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/SkillAdam_R02) | `deepseek-flash` | 207/280 | 完整 Test |
| [skilladam_v25_1_actor_aligned_20261030_001_full_40w_20261108_1710](../../artifacts/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001_full_40w_20261108_1710) | `deepseek-flash` | 230/280 | 完整 Test |
| [skilladam_v25_1_actor_aligned_20261030_001_test280](../../artifacts/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001_test280) | `deepseek-flash` | 229/280 | 完整 Test |
| [spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_skilladam_test280](../../artifacts/methods/skilladam/spreadsheetbench/shared_actor/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_skilladam_test280) | `deepseek-v4.1-flash` | 231/280 | 完整 Test |
| [skilladam_spreadsheetbench_v25_5_feedback_20261108_234037_test280](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261108_234037_test280) | `deepseek-flash` | 223/280 | 完整 Test |
| [trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261112_201115/test280](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261112_201115/test280) | `deepseek-flash` | 220/280 | 完整 Test |
| [trajectory_feedback/skilladam_spreadsheetbench_v41_feedback_20261116_142340/test280](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_feedback_20261116_142340/test280) | `deepseek-v4.1-flash` | 222/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R02_R05_R06_retests_20261120_215624/R02](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R02_R05_R06_retests_20261120_215624/R02) | `deepseek-flash` | 218/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R02_R05_R06_retests_20261120_215624/R05](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R02_R05_R06_retests_20261120_215624/R05) | `deepseek-flash` | 224/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R02_R05_R06_retests_20261120_215624/R06](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R02_R05_R06_retests_20261120_215624/R06) | `deepseek-flash` | 225/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R05_R06_retests_20261120_130320/R05](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R05_R06_retests_20261120_130320/R05) | `deepseek-flash` | 224/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R05_R06_retests_20261120_130320/R06](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R05_R06_retests_20261120_130320/R06) | `deepseek-flash` | 225/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R06_fourth_test_20261120_133647/R06](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R06_fourth_test_20261120_133647/R06) | `deepseek-flash` | 228/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R06_third_test_20261120_132028/R06](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R06_third_test_20261120_132028/R06) | `deepseek-flash` | 230/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/checkpoint_tests_20261120_124039/R01](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/checkpoint_tests_20261120_124039/R01) | `deepseek-flash` | 222/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/checkpoint_tests_20261120_124039/R02](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/checkpoint_tests_20261120_124039/R02) | `deepseek-flash` | 220/280 | 完整 Test |
| [skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/checkpoint_tests_20261120_124039/R05](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/checkpoint_tests_20261120_124039/R05) | `deepseek-flash` | 231/280 | 完整 Test |
| [trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/test280](../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/test280) | `deepseek-flash` | 220/280 | 完整 Test |
| [v25_skilladam_upstream_actor_prompt_20261030_001_skilladam_test280](../../artifacts/methods/skilladam/spreadsheetbench/upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam_test280) | `deepseek-flash` | 220/280 | 完整 Test |

</details>

<details>
<summary>SkillOpt（9 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [spreadsheetbench_skillopt_R02_pre_placeholder_retest280_20261123_SsyMlq/test](../../artifacts/analysis/spreadsheetbench_skillopt_R02_pre_placeholder_retest280_20261123_SsyMlq/test) | `deepseek-flash` | 220/280 | 完整 Test |
| [spreadsheetbench_skillopt_R02_pre_placeholder_test280_20261123_82RTMo/test](../../artifacts/analysis/spreadsheetbench_skillopt_R02_pre_placeholder_test280_20261123_82RTMo/test) | `deepseek-flash` | 228/280 | 完整 Test |
| [spreadsheetbench_skillopt_R02_pre_placeholder_third280_20261123_qSd9pv/test](../../artifacts/analysis/spreadsheetbench_skillopt_R02_pre_placeholder_third280_20261123_qSd9pv/test) | `deepseek-flash` | 226/280 | 完整 Test |
| [spreadsheetbench_skillopt_final_gpt54mini_20261124/test](../../artifacts/analysis/spreadsheetbench_skillopt_final_gpt54mini_20261124/test) | `gpt-5.4-mini` | 178/280 | 完整 Test（含独立补测） |
| [spreadsheetbench_skillopt_r07_retest_20261122_204550/test](../../artifacts/analysis/spreadsheetbench_skillopt_r07_retest_20261122_204550/test) | `deepseek-flash` | 220/280 | 完整 Test |
| [spreadsheetbench_skillopt_r07_third_20261122_205639/test](../../artifacts/analysis/spreadsheetbench_skillopt_r07_third_20261122_205639/test) | `deepseek-flash` | 221/280 | 完整 Test |
| [spreadsheetbench_skillopt_step_tests_20261122_214430/R01](../../artifacts/analysis/spreadsheetbench_skillopt_step_tests_20261122_214430/R01) | `deepseek-flash` | 223/280 | 完整 Test |
| [spreadsheetbench_skillopt_step_tests_20261122_214430/R02](../../artifacts/analysis/spreadsheetbench_skillopt_step_tests_20261122_214430/R02) | `deepseek-flash` | 224/280 | 完整 Test |
| [skillopt/spreadsheetbench_v25_8/test](../../artifacts/methods/skillopt/spreadsheetbench_v25_8/test) | `deepseek-flash` | 226/280 | 完整 Test |

</details>

<details>
<summary>共用对照（4 个现场）</summary>

| 实际评测现场 | Actor | 成功／已评分 | 状态 |
|---|---|---:|---|
| [spreadsheetbench_v25_6_skilladam_rounds_20261112/shared_R00](../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/shared_R00) | `deepseek-flash` | 203/280 | 完整 Test |
| [no_skill](../../experiments/baselines/spreadsheetbench_controls_actor32k_w4_20261026/no_skill) | `deepseek-v4.1-flash` | 173/212 | 停止 |
| [initial_skill](../../experiments/evaluations/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001/four_way/results/initial_skill) | `deepseek-v4.1-flash` | 215/280 | 完整 Test |
| [no_skill](../../experiments/evaluations/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001/four_way/results/no_skill) | `deepseek-v4.1-flash` | 222/280 | 完整 Test |

</details>

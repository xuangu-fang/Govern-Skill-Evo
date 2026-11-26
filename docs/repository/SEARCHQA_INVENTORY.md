# SearchQA v28–v28.16 整理盘点与旧路径映射

[三方法主对照已归档](../../experiments/methods/SEARCHQA.md)，实际提取路径及核验依据见[主对照清单](../../experiments/benchmarks/searchqa/main-comparison.json)。

v28.11–v28.15 的五次训练和 20 次 Test1400 已归档。实验入口、受测 Skill 与实际提取路径见[历史验收清单](../../experiments/benchmarks/searchqa/v28_11-v28_15.json)及[离线复算回执](../../experiments/benchmarks/searchqa/v28_11-v28_15-verification.json)。

v28–v28.10、SkillAdam 和 SkillOpt 的历史基线及跨 Actor 补充评测已归档。三批验收清单覆盖盘点中的全部 39 条训练记录和 96 次评测。[早期与基线验收清单](../../experiments/benchmarks/searchqa/remaining-history.json) · [离线复算回执](../../experiments/benchmarks/searchqa/remaining-history-verification.json)

盘点日期为 2026-11-26，分支 `wyy/day57-tau-autonomous-gse-v25`，Git 基线 `5b1c43dae8b`。盘点纳入当前工作树的已跟踪、未跟踪和忽略材料，并注明外部检出。原始材料只读，拟议位置登记在 [结构化清单与路径映射](searchqa-inventory.json)。

共登记 **39 条训练记录、96 条评测记录、1,057 条路径规则**。训练中有 31 条已完成。评测包含 94 次完整 Test1400 和 2 次早期 SkillOpt Test100。逐题回算覆盖 131,800 份评分。另有 7 个预定测试位置，只有历史调度回执。

## 版本与基线

| 版本或方法 | 训练记录 | 完成训练 | 完整 Test1400 | 历史 Test100 |
| --- | ---: | ---: | ---: | ---: |
| [v28](../methods/v28/EXPERIMENT_PROTOCOL.md) | 4 | 1 | 1 | 0 |
| [v28.1](../methods/v28_1/README.md) | 1 | 1 | 1 | 0 |
| [v28.2](../methods/v28_2/README.md) | 1 | 0 | 0 | 0 |
| [v28.3](../methods/v28_3/README.md) | 1 | 1 | 1 | 0 |
| [v28.4](../methods/v28_4/README.md) | 1 | 1 | 1 | 0 |
| [v28.5](../methods/v28_5/README.md) | 4 | 2 | 3 | 0 |
| [v28.6](../../scripts/runs/run_v28_6_campaign.py) | 2 | 2 | 2 | 0 |
| [v28.7](../../scripts/runs/run_v28_7_campaign.py) | 2 | 2 | 2 | 0 |
| [v28.8](../methods/v28_8/README.md) | 3 | 3 | 4 | 0 |
| [v28.9](../methods/v28_9/README.md) | 1 | 1 | 2 | 0 |
| [v28.10](../methods/v28_10/README.md) | 1 | 1 | 1 | 0 |
| [v28.11](../methods/v28_11/README.md) | 1 | 1 | 7 | 0 |
| [v28.12](../methods/v28_12/README.md) | 1 | 1 | 8 | 0 |
| [v28.13](../methods/v28_13/README.md) | 1 | 1 | 2 | 0 |
| [v28.14](../methods/v28_14/README.md) | 1 | 1 | 2 | 0 |
| [v28.15](../methods/v28_15/README.md) | 1 | 1 | 1 | 0 |
| [v28.16](../methods/v28_16/README.md) | 1 | 1 | 14 | 0 |
| [SkillAdam](../../scripts/runs/run_searchqa_skilladam.py) | 9 | 7 | 24 | 0 |
| [SkillOpt](../../scripts/runs/skillopt/searchqa/README.md) | 3 | 3 | 17 | 2 |
| [共用 R00 原始汇总](../../experiments/evaluations/searchqa_checkpoints_20261111/R00/summary.json) | 0 | 0 | 1 | 0 |

- **早期 v28。** Batch15 到 R10 中断，初版 batch30 到 R09 暂停，优化版 batch30 在 R06 后归档。Replay v3 完成 20 轮，终测 **1,164/1,400**。优化版预定的 Test 目录为空。另外两份 v28 预定测试路径和 batch15 SkillAdam 的预定测试目录当前未定位。[优化版归档状态](../../experiments/comparisons/v28_searchqa_optimized_batch30_20261102_131410/v28_status.json) · [Replay v3 评测](../../experiments/evaluations/v28_searchqa1400_replayv3_batch30_20261102_175059/report.json)
- **v28.1、v28.2、v28.5。** v28.1 的 R15 停止回执属于历史中断，后续完成 20 轮和独立 Test1400。v28.2 在 R03 后暂停。v28.5 的两次 batch30 运行分别停在 R05 和 R04，两次 batch60 运行各完成十轮。[v28.1 最终状态](../../experiments/comparisons/v28_1_searchqa_batch30_20261103/v28_1_status.json) · [v28.2 暂停回执](../../experiments/automations/v28_2_searchqa600_batch30_promptv2_20261104_010013/status.json) · [v28.5 方法文档](../methods/v28_5/README.md)
- **SkillAdam。** 11 月 16 日 12:13 的记录停在首轮完成前，12:30 的独立运行完成十轮并用于主图。11 月 8 日的对齐训练有一次 **1,202/1,400**，归在该训练名下。上游最佳 Skill 的 **1,179/1,400** 单独登记，其受测文本与本地上游样本字节一致。[12:13 检查点](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261116_121322/native/checkpoint.json) · [11 月 8 日评测](../../experiments/evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261108_224443/report.json) · [上游最佳 Skill 评测](../../experiments/evaluations/searchqa_skilladam/open_source_best_test1400_20261106_164155/report.json)
- **SkillOpt。** 11 月 22 日启动的正式版和 11 月 23 日启动的重试版各完成 40 步。正式版 Step 2 的最佳 Skill、正式版 Epoch 末 Skill 和重试版 Step 40 慢更新生成的 Skill 各有独立评测。早期 Main200 对照的初始和最佳 Skill 使用同一 100 题，精确匹配分别为 **90/100** 和 **91/100**。[正式版选优](../../experiments/baselines/searchqa_skillopt_deepseek_flash/selection.json) · [重试版选优](../../experiments/baselines/searchqa_skillopt_retry_20261123_180000/selection.json) · [Main200 记录](../../experiments/results/skillopt_searchqa_main200_hard_s42/README.md)

## 现有主对照的原始证据

三种方法的初始 Skill 与共用 R00 的受测文件逐字节一致。共用评测在 v28.12 的逐轮现场完成，结果为 **1,064/1,400（76.00%）**。[共用 R00 原始汇总](../../experiments/evaluations/searchqa_checkpoints_20261111/R00/summary.json)

| 方法 | 原训练 ID | 最终 Skill 各次完整测试的 EM 题数 | 主图采用的次数与结果 |
| --- | --- | --- | --- |
| v28.16 | [v28_16_searchqa600_batch60_20261112_132531](../../experiments/campaigns/v28_16_searchqa600_batch60_20261112_132531) | [1,193](../../experiments/evaluations/v28_16_searchqa600_batch60_20261112_132531_test1400/summary.json)、[1,180](../../experiments/evaluations/searchqa_v28_16_R03_R10_serial_retest_20261119_225640/R10/summary.json)、[1,182](../../experiments/evaluations/searchqa_v28_16_R10_parallel_retests_20261119_231518/retest2/summary.json)、[1,178](../../experiments/evaluations/searchqa_v28_16_R10_parallel_retests_20261119_231518/retest3/summary.json)、[1,200](../../experiments/evaluations/searchqa_v28_16_R10_retest4_20261119_233122/R10/summary.json) | [1,193](../../experiments/evaluations/v28_16_searchqa600_batch60_20261112_132531_test1400/summary.json)、[1,182](../../experiments/evaluations/searchqa_v28_16_R10_parallel_retests_20261119_231518/retest2/summary.json)、[1,200](../../experiments/evaluations/searchqa_v28_16_R10_retest4_20261119_233122/R10/summary.json)，中位数 **1,193/1,400** |
| SkillAdam | [v28_11_aligned_batch60_20261116_123000](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000) | [1,160](../../experiments/evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000/report.json)、[1,164](../../experiments/evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_retest_20261116_134454/report.json)、[1,162](../../experiments/evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_retest2_20261119_234857/report.json) | [1,160](../../experiments/evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000/report.json)、[1,164](../../experiments/evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_retest_20261116_134454/report.json)、[1,162](../../experiments/evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_retest2_20261119_234857/report.json)，中位数 **1,162/1,400** |
| SkillOpt | [searchqa_skillopt_retry_20261123_180000](../../experiments/baselines/searchqa_skillopt_retry_20261123_180000) | [1,182](../../experiments/baselines/searchqa_skillopt_retry_20261123_180000/test/report.json)、[1,185](../../experiments/evaluations/searchqa_skillopt_retry_best_retest_20261123_223214/report.json)、[1,195](../../experiments/evaluations/searchqa_skillopt_retry_best_retest_20261123_223706/report.json)、[1,188](../../experiments/evaluations/searchqa_skillopt_retry_best_retest_20261124_120141/report.json) | [1,182](../../experiments/baselines/searchqa_skillopt_retry_20261123_180000/test/report.json)、[1,185](../../experiments/evaluations/searchqa_skillopt_retry_best_retest_20261123_223214/report.json)、[1,188](../../experiments/evaluations/searchqa_skillopt_retry_best_retest_20261124_120141/report.json)，中位数 **1,185/1,400** |

- v28.16 的 R08–R10 保存同一最终 Skill。五次完整测试的中位数为 **1,182/1,400**。现有图按日志采用首测、第二次和第四次复测的中位数 **1,193/1,400**。
- SkillOpt 的四次完整测试都使用同一最终 Skill，其中一次为 **1,195/1,400**。现有图采用第 1、2、4 次测试的中位数 **1,185/1,400**。图中 Step 10 的受测文本与该步 `candidate_skill.md` 字节一致，和 `skill_v0010.md` 有字节差异。[Step 10 受测 Skill](../../experiments/evaluations/searchqa_skillopt_retry_step_retests_20261124_120633/step_0010/skill.md)
- 三种方法的图上逐轮取值、采用的评测路径与累计题次均已登记。DeepSeek Flash 主图累计题次依次为 1,200、1,800、10,520。[现有三方法对照](../04_EXPERIMENT_LOG.md#L7947)
- 跨 Actor 的 GPT-5.4-mini 使用各方法的最终 Skill 和同一组 Test1400，v28.16、SkillAdam、SkillOpt 分别精确匹配 **1,156、1,140、1,141** 题。[跨 Actor 三方法汇总](../../artifacts/analysis/searchqa_skillopt_final_gpt54mini_20261124/comparison.json)

## 数据、运行入口与源码

- 数据锁指向 revision `c1a979068ba118d85467179b704031d113d689cc`，13 个文件的 SHA-256 与锁一致。400 Train、200 Validation、1,400 Test 在 ID 清单与题库副本之间顺序一致，三个划分合计 2,000 个唯一 ID。v28 和 SkillAdam 使用合并后的 600 题优化池，SkillOpt 正式版按 Train400 和独立 Selection200 运行。[数据锁](../../data/searchqa/v28_dataset.lock.json) · [600 题优化视图](../../data/searchqa/v28_train600_v1/manifest.json)
- v28 早期训练使用 `src.skill_evolution.v28.cli`。v28.2–v28.16 有独立版本入口。SkillAdam 使用当前 SearchQA 适配器和独立上游检出，SkillOpt 重试版复用 OfficeQA 优化器。清单记录 142 组直接导入，包括其他方法对 v28 的引用。[v28.16 运行入口](../../scripts/runs/run_v28_16_campaign.py) · [SkillAdam 运行入口](../../scripts/runs/run_searchqa_skilladam.py) · [SkillOpt 重试入口](../../scripts/runs/skillopt/searchqa/retry_experiment.py)
- 主对照 SkillAdam 的冻结源码清单 377 项、SkillOpt 重试版 91 项与现有文件摘要一致。SkillOpt 原正式版的 86 项中有 84 项一致，`scripts/runs/skillopt/searchqa/run.py` 和 `src/skillopt_alfworld_native/transport.py` 有字节差异。清单保留原摘要与现有摘要。[原正式版冻结配置](../../experiments/baselines/searchqa_skillopt_deepseek_flash/run.json)

## 旧路径映射

优先匹配精确旧路径，其次匹配最长目录前缀。目录规则覆盖其余后代并保留相对后缀。拟提取的压缩记录使用原始路径从共享归档还原，`source_sha256` 按原字节计算。

| 操作 | 规则数 | 位置和用途 |
| --- | ---: | --- |
| 原位保留 | 338 | 方法包、数据、完整训练和评测、调度与恢复现场、压缩归档。 |
| 拟提取精选 | 681 | 冻结配置、状态、Skill 和结果复制到实验索引所指位置。 |
| 拟迁移配置 | 31 | 版本与基线模板归相应 `profiles/`，共用初始 Skill 归 `experiments/benchmarks/searchqa/controls/`。 |
| 仅有历史引用 | 7 | 调度中存在预定测试路径，其中一个目录为空，其余 6 个路径未定位。 |

- 自进化实验拟归 `experiments/methods/<v28 版本>/<原实验 ID>/`。SkillAdam 拟归 `experiments/methods/skilladam/searchqa/<配置>/<原实验 ID>/`，SkillOpt 拟归 `experiments/methods/skillopt/searchqa/<原实验 ID>/`。独立评测保留用于区分批次、轮次及复测的路径部分，归相应实验的 `results/`。
- 共用评测和历史对照索引拟归 `experiments/benchmarks/searchqa/`。清单记录 795 组静态路径引用及行号。此项覆盖小型代码、配置、文档和调度文件。大型冻结副本和逐题产物通过目录规则及归档键覆盖。

## 核验结果

- 对 94 次完整测试，读取保存的逐题评分，核对 Test1400 的 ID 集合并回算 EM/F1。对两个历史 Test100 核对题目集合一致并回算精确匹配。现代评测同时记录受测文件 SHA-256。报告有 `skill_sha256` 时，按文件原字节或规范 JSON 字符串口径核对。
- 使用归档工具完整回读 741,221 条记录和 2,555 个附件，原字节 SHA-256 全部通过。743,776 个归档原路径键均能命中唯一优先规则。[归档校验入口](../../experiments/benchmark_record_refs/README.md)
- 路径规则的旧键唯一，所有拟提取或迁移的目标相互无冲突，且当前均无同名目标。此次验证范围是已保存结果、文件与静态引用。独立检出与归位后的运行入口验收留待试点。

## 训练记录明细

评测数量按独立评测回执统计。共用 R00 和上游最佳 Skill 的评测见结构化清单。

| 方法 | 原训练 ID | 状态 | 完成轮或步 | 关联评测 | 证据 |
| --- | --- | --- | ---: | ---: | --- |
| v28 | [v28_searchqa600_20261101_235345](../../experiments/campaigns/v28_searchqa600_20261101_235345) | 中断 | 10 | 0 | [状态回执](../../experiments/comparisons/searchqa_v28_skilladam_20261101_235345/v28_status.json) |
| v28 | [v28_searchqa600_batch30_20261102_022539](../../experiments/campaigns/v28_searchqa600_batch30_20261102_022539) | 暂停 | 9 | 0 | [状态回执](../../experiments/comparisons/searchqa_v28_skilladam_batch30_20261102_022539/v28_status.json) |
| v28 | [v28_searchqa600_optimized_batch30_20261102_131410](../../experiments/campaigns/v28_searchqa600_optimized_batch30_20261102_131410) | 归档未完成 | 6 | 0 | [状态回执](../../experiments/comparisons/v28_searchqa_optimized_batch30_20261102_131410/v28_status.json) |
| v28 | [v28_searchqa600_replayv3_batch30_20261102_175059](../../experiments/campaigns/v28_searchqa600_replayv3_batch30_20261102_175059) | 完成训练 | 20 | 1 | [状态回执](../../experiments/comparisons/v28_searchqa_replayv3_batch30_20261102_175059/v28_status.json) |
| v28.1 | [v28_1_searchqa600_batch30_20261103](../../experiments/campaigns/v28_1_searchqa600_batch30_20261103) | 完成训练 | 20 | 1 | [状态回执](../../experiments/comparisons/v28_1_searchqa_batch30_20261103/v28_1_status.json) |
| v28.2 | [v28_2_searchqa600_batch30_promptv2_20261104_010013](../../experiments/campaigns/v28_2_searchqa600_batch30_promptv2_20261104_010013) | 暂停 | 3 | 0 | [状态回执](../../experiments/automations/v28_2_searchqa600_batch30_promptv2_20261104_010013/status.json) |
| v28.3 | [v28_3_searchqa600_batch30_20261104_022828](../../experiments/campaigns/v28_3_searchqa600_batch30_20261104_022828) | 完成训练 | 20 | 1 | [状态回执](../../experiments/campaigns/v28_3_searchqa600_batch30_20261104_022828/training_summary.json) |
| v28.4 | [v28_4_searchqa600_batch30_20261104_180344](../../experiments/campaigns/v28_4_searchqa600_batch30_20261104_180344) | 完成训练 | 20 | 1 | [状态回执](../../experiments/campaigns/v28_4_searchqa600_batch30_20261104_180344/training_summary.json) |
| v28.5 | [v28_5_searchqa600_batch30_20261104_220800](../../experiments/campaigns/v28_5_searchqa600_batch30_20261104_220800) | 暂停 | 5 | 0 | [状态回执](../../experiments/automations/v28_5_searchqa600_batch30_20261104_220800/status.json) |
| v28.5 | [v28_5_searchqa600_batch30_revised_20261104_225519](../../experiments/campaigns/v28_5_searchqa600_batch30_revised_20261104_225519) | 暂停 | 4 | 0 | [状态回执](../../experiments/automations/v28_5_searchqa600_batch30_revised_20261104_225519/status.json) |
| v28.5 | [v28_5_searchqa600_batch60_promptv2_20261105_021321](../../experiments/campaigns/v28_5_searchqa600_batch60_promptv2_20261105_021321) | 完成训练 | 10 | 2 | [状态回执](../../experiments/campaigns/v28_5_searchqa600_batch60_promptv2_20261105_021321/training_summary.json) |
| v28.5 | [v28_5_searchqa600_batch60_workers60_editor64k_20261104_232720](../../experiments/campaigns/v28_5_searchqa600_batch60_workers60_editor64k_20261104_232720) | 完成训练 | 10 | 1 | [状态回执](../../experiments/campaigns/v28_5_searchqa600_batch60_workers60_editor64k_20261104_232720/training_summary.json) |
| v28.6 | [v28_6_searchqa600_batch60_20261105_120753](../../experiments/campaigns/v28_6_searchqa600_batch60_20261105_120753) | 完成训练 | 10 | 1 | [状态回执](../../experiments/campaigns/v28_6_searchqa600_batch60_20261105_120753/training_summary.json) |
| v28.6 | [v28_6_searchqa600_batch60_coordination_20261105_134053](../../experiments/campaigns/v28_6_searchqa600_batch60_coordination_20261105_134053) | 完成训练 | 10 | 1 | [状态回执](../../experiments/campaigns/v28_6_searchqa600_batch60_coordination_20261105_134053/training_summary.json) |
| v28.7 | [v28_7_searchqa600_batch60_max4_20261105_182434](../../experiments/campaigns/v28_7_searchqa600_batch60_max4_20261105_182434) | 完成训练 | 10 | 1 | [状态回执](../../experiments/campaigns/v28_7_searchqa600_batch60_max4_20261105_182434/training_summary.json) |
| v28.7 | [v28_7_searchqa600_batch60_single_decision_20261105_203944](../../experiments/campaigns/v28_7_searchqa600_batch60_single_decision_20261105_203944) | 完成训练 | 10 | 1 | [状态回执](../../experiments/campaigns/v28_7_searchqa600_batch60_single_decision_20261105_203944/training_summary.json) |
| v28.8 | [v28_8_searchqa600_batch60_20261105_235510](../../experiments/campaigns/v28_8_searchqa600_batch60_20261105_235510) | 完成训练 | 10 | 1 | [状态回执](../../experiments/campaigns/v28_8_searchqa600_batch60_20261105_235510/training_summary.json) |
| v28.8 | [v28_8_searchqa600_batch60_decision_revision_v1_20261106_032534](../../experiments/campaigns/v28_8_searchqa600_batch60_decision_revision_v1_20261106_032534) | 完成训练 | 10 | 2 | [状态回执](../../experiments/campaigns/v28_8_searchqa600_batch60_decision_revision_v1_20261106_032534/training_summary.json) |
| v28.8 | [v28_8_searchqa600_batch60_workflow_error_avoidance_20261106_020209](../../experiments/campaigns/v28_8_searchqa600_batch60_workflow_error_avoidance_20261106_020209) | 完成训练 | 10 | 1 | [状态回执](../../experiments/campaigns/v28_8_searchqa600_batch60_workflow_error_avoidance_20261106_020209/training_summary.json) |
| v28.9 | [v28_9_searchqa600_batch60_reusable_actions_v1_20261106_120000](../../experiments/campaigns/v28_9_searchqa600_batch60_reusable_actions_v1_20261106_120000) | 完成训练 | 10 | 2 | [状态回执](../../experiments/campaigns/v28_9_searchqa600_batch60_reusable_actions_v1_20261106_120000/training_summary.json) |
| v28.10 | [v28_10_searchqa600_batch60_reusable_increment_v1_20261106_180953](../../experiments/campaigns/v28_10_searchqa600_batch60_reusable_increment_v1_20261106_180953) | 完成训练 | 10 | 1 | [状态回执](../../experiments/campaigns/v28_10_searchqa600_batch60_reusable_increment_v1_20261106_180953/training_summary.json) |
| v28.11 | [v28_11_searchqa600_batch60_decision_boundaries_v1_20261107_014938](../../experiments/campaigns/v28_11_searchqa600_batch60_decision_boundaries_v1_20261107_014938) | 完成训练 | 10 | 7 | [状态回执](../../experiments/campaigns/v28_11_searchqa600_batch60_decision_boundaries_v1_20261107_014938/training_summary.json) |
| v28.12 | [v28_12_searchqa600_batch60_20261109_024436](../../experiments/campaigns/v28_12_searchqa600_batch60_20261109_024436) | 完成训练 | 10 | 8 | [状态回执](../../experiments/campaigns/v28_12_searchqa600_batch60_20261109_024436/training_summary.json) |
| v28.13 | [v28_13_searchqa600_batch60_20261111_220738](../../experiments/campaigns/v28_13_searchqa600_batch60_20261111_220738) | 完成训练 | 10 | 2 | [状态回执](../../experiments/campaigns/v28_13_searchqa600_batch60_20261111_220738/training_summary.json) |
| v28.14 | [v28_14_searchqa600_batch60_20261112_001311](../../experiments/campaigns/v28_14_searchqa600_batch60_20261112_001311) | 完成训练 | 10 | 2 | [状态回执](../../experiments/campaigns/v28_14_searchqa600_batch60_20261112_001311/training_summary.json) |
| v28.15 | [v28_15_searchqa600_batch60_20261112_120121](../../experiments/campaigns/v28_15_searchqa600_batch60_20261112_120121) | 完成训练 | 10 | 1 | [状态回执](../../experiments/campaigns/v28_15_searchqa600_batch60_20261112_120121/training_summary.json) |
| v28.16 | [v28_16_searchqa600_batch60_20261112_132531](../../experiments/campaigns/v28_16_searchqa600_batch60_20261112_132531) | 完成训练 | 10 | 14 | [状态回执](../../experiments/campaigns/v28_16_searchqa600_batch60_20261112_132531/training_summary.json) |
| SkillAdam | [20261101_235345](../../experiments/baselines/searchqa_skilladam/20261101_235345) | 中断 | 19 | 0 | [状态回执](../../experiments/comparisons/searchqa_v28_skilladam_20261101_235345/skilladam_status.json) |
| SkillAdam | [batch30_20261102_022539](../../experiments/baselines/searchqa_skilladam/batch30_20261102_022539) | 完成训练 | 20 | 1 | [状态回执](../../experiments/baselines/searchqa_skilladam/batch30_20261102_022539/native/checkpoint.json) |
| SkillAdam | [batch60_workers60_20261105_004702](../../experiments/baselines/searchqa_skilladam/batch60_workers60_20261105_004702) | 完成训练 | 10 | 2 | [状态回执](../../experiments/baselines/searchqa_skilladam/batch60_workers60_20261105_004702/native/checkpoint.json) |
| SkillAdam | [batch60_workers60_20261106_225120](../../experiments/baselines/searchqa_skilladam/batch60_workers60_20261106_225120) | 完成训练 | 10 | 2 | [状态回执](../../experiments/baselines/searchqa_skilladam/batch60_workers60_20261106_225120/native/checkpoint.json) |
| SkillAdam | [v28_11_aligned_batch60_20261108_224443](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261108_224443) | 完成训练 | 10 | 2 | [状态回执](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261108_224443/native/checkpoint.json) |
| SkillAdam | [v28_11_aligned_batch60_20261109_010205](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261109_010205) | 完成训练 | 10 | 3 | [状态回执](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261109_010205/native/checkpoint.json) |
| SkillAdam | [v28_11_aligned_batch60_20261113_181314](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261113_181314) | 完成训练 | 10 | 6 | [状态回执](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261113_181314/native/checkpoint.json) |
| SkillAdam | [v28_11_aligned_batch60_20261116_121322](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261116_121322) | 启动后未完成首轮 | 0 | 0 | [状态回执](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261116_121322/native/checkpoint.json) |
| SkillAdam | [v28_11_aligned_batch60_20261116_123000](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000) | 完成训练 | 10 | 7 | [状态回执](../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000/native/checkpoint.json) |
| SkillOpt | [searchqa_skillopt_deepseek_flash](../../experiments/baselines/searchqa_skillopt_deepseek_flash) | 完成训练 | 40 | 5 | [状态回执](../../experiments/baselines/searchqa_skillopt_deepseek_flash/selection.json) |
| SkillOpt | [searchqa_skillopt_retry_20261123_180000](../../experiments/baselines/searchqa_skillopt_retry_20261123_180000) | 完成训练 | 40 | 12 | [状态回执](../../experiments/baselines/searchqa_skillopt_retry_20261123_180000/selection.json) |
| SkillOpt | [skillopt_searchqa_main200_hard_s42](../../experiments/results/skillopt_searchqa_main200_hard_s42) | 完成训练 | 5 | 2 | [状态回执](../../experiments/results/skillopt_searchqa_main200_hard_s42/summary.json) |

# DocVQA 全量盘点与路径映射

盘点日期为 2026-11-26。基线为 `wyy/day57-tau-autonomous-gse-v25` 的 `5b1c43dae8b2`。范围为当前工作树中 v29–v29.11、DocVQA SkillAdam 与 SkillOpt、共用 R00、历史调度、专项分析、源码、数据及两套图片归档。盘点包含未跟踪和忽略的本地材料。

登记 **23 条训练、续跑及准备记录**，其中 **18 条完成训练**。**60 次独立 Test374** 全部通过逐题复算，共 **22,440 份评分**。**1,623 条路径规则** 覆盖两套归档的 **158,399 个归档键**。同一份 Skill 的独立复测各计一次，复用成绩的轮次和比较报告沿用原评测 ID。

[结构化清单与路径映射](docvqa-inventory.json)逐条记录实验原 ID、状态证据、训练及评测的对应关系、受测 Skill 的 SHA-256、实际 Actor、题目集合指纹、原始和拟议路径，以及静态引用和源码冻结比对。

三组主对照样板已经完成，实际提取位置及复核命令见 [DocVQA 实验索引](../../experiments/methods/DOCVQA.md) 和 [样板验收清单](../../experiments/benchmarks/docvqa/main-comparison.json)。v29.8–v29.10 的历史实验也已提取并通过离线复算，见 [历史验收清单](../../experiments/benchmarks/docvqa/v29_8-v29_10.json)。v29.3–v29.7 的 8 次完成训练及 11 次完整评测也已提取并通过离线复算，见 [历史验收清单](../../experiments/benchmarks/docvqa/v29_3-v29_7.json)。v29–v29.2 和早期 SkillAdam 的剩余 6 次评测已归档，60 次 Test374 均纳入 [全量离线验收](../../experiments/benchmarks/docvqa/all-evaluations.json)。下文的全量映射保留初次盘点时的规划口径。

## 各版本与基线

| 版本或方法 | 训练、续跑及准备 | 完成训练 | 独立 Test374 | 其中跨 Actor |
| --- | ---: | ---: | ---: | ---: |
| v29 | 1 | 1 | 1 | 0 |
| v29.1 | 1 | 1 | 1 | 0 |
| v29.2 | 5 | 1 | 1 | 0 |
| v29.3 | 2 | 2 | 2 | 0 |
| v29.4 | 2 | 1 | 1 | 0 |
| v29.5 | 1 | 1 | 1 | 0 |
| v29.6 | 2 | 2 | 2 | 0 |
| v29.7 | 2 | 2 | 5 | 0 |
| v29.8 | 1 | 1 | 7 | 0 |
| v29.9 | 1 | 1 | 1 | 0 |
| v29.10 | 1 | 1 | 1 | 0 |
| v29.11 | 1 | 1 | 10 | 1 |
| SkillAdam | 2 | 2 | 20 | 1 |
| SkillOpt | 1 | 1 | 6 | 1 |
| 共用 | 0 | 0 | 1 | 0 |

- **v29.2** 原运行提交到 R06，R07 Replay 的六次冻结请求额度用尽。第一次迁移续跑被停止，两次失败的准备目录和旧续跑只剩删除回执。缩短 Prompt 后的续跑复用了迁移路径和原实验 ID，完成 11 轮并产出 326/374。清单用独立记录键保留各次状态。 [原运行停止](../../experiments/campaigns/v29_2_docvqa160_epoch1_20261103_185548/stop.json) · [迁移删除回执](../../experiments/automations/v29_2_prompt_compact_restart_20261103/deletion_receipt.json) · [续跑结项](../../experiments/campaigns/migrations/v29_2_references_v4_20261103/v29_2_docvqa160_epoch1_20261103_185548/training_summary.json)

- **v29.3 与 v29.4** 保留首次失败或停止的证据。v29.3 原 Test 启动失败，恢复同一份 R11 Skill 后完成 374 题，计为一次完整评测。v29.4 的旧 Editor 16,384 token 运行按历史回执中止并删除，未启动 Test。32,768 token 运行用新 ID 从初始 Skill 训练。 [v29.3 首次失败](../../experiments/automations/v29_3_docvqa_test374_20261103/status.json) · [v29.3 恢复结项](../../experiments/automations/v29_3_docvqa_test374_20261103_light_runtime/status.json) · [v29.4 重启回执](../../experiments/automations/v29_4_docvqa160_editor32768_20261104_015530/reset_receipt.json)

- **SkillAdam** 的 11 月 2 日和 11 月 8 日训练分别登记，11 月 5 日开源最佳 Skill 两次本地评测另行登记。共用 R00 为 303/374，与三组主实验各自的初始 Skill 字节一致。现存的独立对照评分回执为初始 Skill R00。 [早期训练](../../experiments/baselines/docvqa_skilladam/docvqa160_epoch1_20261102_231431/training_summary.json) · [开源最佳 Skill 首测](../../experiments/evaluations/docvqa_skilladam/official_best_skill_test374_20261105_171151/evaluation.json) · [共用 R00](../../experiments/evaluations/docvqa_checkpoints_20261111/R00/summary.json)

## 三组主对照的原始证据

| 方法与训练 | DeepSeek Flash 各次终测 Hard 题数 | 图中中位数 | 全部终测中位数 | 训练与验证题次 | GPT‑5.4‑mini Hard · ANLS |
| --- | --- | ---: | ---: | ---: | --- |
| [v29.11](../../experiments/campaigns/v29_11_docvqa160_20261117_180000/training_summary.json) | [330](../../experiments/evaluations/v29_11_docvqa160_20261117_180000_test374/summary.json)、[324](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R11_retest/summary.json)、[333](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R11_third/summary.json)、[327](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R11_fourth/summary.json)、[326](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R11_fifth/summary.json) | 330/374 | 327/374 | 290 | [341/374 · 95.56%](../../artifacts/analysis/docvqa_v29_11_skilladam_1108_gpt54mini_20261120/v29.11/summary.json) |
| [SkillAdam](../../experiments/baselines/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230/training_summary.json) | [325](../../experiments/evaluations/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230/summary.json)、[321](../../experiments/evaluations/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230_test374_repeat2/summary.json)、[319](../../experiments/evaluations/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230_test374_repeat3/summary.json) | 321/374 | 321/374 | 480 | [339/374 · 95.78%](../../artifacts/analysis/docvqa_v29_11_skilladam_1108_gpt54mini_20261120/SkillAdam/summary.json) |
| [SkillOpt](../../experiments/baselines/docvqa_skillopt_deepseek_flash/selection.json) | [316](../../experiments/baselines/docvqa_skillopt_deepseek_flash/test/summary.json)、[317](../../experiments/baselines/docvqa_skillopt_deepseek_flash/test_repeat_2/summary.json)、[325](../../experiments/baselines/docvqa_skillopt_deepseek_flash/test_repeat_3/summary.json) | 317/374 | 317/374 | 1,396 | [338/374 · 96.19%](../../artifacts/analysis/docvqa_skillopt_final_gpt54mini_20261124/SkillOpt/summary.json) |

v29.11 的历史图采用前三次终测的 Hard 中位数 **330/374（88.24%）**，纳入后两次后为 **327/374（87.43%）**。逐轮原始回执按实际保留的 Skill 绑定，复用轮次沿用同一评测记录。累计题次从训练和验证的批次回执重算，v29.11 为 160 次 Parent 加 130 次 Candidate，SkillAdam 为三条各 160 次的训练和验证路径。SkillOpt 计入初始 Selection、普通更新和慢更新。 [现有主图取值](../04_EXPERIMENT_LOG.md#L7975) · [累计题次图](../figures/DocVQA-test-success-by-cumulative-episodes.png)

SkillOpt 的正式 Best 来自 12 个普通更新步中的第 7 步，在 Val53 上通过 **46/53**。Step02 的原始实测为 **324/374**，含 epoch 1 空慢更新占位段的 Step03 实测为 **320/374**，两份 Skill 的哈希不同。旧逐步记录对 Step03–Step06 沿用 Step03，现有总图采用 Step02 的成绩；清单保留两种展示口径及两次独立评测。 [Step02](../../experiments/evaluations/docvqa_skillopt_checkpoints_20261123/Step02/summary.json) · [Step03](../../experiments/evaluations/docvqa_skillopt_checkpoints_20261123/Step03/summary.json) · [旧逐步记录](../../experiments/evaluations/docvqa_skillopt_checkpoints_20261123/%E9%80%90%E6%AD%A5%E6%B5%8B%E8%AF%95%E7%BB%93%E6%9E%9C.md)

## 路径规则与归档

精确文件规则优先，其余文件使用最长的目录前缀，保留相对后缀。精选路径是拟新增副本。归档键仍由各自的还原器按原路径访问，`deferred_runtime_target` 只记录后续迁移候选。旧现场被删除后复用路径的情况，保留历史回执，物理路径归当前现场。

| 操作 | 数量 | 目标与用途 |
| --- | ---: | --- |
| 拟提取精选 | 1,234 | v29 系列归 `experiments/methods/<版本>/<原实验 ID>/`。SkillAdam、SkillOpt 归各自的 `docvqa/` 层级，共用对照与跨方法材料归 `experiments/benchmarks/docvqa/`。 |
| 拟迁移配置 | 18 | 训练模板归各版本或基线的 `profiles/`，迁移时同步核对启动入口默认路径、冻结字节哈希和引用。 |
| 原位保留 | 367 | 原始运行、压缩归档、代码包、外部依赖、图表、数据以及共享接口。 |
| 回执存留 | 4 | 已删除的旧目录。曾经复用的迁移路径另由训练记录标注。 |

- 新版 SQLite 归档以仓库根目录为基准，本次展开验证 **87,369 个文件**，并校验 **439 张发布版 PNG** 的 SHA-256。旧版逐轮归档以 `experiments/evaluations/` 为基准，本次验证 **71,030 个文件**，并核对仓库内图片库 **329 张 PNG** 的内容哈希。两套归档键无重叠，全部源文件可达且可映射。 [新版还原入口](../../experiments/docvqa_image_refs/README.md) · [早期还原入口](../../experiments/evaluations/docvqa_checkpoints_shared_images_20261117/README.md)

- 精选及配置共 **1,252 个目标**，逐个检查目标唯一且当前无文件占用。新旧路径、源文件哈希、Git 状态、归档键数及提取规则查 JSON 的 `path_mapping`。引用扫描在代码、配置、文档、启动记录和选定冻结文件中登记了 **666 组**源文件与旧路径的命中位置。

## 数据、依赖与复现边界

- 全部 Test374 使用发布版 `539088ef8a8ada01ac8e2e6d4e372586748a265e` 中同一组 374 个题目 ID。v29 与 SkillAdam 合并 Train107 和 Val53 得到 160 道优化题。SkillOpt 保留独立 Val53 选优。原生评分从已存普通回答抽取答案，并对同版参考答案复算 ANLS，单题 ANLS ≥ 0.999 记为 Hard 通过。逐题回执的答案、指标和受测 Skill 与对应汇总核对一致。 [数据发布清单](../../data/docvqa/releases/539088ef8a8ada01ac8e2e6d4e372586748a265e/dataset_info.json) · [原生评分器](../../src/skill_evolution/skilladam/upstream/skilladam/benchmarks/docvqa/evaluation.py)

- 静态导入登记 **130 个模块**。v29.11 的共享 Actor 来自 v29，执行和回放边界复用 v29.2，其离线入口还直接读取 v29.10 的训练目录和配置。SkillAdam 和 SkillOpt 的启动器引用本地 external 工作树。部分本地源码未纳入 Git，当前核验基于现有工作树及归档。v29.9–v29.11 有实现、配置、测试与原始训练，方法说明目前可从实验日志和实现文件进入。 [v29.11 依赖入口](../../scripts/verification/verify_v29_11_campaign.py#L80) · [共享 Actor 接入](../../src/skill_evolution/v29_11/campaign.py#L4) · [SkillOpt 启动入口](../../scripts/runs/skillopt/docvqa/run.py#L13)

- 对比 **15 份冻结清单的 766 项源码哈希**，其中 **52 项**与现工作树不同，全部能定位到当前文件。v29.11 的 **8/46 项差异**已由用户确认为训练后的有意修改，作为历史记录。SkillOpt 的 **1/86 项差异**对应共享 transport，待训练复现验收时核对。两份主实验的既有 Test 回执均通过逐题复算。 [v29.11 冻结实现](../../experiments/campaigns/v29_11_docvqa160_20261117_180000/implementation.json) · [SkillOpt 冻结运行配置](../../experiments/baselines/docvqa_skillopt_deepseek_flash/run.json)

- 现有 v29.11 离线入口的 **4 项绑定测试通过**。直接读取压缩现场时，端到端预检停在 v29.10 R01 第一题的 Actor 签名。该文件经 SQLite 清单在内存中展开并核对原始哈希后，与 Actor 重新生成的签名一致。预检现已接入图片归档读取，4 项绑定测试和 R01–R11 的 Diagnosis、Preconditioner 与 Editor 交接检查均通过。 [故障点签名](../../experiments/campaigns/v29_10_docvqa160_20261117_131315/rounds/R01/parent_runs/actor/0001/signature.json) · [预检入口](../../scripts/verification/verify_v29_11_campaign.py#L80)

## 逐条训练与评测

<details>
<summary>v29（1 条训练或历史记录，1 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_docvqa160_epoch1_20261102_184845](../../experiments/campaigns/v29_docvqa160_epoch1_20261102_184845/training_summary.json) | 完成训练 | 11 | 1 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_docvqa160_epoch1_20261102_184845](../../experiments/evaluations/v29_docvqa160_epoch1_20261102_184845/summary.json) | 终测首测 | `deepseek-flash` | 322/374 | 94.53% |

</details>

<details>
<summary>v29.1（1 条训练或历史记录，1 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_1_docvqa160_epoch1_20261103_001](../../experiments/campaigns/v29_1_docvqa160_epoch1_20261103_001/training_summary.json) | 完成训练 | 11 | 1 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_1_docvqa160_epoch1_20261103_001](../../experiments/evaluations/v29_1_docvqa160_epoch1_20261103_001/summary.json) | 终测首测 | `deepseek-flash` | 321/374 | 93.54% |

</details>

<details>
<summary>v29.2（5 条训练或历史记录，1 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_2_docvqa160_epoch1_20261103_185548](../../experiments/campaigns/migrations/v29_2_references_v4_20261103/v29_2_docvqa160_epoch1_20261103_185548/training_summary.json) | 完成训练 | 11 | 1 |
| [v29_2_docvqa160_epoch1_20261103_185548#migration-stopped](../../experiments/automations/v29_2_prompt_compact_restart_20261103/deletion_receipt.json) | 迁移续跑停止（回执存留） | — | 0 |
| [v29_2_docvqa160_epoch1_20261103_185548#original](../../experiments/automations/v29_2_docvqa160_epoch1_20261103_185548/status.json) | 原运行中止 | 6 | 0 |
| [v29_2_references_v4_20261103_prepare01_failed](../../experiments/automations/v29_2_prompt_compact_restart_20261103/deletion_receipt.json) | 迁移准备失败（回执存留） | — | 0 |
| [v29_2_references_v4_20261103_prepare02_failed](../../experiments/automations/v29_2_prompt_compact_restart_20261103/deletion_receipt.json) | 迁移准备失败（回执存留） | — | 0 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_2_docvqa_test374_20261103](../../experiments/evaluations/v29_2_docvqa_test374_20261103/summary.json) | 终测首测 | `deepseek-flash` | 326/374 | 93.68% |

</details>

<details>
<summary>v29.3（2 条训练或历史记录，2 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_3_docvqa160_epoch1_20261103_223457](../../experiments/campaigns/v29_3_docvqa160_epoch1_20261103_223457/training_summary.json) | 完成训练 | 11 | 1 |
| [v29_3_revised_docvqa_20261104_003026](../../experiments/campaigns/v29_3_revised_docvqa_20261104_003026/training_summary.json) | 完成训练 | 11 | 1 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_3_docvqa_test374_20261103](../../experiments/evaluations/v29_3_docvqa_test374_20261103/summary.json) | 终测首测 | `deepseek-flash` | 322/374 | 94.03% |
| [v29_3_revised_docvqa_20261104_003026](../../experiments/evaluations/v29_3_revised_docvqa_20261104_003026/summary.json) | 终测首测 | `deepseek-flash` | 321/374 | 93.44% |

</details>

<details>
<summary>v29.4（2 条训练或历史记录，1 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_4_docvqa160_editor32768_20261104_015530](../../experiments/campaigns/v29_4_docvqa160_editor32768_20261104_015530/training_summary.json) | 完成训练 | 11 | 1 |
| [v29_4_docvqa160_epoch1_20261104_014817](../../experiments/automations/v29_4_docvqa160_editor32768_20261104_015530/reset_receipt.json) | 中止并删除（回执存留） | — | 0 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_4_docvqa_test374_editor32768_20261104_015530](../../experiments/evaluations/v29_4_docvqa_test374_editor32768_20261104_015530/summary.json) | 终测首测 | `deepseek-flash` | 323/374 | 93.53% |

</details>

<details>
<summary>v29.5（1 条训练或历史记录，1 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_5_docvqa160_20261104_180257](../../experiments/campaigns/v29_5_docvqa160_20261104_180257/training_summary.json) | 完成训练 | 11 | 1 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_5_docvqa_test374_20261104_180257](../../experiments/evaluations/v29_5_docvqa_test374_20261104_180257/summary.json) | 终测首测 | `deepseek-flash` | 331/374 | 94.72% |

</details>

<details>
<summary>v29.6（2 条训练或历史记录，2 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_6_docvqa160_20261105_012220](../../experiments/campaigns/v29_6_docvqa160_20261105_012220/training_summary.json) | 完成训练 | 11 | 1 |
| [v29_6_parent_memory_delta_v1_docvqa160_20261105_033511](../../experiments/campaigns/v29_6_parent_memory_delta_v1_docvqa160_20261105_033511/training_summary.json) | 完成训练 | 11 | 1 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_6_docvqa160_20261105_012220_test374](../../experiments/evaluations/v29_6_docvqa160_20261105_012220_test374/summary.json) | 终测首测 | `deepseek-flash` | 325/374 | 94.13% |
| [v29_6_parent_memory_delta_v1_docvqa160_20261105_033511_test374](../../experiments/evaluations/v29_6_parent_memory_delta_v1_docvqa160_20261105_033511_test374/summary.json) | 终测首测 | `deepseek-flash` | 325/374 | 93.79% |

</details>

<details>
<summary>v29.7（2 条训练或历史记录，5 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_7_docvqa160_20261105_121504](../../experiments/campaigns/v29_7_docvqa160_20261105_121504/training_summary.json) | 完成训练 | 11 | 1 |
| [v29_7_repeat_docvqa160_20261105_131347](../../experiments/campaigns/v29_7_repeat_docvqa160_20261105_131347/training_summary.json) | 完成训练 | 11 | 4 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_7_docvqa160_20261105_121504_test374](../../experiments/evaluations/v29_7_docvqa160_20261105_121504_test374/summary.json) | 终测首测 | `deepseek-flash` | 324/374 | 93.86% |
| [v29_7_repeat_docvqa160_20261105_131347_retest374_20261105_171711](../../experiments/evaluations/v29_7_repeat_docvqa160_20261105_131347_retest374_20261105_171711/summary.json) | 终测复测 | `deepseek-flash` | 328/374 | 94.39% |
| [v29_7_repeat_docvqa160_20261105_131347_test374](../../experiments/evaluations/v29_7_repeat_docvqa160_20261105_131347_test374/summary.json) | 终测首测 | `deepseek-flash` | 330/374 | 95.07% |
| [v29_7_R03](../../experiments/evaluations/docvqa_checkpoints_20261111/v29_7_R03/summary.json) | 逐轮检查点 | `deepseek-flash` | 317/374 | 92.53% |
| [v29_7_R05](../../experiments/evaluations/docvqa_checkpoints_20261111/v29_7_R05/summary.json) | 逐轮检查点 | `deepseek-flash` | 323/374 | 93.45% |

</details>

<details>
<summary>v29.8（1 条训练或历史记录，7 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_8_docvqa160_20261112_125216](../../experiments/campaigns/v29_8_docvqa160_20261112_125216/training_summary.json) | 完成训练 | 11 | 7 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_8_docvqa160_20261112_125216_test374](../../experiments/evaluations/v29_8_docvqa160_20261112_125216_test374/summary.json) | 终测首测 | `deepseek-flash` | 333/374 | 95.37% |
| [v29_8_R02](../../experiments/evaluations/docvqa_v29_8_checkpoints_20261112/v29_8_R02/summary.json) | 逐轮检查点 | `deepseek-flash` | 317/374 | 92.97% |
| [v29_8_R04](../../experiments/evaluations/docvqa_v29_8_checkpoints_20261112/v29_8_R04/summary.json) | 逐轮检查点 | `deepseek-flash` | 320/374 | 93.23% |
| [v29_8_R06](../../experiments/evaluations/docvqa_v29_8_checkpoints_20261112/v29_8_R06/summary.json) | 逐轮检查点 | `deepseek-flash` | 321/374 | 93.10% |
| [v29_8_R07](../../experiments/evaluations/docvqa_v29_8_checkpoints_20261112/v29_8_R07/summary.json) | 逐轮检查点 | `deepseek-flash` | 325/374 | 94.71% |
| [v29_8_R09](../../experiments/evaluations/docvqa_v29_8_checkpoints_20261112/v29_8_R09/summary.json) | 逐轮检查点 | `deepseek-flash` | 328/374 | 93.77% |
| [v29_8_R10](../../experiments/evaluations/docvqa_v29_8_checkpoints_20261112/v29_8_R10/summary.json) | 逐轮检查点 | `deepseek-flash` | 330/374 | 94.62% |

</details>

<details>
<summary>v29.9（1 条训练或历史记录，1 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_9_docvqa160_20261117_121927](../../experiments/campaigns/v29_9_docvqa160_20261117_121927/training_summary.json) | 完成训练 | 11 | 1 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_9_docvqa160_20261117_121927_test374](../../experiments/evaluations/v29_9_docvqa160_20261117_121927_test374/summary.json) | 终测首测 | `deepseek-flash` | 326/374 | 93.89% |

</details>

<details>
<summary>v29.10（1 条训练或历史记录，1 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_10_docvqa160_20261117_131315](../../experiments/campaigns/v29_10_docvqa160_20261117_131315/training_summary.json) | 完成训练 | 11 | 1 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [v29_10_docvqa160_20261117_131315_test374](../../experiments/evaluations/v29_10_docvqa160_20261117_131315_test374/summary.json) | 终测首测 | `deepseek-flash` | 329/374 | 94.29% |

</details>

<details>
<summary>v29.11（1 条训练或历史记录，10 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [v29_11_docvqa160_20261117_180000](../../experiments/campaigns/v29_11_docvqa160_20261117_180000/training_summary.json) | 完成训练 | 11 | 10 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [R11_fifth](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R11_fifth/summary.json) | 终测复测 | `deepseek-flash` | 326/374 | 94.75% |
| [R11_fourth](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R11_fourth/summary.json) | 终测复测 | `deepseek-flash` | 327/374 | 94.44% |
| [R11_retest](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R11_retest/summary.json) | 终测复测 | `deepseek-flash` | 324/374 | 93.88% |
| [R11_third](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R11_third/summary.json) | 终测复测 | `deepseek-flash` | 333/374 | 95.89% |
| [v29_11_docvqa160_20261117_180000_test374](../../experiments/evaluations/v29_11_docvqa160_20261117_180000_test374/summary.json) | 终测首测 | `deepseek-flash` | 330/374 | 95.39% |
| [v29.11](../../artifacts/analysis/docvqa_v29_11_skilladam_1108_gpt54mini_20261120/v29.11/summary.json) | 跨 Actor | `gpt-5.4-mini` | 341/374 | 95.56% |
| [R01](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R01/summary.json) | 逐轮检查点 | `deepseek-flash` | 315/374 | 92.37% |
| [R02](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R02/summary.json) | 逐轮检查点 | `deepseek-flash` | 318/374 | 94.04% |
| [R05](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R05/summary.json) | 逐轮检查点 | `deepseek-flash` | 328/374 | 94.32% |
| [R08](../../experiments/evaluations/docvqa_v29_11_checkpoints_20261117/R08/summary.json) | 逐轮检查点 | `deepseek-flash` | 329/374 | 94.41% |

</details>

<details>
<summary>SkillAdam（2 条训练或历史记录，20 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [docvqa160_epoch1_20261102_231431](../../experiments/baselines/docvqa_skilladam/docvqa160_epoch1_20261102_231431/training_summary.json) | 完成训练 | 11 | 1 |
| [docvqa160_evidence_v2_20261108_192230](../../experiments/baselines/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230/training_summary.json) | 完成训练 | 11 | 17 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [official_best_skill_retest374_20261105_171948](../../experiments/evaluations/docvqa_skilladam/official_best_skill_retest374_20261105_171948/summary.json) | 外部最佳 Skill | `deepseek-flash` | 329/374 | 94.41% |
| [official_best_skill_test374_20261105_171151](../../experiments/evaluations/docvqa_skilladam/official_best_skill_test374_20261105_171151/summary.json) | 外部最佳 Skill | `deepseek-flash` | 331/374 | 95.02% |
| [docvqa160_epoch1_20261102_231431](../../experiments/evaluations/docvqa_skilladam/docvqa160_epoch1_20261102_231431/summary.json) | 终测首测 | `deepseek-flash` | 325/374 | 94.07% |
| [docvqa160_evidence_v2_20261108_192230_test374_repeat2](../../experiments/evaluations/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230_test374_repeat2/summary.json) | 终测复测 | `deepseek-flash` | 321/374 | 93.45% |
| [docvqa160_evidence_v2_20261108_192230_test374_repeat3](../../experiments/evaluations/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230_test374_repeat3/summary.json) | 终测复测 | `deepseek-flash` | 319/374 | 92.93% |
| [docvqa160_evidence_v2_20261108_192230](../../experiments/evaluations/docvqa_skilladam/docvqa160_evidence_v2_20261108_192230/summary.json) | 终测首测 | `deepseek-flash` | 325/374 | 93.47% |
| [SkillAdam](../../artifacts/analysis/docvqa_v29_11_skilladam_1108_gpt54mini_20261120/SkillAdam/summary.json) | 跨 Actor | `gpt-5.4-mini` | 339/374 | 95.78% |
| [docvqa_checkpoints_20261111/skilladam_R01](../../experiments/evaluations/docvqa_checkpoints_20261111/skilladam_R01/summary.json) | 逐轮检查点 | `deepseek-flash` | 319/374 | 93.27% |
| [docvqa_checkpoints_20261111/skilladam_R02](../../experiments/evaluations/docvqa_checkpoints_20261111/skilladam_R02/summary.json) | 逐轮检查点 | `deepseek-flash` | 314/374 | 93.37% |
| [docvqa_checkpoints_20261111/skilladam_R04](../../experiments/evaluations/docvqa_checkpoints_20261111/skilladam_R04/summary.json) | 逐轮检查点 | `deepseek-flash` | 324/374 | 93.79% |
| [docvqa_checkpoints_20261111/skilladam_R05](../../experiments/evaluations/docvqa_checkpoints_20261111/skilladam_R05/summary.json) | 逐轮检查点 | `deepseek-flash` | 321/374 | 93.38% |
| [docvqa_checkpoints_20261111/skilladam_R06](../../experiments/evaluations/docvqa_checkpoints_20261111/skilladam_R06/summary.json) | 逐轮检查点 | `deepseek-flash` | 321/374 | 93.40% |
| [docvqa_checkpoints_20261111/skilladam_R08](../../experiments/evaluations/docvqa_checkpoints_20261111/skilladam_R08/summary.json) | 逐轮检查点 | `deepseek-flash` | 316/374 | 93.30% |
| [docvqa_skilladam_R02_third_20261111/skilladam_R02](../../experiments/evaluations/docvqa_skilladam_R02_third_20261111/skilladam_R02/summary.json) | 逐轮检查点 | `deepseek-flash` | 317/374 | 92.07% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R01](../../experiments/evaluations/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R01/summary.json) | 逐轮检查点 | `deepseek-flash` | 322/374 | 92.93% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R02](../../experiments/evaluations/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R02/summary.json) | 逐轮检查点 | `deepseek-flash` | 328/374 | 94.50% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R04](../../experiments/evaluations/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R04/summary.json) | 逐轮检查点 | `deepseek-flash` | 324/374 | 93.71% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R05](../../experiments/evaluations/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R05/summary.json) | 逐轮检查点 | `deepseek-flash` | 321/374 | 93.22% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R06](../../experiments/evaluations/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R06/summary.json) | 逐轮检查点 | `deepseek-flash` | 315/374 | 91.79% |
| [docvqa_skilladam_checkpoints_retest_20261111/skilladam_R08](../../experiments/evaluations/docvqa_skilladam_checkpoints_retest_20261111/skilladam_R08/summary.json) | 逐轮检查点 | `deepseek-flash` | 322/374 | 93.18% |

</details>

<details>
<summary>SkillOpt（1 条训练或历史记录，6 次评测）</summary>

| 训练或历史记录 | 状态 | 已完成轮数或步数 | 关联 Test |
| --- | --- | ---: | ---: |
| [docvqa_skillopt_deepseek_flash](../../experiments/baselines/docvqa_skillopt_deepseek_flash/selection.json) | 完成训练 | 12 | 6 |

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [test_repeat_2](../../experiments/baselines/docvqa_skillopt_deepseek_flash/test_repeat_2/summary.json) | 终测复测 | `deepseek-flash` | 317/374 | 93.09% |
| [test_repeat_3](../../experiments/baselines/docvqa_skillopt_deepseek_flash/test_repeat_3/summary.json) | 终测复测 | `deepseek-flash` | 325/374 | 93.97% |
| [test](../../experiments/baselines/docvqa_skillopt_deepseek_flash/test/summary.json) | 终测首测 | `deepseek-flash` | 316/374 | 93.35% |
| [SkillOpt](../../artifacts/analysis/docvqa_skillopt_final_gpt54mini_20261124/SkillOpt/summary.json) | 跨 Actor | `gpt-5.4-mini` | 338/374 | 96.19% |
| [Step02](../../experiments/evaluations/docvqa_skillopt_checkpoints_20261123/Step02/summary.json) | 逐轮检查点 | `deepseek-flash` | 324/374 | 93.89% |
| [Step03](../../experiments/evaluations/docvqa_skillopt_checkpoints_20261123/Step03/summary.json) | 逐轮检查点 | `deepseek-flash` | 320/374 | 93.68% |

</details>

<details>
<summary>共用（0 条训练或历史记录，1 次评测）</summary>

| 独立评测现场 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [R00](../../experiments/evaluations/docvqa_checkpoints_20261111/R00/summary.json) | 共用 R00 | `deepseek-flash` | 303/374 | 91.01% |

</details>

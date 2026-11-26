# DocVQA 实验索引

## 三组主对照

主对照采用 DeepSeek Flash，在同一发布版的 374 道 Test 题上评测。Hard 按单题 ANLS ≥ 0.999 计。共用初始 Skill 首测为 **303/374（81.02%）**。 [共用 R00](../benchmarks/docvqa/controls/R00/README.md)

| 实验 | 各次终测 Hard 通过数 | 图中中位数 | 全部终测中位数 | 训练与验证题次 |
| --- | --- | ---: | ---: | ---: |
| [v29.11](v29_11/v29_11_docvqa160_20261117_180000/README.md) | [330](v29_11/v29_11_docvqa160_20261117_180000/results/v29_11_docvqa160_20261117_180000_test374/summary.json)、[324](v29_11/v29_11_docvqa160_20261117_180000/results/R11_retest/summary.json)、[333](v29_11/v29_11_docvqa160_20261117_180000/results/R11_third/summary.json)、[327](v29_11/v29_11_docvqa160_20261117_180000/results/R11_fourth/summary.json)、[326](v29_11/v29_11_docvqa160_20261117_180000/results/R11_fifth/summary.json) | 330/374 | 327/374 | 290 |
| [SkillAdam](skilladam/docvqa/trajectory_feedback/docvqa160_evidence_v2_20261108_192230/README.md) | [325](skilladam/docvqa/trajectory_feedback/docvqa160_evidence_v2_20261108_192230/results/docvqa160_evidence_v2_20261108_192230/summary.json)、[321](skilladam/docvqa/trajectory_feedback/docvqa160_evidence_v2_20261108_192230/results/docvqa160_evidence_v2_20261108_192230_test374_repeat2/summary.json)、[319](skilladam/docvqa/trajectory_feedback/docvqa160_evidence_v2_20261108_192230/results/docvqa160_evidence_v2_20261108_192230_test374_repeat3/summary.json) | 321/374 | 321/374 | 480 |
| [SkillOpt](skillopt/docvqa/docvqa_skillopt_deepseek_flash/README.md) | [316](skillopt/docvqa/docvqa_skillopt_deepseek_flash/results/test/summary.json)、[317](skillopt/docvqa/docvqa_skillopt_deepseek_flash/results/test_repeat_2/summary.json)、[325](skillopt/docvqa/docvqa_skillopt_deepseek_flash/results/test_repeat_3/summary.json) | 317/374 | 317/374 | 1,396 |

现有图取前三次终测的 Hard 中位数。SkillOpt 的 Step02 和含空慢更新占位段的 Step03 分别关联各自的实测回执。 [逐轮主图](../../docs/figures/DocVQA-v29.11-SkillAdam-SkillOpt-R00-R12-small-multiples.png) · [累计题次图](../../docs/figures/DocVQA-test-success-by-cumulative-episodes.png)

## 离线验收

在仓库根目录运行。命令验收 238 份精选文件的原字节，读取两套图片归档，按同版参考答案复算 34 次 Test374 的 12,716 份回执。其中 12 次为共用 R00 和三组终测，其余为逐轮、检查点复测及跨 Actor 对照。另复算 SkillOpt 第 7 步 Val53 的 46/53。 [结构化验收清单](../benchmarks/docvqa/main-comparison.json)

```sh
python3 scripts/runs/docvqa/verify_comparison.py
```

v29.11 的历史预检使用本机 DocVQA 环境和 v29.10 的冻结训练现场。通过 4 项绑定测试以及全部 11 轮的 Diagnosis、Preconditioner 和 Editor 交接检查。

```sh
/Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_11_campaign.py
```

复算依赖本地 DocVQA 发布版、原始运行目录及归档。 [全量盘点](../../docs/repository/DOCVQA_INVENTORY.md) · [图片归档格式](../docvqa_image_refs/README.md)

## v29.8–v29.10 历史实验

三次训练均使用同一发布版的 160 道优化题，各完成 11 轮。验收核对三版的训练状态链、保留的 Skill 和受测 Skill，并逐题复算了 9 次 Test374 的 3,366 份回执。

| 实验 | 独立 Test374 | 终测 Hard | 终测平均 ANLS |
| --- | ---: | ---: | ---: |
| [v29.8](v29_8/v29_8_docvqa160_20261112_125216/README.md) | 7 | [333/374](v29_8/v29_8_docvqa160_20261112_125216/results/v29_8_docvqa160_20261112_125216_test374/summary.json) | 95.37% |
| [v29.9](v29_9/v29_9_docvqa160_20261117_121927/README.md) | 1 | [326/374](v29_9/v29_9_docvqa160_20261117_121927/results/v29_9_docvqa160_20261117_121927_test374/summary.json) | 93.89% |
| [v29.10](v29_10/v29_10_docvqa160_20261117_131315/README.md) | 1 | [329/374](v29_10/v29_10_docvqa160_20261117_131315/results/v29_10_docvqa160_20261117_131315_test374/summary.json) | 94.29% |

v29.8 的 7 次评测包括 6 次独立检查点和 1 次终测。v29.10 的完整原始训练继续供 v29.11 历史预检读取。 [历史验收清单](../benchmarks/docvqa/v29_8-v29_10.json)

```sh
python3 scripts/runs/docvqa/verify_comparison.py --manifest experiments/benchmarks/docvqa/v29_8-v29_10.json
```

## v29.3–v29.7 历史实验

8 次训练均完成 11 轮。已校验 519 份精选文件、88 轮训练状态与保留 Skill，并复算 11 次 Test374 的 4,114 份逐题回执。

| 实验 | 独立 Test374 | 最终 Skill 首测 Hard | 最终 Skill 复测 Hard |
| --- | ---: | ---: | ---: |
| [v29.3 初版](v29_3/v29_3_docvqa160_epoch1_20261103_223457/README.md) | 1 | [322/374](v29_3/v29_3_docvqa160_epoch1_20261103_223457/results/v29_3_docvqa_test374_20261103/summary.json) | — |
| [v29.3 修订版](v29_3/v29_3_revised_docvqa_20261104_003026/README.md) | 1 | [321/374](v29_3/v29_3_revised_docvqa_20261104_003026/results/v29_3_revised_docvqa_20261104_003026/summary.json) | — |
| [v29.4 Editor 32K](v29_4/v29_4_docvqa160_editor32768_20261104_015530/README.md) | 1 | [323/374](v29_4/v29_4_docvqa160_editor32768_20261104_015530/results/v29_4_docvqa_test374_editor32768_20261104_015530/summary.json) | — |
| [v29.5](v29_5/v29_5_docvqa160_20261104_180257/README.md) | 1 | [331/374](v29_5/v29_5_docvqa160_20261104_180257/results/v29_5_docvqa_test374_20261104_180257/summary.json) | — |
| [v29.6 初版](v29_6/v29_6_docvqa160_20261105_012220/README.md) | 1 | [325/374](v29_6/v29_6_docvqa160_20261105_012220/results/v29_6_docvqa160_20261105_012220_test374/summary.json) | — |
| [v29.6 Parent Memory Delta](v29_6/v29_6_parent_memory_delta_v1_docvqa160_20261105_033511/README.md) | 1 | [325/374](v29_6/v29_6_parent_memory_delta_v1_docvqa160_20261105_033511/results/v29_6_parent_memory_delta_v1_docvqa160_20261105_033511_test374/summary.json) | — |
| [v29.7 首次训练](v29_7/v29_7_docvqa160_20261105_121504/README.md) | 1 | [324/374](v29_7/v29_7_docvqa160_20261105_121504/results/v29_7_docvqa160_20261105_121504_test374/summary.json) | — |
| [v29.7 重复训练](v29_7/v29_7_repeat_docvqa160_20261105_131347/README.md) | 4 | [330/374](v29_7/v29_7_repeat_docvqa160_20261105_131347/results/v29_7_repeat_docvqa160_20261105_131347_test374/summary.json) | [328/374](v29_7/v29_7_repeat_docvqa160_20261105_131347/results/v29_7_repeat_docvqa160_20261105_131347_retest374_20261105_171711/summary.json) |

v29.3 初版的失败与恢复共用一个评测 ID。v29.7 重复训练另有 R03、R05 两次独立检查点评测。v29.4 旧运行的删除回执独立归档。 [v29.4 旧运行](v29_4/v29_4_docvqa160_epoch1_20261104_014817/README.md) · [历史验收清单](../benchmarks/docvqa/v29_3-v29_7.json)

```sh
python3 scripts/runs/docvqa/verify_comparison.py --manifest experiments/benchmarks/docvqa/v29_3-v29_7.json
```

## v29–v29.2 与早期 SkillAdam

本批核验 286 份精选文件，逐题复算 6 次 Test374 的 2,244 份回执。v29.2 原训练、停止的首个迁移和完成的续跑分别保留证据。早期 SkillAdam 本地训练的终测与开源最佳 Skill 的两次本地独立评测分别登记。

| 实验 | Hard | 平均 ANLS |
| --- | ---: | ---: |
| [v29](v29/v29_docvqa160_epoch1_20261102_184845/README.md) | [322/374](v29/v29_docvqa160_epoch1_20261102_184845/results/v29_docvqa160_epoch1_20261102_184845/summary.json) | 94.53% |
| [v29.1](v29_1/v29_1_docvqa160_epoch1_20261103_001/README.md) | [321/374](v29_1/v29_1_docvqa160_epoch1_20261103_001/results/v29_1_docvqa160_epoch1_20261103_001/summary.json) | 93.54% |
| [v29.2 完成的迁移续跑](v29_2/v29_2_docvqa160_epoch1_20261103_185548/README.md) | [326/374](v29_2/v29_2_docvqa160_epoch1_20261103_185548/results/v29_2_docvqa_test374_20261103/summary.json) | 93.68% |
| [SkillAdam 早期本地训练](skilladam/docvqa/shared_actor/docvqa160_epoch1_20261102_231431/README.md) | [325/374](skilladam/docvqa/shared_actor/docvqa160_epoch1_20261102_231431/results/docvqa160_epoch1_20261102_231431/summary.json) | 94.07% |
| [SkillAdam 开源最佳 Skill 首测](skilladam/docvqa/upstream_best/official_best_skill_test374_20261105_171151/README.md) | [331/374](skilladam/docvqa/upstream_best/official_best_skill_test374_20261105_171151/results/summary.json) | 95.02% |
| [SkillAdam 开源最佳 Skill 独立复测](skilladam/docvqa/upstream_best/official_best_skill_retest374_20261105_171948/README.md) | [329/374](skilladam/docvqa/upstream_best/official_best_skill_retest374_20261105_171948/results/summary.json) | 94.41% |

[分批验收清单](../benchmarks/docvqa/v29-v29_2-skilladam.json) · [SkillAdam 开源最佳 Skill 来源](skilladam/docvqa/upstream_best/README.md)

```sh
python3 scripts/runs/docvqa/verify_comparison.py --manifest experiments/benchmarks/docvqa/v29-v29_2-skilladam.json
```

## 全量离线验收

全量验收合并四份归档清单，逐一与盘点核对评测 ID、受测 Skill 哈希、Actor 和 Hard 计数。覆盖 **60 次独立 Test374、22,440 份逐题回执**。SkillOpt 的 Val53 单独核验。 [全量验收清单](../benchmarks/docvqa/all-evaluations.json)

```sh
python3 scripts/runs/docvqa/verify_comparison.py --manifest experiments/benchmarks/docvqa/all-evaluations.json
```

## 独立检出的本地依赖

在检出中按原仓库相对路径提供以下材料。四份分批清单的 `files[].source`、`evaluations[].receipts` 和 SkillOpt 的 `selection.receipts` 给出了评分复算需要的原始位置。

- DocVQA 数据发布版 `539088ef8a8ada01ac8e2e6d4e372586748a265e` 位于 `data/docvqa/releases/`，包含准备后的划分、参考答案和 PNG。
- 新版图片归档使用 `experiments/docvqa_image_refs/manifest.sqlite3`。早期逐轮归档使用 `experiments/evaluations/docvqa_checkpoints_shared_images_20261117/` 下的清单和共享图像。精简回执与归档索引保留原路径。
- v29.11 历史预检还读取 `experiments/campaigns/v29_10_docvqa160_20261117_131315/`。该入口使用 DocVQA Python 环境和本机 `external/SkillAdam` 提交 `b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1`。SkillOpt 启动器使用 `external/SkillOpt` 提交 `7da46ae693ee0329b80225c0128a37d65db10e9e`。

SkillOpt 的本地准备步骤会读取 `prepared/{train,val,test}` 中的 CSV。检出路径变化时，在本地副本中把 CSV 的绝对图片路径调整到当前检出下的同一发布版。独立检出验收使用了这种本地副本，核验了 534 道公开题的请求与评分，以及含 12 次普通更新的离线模拟训练。

独立检出中，60 次历史 Test 的 22,440 份回执、v29.11 的 11 轮历史预检和 SkillAdam 的只读训练预检均已通过。DocVQA 适配器与 v29–v29.11 的 1,112 项单测也在隔离检出中通过。

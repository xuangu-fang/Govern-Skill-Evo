# OfficeQA 实验索引

各实验入口链接冻结训练配置、实际受测 Skill、精选摘要和原始评分日志。

## 三组主对照实验

| 实验 | 最终 Skill 三次 Test172 的 EM 题数 |
| --- | --- |
| [v26.9 正式训练](v26_9/v26_9_officeqa_train74_20261118_180409/README.md) | 122、123、122 |
| [SkillAdam 11 月 20 日晚间第二次训练](skilladam/officeqa/trajectory_feedback/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937/README.md) | 121、117、118 |
| [SkillOpt 11 月 23 日重试版](skillopt/officeqa/skillopt_officeqa_retry_20261123_183232/README.md) | 118、119、117 |

v26.9 的同一最终 Skill 另有一次 GPT-5.4-mini 独立评测，答对 98/172，见 [v26.9 实验入口](v26_9/v26_9_officeqa_train74_20261118_180409/README.md)。

在仓库根目录运行以下命令。它按[验收清单](../benchmarks/officeqa/main-comparison.json)核对精选文件原字节，使用 OfficeQA 压缩归档展开原始回执，再用同版 Test172 答案和原生评分函数逐题复算 EM/F1。完整评测校验 172 个 UID，v26.9 首测另核对 UID0111 的单题补测与原测合并。

```sh
python3 scripts/runs/officeqa/verify_comparison.py
```

## v26.1 和 v26.2 历史实验

| 实验 | 最终 Skill 评测 |
| --- | --- |
| [v26.1 正式训练](v26_1/v26_1_officeqa_train74_roles_20261105_202041/README.md) | DeepSeek Flash 原测 123/171，补测后 124/172。v4.1 Flash 限定子集 115/171。 |
| [v26.2 正式训练](v26_2/v26_2_officeqa_train74_20261117_013308/README.md) | v4.1 Flash 首测 120/171，复测 118/171。两次计划均为 Test172，均缺 UID0111。 |

[11 月 11 日共用初始 Skill 对照](../benchmarks/officeqa/evaluations/officeqa_checkpoints_20261111/R00/README.md)为 85/172。

从仓库根目录按[历史实验验收清单](../benchmarks/officeqa/v26_1-v26_2.json)复核两版。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/v26_1-v26_2.json
```

## v26 和 v26.3–v26.8

| 版本 | 现存实验材料 |
| --- | --- |
| [v26](v26/README.md) | 两次 Pilot、正式训练、中止和预算续跑。正式训练首测为 118/171，UID0111 补测后为 118/172。 |
| [v26.3](v26_3/README.md) | 设计、实现和可执行配置。历史训练目录待原件。 |
| [v26.4](v26_4/README.md) | 训练暂停，最后提交 R03。 |
| [v26.5](v26_5/README.md) | 完成七轮训练，四次独立 Test 均有缺题。 |
| [v26.6](v26_6/README.md) | 完成七轮训练，两次独立 Test 均有缺题。 |
| [v26.7](v26_7/README.md) | 完成七轮训练，Test 评分覆盖 171 题。UID0111 同预算补测仍待评分。 |
| [v26.8](v26_8/README.md) | 完成七轮训练，Test 评分覆盖 170 题。 |

从仓库根目录按[这批实验的实际路径映射与验收清单](../benchmarks/officeqa/v26-remaining.json)复核。v26.7／v26.8 的 R06 两题专项使用优化池，单列于[专项归档](../benchmarks/officeqa/comparisons/v26_8_v26_7_R06_percent_20261118_114935/README.md)。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/v26-remaining.json
```

## SkillAdam 历史实验

[SkillAdam 实验索引](skilladam/officeqa/README.md)汇总两次 11 月 20 日训练、此前正式训练、预检、启动失败、预算续跑和上游 Best Skill 的独立评测。[历史验收清单](../benchmarks/officeqa/skilladam-history.json)记录受测文本与原回执的对应关系。

## SkillOpt 实验

[SkillOpt 实验索引](skillopt/officeqa/README.md)链接 11 月 22 日原版和 11 月 23 日重试版的选优记录、受测 Skill 与评测。[历史验收清单](../benchmarks/officeqa/skillopt-history.json)覆盖原版评测、重试版的独立跨 Actor 评测及两次 Selection。

各实验页也提供核验命令。完整回执仍通过[原归档路径](../benchmark_record_refs/README.md)读取。历史材料范围见[全量盘点](../../docs/repository/OFFICEQA_INVENTORY.md)。

总验收的检查范围、结果和本地依赖见 [OfficeQA 离线总验收](../../docs/repository/OFFICEQA_ACCEPTANCE.md)。

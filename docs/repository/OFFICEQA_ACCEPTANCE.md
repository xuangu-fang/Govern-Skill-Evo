# OfficeQA 离线总验收

2026-11-26，验收覆盖 v26–v26.9、SkillAdam、SkillOpt 和共用初始 Skill 对照。工作基线为 `wyy/day57-tau-autonomous-gse-v25` 的 `5b1c43dae8b`。[实验索引](../../experiments/methods/OFFICEQA.md) · [全量盘点与旧路径](OFFICEQA_INVENTORY.md)

## 原始评分复核

| 清单 | 精选文件 | Test 日志 | 逐题回执 | 评测及补测记录 |
| --- | ---: | ---: | ---: | ---: |
| [三组主对照](../../experiments/benchmarks/officeqa/main-comparison.json) | 90 | 19 | 3,096 | 19 |
| [v26.1、v26.2 和早期 R00](../../experiments/benchmarks/officeqa/v26_1-v26_2.json) | 58 | 8 | 1,201 | 8 |
| [v26、v26.3–v26.8](../../experiments/benchmarks/officeqa/v26-remaining.json) | 157 | 11 | 1,294 | 11 |
| [历史 SkillAdam](../../experiments/benchmarks/officeqa/skilladam-history.json) | 152 | 26 | 3,782 | 32 |
| [历史 SkillOpt](../../experiments/benchmarks/officeqa/skillopt-history.json) | 38 | 6 | 1,032 | 6 |
| 合计 | 495 | 70 | 10,405 | 76 |

495 次文件核对涉及 494 个精选文件，两份清单共用一条 SkillOpt 启动状态。另复算了 3 个优化池专项的 6 份评分，以及 SkillOpt 两次 Selection 的 48 份评分。76 条评测及补测记录与 3 个优化池专项覆盖了盘点的 79 条记录。

三组主对照最终 Skill 的三次 Test172 EM 中位数分别为 v26.9 的 **122/172**、11 月 20 日晚间第二次 SkillAdam 的 **118/172** 和 11 月 23 日重试版 SkillOpt 的 **118/172**。v26.9 首测的中位数计算使用已经补齐 UID0111 的合并结果。早期共用 R00 的 **85/172** 和 v26.9 在 GPT-5.4-mini 上的 **98/172** 各有独立回执。

完整 OfficeQA 压缩归档通过原字节校验，共 **37,683 项**，含 37,157 条记录与 526 个附件。五份清单也在从基线和待提交文件搭建的隔离目录中全部通过。隔离目录使用基线的通用归档读取器，只提供清单引用的历史证据和固定数据。四个 OfficeQA 基线及 SkillAdam 启动器与十个 v26 系列 campaign 模块均可在该目录导入。

## 运行复核

从仓库根目录执行以下命令。评分复算依赖本地 OfficeQA 压缩归档、原路径下的历史记录及固定发布数据。代码回归在 `OfficeQA` 环境执行，还使用本地 SkillAdam 和 SkillOpt 依赖、语料和既有回归夹具。Git 提交保存代码、精选证据和索引，完整归档与数据由本地路径提供。

```sh
python3 experiments/benchmark_record_refs/restore.py officeqa --verify
for manifest in experiments/benchmarks/officeqa/*.json; do
  python3 scripts/runs/officeqa/verify_comparison.py --manifest "$manifest" || exit 1
done
conda run -n OfficeQA python -B -m pytest -q -rs -p no:cacheprovider tests/adapters/officeqa tests/skill_evolution/v26*
```

代码回归共通过 **580 项测试和 278 项子测试**。主回归通过 575 项，另有 5 项因工作树缺旧语料目录而跳过。随后用本地发布包和冻结修订规则在临时目录重建测试语料，复跑两个语料修订测试文件，10 项全部通过，其中包含主回归跳过的 5 项。v26.9 回归在临时目录还原已发布的 Memory checkpoint，再核对历史配置、当前配置和最终 Test 的 20 worker 设置。评分和回归在离线条件下执行，未发起模型请求。

v26.3 的历史训练目录仍缺原件。v26.4 的实现文档保留四处对该原目录的引用，现有配置及实现仍可追溯。v26.4 历史训练最后发布 R03。有限子集、部分结果和补测按各清单的实际 UID 范围验收。[v26.3 状态](../../experiments/methods/v26_3/README.md) · [v26.4 状态](../../experiments/methods/v26_4/README.md)

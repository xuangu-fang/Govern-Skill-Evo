# SearchQA 实验索引

## 三方法主对照

v28.16、SkillAdam 和 SkillOpt 在同一组 Test1400 上使用 DeepSeek Flash。每组实验页链接冻结配置、完成回执、实际受测 Skill 和原始逐题记录。

| 实验 | 最终 Skill 的各次完整测试 | 主图采用 | 主图 EM | 累计训练与验证题次 |
| --- | --- | --- | ---: | ---: |
| [v28.16](v28_16/v28_16_searchqa600_batch60_20261112_132531/README.md) | 1,193、1,180、1,182、1,178、1,200 | 1,193、1,182、1,200 | 1,193/1,400（85.21%） | 1,200 |
| [SkillAdam](skilladam/searchqa/v28_11_aligned/v28_11_aligned_batch60_20261116_123000/README.md) | 1,160、1,164、1,162 | 1,160、1,164、1,162 | 1,162/1,400（83.00%） | 1,800 |
| [SkillOpt](skillopt/searchqa/searchqa_skillopt_retry_20261123_180000/README.md) | 1,182、1,185、1,195、1,188 | 1,182、1,185、1,188 | 1,185/1,400（84.64%） | 10,520 |

[共用 R00](../benchmarks/searchqa/controls/searchqa_checkpoints_20261111/R00/README.md) 为 **1,064/1,400（76.00%）**。主图最终值取表中所列评测的中位数，实验页逐次列出全部完整复测。

[逐轮保留 Skill 图](../../docs/figures/SearchQA-v28.16-SkillAdam-SkillOpt-retained-EM.png) · [累计题次图](../../docs/figures/SearchQA-test-EM-by-cumulative-episodes.png) · [主对照验收清单](../benchmarks/searchqa/main-comparison.json) · [完整盘点与拟议路径](../../docs/repository/SEARCHQA_INVENTORY.md)

## 离线复算

从仓库根目录运行。读取 31 份评测各自的冻结任务计划和原始逐题日志，用 Test1400 答案与 SearchQA 原生评分函数从 Actor 的普通输出重算 EM/F1，并校验精选文件原字节、配置信息、受测 Skill 和主图取值。

```sh
conda run -n SearchQA python -B scripts/runs/searchqa/verify_comparison.py
```

## 运行入口验收

三组入口在禁止联网的独立临时源码副本中通过检查。v28.16 通过训练和 Test 的 `--validate-only`，SkillAdam 通过冻结配置预检，SkillOpt 通过数据划分、40 步计划、冻结配置与已选 Skill 校验。SkillAdam 冻结清单里的 `v27/benchmark.py` 与盘点后的工作树字节有差异，验收在临时副本中使用了哈希匹配的历史文件。[验收回执](../benchmarks/searchqa/verification.json)

## v28.11–v28.15 历史实验

这五次训练各完成十轮，共有 20 次完整 Test1400。各实验页提供冻结配置、完成状态、实际受测 Skill、评测摘要和原始逐题回执。

| 版本 | 评测次数 | 最终保留 Skill 的 EM 题数 |
| --- | ---: | --- |
| [v28.11](v28_11/v28_11_searchqa600_batch60_decision_boundaries_v1_20261107_014938/README.md) | 7 | [1,179](v28_11/v28_11_searchqa600_batch60_decision_boundaries_v1_20261107_014938/results/v28_11_searchqa600_batch60_decision_boundaries_v1_20261107_014938_test1400/summary.json)、[1,172](v28_11/v28_11_searchqa600_batch60_decision_boundaries_v1_20261107_014938/results/v28_11_searchqa600_batch60_decision_boundaries_v1_20261107_014938_test1400_retest_20261107_025608/summary.json) / 1,400 |
| [v28.12](v28_12/v28_12_searchqa600_batch60_20261109_024436/README.md) | 8 | [1,172](v28_12/v28_12_searchqa600_batch60_20261109_024436/results/v28_12_searchqa600_batch60_20261109_024436_test1400/summary.json)、[1,181](v28_12/v28_12_searchqa600_batch60_20261109_024436/results/v28_12_searchqa600_batch60_20261109_024436_test1400_retest_20261109_123544/summary.json)、[1,177](v28_12/v28_12_searchqa600_batch60_20261109_024436/results/v28_12_searchqa600_batch60_20261109_024436_test1400_third_20261111/summary.json) / 1,400 |
| [v28.13](v28_13/v28_13_searchqa600_batch60_20261111_220738/README.md) | 2 | [1,179](v28_13/v28_13_searchqa600_batch60_20261111_220738/results/v28_13_searchqa600_batch60_20261111_220738_test1400/summary.json)、[1,173](v28_13/v28_13_searchqa600_batch60_20261111_220738/results/v28_13_searchqa600_batch60_20261111_220738_test1400_retest_20261111_231012/summary.json) / 1,400 |
| [v28.14](v28_14/v28_14_searchqa600_batch60_20261112_001311/README.md) | 2 | [1,196](v28_14/v28_14_searchqa600_batch60_20261112_001311/results/v28_14_searchqa600_batch60_20261112_001311_test1400/summary.json)、[1,187](v28_14/v28_14_searchqa600_batch60_20261112_001311/results/v28_14_searchqa600_batch60_20261112_001311_test1400_retest_20261112_013701/summary.json) / 1,400 |
| [v28.15](v28_15/v28_15_searchqa600_batch60_20261112_120121/README.md) | 1 | [1,163](v28_15/v28_15_searchqa600_batch60_20261112_120121/results/v28_15_searchqa600_batch60_20261112_120121_test1400/summary.json) / 1,400 |

v28.11 的两份 R10 短版消融均为 1,182/1,400。v28.12 逐轮评测复用已归档的共用 R00，并保留相同 Skill 在不同轮次的对应关系。

[历史验收清单](../benchmarks/searchqa/v28_11-v28_15.json) · [离线复算回执](../benchmarks/searchqa/v28_11-v28_15-verification.json)

```sh
conda run -n SearchQA python -B scripts/runs/searchqa/verify_comparison.py --manifest experiments/benchmarks/searchqa/v28_11-v28_15.json
```

## 早期版本与历史基线

这批归档纳入 31 条训练记录和 45 次评测。三份验收清单合计覆盖盘点中的 39 条训练记录和 96 次评测。

| 入口 | 本批记录 |
| --- | --- |
| [v28–v28.10 早期实验](../benchmarks/searchqa/v28-v28_10.md) | 21 条训练记录，18 次 Test1400 |
| [SkillAdam 历史基线](skilladam/searchqa/README.md) | 8 条训练记录，17 次 Test1400，含上游最佳 Skill 的独立评测 |
| [SkillOpt 历史基线](skillopt/searchqa/README.md) | 2 条训练记录，5 次 Test1400 和 2 次 Main200 Test100 |
| [GPT-5.4-mini 跨 Actor 评测](../benchmarks/searchqa/comparisons/gpt54mini/README.md) | 沿用主对照的三份最终 Skill，各评估一次 Test1400 |

7 个预定评测路径只有调度回执或空目录，状态见对应实验页。较大的运行快照通过原路径和 SHA-256 引用。[历史验收清单](../benchmarks/searchqa/remaining-history.json) · [离线复算回执](../benchmarks/searchqa/remaining-history-verification.json)

```sh
conda run -n SearchQA python -B scripts/runs/searchqa/verify_comparison.py --manifest experiments/benchmarks/searchqa/remaining-history.json
```

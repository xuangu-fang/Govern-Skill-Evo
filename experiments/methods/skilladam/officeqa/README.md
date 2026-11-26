# SkillAdam 的 OfficeQA 实验

各行保留原实验 ID。Test 成绩可从实验入口定位到实际受测 Skill 和逐题日志。下表中的题数为 EM 答对数。

| 实验 | 状态与评分 |
| --- | --- |
| [11 月 20 日凌晨第一次训练](trajectory_feedback/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358/README.md) | 7 次迭代，R06 采纳最终 Skill。四次最终 Skill 测试答对 121、120、121、118 题，各 172 题。 |
| [11 月 20 日晚间第二次训练](trajectory_feedback/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937/README.md) | 7 次迭代，R04 采纳最终 Skill。三次 DeepSeek Flash 测试答对 121、117、118 题，各 172 题。另有一次 GPT-5.4-mini 独立评测。 |
| [11 月 16 日 v4.1 Flash 训练](trajectory_feedback/skilladam_officeqa_flash41_7rounds_20261116_212008/README.md) | 7 次迭代，保留各轮原测、补测、合并摘要和最终 Skill 的独立复测。 |
| [11 月 12 日输入对齐重训](trajectory_feedback/skilladam_officeqa_input_v2_rerun_20261112_185030/README.md) | 8 次迭代。最终 Skill 原测 119/171，补测后 119/172；R03 各次评测独立登记。 |
| [11 月 8 日输入对齐训练](trajectory_feedback/skilladam_officeqa_input_v2_20261108_185409/README.md) | 8 次迭代，最终 Skill 为 116/172。 |
| [10 月 29 日正式训练](native_training/skilladam_officeqa_official_train74_epoch1_20261029_230230/README.md) | 8 次迭代，原测 107/171，UID0111 补测答对，合并为 108/172。 |
| [10 月 29 日 64K 配置与预检](native_training/skilladam_officeqa_official_iterations_deepseek_flash_uid0007_64k_20261029_001/README.md) | 配置和预检记录齐备。 |
| [10 月 29 日修正版尝试 001](native_training/skilladam_officeqa_train74_epoch1_deepseek_flash_corrected_v2_20261029_001/README.md) | 启动失败，保留失败证据。 |
| [10 月 29 日修正版尝试 002](native_training/skilladam_officeqa_train74_epoch1_deepseek_flash_corrected_v2_20261029_002/README.md) | 有启动后状态，完成回执缺失。 |
| [10 月 29 日 UID0007 扩预算续跑](native_training/skilladam_officeqa_train74_epoch1_deepseek_flash_uid0007_64k_20261029_001/README.md) | 完成 8 次迭代，保留导入状态和最终 Skill。 |
| [上游发布的 Best Skill](upstream_best/skilladam_officeqa_open_source_best_test172_20261105_231839/README.md) | 独立 Test172 为 121/172。 |

[历史验收清单](../../../benchmarks/officeqa/skilladam-history.json)包括九条历史训练或准备记录、上游发布版评测，以及晚间第二次训练单独的 GPT-5.4-mini 评测。晚间训练的 DeepSeek Flash 原测与复测仍沿用[主对照验收清单](../../../benchmarks/officeqa/main-comparison.json)。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/skilladam-history.json
```

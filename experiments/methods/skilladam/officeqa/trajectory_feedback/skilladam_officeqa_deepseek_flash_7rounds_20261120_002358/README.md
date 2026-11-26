# skilladam_officeqa_deepseek_flash_7rounds_20261120_002358

11 月 20 日凌晨第一次独立训练。74 道优化题，完成 7 次迭代。R06 采纳最终 Skill。

[冻结配置](config/plan.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [状态证据](results/result.json) · [原始训练材料](../../../../../baselines/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358) · [历史运行入口](../../../../../../scripts/runs/run_officeqa_skilladam_batch_schedule.py) · [启动和恢复记录](../../../../../launches/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358)

| 评测 | 已评分／计划 | EM 题数 | 待评 | 证据 |
| --- | ---: | ---: | --- | --- |
| 最终 Skill 首测 | 172/172 | 121 | — | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_test172/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_test172/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_test172/batch/actor/results.jsonl) |
| R04 第 1 次复测 | 172/172 | 112 | — | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R04_test172_repeat1_20261120_130113/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R04_test172_repeat1_20261120_130113/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R04_test172_repeat1_20261120_130113/batch/actor/results.jsonl) |
| R05 第 1 次复测 | 172/172 | 122 | — | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R05_test172_repeat1_20261120_130113/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R05_test172_repeat1_20261120_130113/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R05_test172_repeat1_20261120_130113/batch/actor/results.jsonl) |
| R06 第 2 次复测 | 172/172 | 121 | — | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R06_test172_repeat2_20261120_130043/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R06_test172_repeat2_20261120_130043/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R06_test172_repeat2_20261120_130043/batch/actor/results.jsonl) |
| R06 第 3 次复测 | 172/172 | 118 | — | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R06_test172_repeat3_20261120_132225/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R06_test172_repeat3_20261120_132225/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_R06_test172_repeat3_20261120_132225/batch/actor/results.jsonl) |
| R01 评测 | 172/172 | 112 | — | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R01/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R01/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R01/batch/actor/results.jsonl) |
| R04 评测 | 172/172 | 117 | — | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R04/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R04/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R04/batch/actor/results.jsonl) |
| R05 评测 | 172/172 | 118 | — | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R05/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R05/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R05/batch/actor/results.jsonl) |
| R06 评测 | 172/172 | 120 | — | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R06/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R06/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_002358_round_tests_20261120_122105/R06/batch/actor/results.jsonl) |

[实际路径映射与验收清单](../../../../../benchmarks/officeqa/skilladam-history.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/skilladam-history.json
```

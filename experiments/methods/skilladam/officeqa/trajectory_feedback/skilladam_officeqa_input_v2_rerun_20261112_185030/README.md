# skilladam_officeqa_input_v2_rerun_20261112_185030

完成训练。74 道优化题，完成 8 次迭代。

[冻结配置](config/plan.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [状态证据](results/result.json) · [原始训练材料](../../../../../baselines/skilladam_officeqa_input_v2_rerun_20261112_185030) · [历史运行入口](../../../../../../scripts/runs/run_officeqa_skilladam_deepseek.py) · [启动和恢复记录](../../../../../launches/skilladam_officeqa_input_v2_rerun_20261112_185030)

| 评测 | 已评分／计划 | EM 题数 | 待评 | 证据 |
| --- | ---: | ---: | --- | --- |
| 最终 Skill 首测 | 171/172 | 119 | UID0111 | [受测 Skill](results/skilladam_officeqa_input_v2_rerun_20261112_185030_test172/skill.md) · [摘要](results/skilladam_officeqa_input_v2_rerun_20261112_185030_test172/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_input_v2_rerun_20261112_185030_test172/batch/actor/results.jsonl) |
| 补测 | 1/1 | 0 | — | [受测 Skill](results/skilladam_officeqa_input_v2_rerun_20261112_185030_test172/skill.md) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_input_v2_rerun_20261112_185030_test172_UID0111_retry3/attempt_1/actor/results.jsonl) |
| R02 评测 | 172/172 | 118 | — | [受测 Skill](results/officeqa_checkpoints_skilladam_second_20261112/R02/skill.md) · [摘要](results/officeqa_checkpoints_skilladam_second_20261112/R02/report.json) · [原始评分日志](../../../../../evaluations/officeqa_checkpoints_skilladam_second_20261112/R02/batch/actor/results.jsonl) |
| R03 评测 | 171/172 | 124 | UID0111 | [受测 Skill](results/officeqa_checkpoints_skilladam_second_20261112/R03/skill.md) · [摘要](results/officeqa_checkpoints_skilladam_second_20261112/R03/report.json) · [原始评分日志](../../../../../evaluations/officeqa_checkpoints_skilladam_second_20261112/R03/batch/actor/results.jsonl) |
| R03_supplement 补测 | 1/1 | 0 | — | [受测 Skill](results/officeqa_checkpoints_skilladam_second_20261112/R03/skill.md) · [原始评分日志](../../../../../evaluations/officeqa_checkpoints_skilladam_second_20261112/R03_supplement/UID0111_attempt_1/actor/results.jsonl) |
| R03 独立复测 | 172/172 | 114 | — | [受测 Skill](results/skilladam_officeqa_second_R03_retest_20261112_234655/test172/skill.md) · [摘要](results/skilladam_officeqa_second_R03_retest_20261112_234655/test172/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_second_R03_retest_20261112_234655/test172/batch/actor/results.jsonl) |
| 最终 Skill 原测与补测合并 | 172/172 | 119 | — | [受测 Skill](results/skilladam_officeqa_input_v2_rerun_20261112_185030_test172/skill.md) · [摘要](results/skilladam_officeqa_input_v2_rerun_20261112_185030_test172_UID0111_retry3/combined_report.json) · [原测日志](../../../../../evaluations/skilladam_officeqa_input_v2_rerun_20261112_185030_test172/batch/actor/results.jsonl) · [补测回执](../../../../../evaluations/skilladam_officeqa_input_v2_rerun_20261112_185030_test172_UID0111_retry3/attempt_1/actor/results.jsonl) |
| R03 原测与补测合并 | 172/172 | 124 | — | [受测 Skill](results/officeqa_checkpoints_skilladam_second_20261112/R03/skill.md) · [摘要](results/officeqa_checkpoints_skilladam_second_20261112/R03_supplement/combined_report.json) · [原测日志](../../../../../evaluations/officeqa_checkpoints_skilladam_second_20261112/R03/batch/actor/results.jsonl) · [补测回执](../../../../../evaluations/officeqa_checkpoints_skilladam_second_20261112/R03_supplement/UID0111_attempt_1/actor/results.jsonl) |

[实际路径映射与验收清单](../../../../../benchmarks/officeqa/skilladam-history.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/skilladam-history.json
```

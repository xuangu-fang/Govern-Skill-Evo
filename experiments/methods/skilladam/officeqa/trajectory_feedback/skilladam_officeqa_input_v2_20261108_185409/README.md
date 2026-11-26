# skilladam_officeqa_input_v2_20261108_185409

完成训练。74 道优化题，完成 8 次迭代。

[冻结配置](config/plan.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [状态证据](results/result.json) · [原始训练材料](../../../../../baselines/skilladam_officeqa_input_v2_20261108_185409) · [历史运行入口](../../../../../../scripts/runs/run_officeqa_skilladam_deepseek.py) · [启动和恢复记录](../../../../../launches/skilladam_officeqa_input_v2_20261108_185409)

| 评测 | 已评分／计划 | EM 题数 | 待评 | 证据 |
| --- | ---: | ---: | --- | --- |
| 最终 Skill 首测 | 172/172 | 116 | — | [受测 Skill](results/skilladam_officeqa_input_v2_20261108_185409_test172/skill.md) · [摘要](results/skilladam_officeqa_input_v2_20261108_185409_test172/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_input_v2_20261108_185409_test172/batch/actor/results.jsonl) |

[实际路径映射与验收清单](../../../../../benchmarks/officeqa/skilladam-history.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/skilladam-history.json
```

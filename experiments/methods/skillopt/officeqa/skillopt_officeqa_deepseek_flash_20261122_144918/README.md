# skillopt_officeqa_deepseek_flash_20261122_144918

11 月 22 日原版。使用 50 道 Train 和 24 道 Selection，完成 4 个 epoch、8 个普通更新。
原生 Selection 在第 3 步选出 Best Skill，答对 20/24。

[冻结训练配置](config/plan.json) · [初始 Skill](config/initial_skill.md) · [Best Skill](results/final_skill.md) · [训练完成回执](results/result.json) · [原始训练](../../../../baselines/skillopt_officeqa_deepseek_flash_20261122_144918) · [启动记录](../../../../launches/skillopt_officeqa_deepseek_flash_20261122_144918)

[原生训练摘要](results/native_summary.json) · [逐步选优记录](results/history.json) · [最终 Selection 检查](results/final_selection_promotion.json) · [第 3 步 Selection 日志](../../../../baselines/skillopt_officeqa_deepseek_flash_20261122_144918/native/steps/step_0003/selection_eval/results.jsonl)

| 独立评测 | EM 题数 | 证据 |
| --- | ---: | --- |
| 第 1 步保留 Skill | 122/172 | [受测 Skill](results/skillopt_officeqa_deepseek_flash_20261122_144918_retained_step01_test172_20261122_213534/skill.md) · [原评分摘要](results/skillopt_officeqa_deepseek_flash_20261122_144918_retained_step01_test172_20261122_213534/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_deepseek_flash_20261122_144918_retained_step01_test172_20261122_213534/batch/actor/results.jsonl) |
| 第 2 步保留 Skill | 117/172 | [受测 Skill](results/skillopt_officeqa_deepseek_flash_20261122_144918_retained_step02_test172_20261122_213534/skill.md) · [原评分摘要](results/skillopt_officeqa_deepseek_flash_20261122_144918_retained_step02_test172_20261122_213534/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_deepseek_flash_20261122_144918_retained_step02_test172_20261122_213534/batch/actor/results.jsonl) |
| Best Skill 首测 | 124/172 | [受测 Skill](results/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172/skill.md) · [原评分摘要](results/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172/batch/actor/results.jsonl) |
| Best Skill 第一次复测 | 121/172 | [受测 Skill](results/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172_repeat2_20261122_204658/skill.md) · [原评分摘要](results/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172_repeat2_20261122_204658/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172_repeat2_20261122_204658/batch/actor/results.jsonl) |
| Best Skill 第二次复测 | 120/172 | [受测 Skill](results/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172_repeat3_20261122_205701/skill.md) · [原评分摘要](results/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172_repeat3_20261122_205701/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172_repeat3_20261122_205701/batch/actor/results.jsonl) |

[历史逐步评测报告](reports/skillopt_officeqa_deepseek_flash_20261122_144918_retained_steps_test172.md) · [实际路径映射与验收清单](../../../../benchmarks/officeqa/skillopt-history.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/skillopt-history.json
```

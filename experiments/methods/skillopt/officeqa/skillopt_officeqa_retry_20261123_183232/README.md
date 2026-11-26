# skillopt_officeqa_retry_20261123_183232

11 月 23 日的重试训练。4 个 epoch，8 个普通更新，使用 50 道 Train 和 24 道 Selection。第 3 步选出的 Best Skill 在 Selection 上答对 20/24。

[冻结训练配置](config/plan.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [原始训练](../../../../baselines/skillopt_officeqa_retry_20261123_183232) · [历史重试启动脚本](../../../../launches/skillopt_officeqa_retry_20261123_183232/campaign.py) · [通用基线入口](../../../../../scripts/runs/run_officeqa_baselines.py)

以下评测使用 DeepSeek Flash。每条证据保留原实验路径和当次受测 Skill。

| 评测 | EM 题数 | 证据 |
| --- | ---: | --- |
| R01 测试 | 107/172 | [受测 Skill](results/skillopt_officeqa_retry_20261123_183232_retained_step01_test172/skill.md) · [摘要](results/skillopt_officeqa_retry_20261123_183232_retained_step01_test172/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_retry_20261123_183232_retained_step01_test172/batch/actor/results.jsonl) |
| R01 复测 | 107/172 | [受测 Skill](results/skillopt_officeqa_retry_20261123_183232_retained_step01_test172_repeat2/skill.md) · [摘要](results/skillopt_officeqa_retry_20261123_183232_retained_step01_test172_repeat2/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_retry_20261123_183232_retained_step01_test172_repeat2/batch/actor/results.jsonl) |
| 最终 Skill 首测 | 118/172 | [受测 Skill](results/skillopt_officeqa_retry_20261123_183232_best_test172/skill.md) · [摘要](results/skillopt_officeqa_retry_20261123_183232_best_test172/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_retry_20261123_183232_best_test172/batch/actor/results.jsonl) |
| 最终 Skill 第二次测试 | 119/172 | [受测 Skill](results/skillopt_officeqa_retry_20261123_183232_best_test172_repeat2/skill.md) · [摘要](results/skillopt_officeqa_retry_20261123_183232_best_test172_repeat2/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_retry_20261123_183232_best_test172_repeat2/batch/actor/results.jsonl) |
| 最终 Skill 第三次测试 | 117/172 | [受测 Skill](results/skillopt_officeqa_retry_20261123_183232_best_test172_repeat3/skill.md) · [摘要](results/skillopt_officeqa_retry_20261123_183232_best_test172_repeat3/report.json) · [原始评分日志](../../../../evaluations/skillopt_officeqa_retry_20261123_183232_best_test172_repeat3/batch/actor/results.jsonl) |

[源路径、受测 Skill SHA-256 与离线验收清单](../../../../benchmarks/officeqa/main-comparison.json)

[原生训练摘要](results/native_summary.json) · [逐步选优记录](results/history.json) · [最终 Selection 检查](results/final_selection_promotion.json) · [第 3 步 Selection 日志](../../../../baselines/skillopt_officeqa_retry_20261123_183232/native/steps/step_0003/selection_eval/results.jsonl)

同一 Best Skill 的 GPT-5.4-mini 独立评测为 **94/172**。[受测 Skill](results/officeqa_skillopt_final_gpt54mini_20261124/skill.md) · [摘要](results/officeqa_skillopt_final_gpt54mini_20261124/summary.json) · [原始评分日志](../../../../../artifacts/analysis/officeqa_skillopt_final_gpt54mini_20261124/runs/actor/results.jsonl) · [历史验收清单](../../../../benchmarks/officeqa/skillopt-history.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --method SkillOpt
```

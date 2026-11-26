# skilladam_officeqa_deepseek_flash_7rounds_20261120_215937

11 月 20 日晚间第二次独立训练。74 道优化题，7 次迭代。R04 采纳最终 Skill。

[冻结训练配置](config/plan.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [原始训练](../../../../../baselines/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937) · [历史启动记录](../../../../../launches/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937) · [启动入口](../../../../../../scripts/runs/run_officeqa_skilladam_batch_schedule.py)

以下评测使用 DeepSeek Flash。每条证据保留原实验路径和当次受测 Skill。

| 评测 | EM 题数 | 证据 |
| --- | ---: | --- |
| R02 测试 | 114/172 | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_20261121_004141/R02/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_20261121_004141/R02/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_20261121_004141/R02/batch/actor/results.jsonl) |
| R02 复测 | 120/172 | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_repeat1_20261121_005413/R02/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_repeat1_20261121_005413/R02/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_repeat1_20261121_005413/R02/batch/actor/results.jsonl) |
| R03 测试 | 118/172 | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_20261121_004141/R03/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_20261121_004141/R03/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_20261121_004141/R03/batch/actor/results.jsonl) |
| R03 复测 | 120/172 | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_repeat1_20261121_005413/R03/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_repeat1_20261121_005413/R03/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R02_R03_test172_repeat1_20261121_005413/R03/batch/actor/results.jsonl) |
| 最终 Skill 首测 | 121/172 | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_test172/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_test172/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_test172/batch/actor/results.jsonl) |
| 最终 Skill 第一次复测 | 117/172 | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R04_final_test172_repeat1_20261121_000620/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R04_final_test172_repeat1_20261121_000620/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R04_final_test172_repeat1_20261121_000620/batch/actor/results.jsonl) |
| 最终 Skill 第二次复测 | 118/172 | [受测 Skill](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R04_final_test172_repeat2_20261121_001928/skill.md) · [摘要](results/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R04_final_test172_repeat2_20261121_001928/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R04_final_test172_repeat2_20261121_001928/batch/actor/results.jsonl) |

[源路径、受测 Skill SHA-256 与离线验收清单](../../../../../benchmarks/officeqa/main-comparison.json)

同一最终 Skill 的 GPT-5.4-mini 独立评测为 **93/172**。[受测 Skill](results/officeqa_v26_9_skilladam_1120_evening_gpt54mini_20261121/SkillAdam/skill.md) · [摘要](results/officeqa_v26_9_skilladam_1120_evening_gpt54mini_20261121/SkillAdam/summary.json) · [原始评分日志](../../../../../../artifacts/analysis/officeqa_v26_9_skilladam_1120_evening_gpt54mini_20261121/SkillAdam/runs/actor/results.jsonl) · [历史验收清单](../../../../../benchmarks/officeqa/skilladam-history.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --method SkillAdam
```

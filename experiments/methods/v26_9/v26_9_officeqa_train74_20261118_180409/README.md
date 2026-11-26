# v26_9_officeqa_train74_20261118_180409

7 轮正式训练，74 道优化题。R06 发布最终 Skill，R07 沿用。

[冻结训练配置](config/config.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [原始训练](../../../campaigns/v26_9_officeqa_train74_20261118_180409) · [历史启动记录](../../../launches/v26_9_officeqa_train74_20261118_180409) · [启动入口](../../../../scripts/runs/run_v26_9_campaign.py)

以下评测使用 DeepSeek Flash。每条证据保留原实验路径和当次受测 Skill。

| 评测 | EM 题数 | 证据 |
| --- | ---: | --- |
| R01 测试 | 93/172 | [受测 Skill](results/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/R01/skill.md) · [摘要](results/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/R01/summary.json) · [原始评分日志](../../../evaluations/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/R01/runs/actor/results.jsonl) |
| R02 测试 | 118/172 | [受测 Skill](results/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/R02/skill.md) · [摘要](results/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/R02/summary.json) · [原始评分日志](../../../evaluations/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/R02/runs/actor/results.jsonl) |
| 最终 Skill 原测 | 121/171（缺 UID0111） | [受测 Skill](results/v26_9_officeqa_final_test172_w20_20261118_180409/skill.md) · [原始评分日志](../../../evaluations/v26_9_officeqa_final_test172_w20_20261118_180409/runs/actor/results.jsonl) |
| 最终 Skill 首测（合并） | 122/172 | [受测 Skill](results/v26_9_officeqa_UID0111_65536_20261118_194128/skill.md) · [摘要](results/v26_9_officeqa_UID0111_65536_20261118_194128/combined_report.json) · [原测日志](../../../evaluations/v26_9_officeqa_final_test172_w20_20261118_180409/runs/actor/results.jsonl) · [补测日志](../../../evaluations/v26_9_officeqa_UID0111_65536_20261118_194128/runs/actor/results.jsonl) |
| 最终 Skill 第一次复测 | 123/172 | [受测 Skill](results/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/final/skill.md) · [摘要](results/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/final/summary.json) · [原始评分日志](../../../evaluations/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/final/runs/actor/results.jsonl) |
| 最终 Skill 第二次复测 | 122/172 | [受测 Skill](results/v26_9_officeqa_final_test172_w20_repeat2_20261120_134237/skill.md) · [摘要](results/v26_9_officeqa_final_test172_w20_repeat2_20261120_134237/summary.json) · [原始评分日志](../../../evaluations/v26_9_officeqa_final_test172_w20_repeat2_20261120_134237/runs/actor/results.jsonl) |

原测覆盖 171 题。UID0111 在独立 65,536 输出 token 配置下补测，原测和补测日志共同组成 172 题结果。

同一最终 Skill 的 GPT-5.4-mini 独立评测为 **98/172**。[受测 Skill](results/officeqa_v26_9_skilladam_1120_evening_gpt54mini_20261121/v26.9/skill.md) · [摘要](results/officeqa_v26_9_skilladam_1120_evening_gpt54mini_20261121/v26.9/summary.json) · [原始评分日志](../../../../artifacts/analysis/officeqa_v26_9_skilladam_1120_evening_gpt54mini_20261121/v26.9/runs/actor/results.jsonl)

[源路径、受测 Skill SHA-256 与离线验收清单](../../../benchmarks/officeqa/main-comparison.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --method v26.9
```

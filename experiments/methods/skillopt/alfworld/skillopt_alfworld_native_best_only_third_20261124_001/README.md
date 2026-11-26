# ALFWorld SkillOpt 第三次训练

训练 ID 为 `skillopt_alfworld_native_best_only_third_20261124_001`。共 4 个 epoch，每轮使用 39 道训练题，在 18 道 Selection 题上选优。训练结束后对 Best Skill 执行 134 题测试。

[原始训练](../../../../../artifacts/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001/campaign) · [配置](skillopt.json) · [冻结输入](manifest.json) · [训练摘要](results/summary.json) · [逐步历史](results/history.json) · [Best Skill](results/best_skill.md) · [Final Skill](results/final_skill.md)

第 4 轮慢更新产生最终 Skill，Best 首测为 122/134。相同文本随后三次复测为 116、120、118 / 134，中位数为 118/134。R01 加入占位段前的候选和轮末保存的文本也各自有一次评测，分别为 120/134 和 119/134。

| 评测 ID 或角色 | 成功题数 | 材料 |
|---|---:|---|
| Best 首测 | 122/134 | [受测 Skill](results/best_skill.md) · [摘要](results/test_eval/summary.json) · [本地逐题记录](../../../../../artifacts/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001/campaign/test_eval/results.jsonl) |
| alfworld_skillopt_third_R01_R02_test134_20261124_203057/R01 | 119/134 | [受测 Skill](results/skills/skill_v0001.md) · [摘要](results/alfworld_skillopt_third_R01_R02_test134_20261124_203057/R01/summary.json) · [本地逐题记录](../../../../../artifacts/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001/evaluations/alfworld_skillopt_third_R01_R02_test134_20261124_203057/R01/results.jsonl) |
| alfworld_skillopt_third_R01_R02_test134_20261124_203057/R02 | 121/134 | [受测 Skill](results/skills/skill_v0002.md) · [摘要](results/alfworld_skillopt_third_R01_R02_test134_20261124_203057/R02/summary.json) · [本地逐题记录](../../../../../artifacts/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001/evaluations/alfworld_skillopt_third_R01_R02_test134_20261124_203057/R02/results.jsonl) |
| alfworld_skillopt_third_R01_pre_placeholder_R04_test134_20261124_204902/R01_pre_placeholder | 120/134 | [受测 Skill](results/steps/step_0001/candidate_skill.md) · [摘要](results/alfworld_skillopt_third_R01_pre_placeholder_R04_test134_20261124_204902/R01_pre_placeholder/summary.json) · [本地逐题记录](../../../../../artifacts/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001/evaluations/alfworld_skillopt_third_R01_pre_placeholder_R04_test134_20261124_204902/R01_pre_placeholder/results.jsonl) |
| alfworld_skillopt_third_R01_pre_placeholder_R04_test134_20261124_204902/R04_final | 118/134 | [受测 Skill](results/final_skill.md) · [摘要](results/alfworld_skillopt_third_R01_pre_placeholder_R04_test134_20261124_204902/R04_final/summary.json) · [本地逐题记录](../../../../../artifacts/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001/evaluations/alfworld_skillopt_third_R01_pre_placeholder_R04_test134_20261124_204902/R04_final/results.jsonl) |
| alfworld_skillopt_third_final_retest2_20261124_194311/R04 | 120/134 | [受测 Skill](results/skills/skill_v0004.md) · [摘要](results/alfworld_skillopt_third_final_retest2_20261124_194311/R04/summary.json) · [本地逐题记录](../../../../../artifacts/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001/evaluations/alfworld_skillopt_third_final_retest2_20261124_194311/R04/results.jsonl) |
| alfworld_skillopt_third_final_retest_20261124_192516/R04 | 116/134 | [受测 Skill](results/skills/skill_v0004.md) · [摘要](results/alfworld_skillopt_third_final_retest_20261124_192516/R04/summary.json) · [本地逐题记录](../../../../../artifacts/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001/evaluations/alfworld_skillopt_third_final_retest_20261124_192516/R04/results.jsonl) |

在仓库根目录核对本次训练的冻结输入和数据划分：

```sh
/Users/didi/miniforge3/envs/skillopt/bin/python -B scripts/runs/run_skillopt_alfworld_native.py check --experiment experiments/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001
```

# SkillOpt DocVQA 主对照运行

Train107 运行 4 个 epoch，完成 12 个普通更新步。独立 Val53 选出第 7 步，Hard 为 46/53。最终 Test 使用冻结的 Best Skill。

[冻结训练配置](config/run.json) · [训练或选优回执](results/selection.json) · [初始 Skill](results/campaign/skills/skill_v0000.md) · [最终受测 Skill](results/best_skill.md) · [完整运行原目录](../../../../baselines/docvqa_skillopt_deepseek_flash)

## 终测及独立复测

| 次序 | DeepSeek Flash Hard | 平均 ANLS |
| ---: | ---: | ---: |
| 1 | [316/374](results/test/summary.json) | 93.35% |
| 2 | [317/374](results/test_repeat_2/summary.json) | 93.09% |
| 3 | [325/374](results/test_repeat_3/summary.json) | 93.97% |

Step02 首测为 324/374。含空慢更新占位段的 Step03 首测为 320/374，两份实际受测 Skill 各有独立哈希。总图对 R02–R06 及慢更新 S2 沿用 Step02，早期逐步表对 Step03–Step06 沿用 Step03。

## 逐轮及跨 Actor 评测

| 原评测 | 阶段 | Actor | Hard | 平均 ANLS |
| --- | --- | --- | ---: | ---: |
| [docvqa_skillopt_final_gpt54mini_20261124/SkillOpt](results/docvqa_skillopt_final_gpt54mini_20261124/SkillOpt/summary.json) | 跨 Actor | `gpt-5.4-mini` | 338/374 | 96.19% |
| [docvqa_skillopt_checkpoints_20261123/Step02](results/Step02/summary.json) | 逐轮检查点 | `deepseek-flash` | 324/374 | 93.89% |
| [docvqa_skillopt_checkpoints_20261123/Step03](results/Step03/summary.json) | 逐轮检查点 | `deepseek-flash` | 320/374 | 93.68% |

[三组主对照与离线验收](../../../DOCVQA.md)

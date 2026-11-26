# SkillOpt 的 OfficeQA 实验

两次训练都使用 50 道 Train 和 24 道 Selection，完成 4 个 epoch、8 次普通更新。各自的 Best Skill 来自第 3 步，Selection 均为 20/24。两次训练的 Best Skill 各自保留受测文本和独立回执。

| 实验 | 逐步 Test172 | Best Skill 的 Test172 |
| --- | --- | --- |
| [11 月 22 日原版](skillopt_officeqa_deepseek_flash_20261122_144918/README.md) | 第 1 步 122/172，第 2 步 117/172 | DeepSeek Flash 三次分别为 124、121、120/172 |
| [11 月 23 日重试版](skillopt_officeqa_retry_20261123_183232/README.md) | 第 1 步两次均为 107/172 | DeepSeek Flash 三次分别为 118、119、117/172。GPT-5.4-mini 独立评测为 94/172 |

[历史验收清单](../../../benchmarks/officeqa/skillopt-history.json)覆盖原版五次 Test172、重试版的 GPT-5.4-mini 评测以及两次第 3 步 Selection。重试版的 DeepSeek Flash 评测使用[主对照验收清单](../../../benchmarks/officeqa/main-comparison.json)。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/skillopt-history.json
python3 scripts/runs/officeqa/verify_comparison.py --method SkillOpt
```

可执行配置副本见 [DeepSeek Flash 正式配置](profiles/officeqa_skillopt_deepseek_flash.json)和 [SkillOpt 配置模板](profiles/officeqa_skillopt.example.json)。

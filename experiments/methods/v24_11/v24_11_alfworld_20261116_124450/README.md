# v24_11_alfworld_20261116_124450

六轮训练，共 57 道优化题。R01 沿用初始 Skill，R03 沿用 R02，R05 沿用 R04。下表按实际受测的发布轮次登记，每次评测覆盖同一组 134 道留出题。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [逐轮发布记录](results/training_summary.json) · [最终 Skill](results/final_skill.md) · [原始训练](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450) · [启动记录](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450/launch)

本次训练使用 v24.10 的 [Diagnosis](../../../../src/skill_evolution/v24_10/prompts/diagnosis.md)、[Preconditioner](../../../../src/skill_evolution/v24_10/prompts/preconditioner.md)、[Editor](../../../../src/skill_evolution/v24_10/prompts/editor.md)，以及[当次 Replay](config/replay.md)。四份提示词均与训练请求及[冻结契约](config/contract.json)的 SHA-256 一致。当前 v24.11 的 `__init__.py`、`campaign.py`、`prompts/replay.md` 已与当时的契约不同，并新增了 `outputs.py` 和本版的 Preconditioner、Editor 提示词。以下成绩归属于该冻结运行。

| 评测 | 成功题数 | 材料 |
|---|---:|---|
| R02 首测 | 129/134 | [受测 Skill](results/R02_skill.md) · [摘要](results/v24_11_alfworld_20261116_124450_checkpoints_test134/R02/summary.json) · [原始回执](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450_checkpoints_test134/R02/episodes) |
| R02 复测 | 123/134 | [受测 Skill](results/R02_skill.md) · [摘要](results/v24_11_alfworld_20261116_124450_R02_R06_retest134_20261124_123406/R02/summary.json) · [原始回执](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450_R02_R06_retest134_20261124_123406/R02/episodes) |
| R04 首测 | 129/134 | [受测 Skill](results/R04_skill.md) · [摘要](results/v24_11_alfworld_20261116_124450_checkpoints_test134/R04/summary.json) · [原始回执](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450_checkpoints_test134/R04/episodes) |
| R04 复测 | 125/134 | [受测 Skill](results/R04_skill.md) · [摘要](results/v24_11_alfworld_20261116_124450_R04_retest134_20261124_125720/R04/summary.json) · [原始回执](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450_R04_retest134_20261124_125720/R04/episodes) |
| R06 首测 | 127/134 | [受测 Skill](results/final_skill.md) · [摘要](results/v24_11_alfworld_20261116_124450_test134/summary.json) · [原始回执](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450_test134/episodes) |
| R06 第一次复测 | 125/134 | [受测 Skill](results/final_skill.md) · [摘要](results/v24_11_alfworld_20261116_124450_test134_retest_20261116_184316/summary.json) · [原始回执](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450_test134_retest_20261116_184316/episodes) |
| R06 第二次复测 | 125/134 | [受测 Skill](results/final_skill.md) · [摘要](results/v24_11_alfworld_20261116_124450_test134_third_20261116_190023/summary.json) · [原始回执](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450_test134_third_20261116_190023/episodes) |
| R06 第三次复测 | 127/134 | [受测 Skill](results/final_skill.md) · [摘要](results/v24_11_alfworld_20261116_124450_test134_fourth_20261119_223048/summary.json) · [原始回执](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450_test134_fourth_20261119_223048/episodes) |
| R06 第四次复测 | 124/134 | [受测 Skill](results/final_skill.md) · [摘要](results/v24_11_alfworld_20261116_124450_R02_R06_retest134_20261124_123406/R06/summary.json) · [原始回执](../../../../artifacts/methods/v24_11/v24_11_alfworld_20261116_124450_R02_R06_retest134_20261124_123406/R06/episodes) |

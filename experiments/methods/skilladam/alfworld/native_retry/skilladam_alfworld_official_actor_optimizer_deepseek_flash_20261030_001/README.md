# SkillAdam · ALFWorld · Actor 与优化器均使用官方模型

在官方优化器配置的基础上，将 Actor 也切换为官方 deepseek-flash。沿用相同的初始 Skill、任务清单、原生重试与 Gate。 [来源实验](../skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/README.md)

六轮正式训练已完成，Gate 接受四轮、拒绝两轮。训练最终导出的 Skill 分别用于首测和复测。

[Actor 配置](config/actor.json) · [优化器与训练参数](config/skilladam.json) · [初始 Skill](config/initial_skill.md) · [任务划分](config/splits) · [准备时的预检记录](results/preflight.json)

[逐轮训练摘要](results/training_summary.json) · [最终 Skill](results/final_skill.md) · [原始训练与恢复后的检查点](../../../../../../artifacts/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/checkpoint.json)

| 评测 | 成功 / 总数 | 精选结果 | 原始轨迹 |
|---|---:|---|---|
| 首测 | 117 / 134 | [评测摘要](results/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001_test134/summary.json) | [逐题记录](../../../../../../artifacts/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001_test134/episodes) |
| 复测 | 116 / 134 | [评测摘要](results/skilladam_alfworld_retest134_20261107_231301/summary.json) | [逐题记录](../../../../../../artifacts/methods/skilladam/alfworld/native_retry/skilladam_alfworld_retest134_20261107_231301/episodes) |

从仓库根目录执行以下命令可从训练检查点和两次评测的逐题轨迹复核结果。

```sh
/Users/didi/miniforge3/envs/skilladam/bin/python -B -m src.skill_evolution.skilladam.alfworld.native_retry.archive
```

## 离线预检

从仓库根目录运行。配置中记录的历史输出路径由运行入口解析到当前归档位置。

```sh
/Users/didi/miniforge3/envs/skilladam/bin/python -B scripts/runs/skilladam/alfworld/native_retry/run_skilladam_alfworld_official_models.py --experiment experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/config --check
```

[启动日志与进程回执](../../../../../../artifacts/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/launch) · [首测执行记录](results/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001_test134/execution.json) · [首测日志与退出状态](../../../../../../artifacts/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001_test134/launch) · [首轮补丁失败与恢复记录](../../../../../../artifacts/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/recovery/iteration_0_patch)

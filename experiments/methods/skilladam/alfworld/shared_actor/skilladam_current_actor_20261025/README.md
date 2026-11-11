# SkillAdam · ALFWorld 共享 Actor

本次正式训练（`skilladam_current_actor_20261025`）已完成六轮。使用共享 Actor 和原生 SkillAdam 优化器，以 39 个 Train 和 18 个 Selection 任务优化 Skill。每轮在同一批任务上比较 baseline 与 candidate，hard 成功率持平或上升即接受。前五轮 Gate 接受，第六轮拒绝。首测使用训练最终导出的 Skill，在独立的 134 个 Test 任务中成功 120 个（89.55%）。

| 材料 | 精选结果与配置 | 原始记录 |
|---|---|---|
| 训练输入 | [Actor](config/actor.json)、[初始 Skill](config/initial_skill.md)、[正式参数](config/skilladam.json)、[任务划分](config/splits) | [原实验说明](config/provenance/before_layout/README.md) |
| 六轮训练 | [逐轮 Gate 与成功数](results/training_summary.json)、[最终 Skill](results/final_skill.md) | [完成记录](../../../../../../artifacts/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/completion.json)、[检查点](../../../../../../artifacts/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/checkpoint.json)、[第三轮重试与 JSON 修复记录](../../../../../../artifacts/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/recovery) |
| 首测（`skilladam_current_actor_20261025_test134`） | [首测摘要](results/skilladam_current_actor_20261025_test134/summary.json) | [启动记录](../../../../../../artifacts/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025_test134/launch.json)、[逐题结果](../../../../../../artifacts/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025_test134/results.jsonl)、[轨迹](../../../../../../artifacts/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025_test134/episodes) |

[Smoke 配置](config/smoke.json)定义了一轮两题的验证；本次归档仅找到该配置。原始训练与首测目录保存在本机，Git 中可保存的精选结果位于本目录的 `results/`。

## 离线读取

在仓库根目录运行。第一条命令核对原实验输入、上游版本和批次，第二条将六轮决策与检查点比对，并逐题核对首测轨迹。

```sh
/Users/didi/miniforge3/envs/skilladam/bin/python -B scripts/runs/skilladam/alfworld/shared_actor/run_skilladam_aligned.py check
/Users/didi/miniforge3/envs/skilladam/bin/python -B scripts/runs/skilladam/alfworld/shared_actor/run_skilladam_aligned.py read-archive
```

原清单记录了整理前的源码，相关文件保存在 [历史输入](config/provenance/before_layout)。当前[运行入口](../../../../../../scripts/runs/skilladam/alfworld/shared_actor/run_skilladam_aligned.py)与[共享后端](../../../../../../src/skill_evolution/skilladam/alfworld/shared_actor/backend.py)由离线测试覆盖。预检优先使用归档目录旁 `upstream/` 下与原提交一致的本地检出，也支持使用相同版本的 `external/SkillAdam`。

[启动日志与进程回执](../../../../../../artifacts/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/launch)

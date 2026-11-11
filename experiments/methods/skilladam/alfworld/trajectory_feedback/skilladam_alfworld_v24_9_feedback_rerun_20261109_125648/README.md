# SkillAdam · ALFWorld 逐步轨迹反馈 · 独立重训

本次从双官方模型配置的初始 Skill 开始，沿用同一 Actor、优化器、57 道优化任务和六轮 Gate。训练时，轨迹压缩器额外读取每一步实际发送给 Actor 的可选动作、已执行动作、随后观察与环境反馈。补丁和 Momentum 继续使用原生 SkillAdam 流程。[配置来源与反馈入口](config/baseline_reference.json) · [双官方模型基线](../../native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/README.md)

六轮中有 4 轮通过 Gate。[逐轮训练摘要](results/training_summary.json) · [最终 Skill](results/final_skill.md) · [训练检查点](../../../../../../artifacts/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648/checkpoint.json) · [启动记录](../../../../../../artifacts/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648/launch/campaign.launch.json)

| 评测 | 成功 / 总数 | 成功率 | 原始逐题结果 |
|---|---:|---:|---|
| [首测](results/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648_test134/summary.json) | 110 / 134 | 82.09% | [results.jsonl](../../../../../../artifacts/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648_test134/results.jsonl) |

本次重训从初始 Skill 重新执行六轮优化，首测使用本次导出的最终 Skill。[首次训练及其固定 Skill 复测](../skilladam_alfworld_v24_9_feedback_20261109_001507/README.md)

## 离线复核

在仓库根目录运行。第一条命令逐题核对本次评测，第二条使用基线训练轨迹和模拟 HTTP 请求验证反馈实现。

```sh
/Users/didi/miniforge3/envs/skilladam/bin/python -B -m src.skill_evolution.skilladam.alfworld.trajectory_feedback.archive skilladam_alfworld_v24_9_feedback_rerun_20261109_125648
/Users/didi/miniforge3/envs/skilladam/bin/python -B scripts/runs/skilladam/alfworld/trajectory_feedback/verify_alfworld_skilladam_v24_9_feedback.py
```

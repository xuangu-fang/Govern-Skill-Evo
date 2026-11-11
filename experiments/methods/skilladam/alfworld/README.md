# SkillAdam · ALFWorld

按 SkillAdam 自身的实验配置组织。同一配置下，训练使用原实验 ID，首测与复测各自使用独立的评测 ID，并指向评测实际使用的 Skill。

| 已整理配置 | 训练或准备记录 | 评测 |
|---|---|---|
| 共享 Actor（`shared_actor`） | [六轮训练与最终 Skill](shared_actor/skilladam_current_actor_20261025/README.md) | [120 / 134（89.55%）](shared_actor/skilladam_current_actor_20261025/results/skilladam_current_actor_20261025_test134/summary.json) |
| 原生重试 | [材料与预检](native_retry/skilladam_alfworld_native_retry_20261029_001/README.md) | 仅准备 |
| 官方优化器 | [材料与预检](native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/README.md) | 仅准备 |
| Actor 与优化器均使用官方模型 | [六轮训练与最终 Skill](native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/README.md) | [首测 117 / 134](native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/results/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001_test134/summary.json) · [复测 116 / 134](native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/results/skilladam_alfworld_retest134_20261107_231301/summary.json) |
| 逐步轨迹反馈 · 首次训练 | [六轮训练与最终 Skill](trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/README.md) | [首测 120 / 134](trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/results/skilladam_alfworld_v24_9_feedback_20261109_001507_test134/summary.json) · [固定 Skill 复测 121 / 134](trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/results/skilladam_alfworld_v24_9_feedback_20261109_001507_retest_20261109_012307_test134/summary.json) |
| 逐步轨迹反馈 · 独立重训 | [六轮训练与最终 Skill](trajectory_feedback/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648/README.md) | [首测 110 / 134](trajectory_feedback/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648/results/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648_test134/summary.json) |

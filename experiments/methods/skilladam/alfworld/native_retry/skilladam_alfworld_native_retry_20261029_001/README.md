# SkillAdam · ALFWorld · 原生重试

在共享 Actor 配置上启用上游 SDK 的 2 次重试，将训练并发调至 10。Actor 与优化器均使用内网 deepseek-v4.1-flash。 [来源实验](../../shared_actor/skilladam_current_actor_20261025/README.md)

已完成配置准备与离线预检。当前归档没有训练或 Test 记录。

[Actor 配置](config/actor.json) · [优化器与训练参数](config/skilladam.json) · [初始 Skill](config/initial_skill.md) · [任务划分](config/splits) · [准备时的预检记录](results/preflight.json)

[原配置说明](config/provenance/README.before-layout.md) · [验证记录](results/verification.json) · [并发修订](config/configuration_revisions/001_official_workers) · [修订后核验](results/official_settings_verification.json) · [复核记录](results/reaudit.json)

## 离线预检

从仓库根目录运行。配置中记录的历史输出路径由运行入口解析到当前归档位置。

```sh
/Users/didi/miniforge3/envs/skilladam/bin/python -B scripts/runs/skilladam/alfworld/native_retry/run_skilladam_alfworld_native_retry.py --experiment experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/config --check
```

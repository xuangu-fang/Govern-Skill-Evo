# SkillAdam · ALFWorld · 官方优化器

沿用原生重试和 10 并发，仅将优化器改为官方 deepseek-flash。Actor 继续使用内网 deepseek-v4.1-flash。 [来源实验](../skilladam_alfworld_native_retry_20261029_001/README.md)

已完成配置准备与离线预检。当前归档没有训练或 Test 记录。

[Actor 配置](config/actor.json) · [优化器与训练参数](config/skilladam.json) · [初始 Skill](config/initial_skill.md) · [任务划分](config/splits) · [准备时的预检记录](results/preflight.json)

[原配置说明](config/provenance/README.before-layout.md) · [验证记录](results/verification.json)

## 离线预检

从仓库根目录运行。配置中记录的历史输出路径由运行入口解析到当前归档位置。

```sh
/Users/didi/miniforge3/envs/skilladam/bin/python -B scripts/runs/skilladam/alfworld/native_retry/run_skilladam_alfworld_official_optimizer.py --experiment experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/config --check
```

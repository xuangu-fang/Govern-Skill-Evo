# SpreadsheetBench v25.1

使用当前轮证据调整 Preconditioner，关闭知识复审。正式训练配置使用 `v25_1_current_update_evidence_to_behavior_v1`，训练与首测使用各自的配置。[实验记录](../../../experiments/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1/README.md)

- [方法和 Actor 源码](../../../src/skill_evolution/v25_1)、[已批准的提示词](../../../experiments/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1/config/bundle/approved_prompts/v25_1)、[离线测试](../../../tests/skill_evolution/v25_1/offline_suite)
- [历史双方法调度入口](../../../scripts/runs/spreadsheetbench/schedules/v25_1_skilladam_run_20261030_001/launcher/control.py)、[调度配置](../../../experiments/benchmarks/spreadsheetbench/schedules/v25_1_skilladam_run_20261030_001/settings.json)。维护版调度按方法选择 v25.1 或 SkillAdam 的实现。
- [v25.2 准备脚本](../../../scripts/runs/v25_2/prepare_v25_2_comparison.py) 直接读取 v25.2 已发布的配置。v25.1 作为当时的实验基线保留。[SkillAdam Actor 准备脚本](../../../scripts/runs/skilladam/spreadsheetbench/aligned_actor/prepare_skilladam_v25_1_actor.py) 读取独立归档的对齐 Actor 配置，其中保留了与 v25.1 对齐的消息和评分口径。

从仓库根目录验收，环境需有 pytest、openpyxl 和 requests。

```sh
python scripts/runs/v25_1/verify_bundle.py
python -m pytest -q tests/skill_evolution/v25_1/offline_suite
```

本机保有原始运行时，执行 `python scripts/runs/v25_1/verify_bundle.py --archive` 核对逐轮记录及全部 280 条轨迹。维护代码及合成测试可以在仅有源码和精选材料的检出中运行。

为新实验准备输入时，执行 `python -m src.skill_evolution.v25_1.cli prepare --output <新目录>`。训练命令使用 `python -m src.skill_evolution.v25_1.cli run --config <新目录>/config/config.json --campaign <新训练目录>`。评测命令使用 `python -m src.skill_evolution.v25_1.evaluation run --experiment <新目录> --campaign <新训练目录> --root <新测试目录>`。真实运行需要 Verified-400 数据、模型访问和 Docker 环境。

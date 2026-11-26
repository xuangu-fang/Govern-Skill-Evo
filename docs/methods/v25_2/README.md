# SpreadsheetBench v25.2

v25.2 延续 v25.1 的训练流程，改用两份经复审的提示词：Diagnosis 选择至多两项更新，Preconditioner 对当前更新给出更精简的调整。[方法源码](../../../src/skill_evolution/v25_2) · [已批准的提示词](../../../experiments/methods/v25_2/v25_2_prompt_only_20261101_001/config/approved_prompts) · [实验记录](../../../experiments/methods/v25_2/v25_2_prompt_only_20261101_001/README.md)

## 运行入口

在仓库根目录使用。准备命令从发布配置生成训练和首测输入，按本次检出位置解析 Verified-400 工作簿。正式运行需要模型访问及对应 Docker 镜像。

```sh
python -m src.skill_evolution.v25_2.cli prepare --output <新目录>
python -m src.skill_evolution.v25_2.cli run --config <新目录>/config/config.json --campaign <新训练目录>
python -m src.skill_evolution.v25_2.evaluation run --experiment <新目录> --campaign <新训练目录> --root <新测试目录>
```

[联合运行入口](../../../scripts/runs/v25_2/run_pipeline.py) 的 `check` 可离线检查发布记录。`start --output <新目录>` 用于需要正式训练、测试及与两组历史结果比较的独立运行。

## 离线核对

```sh
python scripts/runs/v25_2/verify_bundle.py
python -m pytest -q tests/skill_evolution/v25_2 tests/skill_evolution/v25_3 tests/skill_evolution/v25_4
```

持有本机原始记录时，可加 `--archive` 核对 8 轮训练和 280 条测试轨迹。v25.3、v25.4、v25.5 的 Actor 均加载本版方法包，使用本实验的训练配置、首测评分器和训练时的运行环境记录。三版各自的提示词和已完成实验仍归各自版本。

使用三个下游训练入口时，可用 `prepare --output <新目录>` 生成本次整理后的配置和运行契约。旧实验记录仍使用当时的运行契约。

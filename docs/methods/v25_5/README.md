# SpreadsheetBench v25.5

v25.5 沿用 v25.4 的运行流程，修订 Diagnosis、Preconditioner 和 Editor 提示词。[设计清单](design_manifest.json) · [方法代码与提示词](../../../src/skill_evolution/v25_5)

| 实验记录 | 状态 |
|---|---|
| [DeepSeek 官方线路](../../../experiments/methods/v25_5/v25_5_spreadsheetbench_deepseek/README.md) | 8 轮训练；完整首测 225/280，全量复测 230/280 |
| [代理配置](../../../experiments/methods/v25_5/v25_5_spreadsheetbench_proxy/README.md) | 已初始化，0 轮 |
| [Editor 修订前代理配置](../../../experiments/methods/v25_5/v25_5_spreadsheetbench_proxy_before_editor_revision/README.md) | 已初始化，0 轮，保留当时的设计和提示词 |

## 运行和验收

从仓库根目录运行。[训练与首测入口](../../../scripts/runs/v25_5/run_v25_5_train_test.py) 的默认配置使用代理线路。需要 SpreadsheetBench 环境、本地 Docker 镜像、工作簿、v25.4 历史运行和共享压缩归档。以下命令在新目录生成配置，并运行[工作簿和提示词专项验收](../../../scripts/verification/v25_5/verify_v25_5_offline.py)。

```sh
python scripts/runs/v25_5/run_v25_5_train_test.py verify --output <新目录>
```

核对历史成绩时，第一条命令读取精选材料；第二条同时核对原始训练提交和 560 条评测轨迹。

```sh
python scripts/runs/v25_5/verify_bundle.py
python scripts/runs/v25_5/verify_bundle.py --archive
```

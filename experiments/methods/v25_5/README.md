# SpreadsheetBench v25.5 实验索引

[方法说明](../../../docs/methods/v25_5/README.md)

| 实验 | 状态 | 完成轮次 | 评测 |
|---|---|---:|---|
| [v25_5_spreadsheetbench_deepseek](v25_5_spreadsheetbench_deepseek/README.md) | 完成训练 | 8 | 230/280、225/280 |
| [v25_5_spreadsheetbench_proxy](v25_5_spreadsheetbench_proxy/README.md) | 仅准备 | 0 | — |
| [v25_5_spreadsheetbench_proxy_before_editor_revision](v25_5_spreadsheetbench_proxy_before_editor_revision/README.md) | 仅准备（Editor 修订前） | 0 | — |

从仓库根目录使用 SpreadsheetBench Python 执行离线校验。接入压缩归档后可增加 `--archive` 读回原始记录。

```sh
python scripts/runs/v25_5/verify_bundle.py
python scripts/runs/v25_5/verify_bundle.py --archive
```

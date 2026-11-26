# SpreadsheetBench v25.3 实验索引

[方法说明](../../../docs/methods/v25_3/README.md)

| 实验 | 状态 | 完成轮次 | 评测 |
|---|---|---:|---|
| [v25_3_spreadsheetbench_20261106_1200](v25_3_spreadsheetbench_20261106_1200/README.md) | 启动流程取消，训练未开始 | 0 | — |
| [v25_3_spreadsheetbench_proxy](v25_3_spreadsheetbench_proxy/README.md) | 完成训练 | 8 | 214/280 |

从仓库根目录使用 SpreadsheetBench Python 执行离线校验。接入压缩归档后可增加 `--archive` 读回原始记录。

```sh
python scripts/runs/v25_3/verify_bundle.py
python scripts/runs/v25_3/verify_bundle.py --archive
```

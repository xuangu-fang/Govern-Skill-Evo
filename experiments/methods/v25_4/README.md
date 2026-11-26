# SpreadsheetBench v25.4 实验索引

[方法说明](../../../docs/methods/v25_4/README.md)

| 实验 | 状态 | 完成轮次 | 评测 |
|---|---|---:|---|
| [v25_4_spreadsheetbench_proxy](v25_4_spreadsheetbench_proxy/README.md) | 完成训练 | 8 | 3/4、222/280、225/280、8/10 |

从仓库根目录使用 SpreadsheetBench Python 执行离线校验。接入压缩归档后可增加 `--archive` 读回原始记录。

```sh
python scripts/runs/v25_4/verify_bundle.py
python scripts/runs/v25_4/verify_bundle.py --archive
```

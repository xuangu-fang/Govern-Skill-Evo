# SpreadsheetBench v25.2 实验索引

[方法说明](../../../docs/methods/v25_2/README.md)

| 实验 | 状态 | 完成轮次 | 评测 |
|---|---|---:|---|
| [v25_2_prompt_only_20261101_001](v25_2_prompt_only_20261101_001/README.md) | 完成训练 | 8 | 229/280 |

从仓库根目录使用 SpreadsheetBench Python 执行离线校验。接入压缩归档后可增加 `--archive` 读回原始记录。

```sh
python scripts/runs/v25_2/verify_bundle.py
python scripts/runs/v25_2/verify_bundle.py --archive
```

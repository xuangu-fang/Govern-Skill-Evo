# SpreadsheetBench v25.1 实验索引

[方法说明](../../../docs/methods/v25_1/README.md)

| 实验 | 状态 | 完成轮次 | 评测 |
|---|---|---:|---|
| [v25_v25_1_common_actor_no_review_20261030_001_v25_1](v25_v25_1_common_actor_no_review_20261030_001_v25_1/README.md) | 完成训练 | 8 | 223/280 |

从仓库根目录使用 SpreadsheetBench Python 执行离线校验。接入压缩归档后可增加 `--archive` 读回原始记录。

```sh
python scripts/runs/v25_1/verify_bundle.py
python scripts/runs/v25_1/verify_bundle.py --archive
```

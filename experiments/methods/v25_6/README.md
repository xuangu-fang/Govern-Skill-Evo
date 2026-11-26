# SpreadsheetBench v25.6 实验索引

[方法说明](../../../docs/methods/v25_6/README.md) · [候选提交清单](checkout_paths.txt)

| 训练 | 发布与评测 |
|---|---|
| [v25_6_spreadsheetbench_deepseek](v25_6_spreadsheetbench_deepseek/README.md) | 官方 DeepSeek Flash，120 题、8 轮。11 次完整评测和 2 题专项复跑。R08 全量成绩为 225、229、222 / 280。 |

从仓库根目录执行精选材料校验，接入本地归档后可以逐题读回。

```sh
python3 scripts/runs/v25_6/verify_bundle.py
python3 scripts/runs/v25_6/verify_bundle.py --archive
```

以 v25.8 提交 `6135f2eb398` 为基线，使用候选文件和 800 份基准工作簿在独立检出完成常规离线预检。挂载归档后读回 225 条训练轨迹和 3,082 份评测回执。R07 只执行 Parent，累计训练题次为 225。

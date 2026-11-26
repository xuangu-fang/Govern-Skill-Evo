# SpreadsheetBench v25.7 实验索引

[方法说明](../../../docs/methods/v25_7/README.md) · [候选提交清单](checkout_paths.txt)

| 运行 | 模型 | 发布与评测 |
|---|---|---|
| [v25_7_spreadsheetbench_deepseek](v25_7_spreadsheetbench_deepseek/README.md) | DeepSeek Flash | 仅准备，归档初始 Skill 与预检报告。 |
| [v25_7_spreadsheetbench_v41_20261116](v25_7_spreadsheetbench_v41_20261116/README.md) | DeepSeek v4.1 Flash | 120 题、8 轮，10 次完整评测。R08 为 227、226、226 / 280。 |
| [v25_7_spreadsheetbench_official_20261118_212017](v25_7_spreadsheetbench_official_20261118_212017/README.md) | DeepSeek Flash | 120 题、8 轮。R08 正式评测为 216 / 280。 |

从仓库根目录执行精选材料校验，接入本地归档后可以读回三条记录。使用 `--run <运行 ID>` 可单独验证。

```sh
python3 scripts/runs/v25_7/verify_bundle.py
python3 scripts/runs/v25_7/verify_bundle.py --archive
```

候选清单建立在 v25.6 的候选范围之上。独立检出中，当前入口的 public 和 internal 两套离线预检均通过。挂载归档后读回两次完成训练的 480 条轨迹、11 次评测的 3,080 份回执，并核对仅准备记录的 R00 与历史源码合同。

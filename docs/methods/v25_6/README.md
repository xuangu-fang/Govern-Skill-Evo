# SpreadsheetBench v25.6

v25.6 使用本版本的 [Diagnosis](prompt_draft/diagnosis.md)、[Preconditioner](prompt_draft/preconditioner.md) 和 [Editor](prompt_draft/editor.md)。训练使用 15 并发，最终测试使用 40 并发。其余配置沿用 [v25.5 DeepSeek 官方配置](../../../experiments/methods/v25_5/v25_5_spreadsheetbench_deepseek/config/config.json)。

## 运行入口

从仓库根目录运行离线检查。该命令检查配置、工作簿、运行环境、提示词绑定，并用模拟数据确认测试入口只收到最终 Skill。

```sh
/Users/didi/miniforge3/envs/spreadsheetbench/bin/python scripts/runs/v25_6/run_v25_6_train_test.py verify
```

`prepare` 准备实验，`run` 通过官方 DeepSeek API 启动或继续训练和最终测试。默认输出目录为 `artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek`，可用 `--output` 指定。

## 训练快照与最终测试

[实验归档](../../../experiments/methods/v25_6/README.md)收录正式训练、逐轮保留 Skill、11 次完整评测和两题专项复跑。

准备时保存初始 Skill 到 `snapshots/R00.md`。每轮训练后，把 gate 实际保留的 Skill 保存到 `snapshots/R01.md` 至 `snapshots/R08.md`，供查看训练过程。

8 轮训练完成后，测试程序读取 `campaign/final_skill.md`，在固定的 280 道测试题上评测这一份 Skill。整题成功数、成功率和逐题结果保存在 `test/summary.json`。

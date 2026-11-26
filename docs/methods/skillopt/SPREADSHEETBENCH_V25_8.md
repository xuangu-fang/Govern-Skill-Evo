# SpreadsheetBench SkillOpt 与 v25.8、SkillAdam 对照

[正式运行与历史准备档](../../../experiments/methods/skillopt/spreadsheetbench/README.md)包含冻结配置、原生检查点、Selection、受测 Skill 和评测索引。

从仓库根目录运行离线验收。默认动作也是 `verify`，需要本机已有的 SpreadsheetBench Docker 镜像和两次正式运行的归档。

```sh
/Users/didi/miniforge3/envs/skillopt/bin/python scripts/runs/skillopt/spreadsheetbench/run.py verify
```

入口把解析后的配置和验收报告写入 `artifacts/methods/skillopt/spreadsheetbench_v25_8/`，可通过 `--output` 指定目录。验收用模拟响应和临时合成数据，实际执行 Docker 中的工作簿程序，并走完整的原生优化循环。

| 动作 | 行为 |
|---|---|
| `verify` | 对照 11 月 18 日 v25.8、11 月 20 日 SkillAdam 的冻结配置和源码，检查 800 份工作簿文件、Docker 环境、Actor 请求、评分及优化器。结果见 `offline_verification.json`。 |
| `train` | 使用正式模型执行 4 个 epoch，在 40 题 Selection 上完成最终选优。 |
| `test` | 读取已完成的 `selection.json` 与匹配的 `best_skill.md`，用 40 并发评测固定 280 题。 |
| `train-test` | 顺序执行正式训练、最终选优和 Best 测试。 |

训练读取上游提交 `7da46ae693ee0329b80225c0128a37d65db10e9e` 的 SpreadsheetBench 配置、数据拆分及初始 Skill。Actor 和优化器走官方 DeepSeek Flash，使用项目根目录的 `.env`。Actor 在 v25.8 的 SpreadsheetBench Python 中运行，优化器在 SkillOpt Python 中运行。Actor 配置文件内保留了原实验的 8 × 15 批次记录，实际训练批次由 SkillOpt DataLoader 生成。每个 epoch 的两个 40 题批次及任务顺序可在验收报告中查看。

正式入口保留原生反思、合并、编辑、严格 hard Gate、slow update 和 meta skill。按论文 §3.6 启用 `slow_update_gate_with_selection=true`。从第 2 个 epoch 末开始，每个慢更新候选也需要在同一批 40 道 Selection 题上严格提升 hard 才能被采纳。官方配置中 `max_analyst_rounds=3`，此固定版本的 Trainer 读取并打印该值，SpreadsheetBench 的 patch 反思路径按 minibatch 调用 analyst。编辑预算由上游 scheduler 在有可编辑提案的步骤推进。

为支持单独执行 Test，入口关闭 Trainer 自带的组合测试阶段，在训练完成后单独执行同样的最终 Selection 晋升规则。若最后一版和已选 Best 相同就复用分数，否则用同一批 40 题复评；严格提升才晋升。交付物是**运行目录根部**的 `best_skill.md`。对应的步骤、来源、Selection hard 分数及内容摘要保存在 `selection.json`。测试沿用 v25.8 的修正元数据及评测写入器，`test/summary.json` 包含成功题数、hard、逐题平均单元格通过率及逐题轨迹路径。

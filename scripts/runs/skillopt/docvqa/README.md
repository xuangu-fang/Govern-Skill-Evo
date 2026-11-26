# DocVQA SkillOpt

运行入口使用本地 `external/SkillOpt` 的 DocVQA DataLoader、提示词和原生 Trainer。Actor 复用 v29.11 和 DocVQA SkillAdam 的图文请求、技术重试和评分实现。模型请求参数和 SkillOpt 参数保存在运行目录的 `run.json`。[实验配置](../../../../experiments/configs/docvqa_skillopt_deepseek_flash.yaml)

| 阶段 | 配置 |
|---|---|
| Train | 官方 107 题，seed 42，每个 epoch 洗牌，每批 40、40、27 题。4 个 epoch 共 12 个常规更新步。 |
| Selection | 固定使用官方 Val 的全部 53 题。普通补丁和跨 epoch 的 slow update 均按 Hard 严格提升采纳。最终候选与 Best 不同时再做一次 Selection，冻结根目录的 `best_skill.md`。 |
| Test | 官方 374 题，60 并发。每次独立评测汇报 Hard 通过数、通过率、平均 ANLS 和实际 Actor 请求数。 |
| Actor 与优化器 | 两者均使用 DeepSeek 官方 `deepseek-flash`，温度 1、medium reasoning、thinking enabled、300 秒超时。Actor 单次最多输出 32,768 tokens，优化器的 patch 路径最多输出 16,384 tokens。训练和验证的 Actor 并发为 16。 |
| 优化流程 | 原生成功与失败反思、层级合并、排序和 patch 更新。反思和合并批量均为 8，analyst 并发 16。编辑预算按 cosine 从 4 衰减至 2，第 2 个 epoch 起启用 20 题慢更新比较和优化器侧 meta skill。 |

## 离线验证

在仓库根目录执行以下命令。验证器逐题比对已准备好的真实数据和原生图文请求，在临时目录使用合成图像及模拟模型完成同等规模的训练、验证、测试和中断恢复。报告中的模拟调用计数用于核验流程。

```sh
PY=/Users/didi/miniforge3/envs/DocVQA/bin/python
RUN=scripts/runs/skillopt/docvqa/run.py
"$PY" "$RUN" verify --report artifacts/verification/docvqa_skillopt_deepseek_flash/verification.json
```

## 正式训练和测试

`train` 和 `test` 使用仓库根目录的 `.env`，也支持 `--env-file` 指定 DeepSeek 凭据文件。以下命令使用同一运行目录。训练完成后生成 `selection.json` 和 `best_skill.md`，测试启动时校验文件哈希。

```sh
"$PY" "$RUN" train --output experiments/baselines/docvqa_skillopt_deepseek_flash
"$PY" "$RUN" test --output experiments/baselines/docvqa_skillopt_deepseek_flash
```

首次测试结果位于 `test/summary.json`。重跑相同测试命令会复用已完成的逐题结果。需要独立复测时在测试命令末尾添加 `--repeat 2` 或 `--repeat 3`，结果分别保存到 `test_repeat_2/` 和 `test_repeat_3/`。

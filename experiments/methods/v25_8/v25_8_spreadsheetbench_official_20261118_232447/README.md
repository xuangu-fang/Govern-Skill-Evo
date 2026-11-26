# v25_8_spreadsheetbench_official_20261118_232447

11 月 18 日准备的官方 DeepSeek Flash 运行于北京时间 11 月 19 日 00:26 启动。训练使用 120 道题，分 8 轮，每轮 15 题。评测使用固定的 280 道留出题。评分主指标为整题完全成功率，辅助指标为逐题单元格正确率的平均值。

[冻结训练配置](config/train.json) · [冻结 Test 配置](config/test.json) · [源码合同](config/contract.json) · [Docker 运行环境](config/runtime.json) · [原始启动记录](../../../../artifacts/methods/v25_8/v25_8_spreadsheetbench_official_20261118_232447/launch.json)

## 训练发布

[逐轮发布记录](results/training_summary.json)保存每轮的父提交、发布提交、Gate 决策和保留 Skill 的 SHA-256。R04 的 Gate 沿用 R03 文本。R00 的共用基线测试另在[初始 Skill 对照](../../../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/shared_R00/summary.json)登记。

| 轮次 | Parent 成功 | Candidate 成功 | 采纳／拒绝／暂缓 | 发布 Skill |
|---|---:|---:|---:|---|
| R00 | — | — | — | [初始 Skill](results/skills/R00.md) |
| R01 | 9/15 | 12/15 | 2／0／3 | [R01 Skill](results/skills/R01.md) |
| R02 | 11/15 | 12/15 | 2／0／2 | [R02 Skill](results/skills/R02.md) |
| R03 | 10/15 | 10/15 | 1／1／2 | [R03 Skill](results/skills/R03.md) |
| R04 | 12/15 | 11/15 | 0／0／3 | [R04 Skill](results/skills/R04.md) |
| R05 | 10/15 | 12/15 | 2／0／2 | [R05 Skill](results/skills/R05.md) |
| R06 | 11/15 | 14/15 | 3／0／1 | [R06 Skill](results/skills/R06.md) |
| R07 | 14/15 | 14/15 | 1／0／1 | [R07 Skill](results/skills/R07.md) |
| R08 | 9/15 | 13/15 | 3／0／1 | [R08 Skill](results/skills/R08.md) |

## 评测

R08 的三次官方 DeepSeek Flash 评测中位数为 **227/280**。独立的 GPT-5.4-mini 评测使用同一份 R08 Skill。主目录有 279 份标准回执，`test:191-40` 在 128,000 token 的独立补测中通过，合计 **180/280**。该补测保留请求、执行与评分记录。

[机器可读评测索引](results/evaluations.json)连接每场评测的精选摘要、受测 Skill 哈希和原始归档路径。

| 受测轮次 | 评测 | Actor | 整题成功 | 摘要 | 原件 |
|---|---|---|---:|---|---|
| R01 | 首测 | `deepseek-flash` | 220/280 | [摘要](results/spreadsheetbench_v25_8_round_tests_20261119__R01/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R01) |
| R01 | 第 2 次评测 | `deepseek-flash` | 214/280 | [摘要](results/spreadsheetbench_v25_8_round_retests_20261119_191247__R01/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R01) |
| R01 | 第 3 次评测 | `deepseek-flash` | 216/280 | [摘要](results/spreadsheetbench_v25_8_R01_third_20261120_221556__R01/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_R01_third_20261120_221556/R01) |
| R02 | 首测 | `deepseek-flash` | 220/280 | [摘要](results/spreadsheetbench_v25_8_round_tests_20261119__R02/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R02) |
| R02 | 第 2 次评测 | `deepseek-flash` | 210/280 | [摘要](results/spreadsheetbench_v25_8_round_retests_20261119_191247__R02/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R02) |
| R02 | 第 3 次评测 | `deepseek-flash` | 223/280 | [摘要](results/spreadsheetbench_v25_8_R02_repeat_20261119_193936__R02/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_R02_repeat_20261119_193936/R02) |
| R03 | 首测 | `deepseek-flash` | 219/280 | [摘要](results/spreadsheetbench_v25_8_round_tests_20261119__R03/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R03) |
| R03 | 第 2 次评测 | `deepseek-flash` | 216/280 | [摘要](results/spreadsheetbench_v25_8_round_retests_20261119_191247__R03/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R03) |
| R05 | 首测 | `deepseek-flash` | 217/280 | [摘要](results/spreadsheetbench_v25_8_round_tests_20261119__R05/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R05) |
| R05 | 第 2 次评测 | `deepseek-flash` | 217/280 | [摘要](results/spreadsheetbench_v25_8_R05_repeat_20261119_183030__R05/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_R05_repeat_20261119_183030/R05) |
| R05 | 第 3 次评测 | `deepseek-flash` | 210/280 | [摘要](results/spreadsheetbench_v25_8_round_retests_20261119_191247__R05/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R05) |
| R06 | 首测 | `deepseek-flash` | 220/280 | [摘要](results/spreadsheetbench_v25_8_round_tests_20261119__R06/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R06) |
| R06 | 第 2 次评测 | `deepseek-flash` | 220/280 | [摘要](results/spreadsheetbench_v25_8_round_retests_20261119_191247__R06/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_retests_20261119_191247/R06) |
| R07 | 首测 | `deepseek-flash` | 227/280 | [摘要](results/spreadsheetbench_v25_8_round_tests_20261119__R07/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_round_tests_20261119/R07) |
| R07 | 第 2 次评测 | `deepseek-flash` | 224/280 | [摘要](results/spreadsheetbench_v25_8_R07_R08_retests_20261119_201604__R07/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_R07_R08_retests_20261119_201604/R07) |
| R08 | 首测 | `deepseek-flash` | 228/280 | [摘要](results/v25_8_spreadsheetbench_official_20261118_232447__test/summary.json) | [原始目录](../../../../artifacts/methods/v25_8/v25_8_spreadsheetbench_official_20261118_232447/test) |
| R08 | 第 2 次评测 | `deepseek-flash` | 227/280 | [摘要](results/spreadsheetbench_v25_8_R07_R08_retests_20261119_201604__R08/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_R07_R08_retests_20261119_201604/R08) |
| R08 | 第 3 次评测 | `deepseek-flash` | 227/280 | [摘要](results/spreadsheetbench_v25_8_R08_third_20261120_140000__R08/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_R08_third_20261120_140000/R08) |
| R08 | 跨 Actor（含独立补测） | `gpt-5.4-mini` | 180/280 | [摘要](results/spreadsheetbench_v25_8_final_gpt54mini_20261119__test/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_8_final_gpt54mini_20261119/test) |


## 离线核验

从仓库根目录执行。第一条校验精选材料、受测 Skill 哈希及冻结合同。第二条读取历史提交、Gate、训练轨迹、测试回执和独立补测。它使用共享压缩归档的原路径键，兼容历史回执中的绝对路径。

```sh
python3 scripts/runs/v25_8/verify_bundle.py
python3 scripts/runs/v25_8/verify_bundle.py --archive
```

历史读回需要原始训练和评测目录，以及 `experiments/benchmark_record_refs/spreadsheetbench/` 的共享数据。精选配置和 Skill 已保存为经验证的原始字节，可在独立检出直接核验。[共享归档说明](../../../benchmark_record_refs/README.md)

[候选提交文件清单](config/checkout_paths.txt)列出在当前分支基线之上、独立验收使用的文件，含 v25.8 冻结合同引用的 `v28/output_feedback.py` 和常规入口所需的旧版基础配置。常规入口预检还需要本机的 SpreadsheetBench Python 环境、`govern-skill-v25-python:rc1` Docker 镜像及 Trace2Skill Verified-400 数据。运行时和数据的定位见[方法说明](../../../../docs/methods/v25_8/README.md)。

独立检出以 `c1e604e56aa` 为基线，使用上述 245 个候选路径和 800 份基准工作簿。常规入口的 public、internal 两套离线预检均通过，生成的合同与历史合同逐项一致。挂载历史归档后，核验读回了 240 条训练轨迹、5,319 份标准测试回执和 1 份独立补测。

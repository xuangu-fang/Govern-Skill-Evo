# SpreadsheetBench SkillOpt 实验索引

[方法、Actor 对齐与 Selection 规则](../../../../docs/methods/skillopt/SPREADSHEETBENCH_V25_8.md)

| 记录 | 状态 |
|---|---|
| [10 月 29 日原生方案](skillopt_spreadsheetbench_official_actor48k_20261029/README.md) | 已准备与预检。 |
| [11 月 22 日正式运行](spreadsheetbench_v25_8/README.md) | 完成 4 个 epoch、8 次普通更新，Selection 选中第 7 步，39/40。归档 9 次完整评测。 |

从仓库根目录执行。

```sh
python3 scripts/runs/skillopt/spreadsheetbench/verify_bundle.py
python3 scripts/runs/skillopt/spreadsheetbench/verify_bundle.py --archive
```

历史读回会核对原生历史、Selection 的 40 份回执、两份 R02 文本、8 次常规 Test 及 1 次含独立补测的 Test。常规 SkillOpt 入口的容器与合成流程验收见方法文档。

[候选提交清单](checkout_paths.txt)包含 SkillOpt 精选归档、对照页和运行入口。精选材料校验及历史读回均在独立检出通过。常规入口的 Docker 与合成训练验收使用本机固定版本的 SkillOpt 上游环境。

# v24.2 在 ALFWorld 上的训练与评测

实验 ID 为 `v24_2_alfworld_20261106_195800`。这次实验从共同初始 Skill 和空 Memory 开始，在 57 道优化任务上执行六轮。R03 选中整个 Candidate，R04 选中部分更新，R05 和 R06 沿用 Parent。R06 发布的 Skill 用于两次独立的 134 题 Test。[训练摘要](results/training_summary.json) · [最终 Skill](results/final_skill.md) · [方法与运行命令](../../../../docs/methods/v24_2/README.md)

| 评测 | 成功题数 | 成功率 | Git 摘要 | 本机完整记录 |
|---|---:|---:|---|---|
| 首测 | 118/134 | 88.06% | [结果](results/v24_2_alfworld_20261106_195800_test134/summary.json) | [逐题轨迹与评测输入](../../../../artifacts/methods/v24_2/v24_2_alfworld_20261106_195800_test134/) |
| 固定 Skill 复测 | 115/134 | 85.82% | [结果](results/v24_2_alfworld_20261106_195800_test134_retest_20261106_212245/summary.json) | [逐题轨迹与评测输入](../../../../artifacts/methods/v24_2/v24_2_alfworld_20261106_195800_test134_retest_20261106_212245/) |

两次评测各自保留 Actor 的执行记录。[逐题对照与结果解释](reports/REPORT.md)

### 输入与运行现场

- [训练配置](config/config.json)含六批任务的顺序、Actor 参数和环境输入；[运行环境](config/runtime.json)和[原始训练契约](config/contract.json)记录该次运行使用的条件。
- [完整训练目录](../../../../artifacts/methods/v24_2/v24_2_alfworld_20261106_195800/)保存各轮输入、Gate 决定、发布状态和检查点。[启动记录](../../../../artifacts/methods/v24_2/v24_2_alfworld_20261106_195800/launch/)保存训练、首测与复测日志。
- [历史离线验收](../../../../artifacts/methods/v24_2/v24_2_alfworld_offline_001/)来自早期修订。它使用独立的夹具与记录，与这次六轮正式训练分别归档。

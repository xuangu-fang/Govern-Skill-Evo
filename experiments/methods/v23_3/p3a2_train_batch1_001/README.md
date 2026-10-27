# V23.3 Batch-1 A/B 实验

本实验比较 V23 自由调整与 V23.3 历史响应条件化 Patch。最终行为比较采用首个有效的 A2/B7，各组在相同六条任务上执行；追加生成次数不同，不是等预算的一次生成对照。

## 配置与结论

- [实验协议](PROTOCOL.md)、[配置](config.json)、[任务](tasks.json)、[Parent Skill](parent.md)
- [Preconditioner 比较](PRECONDITIONER_COMPARISON.md)、[Editor 报告](EDITOR_REPORT.md)
- [配对 Replay](REPLAY_REPORT.md)、[行为分析](PAIRED_BEHAVIOR_ANALYSIS.md)、[轨迹证据摘录](TRAJECTORY_EVIDENCE.md)
- [最终指标](final_metrics.json)、[成本与重试](RETRY_REPORT.md)、[最终决策](P3A2_DECISION.md)

## 历史修订

- [并行执行修订](amendment_parallel/README.md)
- [A/B 第二次生成修订](amendment_resampling/README.md)
- B 追加生成：[第 3 次](amendment_B_generation3/README.md)、[第 4 次](amendment_B_generation4/README.md)、[第 5 次](amendment_B_generation5/README.md)、[第 6 次](amendment_B_generation6/README.md)、[第 7 次](amendment_B_generation7/README.md)

修订目录中的配置、源码及阶段报告是历史快照；当前实验脚本位于本目录。历史冻结清单和元数据内的原路径保持原文，报告中的原始文件链接已更新。

## 原始归档与读取

[本地归档](../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/)保存完整输入、Memory、请求响应、18 条任务轨迹、日志和运行状态；不进入 Git。

| 本地材料 | 路径 |
|---|---|
| Grouping、Diagnosis、A/B 各次生成的原始输入与调用 | [runs](../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/runs/) |
| Editor 原始输入及调用 | [editors](../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/editors/) |
| Parent/A/B 完整轨迹与逐步调用 | [episodes](../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/episodes/) |
| 完整行为分析与逐次调用账本 | [analysis.json](../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/analysis.json) |

本目录的 `runs/`、`editors/`、`episodes/` 只保留精选输出、候选、Diff、校验和失败证据。`archive_io.load_saved` 在系统临时目录拼合读取所需文件，并仅在临时元数据中连接上游路径；完成或失败后均删除临时目录，不修改历史源文件。当前脚本使用归档位置判断任务和生成是否已经执行。

离线读取选定的 A2/B7 可调用 `repeat_pc.selected("A")` 和 `repeat_pc.selected("B")`，不发起模型请求。分析和报告脚本读取新位置，不再依赖在线启动入口的冻结检查与 API 配置。

迁移前后，Grouping、Diagnosis 和 A2/B7 的加载均通过。旧 A/B Editor 归档与当前 Editor Prompt 不一致，原加载器仍报 `Saved Editor prompt/input differs`；这是迁移前已有的版本差异，归档未为通过校验而重写。历史在线启动的冻结约束保留，本次未重新运行模型、环境或历史实验。

# B 第三次生成

本目录保存第三次生成前的配置、源码及冻结记录。`repeat_pc.py` 是当时第二次生成脚本的历史快照，不是独立运行入口；`preconditioner_gate.json` 记录前两次尝试的状态。

- [实验修订说明](../B_GENERATION3_AMENDMENT.md)
- [第三次输出评价](../B_THIRD_ATTEMPT_EVALUATION.md)
- [输出与失败证据](../runs/B_retry_002/)：保留解析输出、原始输出正文、响应摘要、Prompt、输入预算、引用审计、错误堆栈和校验结论。
- [完整输入与调用归档](../../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/runs/B_retry_002/)：本地保存 `input.json`、`model_input.json`、`messages.json`、`run.json` 和 `call/`，不进入 Git。
- [运行日志](../../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/B_generation3.log)：本地归档。

第三次生成对应主实验的 `runs/B_retry_002`。输出因 `reason: unavailable historical reference` 未通过校验，没有有效 Effective Plan、Candidate、Editor 或 Replay 结果。

当前主实验 `repeat_pc.py` 从归档位置读取已迁移的生成状态；`analyze.py` 同时读取实验目录和归档目录中的调用账本。冻结记录及日志中的旧路径保留为历史信息。其余 generation 的配置与源码快照保持原样。

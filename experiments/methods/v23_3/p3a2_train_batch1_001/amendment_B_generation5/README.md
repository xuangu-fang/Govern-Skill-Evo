# B 第五次生成

本目录保存本次追加生成前的配置、报告及源码快照；其中 `repeat_pc.py`、`write_final_reports.py` 是历史版本，不是独立运行入口。当前主实验入口位于上一级目录，冻结记录和历史报告原文保持不变。

- [实验修订说明](../B_GENERATION5_AMENDMENT.md)
- [本次输出评价](../B_FIFTH_ATTEMPT_EVALUATION.md)
- [输出与必要证据](../runs/B_retry_004/)：保留 Prompt、输入预算、原始输出正文、解析结果、响应摘要及校验材料。
- [完整输入与调用归档](../../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/runs/B_retry_004/)：本地保存输入、消息、模型输入、运行元数据和调用记录，不进入 Git。
- [本阶段原始快照](../../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/amendment_B_generation5/)：完整调用账本及本阶段已有的辅助清单、补丁或日志；配置、报告、指标、源码快照和必要审计仍在本目录。
- [运行日志](../../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/B_generation5.log)

本次未通过校验：`Parent context/deletion text differs at declared position`。没有有效 Effective Plan，也没有由本次尝试产生的 Candidate、Editor 或 Replay 结果。

当前主实验 `repeat_pc.py` 从归档读取历史生成状态，`analyze.py` 汇总实验目录与归档目录中的调用记录。历史记录内的旧路径用于说明当时的运行位置，不改写为新的实验事实。

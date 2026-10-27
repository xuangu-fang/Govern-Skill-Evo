# 并行执行修订快照

[修订说明](../PARALLEL_AMENDMENT.md)记录该实验从串行调整为四并发的背景和边界。本目录保留授权、配置、冻结记录、交接记录、离线测试结果及当时的 `run.py`、`transport.py` 源码快照，不作为当前独立运行入口。

实际执行数据共用主实验的[本地归档](../../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/)：逐步轨迹位于 `episodes/`，并发日志、运行锁和节流状态位于归档根目录。当前并行入口是上一级 `parallel.py`，从归档读取已有结果并跳过已执行任务。

当前结论见[最终决策](../P3A2_DECISION.md)及[配对 Replay](../REPLAY_REPORT.md)。历史配置、授权和源码快照保持原文。

# r06_actor_comparison_001：Actor 比较材料

本目录保留 [实验协议](PROTOCOL.md)、[结果报告](REPORT.md)、[机制分析](MECHANISMS.md)、[轨迹证据索引](TRACE_INDEX.md)、[配置](config/)、Parent/Candidate 和源码。

## 保留结果与必要证据

- [逐任务指标与汇总](results/)，包括 Parent/Candidate 每条任务的指标、紧凑轨迹、[配对统计](results/summary.json) 和 [CSV](results/task_results.csv)。
- [逐 episode 和配对审计](results/audit.json)、[执行回执与单步重试](results/execution_receipt.json)。
- [运行选择与完成状态](runs/)：保留 `selected.json` 与各次 `attempt.json`；[整体完成记录](completion.json) 也保持原文。

历史共有 **14 条完整 episode、333 次 HTTP 尝试**，episode 重启次数为 **0**。任务未成功与技术中断是不同状态；原报告的成功率、机制判断和失败边界均未改写。

## 本地原始归档

[归档 runs/](../../../../artifacts/methods/v23_4/r06_actor_comparison_001/runs/) 保存完整轨迹、逐步 HTTP 正文、进程日志、命令和启动记录；运行锁也已归档。

[公共读取工具](../archive_io.py) 解析历史路径并合并枚举分开存放的记录。`run.py` 复用保留的选中结果或完成标记，已迁移实验的新原始输出写入 artifacts；`analyze.py` 和后续 Replay 读取归档中的轨迹及对应响应文件。

历史 JSON 中的轨迹路径保持原文，由读取逻辑解析；报告链接已指向新位置。历史启动和审计校验没有放宽，本次没有重跑 Actor、模型或完整历史审计。只克隆 Git 不包含完整轨迹与响应。

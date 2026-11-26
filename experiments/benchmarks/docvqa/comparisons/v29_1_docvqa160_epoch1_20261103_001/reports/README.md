# v29.1 训练与 Test 监督

2026-11-03 后续授权：用户要求定位并修复运行时快照异常，再启动正式 Test。
本次局部修复、诊断证据及验收条件见 `runtime_repair.md`；仅本控制器的 Darwin
子进程增加 `MallocMediumZone=0`，不改变原实验配置、Prompt、评分、归档或累计恢复额度。
以下原始监督规则继续适用，源码禁改条款仅对上述已授权运行修复例外。

用户于 2026-11-03 授权启动正式训练，完成后自动启动 Test；训练和 Test 共用最多 3 次原配置外层恢复，首次启动不计数。第三次恢复仍失败则保持 halted，不再尝试。不得修改 Prompt、源码、模型、预算、超时、数据顺序或 Gate，不清零内部六次尝试额度，不通过删除归档重新采样。

- 控制程序：本目录 `control.py`，使用 `/Users/didi/miniforge3/envs/DocVQA/bin/python -B`。
- 状态：`v29_1_status.json`；恢复计数：`resume_attempts`；启动记录：`v29_1_launches.json`。
- 配置原文：`launch_manifest.json`；每次启动/恢复与正式配置直接比较。
- Train：`experiments/campaigns/v29_1_docvqa160_epoch1_20261103_001`。
- Test：`experiments/evaluations/v29_1_docvqa160_epoch1_20261103_001`。
- 日志：本目录 `v29_1_training.log`、`v29_1_test.log`、`v29_1_supervisor.log`。

`control.py status --arm v29_1` 查看状态。只有确认 worker 和 child 均不活跃且继承锁已释放时，使用 `control.py review --arm v29_1` 恢复；每次 review 最多消费一次全局恢复额度，计数在启动前持久化。锁或匹配命令的活进程仍存在时不重复启动。普通错题、Gate RETAIN 或执行较慢不算中断，不杀进程。

worker 完成训练后核对全部 11 批、160 题及最终 Skill，再启动独立 Test；Test 入口会先执行 final_parent 完整审计，之后才发送 374 题请求。恢复 Test 不重新训练。完成后保存 summary 路径并关闭监督状态。耗尽、语义停止或完整性错误不能通过变更原程序和归档绕过。

监督器的 7 项离线检查见 `supervisor_checks.json`；它们使用临时目录和模拟进程，验证三次额度、重复启动防护及阶段转换。

Codex heartbeat 每 10 分钟检查一次，仅在恢复、训练转 Test、最终完成、停止或需要用户处理时通知；正常运行不重复播报。达到 complete / halted 后暂停该 heartbeat，不归档聊天。

# v27 Actor 归档恢复缺口修复

本轮针对复审确认的恢复缺口修复实现并执行离线验收。未启动实验、未调用真实模型。五个方法模块的主要职责、Prompt、输出 schema、Preconditioner／Replay 证据权限、Gate 和六次请求总额度保持不变。

## 修复边界

原实现只根据单题 `result.json` 选择完成校验路径。即使 `trajectory.json` 或批次 `records.json` 已证明任务完成，只要 result 和响应归档丢失，就可能将旧请求误判为 unknown 并再次发送，随后才因轨迹冲突停止。

本轮只调整两个运行文件：

- `benchmarks/lmb/actor.py`：`trajectory.json` 同样触发只读完成校验。不能因 result 缺失而退回技术重试。
- `benchmarks/lmb/adapter.py`：持有批次锁后、启动任何 worker 前预检所有已知完成项。已有批次记录时校验完整覆盖、顺序和各任务原始归档后直接复用；没有批次汇总时逐题检查 trajectory 或 result，确认完整性后才允许执行尚未完成的任务。

这同时保护 Campaign 的 Parent／Candidate、独立 Test 恢复和直接 Actor 调用。混合了已完成题目与待执行题目的批次，若任一完成归档损坏，将在调度待执行题目前停止。结果、响应或轨迹缺失均不能通过重新作答补救。

正常中断恢复仍按原行为执行：

| 已保存状态 | 恢复行为 |
|---|---|
| 请求 started，尚无响应且没有完成记录 | 原请求计入 unknown；下一次请求沿用原槽位总额度，不重置为第一次 |
| 完整 response.json，尚未生成 result／trajectory | 本地解析并完成，不新增请求 |
| 完整 HTTP 状态和正文，尚未生成 response.json／result | 从 HTTP 归档恢复并完成，不新增请求 |
| 合法 result，尚未生成 trajectory／批次汇总 | 校验原始归档后补齐后续产物，不新增请求 |
| trajectory 或批次 records 已存在，但完成依赖损坏 | 停止；不得转为 unknown 或发送新请求 |

## 回归覆盖

新增 [test_actor_recovery.py](../../../tests/skill_evolution/v27/test_actor_recovery.py) 六个测试方法：

1. Campaign Parent 和 Candidate 均覆盖：批次汇总未保存，只剩单题完成轨迹；分别移除 result、result＋response，两次恢复均零新增请求，批次文件内容保持不变。
2. 已完成124道合成 Test：保留批次完成记录，分别移除 result、result＋response、result＋response＋trajectory；恢复均零新增请求。恢复被移除的文件后，健康重放仍零新增请求。
3. Campaign 混合批次：一题已完成、一题请求中断。完成题归档损坏时整个批次零新增请求；恢复有效归档后只重试真正未完成的一题，api_requests 为2且第一槽标为 unknown。
4. Test 混合批次：123题已完成、一题请求中断。先验证损坏完成项导致零新增请求，再验证修复归档后只新增1次请求，最终124题完成、总请求125次。
5. Campaign 在 response 落盘、HTTP 落盘、result 落盘三个位置中断，恢复均不重新发送请求，单题 api_requests 保持1。
6. 直接 Actor 调用遇到已有 trajectory 而 result／response 丢失时，停止且单题文件内容不变。

已有六次耗尽不重置、发布前后恢复、HTTP 后备归档、C01 完整容量场景等测试继续执行。验收映射的 `completed_actor_missing_result_resume` 记录这六项新增测试；F10／F11 增补对应的正常中断恢复用例。

## 离线验收

使用 `/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python`，沿用网络连接和子进程封锁，不读取真实模型凭据。新增执行数据均为 `synthetic:*`；真实177题仅作本地数据及映射核对。

本轮总计49个测试，失败0、错误0、跳过0；真实模型请求0、网络连接尝试0、实验启动0；raw／prepared_v1 数据哈希不变。

恢复修复阶段的49测试报告保存在 `artifacts/verification/v27_offline_actor_recovery_20261030/`：

- [总报告](../../../artifacts/verification/v27_offline_actor_recovery_20261030/validation.json)
- [逐测试结果](../../../artifacts/verification/v27_offline_actor_recovery_20261030/test_results.json)
- [验收映射及修复回归结果](../../../artifacts/verification/v27_offline_actor_recovery_20261030/acceptance.json)
- [测试日志](../../../artifacts/verification/v27_offline_actor_recovery_20261030/unittest.log)

此前33／43测试报告均保留。本轮 C01 的规模、预算和结论未扩大：只确认有界合成场景与超限拒绝行为，不声称已核实真实服务上下文容量。107项清单仍仅报告对应自动检查状态，历史人工样例不冒充本轮重新执行的语义判断。

## 后续边界回归固化

将复审期间独立验证的两种边界加入同一测试文件，新增两个测试方法，均分别覆盖 Campaign 和124题合成 Test：

1. `test_pending_first_damaged_completed_last_blocks_all_workers`：待执行题放在批次最前，已完成题放在最后；保留最后一题的轨迹，移除 result 和 response，批次没有汇总文件。重复恢复必须在创建线程池前失败，零新增请求，批次文件内容不变。
2. `test_corrupt_result_only_completion_blocks_all_workers`：同样采用上述顺序，但移除最后一题的 trajectory，保留合法 response 并损坏 result 的 content，覆盖仅有 result 完成标记的预检分支。重复恢复同样必须在创建线程池前失败。

两种场景都通过禁止构造 `ThreadPoolExecutor` 验证检查时机，不依赖线程恰好按有利顺序运行。恢复合法归档后，测试用请求目标记录确认只新增最前面未完成题目的1次请求；该题 api_requests 为2，原槽状态为 unknown，其余完成题仍为1。result-only 场景恢复时仍不放回 trajectory，验证系统能够无请求补齐轨迹。随后再次恢复零新增请求。

验收映射新增 `pending_first_and_result_only_archive_boundaries`。本次只修改测试、映射和说明文档，运行源码、Prompt、主要职责及输出契约均未改动。

独立 LMB 环境复验共51个测试通过，失败0、错误0、跳过0；网络连接尝试、真实模型请求、实验启动均为0，raw／prepared_v1 哈希未变化。C01 结果与49测试阶段相同，适用范围没有扩大。

最新结果：

- [总报告](../../../artifacts/verification/v27_offline_actor_boundaries_20261030/validation.json)
- [逐测试结果](../../../artifacts/verification/v27_offline_actor_boundaries_20261030/test_results.json)
- [验收与边界回归映射](../../../artifacts/verification/v27_offline_actor_boundaries_20261030/acceptance.json)
- [完整测试日志](../../../artifacts/verification/v27_offline_actor_boundaries_20261030/unittest.log)

49测试阶段报告保留，不覆盖。

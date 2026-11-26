# v27 Memory 发布内复用（2026-11-02）

修复已直接进入主工作区 v27，参照 v28/v29 的单次 Memory operation 设计。没有启动训练或正式 Test，没有真实模型请求。

## 结果

| 合成场景（已有 3 次历史提交） | 修改前完整历史遍历 | 修改后完整历史遍历 |
|---|---:|---:|
| 单独 commit_memory | 2 | 1 |
| 准备目录、提交、生成 view、发布前读取 | 6 | 1 |

以上通过修改前保存的实现与当前实现执行同一组合成数据测得。两种实现的提交对象、Memory view、active.json 和新提交文件字节一致。计数范围是一次正常发布；不包括轮次开始、跨请求或新进程的冷检查，也不代表实际训练速度提升倍数。不能由此推导 v28 的历史耗时或 v27 的 API 费用。

## 实现

- `contracts/memory.py`：单独提交直接使用首次 _archive 返回的 entries/contexts 生成当前 view，不再通过 load_memory 重复遍历；写入前保留 Active 一致性核对。
- `memory_operation.py`：ContextVar 绑定当前 benchmark 与 Memory 合约。单个作用域内记录已经验证的历史、条目和 view，向调用者返回独立副本。提交读取固定的原始字节快照，提交及退出前检查归档字节、目录成员和 Active 状态。
- `evolution.py`：作用域只覆盖准备 Memory 到最终发布，不跨长时间模型调用。复制目标必须与已验证源前缀一致才复用；已有更先进状态的恢复目标必须冷检查。提交后增量构造新 view，后续读取复用。发布官方 state 前再次核对，包含 base/view/result 收据。
- 沿用原文件锁、不可变提交文件、原子 Active 切换、pending 同输入恢复及幂等提交。异常或 KeyboardInterrupt 退出时释放缓存，下一次调用重新验证。
- LMB 历史证据为自包含记录，因此没有移植 v28/v29 的 Actor 批次缓存。Replay Prompt、评分、Knowledge 和落盘格式、模型配置、重试预算未改。

## 验证

- v27 全量离线测试 **98/98** 通过，其中新增 12 项 Memory 回归。
- 共享合约兼容回归 **13/13** 通过：v28 Memory publication 6 项，v29 Memory reuse 7 项。
- 覆盖：冷加载与 benchmark 隔离、返回对象不可污染缓存、整条修订及空提交、篡改归档/Active/目录成员、作用域退出检查、提交写入与 Active 切换处中断、pending/tmp 恢复、已推进目标冷校验、真实发布路径计数、发布前篡改阻止 state 前进、恢复不触发模型生成。
- 所有验证屏蔽网络与模型子进程；真实模型调用为 0，正式数据哈希保持一致。
- v28 源码未改。本任务没有编辑 v29；工作期间观察到另一任务修改 v29 README、modules.py 和 DocVQA evidence.py，保留其修改；兼容回归在更新后的代码上通过。
- 首次在 LMB 环境尝试 v29 测试时因缺少 Pillow 无法导入；随后使用现有 DocVQA 环境通过。初次日志保留，不安装或更改环境。

## 证据和复验

- `verification/validation.json`、`verification/unittest.log`：v27 完整结果。
- `shared_contract_regressions.json`、同名 `.log`：v28/v29 兼容回归。
- `traversal_comparison.json`：修改前后遍历次数及落盘字节比较。
- `summary.json`、`changes.patch`、`before/`：修改清单和比较基线。这里的哈希仅用于离线变更审计，没有新增源码或 Prompt 运行时冻结。

在项目根目录运行：

```sh
/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python -B scripts/verification/verify_v27_offline.py --output /tmp/v27_memory_recheck
/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python -B scripts/verification/verify_v27_memory_reuse.py
```

等待用户明确通知后才启动新训练与正式测试。没有新增或恢复定时任务。

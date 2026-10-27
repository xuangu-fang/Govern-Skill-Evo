# V23.4 请求级输出预算恢复

日期：2026-10-23。用户明确授权当前 R03 Preconditioner 输出上限翻倍，并确认后续规则适用于全部模块与 Actor。

## 生效策略

- 当前 R03 Preconditioner 已在 16,384 token 下连续 6 次截断；attempt 007 从 32,768 开始。
- 每个新模块调用/Actor 步骤从 16,384 开始。同一预算连续 6 次 `finish_reason=length` 后仅该调用预算翻倍，后续重复此规则。
- 非 length 的技术/格式失败保留 3 次上限，永久 HTTP 错误停止；语义结果不重采样。
- Actor 在同一环境步骤重试，不因截断重新运行 episode；下一步恢复 16,384。
- 原模型、Prompt、输入容量、任务清单、并发、50 步上限与 Gate 不变。
- 不启动 Test；其入口已兼容该策略。

## 冻结与审计

原始 Campaign config、initial_config、contract 和全部历史结果保留原样。
仅在 `S1/amendments/output_budget_v1/` 增加用户授权、修订源码完整快照、哈希和差异。
运行时检查修订快照，其他源码/Prompt 漂移仍拒绝。模块每次实际预算保存于 attempt 的
`output_budget.json` 和 `request.json`；Actor 每次实际请求、原始响应与用量均归档并校验。

第三轮 Parent 已在旧执行实现下结束；Candidate 使用新增恢复实现。通过既有显式
implementation review 记录准确旧/新源码哈希与差异。结果分析须注明此次执行条件变更，
不得将全程描述为固定 16K、每请求最多 3 次的原冻结实验。

## 验证

- 新增专项测试最终 **15 passed**：六次截断翻倍、连续扩容、下一调用归零、普通错误上限、
  原六次失败归档接续、成功记录复用、保存响应零请求恢复、源码漂移拒绝、真实旧 Parent 配对审计、
  Actor 同步重试与原始响应校验、未来 Test 命令接通。
- 联合运行专项测试（当时 14 项）、evolution/evaluation/benchmark 与 upstream protocol：**68 passed**。
- Actor 原有 skill contract：**10 passed，4 subtests passed**。
- 最后新增的未来 Test 入口测试随全部 15 项专项测试重跑通过。
- `git diff --check` 通过，正式 `benchmark.verify` 返回 `ready_offline`。
- 使用冻结 Actor 解释器 `/Users/didi/miniforge3/envs/alfworld/bin/python` 的新入口 dry-run 通过。
  初次误用总运行器 tau2 解释器的 dry-run 因无 ALFWorld 依赖失败，未执行任务；已用正确解释器复核。

## 真实启动

2026-10-23 01:44:34 +08:00 启动恢复进程 PID 14811。
已确认 R03 Preconditioner attempt 007 实际请求 `max_tokens=32768`，启动检查时尚在等待响应。
日志：`artifacts/methods/v23_4/v23_4_alfworld_formal_001/execution/optimization_budget_resume_20261023T014434+0800.log`。

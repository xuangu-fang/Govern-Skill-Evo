# V23.4 Replay 输入视图：设计、实现与离线验证

日期：2026-10-22。范围：用户授权的第 1—3 项。**已完成契约、实现和离线验证；没有真实 LLM、Actor 或新 Replay 调用，没有发布 Memory。**

## 实现内容

- [模型视图契约](../../../../docs/methods/v23_4/REPLAY_INPUT_VIEW.md)：版本 `v23_4_replay_pairs_memory_v3_v1`，保持七个顶层字段、一次学习调用及 entries/revises/knowledge/evidence 输出。
- 当前 runs 根据已核验 pairs 交错排列；完整 run 内容不变。Pair 中提供真实 task_id、双方 status/success/steps；无效动作计数，HTTP 重试/未执行请求不计数。
- 历史证据原样复用 Memory v3 的固定窗口、完整 trace、菜单池及边界说明；不改变 Preconditioner 的 v3 视图。
- 从不可变 Memory archive 提取真实历史 Pair，核对 SHA256、context、原始来源内容与可用配对审计。只输出双方均已提供的历史 Pair；单侧或显式未知来源进入 unpaired_runs，不补轨迹、不猜配对。
- 完整 bundle 与压缩模型视图分开保存；模型视图及来源清单可重建核验。旧归档按旧视图读取，新旧视图不能静默复用目录。

生产修改限于 [V23.4 replay.py](../../../../src/skill_evolution/v23_4/replay.py)，新增 [replay_view.py](../../../../src/skill_evolution/v23_4/replay_view.py) 为确定性装配辅助代码及 [格式说明](../../../../src/skill_evolution/v23_4/replay_view_prompt.md)。不是新增学习模块、审核 Agent 或调用阶段。原 Replay Prompt、旧 V23 模块、Memory 存储、v3 算法和旧实验文件没有改写。

pre-change replay.py 与其 SHA256 保存在 baseline_sources；它与两次旧 Replay 冻结的源码哈希一致。旧 R05/R06 请求可通过显式 legacy 视图逐字重建，旧档案无需迁移。

## R05 / R06 完整冻结输入离线验证

| 检查 | R05 | R06 |
|---|---:|---:|
| 当前 Pair | 10 | 7 |
| 当前实际动作，全部完整保留 | 301 | 330 |
| 可见历史 Pair | 35 | 29 |
| 历史完整动作/反馈 | 1,716 | 1,586 |
| 历史详细状态步骤 | 416 | 393 |
| 原用户消息字符 | 1,496,364 | 1,445,383 |
| 新用户消息字符 | 884,454 | 857,128 |
| 用户消息字符减少 | **40.89%** | **40.70%** |
| 新请求字符预算计量 | 989,515 | 959,309 |

新请求预算计量沿用运行器对完整 messages JSON 的字符统计，含 System 及转义，不能与用户正文字符数混为一谈。增加 Pair 元数据后，降幅略低于单独 v3 投影。没有真实调用，因此未测新 token 用量或语义效果。

两组分别核对 42/47 个旧实验及原 Memory 来源文件，前后哈希不变。现有 v3 投影逐项一致；移除本次追加的 pairs/unpaired_runs 后即等于原 compact_memory 输出。当前 parent/diff/plan/command_sets 和每个 run 对象保持完全相同。

旧 Replay 提案仍通过原引用校验，但不因此获得语义批准。本次没有修补或发布 R05/R06 的旧候选，没有把预览 Memory 用作新历史。

完整结果：[RESULTS.json](RESULTS.json)。冻结视图：[R05](../../../../artifacts/methods/v23_4/replay_input_view_001/cases/R05/model_input.json)、[R06](../../../../artifacts/methods/v23_4/replay_input_view_001/cases/R06/model_input.json)。本实验明确沿用原 evaluation bundle，**没有把新的评估 Parent 轨迹伪装成生成旧 Plan 的事实，也不声称完成生产 Editor 原始血缘加载验证**。

## 测试结果

新增 25 项测试，覆盖：

- 按 Pair 排列而非按数组/相同任务描述猜配对；身份、覆盖、交换关系不一致时拒绝。
- 当前完整事实不变；空动作计数、HTTP 重试不计数、技术中断和 pending 请求保留正确语义。
- 复用 v3 投影；单侧/未知来源、同名步骤跨 context、历史编辑/轨迹/菜单/配对篡改及哈希变化。
- 新归档重载、模型视图与清单篡改拒绝、Active 后续变化不破坏旧运行的不可变来源。
- 完整 Memory 修订提交、重载、幂等和后续 Preconditioner 投影；不把压缩视图写入存储。
- 旧无 input_view 归档兼容、跨视图重用拒绝、输入预算失败且零模型调用。

首轮本地链路与新测试：46 passed。最终相关回归：**409 passed，6 deselected**；两组有重叠，不相加。

完整回归首次为 409 passed、1 failed、5 deselected。唯一失败是旧 `test_old_archive_and_editor_still_reload`：V23.3 已冻结 Editor Prompt 与此前修订的共享 Editor Prompt 不同。替换成本次修改前的 V23.4 Replay 模块后，同一测试仍以 `Saved Editor prompt/input differs` 失败，确认与本次 Replay 投影无关。没有修改旧档案或放宽 Editor 检查；最终将这项既有历史归档检查与另外五项历史测试一并排除并明确记录。

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q \
  tests/skill_evolution/v23_4 \
  tests/skill_evolution/v23_3/test_memory_view.py \
  tests/skill_evolution/v23/test_editor.py \
  tests/skill_evolution/v23/test_preconditioner.py \
  tests/skill_evolution/v23/test_replay_memory.py \
  -k 'not real_handoff_and_legacy_readonly and not real_archives_handoff_readonly and not frozen_real_readonly_interfaces and not actual_replay_sources_and_readonly_reuse and not actual_memory_control_changes_only_memory and not old_archive_and_editor_still_reload'

PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.replay_input_view_001.check
```

离线脚本无模型调用入口，重复运行核对既有产物，不覆盖变化后的结果。freeze.json 记录本次源码、真实来源及新视图哈希；旧冻结清单不改写。

## 尚未验证

结构与事实保持已通过，不证明知识更准确。R05/R06 新视图的真实 Replay 是后续独立一步；应使用当前冻结完整事实与原 Memory，一次生成、保留原始响应，再核查此前错误及新遗漏。

默认生产预算仍为 400000 字符，两组新请求仍超过它。后续真实实验需显式冻结足够的预算，不能静默截断。历史详细窗口以外的状态仍未知；历史 Pair 索引不恢复缺失状态，也不自动证明独立因果。

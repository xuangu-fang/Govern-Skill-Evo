# 多 Knowledge P3：链路适配与离线报告

日期：2026-10-22。P3 已完成；默认仍为旧 Memory 契约。本轮没有真实模型调用，没有发布正式 Active Memory。技术验证不代表 Knowledge 语义质量改善。

## 完成内容

同一个 `memory_contract` 已贯通：

`新 Memory → Preconditioner 输入 → 模型视图 → Adjustment → Patch → 共享编译器 → Effective Plan`。

还贯通了 Replay 完整事实构建、模型视图、逐 Knowledge 输出校验、保存/重载、历史 Pair 来源，以及 Editor 接口内部再次编译 Effective Plan 的环节。Editor 新归档记录并核对上游契约，模型仍只收到 Parent 与 Effective Plan。

Memory v3 使用全部 Knowledge 的有序证据并集决定原有窗口；不拼接文本、不丢失逐条 Evidence、不改变固定 ±2、完整动作反馈和菜单去重。历史 archive 按自身契约校验，仍核对路径哈希、实际编辑、执行与 Pair 任务身份。

P3 使用独立的结构适配 Prompt 版本 `v23_4_replay_multi_knowledge_contract_v1`，没有覆盖旧 Prompt。P4 的学习 Prompt 版本 `v23_4_replay_multi_knowledge_v1` 尚未实现，后续需另行登记并保留 P3 模板的重载能力。

实现与 API 说明：[MULTI_KNOWLEDGE_P3.md](../../../../docs/methods/v23_4/MULTI_KNOWLEDGE_P3.md)。

## 测试结果

| 检查 | 结果 |
|---|---|
| 原有 V23.4 与 v3 视图回归 | 243 passed |
| 新链路与 Editor 相关回归 | 169 passed |
| V23、V23.3、V23.4 全目录 | 960 项：950 passed、1 failed、9 errors，79.48 秒 |
| 最终 P3 链路测试（补充新 Editor→Replay 交接及空 Memory 的 Editor 版本检查） | 43 passed，3.55 秒 |
| 保护文件与旧 Prompt | 11,527 个既有文件 hash 不变 |
| 真实模型调用 / 正式 Memory 发布 | 0 / 0 |

不同轮次测试有重叠，不能相加为总测试量。全目录回归之后仅增加测试断言和两个 Editor 版本反例；最终定向测试全部通过，生产代码未再变更。

全目录中的 10 个未通过节点与 P2 记录完全一致：9 个 formal_evaluation 在 fixture 阶段检查当前源码/Prompt 与旧正式评估冻结版本相同；1 个 Gate 历史归档读取因旧 Editor Prompt 与当前模板不同而失败。本轮未跳过、删除或放宽这些检查，也未改写冻结版本。P2 已通过改动前源码复核这些既有失败；本轮比较了相同节点清单。

机器可读结果：[TEST_RESULTS.json](TEST_RESULTS.json)、[完整回归 XML](../../../../artifacts/methods/v23_4/multi_knowledge_p3_001/pytest.xml)、[最终链路 XML](../../../../artifacts/methods/v23_4/multi_knowledge_p3_001/chain.xml)。原文件保护核验：[INTEGRITY.json](INTEGRITY.json)、[原始哈希清单](protected_before.json)。

## 重点验证

1. 从旧 commit 兼容读取新格式，生成多 Knowledge Replay 提案，提交并重载新 commit；随后恢复旧新两个 context 的历史 Pair。
2. 第二条 Knowledge 引用独立执行，确实进入 sources、模型视图和 Preconditioner 理由引用；不会只消费第一条。
3. 对长轨迹中第 1、14 步的分散引用，保留 18 步完整动作/反馈，详细窗口为 1–3、12–16；跨 Knowledge 重复引用不重复来源或菜单。
4. Preconditioner 真实调用链中对共享编译器做契约断言，验证新契约贯穿生成与归档重载。Keep、撤回、修改分别保留原行为；晚出现的错误 Patch 不产生部分 Effective Plan。
5. Editor 交接再次编译时使用同一契约，新 Candidate 的 actual_diff 可继续构建 Replay；Editor 模型输入不新增 Memory。
6. 输入、投影、消息、Adjustment 及共享编译器对非空新 Memory 的错误旧契约均拒绝；空 Memory 的归档复用、缺失/错误/未知版本也拒绝。
7. Replay 的旧形状输出、第二条 Knowledge 错误引用、截断、重复 JSON key、预算不足均失败，不降级为空提案、不自动重试、不发布 Memory。
8. 冻结 R05/R06 的旧 messages 仍精确重建；转换为新表示后，model_input 只有 memory.entries 的结构变化，当前 runs/pairs 与历史 sources/windows/menus/pairs 均相等。

## 兼容与后续边界

所有新格式 API 显式启用；默认旧值不变。原始历史档案不迁移，完整事实与模型视图继续分离。旧 Prompt、旧 v3/Pair 说明按原字节保留，新说明按契约选择。

本轮修改了 9 个现有生产 Python 文件，新增 3 个格式/结构模板和 1 个测试文件。相对本轮开始状态的差异见 [code_changes.diff](code_changes.diff)，改动前源码位于 `before/`，当前源码指纹见 [SOURCE_SHA256.json](SOURCE_SHA256.json)。这些副本用于审计，不是额外运行模块。

P4 尚需设计多 Knowledge 的语义学习方式；P5 尚需统一验收最终模板与链路；P6 尚需在冻结 R05/R06 上独立开展真实模型验证。重要历史认识是否遗漏、每条 Evidence 是否充分支持文本，以及多 Knowledge 是否改善学习，均未在本轮得到真实模型验证。

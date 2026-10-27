# R06 Replay / Memory 验证结果

日期：2026-10-22（Asia/Shanghai）。

**已完成本轮验证：Replay 调用、结构校验和 Memory 生命周期通过；语义核对发现需修正之处，原始 Memory 候选尚不直接采用。** 未运行新 Actor、未开始 R05、未修改 Replay Prompt，也未把结果写回历史 Active Memory。

## 输入与运行

- Editor：`semantic_generation_005` 首次合法输出的 Candidate、实际 Skill Diff，以及冻结的 Effective Plan。
- 执行：`r06_actor_comparison_001` 新跑的全部 7 对任务、14 条轨迹、330 步。Parent 5/7、Candidate 6/7；197 → 133 步。
- Memory：`semantic_generation_004/config/memory.json`，与 S1/R05 历史 Memory 完全一致，7 个 Active 条目。
- 使用现有 V23.4 Replay Prompt、既有 paired facts builder、response validator、Memory commit/load 和 compact Memory projection。
- **1 次逻辑调用、1 次 HTTP、0 次重启**；首次结构有效输出即选中，没有语义重采样或输出修补。耗时 156.294 秒。
- API 报告用量：462,460 input + 26,021 completion = 488,481 tokens；金额未提供。输入 1,597,785 字符，本实验预算 2,000,000；生产默认 400,000 未变。

重要边界：新 Parent 轨迹不是生成旧 Plan 的那批事实。实验适配器单独验证实际 Editor 输出，再使用新评估 facts 构造明确的 evaluation view。**本次未验证生产 Editor→Replay loader 的原始轨迹血缘交接，也未把新轨迹伪装成旧 Diagnosis 的输入。** 详见 [PROTOCOL.md](PROTOCOL.md) 与 [provenance.json](config/provenance.json)。

## Memory 结果

| 修订 | 主要内容 | 本轮核对 |
|---|---|---|
| M7 → 预览 M12 | 持有精确目标且动作可用时直接温变，减少插入/开关；保留搜索失败时未触发的边界 | 核心方向正确，但错误声称热番茄两组同一步取目标；冷盘子的局部省一步与整体多一步混淆 |
| M10 → 预览 M13 | 逐个候选搜索及防循环指引的混合响应；书任务修复、信用卡更快、苹果仍失败 | 主要事实成立；应更明确保留书任务仍循环、信用卡未触发防循环、历史修复的非因果边界 |

输出修订了已有相关条目，没有另外堆积两个并列重复条目。预览 Active 仍为 7 条：M1、M2、M6、M9、M11、M12、M13。M12/M13 是隔离副本的确定性分配 ID，**不是正式采纳状态**。

具体错误、局部动作机会及引用窗口的人工核对见 [SEMANTIC_REVIEW.md](SEMANTIC_REVIEW.md)。引用合法不代表语义支持充分；主结论不能标成“全部通过”。

## 程序与离线验证

1. 14 条原始轨迹审计、7 对任务/环境初始状态/Actor 配置匹配；使用 Editor 真正写入的 Diff，重建 Candidate 一致。
2. Replay 原始响应、请求、首次选中规则、输出校验和冻结源 SHA256 复核通过。
3. 原始提案在 `memory_preview/` 历史副本中提交、重新加载、重复提交幂等检查通过；旧归档字节未变。
4. 历史及新证据引用均可解析；新本轮引用加独立 context 前缀，旧引用保持原 context。条目修订和 Active 索引一致。
5. 当前压缩视图保留 1,916 步完整 action/feedback、504 步详细状态；186 个数字步引用均在详细窗口内。保留的 before/after 状态和动作菜单与完整源一致。既有 Preconditioner 消息投影可直接消费。
6. 源 Memory 的所有 JSON SHA256 和重新加载内容均未变化。
7. 定向 facts/grouping/Replay/Memory 测试：113 passed。完整 V23.4 测试：156 passed（含新增 5 项，两个集合有重叠，不相加）。

本轮遇到并修复一项真实证据兼容问题：Parent P4:35 确实执行了空字符串动作并收到 `Nothing happens.`。旧 facts 和 Memory validator 拒绝非空字符串检查之外的这条真实记录。现在仅允许 action 为任意字符串，仍核验类型、执行连续性、菜单合法性及反馈；没有改写该动作，也没有改变 Actor。

源修改仅涉及 `src/skill_evolution/v23/facts.py` 和 `memory.py` 的动作字符串校验。旧源码、旧 SHA256 与最小差异保存于 [baseline_sources](baseline_sources/compatibility.diff)。所有旧实验冻结记录未改写；新实验显式冻结新版本。测试覆盖空动作归档往返与非字符串拒绝。

## 产物与复现

- [API 审计](AUDIT.json)
- [Memory 往返审计](results/MEMORY_AUDIT.json)
- [原始 Replay](runs/R06_replay/attempt_001/parsed.json)
- [独立 Memory 候选](../../../../artifacts/methods/v23_4/r06_replay_memory_001/results/memory_candidate.json)
- [供后续 Preconditioner 使用的压缩视图](../../../../artifacts/methods/v23_4/r06_replay_memory_001/results/memory_view.json)
- [人工语义审查](SEMANTIC_REVIEW.md)

离线复核（不调用模型）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.r06_replay_memory_001.run audit
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.r06_replay_memory_001.check_memory
```

后续若继续，先针对 F1/F2 及条件引用做最小措辞/证据修正或独立的新验证；保留本轮原始输出作为失败证据。当前不需要新增审核 Agent 或扩大算法设计。

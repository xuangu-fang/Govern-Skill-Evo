# 多 Knowledge P4 候选学习 Prompt 与离线验收

日期：2026-10-22。候选已冻结并接入显式版本选择，已准备 R05/R06 待发送消息；未运行真实模型。语义效果仍待 P6 验证。

## 候选内容

用户原稿：`/Users/didi/Downloads/replay_multi_knowledge_learning_prompt_v1.md`。保留原始字节，候选只作两处已讨论的修改：

1. 将 `Choose one of` 改为按相关主题决定新增、修订或不变，允许同一响应同时新增和修订；只有所有主题均无需更新时才返回空 entries。
2. 补充历史细节不足的处理：区分无法复核与证据反驳，保留有支持的比较，说明未决之处。

[原稿](../../../experiments/methods/v23_4/multi_knowledge_p4_001/original_prompt.md)、[候选](../../../experiments/methods/v23_4/multi_knowledge_p4_001/candidate_prompt.md)、[两处差异](../../../experiments/methods/v23_4/multi_knowledge_p4_001/prompt_changes.diff)。生产登记的候选与冻结副本逐字一致。

学习重点是条件性认识的粒度、被修订 Memory 内实质认识的逐项校准、完整数组替换，以及各 Knowledge 独立成立且相互协调。没有增加 JSON 字段、Knowledge ID、额外调用或审核 Agent。

## 版本与装配

| Prompt 版本 | Memory 契约 | 默认行为 |
|---|---|---|
| `v23_4_replay_v1` | `entries_sources` | 不传参数的既有默认，保持不变 |
| `v23_4_replay_multi_knowledge_contract_v1` | `entries_sources_multi_knowledge_v1` | 显式选择新 Memory、但不指定 Prompt 时仍沿用 P3 |
| `v23_4_replay_multi_knowledge_v1` | `entries_sources_multi_knowledge_v1` | P4 候选，必须显式指定 |

`messages_for` 和 `run_replay` 新增可选 `prompt_version`。加载器按归档内明确的 Prompt 版本查登记表，而不是用当前默认猜测；可通过 `expected_prompt_version` 限定期望值。未知版本、契约不匹配、跨版本复用均拒绝，空 Memory 和空输出也不例外。

P4 主文无占位符，由程序按顺序拼接：候选主文 → Actor execution context → 既有 Memory v3 说明 → Pair 说明 → 多 Knowledge 格式说明。各段仅出现一次。旧模板仍采用原有占位符渲染，旧默认与 P3 文件不改写。

P4 明确使用包含任务身份与结果统计的 Pair 输入，因此只允许既有 `v23_4_replay_pairs_memory_v3_v1` 视图；不静默切到缺少这些元数据的旧完整视图。

## 标准生产归档的调用示例

```python
from src.skill_evolution.v23 import memory
from src.skill_evolution.v23_4 import replay

NEW = memory.MULTI_KNOWLEDGE_CONTRACT
P4 = replay.LEARNING_PROMPT_VERSION

messages = replay.messages_for(
    bundle, memory_contract=NEW, prompt_version=P4,
    history_sources=history_sources,
)
saved = replay.run_replay(
    bundle, new_isolated_directory, generate=generate,
    memory_contract=NEW, prompt_version=P4,
    history_sources=history_sources, max_input_chars=declared_budget,
)
replay.load_replay(
    new_isolated_directory,
    expected_memory_contract=NEW, expected_prompt_version=P4,
)
```

示例不构造真实生成器。模型输出仍按 P2 验证，每项 revises 替换完整数组；程序不自动复制旧 Knowledge，不因 Prompt 有完整性要求就假定语义完整。运行 Replay 不自动发布 Memory。

## 冻结 R05/R06 输入

输出位于 [multi_knowledge_p4_001/cases](../../../experiments/methods/v23_4/multi_knowledge_p4_001/cases/)，每例包含完整 bundle、model_input、实际 messages、system_prompt、历史 Pair 来源与调用配置。

| 项目 | R05 | R06 |
|---|---:|---:|
| 当前 Pair | 10 | 7 |
| 当前完整轨迹 | 20 | 14 |
| 原始 Active Memory | 7 | 7 |
| 兼容包装后的 Knowledge | 7 | 7 |
| 请求字符数（沿用预算计算方式） | 995,446 | 965,240 |

旧长 Knowledge 只包装成单项，未预先语义拆分；如何拆分、保留和修订交给候选 Replay。两例都低于既有 1,200,000 字符预算，实际 token 未测量。

验证结论：

- 相对原始冻结 bundle，仅 Memory Entry 表示由字符串变为单项数组；原文、Evidence、sources、实际编辑、Plan、当前完整执行等不变。
- 相对旧单 Knowledge 的模型视图，只有 memory.entries 表示改变；当前配对结果、历史窗口、菜单和 Pair 索引不变。
- 相对 P3 新格式消息，User 字符串完全一致，只有 System 学习 Prompt 改变。
- 模型配置、预算与重试上限直接继承上一轮冻结配置；没有读取密钥、创建生成器或调用服务。

原 R05/R06 使用专用实验 attempt 归档，不含标准生产 Editor 的 run.json。本轮按其既有方式核验 response→parsed→严格 Patch→Candidate/actual.diff→冻结 Plan/background，且保存来源哈希；未改写成伪造的生产归档，未放宽生产 validate_bundle。**生产运行器的完整链路由独立合成测试验证，真实 R05/R06 后续仍需使用原实验调用路径并显式选择新输出校验。**

## 离线验收与下一步

新增测试覆盖两处修订、装配唯一性、三版本重载、空 Memory 跨版本拒绝、错误配置/视图/模板/输出篡改，以及同时新增和修订的提案经 Memory→Preconditioner Patch→Effective Plan→Editor 的交接。

冻结构建器仅提供 `prepare` 和 `verify`，可重建两例待发送消息并核对文件哈希；没有运行模型的命令。结果与已知历史冻结异常见 [报告](../../../experiments/methods/v23_4/multi_knowledge_p4_001/REPORT.md)。

P4 候选接入及本轮要求的离线技术验收已完成。P6 应独立检查重要历史比较的保留、事实与解释、证据充分性、粒度和膨胀；不能将本轮结构测试当作这些语义要求已经满足。

# Replay 输入视图 v4：仅去重完全一致的代码体

本页记录输入视图 v4 的实施；后续学习 Prompt 已更新为 [Replay v3](REPLAY_CONDITIONAL_COMPARISON.md)，输入视图及解码说明保持不变。下文 Prompt v2 指视图 v4 实施时的版本。

2026-10-28。恢复与去重都发生在模型输入表示层；没有运行模型实验或修改经验学习要求。

## 范围

默认输入视图为 `v25_replay_pairs_knowledge_only_v4`，保留 v3 的共享初始消息、pairs 前置和 Parent/Candidate 邻接，只增加 response/executed_code 的精确重复表示。

满足以下条件才压缩某条 attempt：

- `executed` 为 true，response 为有效的单个 Python 代码围栏响应。
- 使用现有 `protocol.extract_code` 得到的原始代码体和适配后代码完全一致。
- 该代码体与已保存 executed_code 字符串逐字相同，包括空白、换行和结尾换行。

路径赋值适配、其他代码差异、仅空白不同、未执行记录、null 代码及无效响应均不压缩。没有使用相似度、strip 后相等或语义等价判断。

## 表示与还原

只替换符合条件的 executed_code 字段值：

```json
{"executed_code":{"from_response":"python_fence_body_exact_v1"}}
```

标记仅指向**同一 attempt** 的完整 response，不跨 run 或 attempt 共享。response 的代码围栏、前后空白和原始消息全部保留。

`benchmarks/spreadsheetbench/replay_code_view.py` 提供 `share_code` 与 `restore_code`，均返回副本。还原时检查标记精确匹配、确实执行过，以及 response 代码体没有经过路径等适配；不能把路径适配记录伪装成相同代码。生成原文和实际执行代码这两个事实仍可分别恢复。标记不是新证据 ID，Knowledge 继续引用原 attempt。

代码体按现有执行器的严格围栏解析取得：fullmatch 提取正文后加一个换行，不清洗、不改大小写、不更换换行符。没有改变执行器或路径适配逻辑。未压缩的 executed_code 继续为原字符串或 null。

## 与初始共享和时间线的组合

顺序为：验证原 bundle → 构造配对视图 → 共享初始消息 → 精确代码去重 → 原时间线投影。

时间线仍根据完整 response 重建 Actor 历史，不使用 executed_code 代替 Actor 响应。其投影与还原实现没有修改，能够保留代码标记。`restore_code(v4)` 精确还原 v3 视图；再展开初始共享消息、还原既有时间线，可恢复共享前的允许证据视图。原本未纳入视图的临时格式修正 API 历史不被凭空补回。

评分、反馈、Memory、证据引用、run/attempt 身份及配对信息不变。原始 input.json、Actor 记录和 Memory archive 仍保留完整内容，不压缩或改写。

## Prompt、配置和兼容

- Replay 学习 Prompt 正文、镜像及版本保持 `v25_replay_evidence_calibrated_v2`，Preconditioner 继续默认 `v25_preconditioner_evidence_decision_boundaries_v7`。
- 仅 v4 追加 [表示解码说明](prompts/replay_exact_code_view.md)。它明确标记如何展开，以及如何理解原时间线说明中的完整 executed_code，不新增学习限制。
- 旧 v1/v2/v3 输入视图保留；v3 仍使用原初始消息共享说明，旧 system 文本和请求可精确重建。显式更改版本标签不能重新解释旧请求。
- 新默认及未来 batch15 配置采用 v4；旧 campaign 和实验记录不升级。读取兼容不代表可以绕过冻结源码检查续跑旧实验。
- 调用参数、格式修正和技术重试机制不变；解码错误属于本地输入/归档问题，不作为新的模型纠错事实。

## 离线校验

83 项测试通过，覆盖精确正文、Unicode/空白/换行保留、路径适配与其他差异不压缩、无效标记拒绝、初始共享/时间线组合往返、旧三个视图与两个 Prompt 版本的归档兼容、原生格式反馈及技术超时后请求不变。

另只读校验六份真实历史归档及此前四份 v2/v3 离线归档夹具，用原 R05/R06 输入验证 v4 → v3 精确往返；复用已保存输出构造 v4 离线夹具并原生重载。没有生成新模型回答，也没有重新评分或发布 Memory。

完整记录及输入体积见 [离线校验](../../../experiments/methods/v25/replay_exact_code_v4_offline_20261028_001/reports/README.md)。这些验证证明表示无损和归档兼容，不证明 Replay 输出质量改善。

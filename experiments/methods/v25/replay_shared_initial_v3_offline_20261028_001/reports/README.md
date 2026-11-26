# Replay 输入视图 v3：共享初始消息离线验证

2026-10-28。没有模型调用、真实训练/评估、Replay 新输出生成或 Memory 发布。

## 实现范围

默认 `v25_replay_pairs_knowledge_only_v3` 保留配对概览前置和 Parent/Candidate 邻接，并共享跨 run 完全相同的 system 以及同一 pair 内完全相同的完整初始 user 消息序列。

旧输入视图 v1、v2 均保留原请求重建路径。Replay 学习 Prompt 文件及版本保持 v2，Preconditioner 保持 v7；新视图 system 仅追加共享表示的解码说明。response/code 不去重。见 [完整说明](../../../../../docs/methods/v25/REPLAY_SHARED_INITIAL.md)。

## 测试

```text
/tmp/govern-skill-v25-venv/bin/python -m pytest -q \
  tests/skill_evolution/v25/test_replay_shared_initial.py \
  tests/skill_evolution/v25/test_replay_input_views.py \
  tests/skill_evolution/v25/test_replay_versions.py \
  tests/skill_evolution/v25/test_timeline.py \
  tests/skill_evolution/v25/test_configuration.py \
  tests/skill_evolution/v25/test_pipeline.py

63 passed in 12.86s
```

使用固定响应及临时合成任务。覆盖完整视图和时间线视图往返、每条消息的精确内容、空白/大小写/元数据/消息数量差异不共享、多条 user 消息顺序、跨 pair 相同任务仍独立、坏指针和非规范共享拒绝、共享 ID 不能作为证据引用、旧视图与 Prompt 版本组合重读、格式修正的 base messages 不变，以及配置与流程。

## 真实历史输入校验

[validate_archives.py](../../../../../artifacts/methods/v25/analysis/replay_shared_initial_v3_offline_20261028_001/validate_archives.py) 禁止 requests 网络调用，使用原生 `load_replay` 重读以下六份历史归档，并精确重建其原请求：

- 原始训练 R01、R04、R05、R06：Replay Prompt v1 / 输入视图 v1。
- 前次 DeepSeek 单模块 R05、R06：Replay Prompt v2 / 输入视图 v1。

对六份输入分别在内存构造 v2、v3 视图，逐项验证：

- v3 展开共享初始消息后，与 v2 user JSON 完全一致；时间线投影前后都成立。
- pairs 前置且每对 Parent/Candidate 邻接。
- 每条 response、executed_code、反馈、评分、Memory 及原始 bundle 不变。
- 原先保存的 Replay 输出继续通过相同证据引用和输出契约校验。

另外为 R05/R06 各建立 v2、v3 两份原生归档夹具，共四份，位于 `saved_output_fixtures/`。这些夹具直接复用原来保存的输出，`call_config.offline_saved_output=true`，response 注明 `offline_reused_from`，没有生成新回答，没有伪造模型用量。四份均可原生重载。对旧 v2 Prompt / 新输入视图的组合兼容性由这些夹具覆盖；真实模型效果未测试。

全部结果见 [archive_validation.json](../../../../../artifacts/methods/v25/analysis/replay_shared_initial_v3_offline_20261028_001/archive_validation.json)。

## 字符数变化

以下为完成原有时间线投影后的 **Replay user 消息字符数**，包括共享查找表及指针；不代表 token 测量。R05/R06 两份 Prompt 版本归档的 user 输入一致，数值相同。

| 原始输入 | 配对视图 v2 | 共享视图 v3 | 减少 |
|---|---:|---:|---:|
| R01 | 1,238,323 | 1,015,565 | 18.0% |
| R04 | 568,557 | 344,872 | 39.3% |
| R05 | 528,806 | 316,845 | 40.1% |
| R06 | 688,910 | 379,623 | 44.9% |

R05/R06 各使用 2 份共享 system、15 份 pair 内共享 user 消息。额外解码说明位于 system 消息，完整 messages JSON 的字符数也单独记录在校验 JSON 中。未测量 token、延迟、成本或 Replay 质量变化。

## 完整性与兼容边界

修改前 [before_sha256.json](../../../../../artifacts/methods/v25/analysis/replay_shared_initial_v3_offline_20261028_001/before_sha256.json) 固定了 5,297 份既有文件。仅八个既有文件发生预期变化：Replay 视图及消息组装、时间线适配、原输入视图测试、未来 batch15 配置和三份说明文档。其他被检查文件哈希不变，包括 Replay/Preconditioner Prompt 正文与镜像、原训练和单模块归档、前次配对布局离线记录。新模块、新测试、新文档及本目录为新增文件。

旧归档只读兼容；旧 campaign 的冻结源码检查仍保持，不自动升级或绕过。还原的是先前授权的证据视图，不补回原视图已经排除的临时 Actor 格式修正历史。原始完整归档继续保留。

# Replay 精确代码去重 v4 离线校验

2026-10-28。模型调用 0 次；未运行训练、完整链路、重新评分或 Memory 发布。两份新归档夹具复用历史已保存输出，只用于验证原生归档写入和读取，不是新模型实验结果。

## 实现与边界

默认输入视图从 v3 升为 `v25_replay_pairs_knowledge_only_v4`。同一 attempt 中，只有已执行、有效 Python 围栏响应、未经路径适配，且原始代码体与 executed_code 逐字一致时，才将 executed_code 替换为可逆标记。完整 response 保留。路径适配或其他差异继续完整展示。

共享初始消息、pairs 前置及 Parent/Candidate 邻接保留。旧 v1/v2/v3 请求和归档仍按原版本解释，原始 input.json 不压缩。Replay 学习 Prompt 保持 v2，Preconditioner 默认 v7；仅 v4 增加输入表示的解码说明。

实现说明见 [REPLAY_EXACT_CODE.md](../../../../../docs/methods/v25/REPLAY_EXACT_CODE.md)。

## R05 / R06 输入体积

基于此前 Replay v2 DeepSeek 单模块实验的原输入构造 v3/v4 请求。分词使用离线 `cl100k_base`，统计 system + user 内容，包括新增标记和解码说明，不含聊天协议封装；它是代理估算，**不是经验证的 DeepSeek Token 数或实际计费值**。

| 轮次 | 精确重复去重 | 路径适配保留 | v3 → v4 user 字符 | v3 → v4 内容 Token 估算 | 净减少 |
| --- | ---: | ---: | ---: | ---: | ---: |
| R05 | 21 | 10 | 316,845 → 246,975 | 96,280 → 76,746 | 19,534（20.3%） |
| R06 | 22 | 9 | 379,623 → 288,772 | 116,415 → 90,751 | 25,664（22.0%） |

总计压缩 43 条精确重复记录，19 条路径适配记录保留两份完整内容。这是表示层的实际净缩减，区别于此前直接删除字段得到的理论节省。

## 验证结果

- 83 项测试通过（15.26 秒）：精确正文、空白/Unicode/换行、路径及其他差异保留、无效标记拒绝、时间线与初始共享组合往返、证据引用、旧版本兼容、原生格式修正和技术重试。
- 10 份旧归档通过原生读取、旧请求精确重建和 v4 → v3 往返：原 campaign R01/R04/R05/R06、此前 Replay v2 的 R05/R06，以及此前 v2/v3 的四份离线夹具。
- 两份新的 v4 离线夹具通过原生重载，输出明确标注为复用历史回答。
- 共享消息表、配对、Memory、评分、反馈、response 和证据引用不变。展开代码标记和既有时间线/初始共享后恢复完整允许证据视图。
- 对照修改前 5,891 个既有文件的 SHA-256，只有本次允许修改的 9 个既有实现、测试、配置及文档文件变化；历史实验、旧夹具、学习 Prompt、路径适配器和其他快照文件均未改变。

测试命令：

```sh
/tmp/govern-skill-v25-venv/bin/python -m pytest -q \
  tests/skill_evolution/v25/test_replay_exact_code.py \
  tests/skill_evolution/v25/test_replay_shared_initial.py \
  tests/skill_evolution/v25/test_replay_input_views.py \
  tests/skill_evolution/v25/test_replay_versions.py \
  tests/skill_evolution/v25/test_timeline.py \
  tests/skill_evolution/v25/test_configuration.py \
  tests/skill_evolution/v25/test_pipeline.py
```

记录：[校验脚本](../../../../../artifacts/methods/v25/analysis/replay_exact_code_v4_offline_20261028_001/validate_archives.py)、[逐归档结果](../../../../../artifacts/methods/v25/analysis/replay_exact_code_v4_offline_20261028_001/archive_validation.json)、[修改前快照](../../../../../artifacts/methods/v25/analysis/replay_exact_code_v4_offline_20261028_001/before_sha256.json)、[修改后快照](../../../../../artifacts/methods/v25/analysis/replay_exact_code_v4_offline_20261028_001/after_sha256.json)。脚本使用已有本地 tiktoken 包及缓存，并禁用 requests 网络请求。

以上结果证明输入表示无损及归档兼容；没有验证模型能否更好地利用压缩后的输入，也不据此声称 Replay 输出质量改善。

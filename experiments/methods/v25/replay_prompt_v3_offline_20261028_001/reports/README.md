# Replay Prompt v3 离线验证

2026-10-28。模型调用 0 次，没有真实 Actor 执行、完整链路、训练、评分或 Memory 发布。

当前默认：Replay 学习 Prompt `v25_replay_conditional_comparison_v3`，输入视图 `v25_replay_pairs_knowledge_only_v4`，Preconditioner `v25_preconditioner_evidence_decision_boundaries_v7`。

## 修改

按批准方案局部替换和合并 §1/§3/§4/§6：先做条件下的双边行为比较再关联 Skill 修改；让主张强度匹配程序/输入/日志/评分的支持范围；合并案例时分别核对行为与配对结果；检查全称、排他、新增等概括和条目间矛盾。

保留机制假设与经验泛化空间，不设置最低案例数、固定条数、强制句式或独立因果证明门槛。§2、§5、§7 及 Current pairing view 原文保持不变。v2 原文另存 `replay_legacy_v2.md`，v1 不变，三种学习 Prompt 与输入视图独立选择。

正文空白分词 2,707 → 2,839（+132，约 4.9%）。详见 [修改与兼容说明](../../../../../docs/methods/v25/REPLAY_CONDITIONAL_COMPARISON.md)。

## 自动验证

**94 项测试通过，18.66 秒。** 使用固定响应和临时合成任务验证版本切换、旧版本标签误用拒绝、历史/输入不变、原生格式反馈、技术重试，以及输入视图 v4 的共享/配对/精确代码还原。

```sh
/tmp/govern-skill-v25-venv/bin/python -m pytest -q \
  tests/skill_evolution/v25/test_replay_versions.py \
  tests/skill_evolution/v25/test_replay_input_views.py \
  tests/skill_evolution/v25/test_replay_shared_initial.py \
  tests/skill_evolution/v25/test_replay_exact_code.py \
  tests/skill_evolution/v25/test_task_requirement_versions.py \
  tests/skill_evolution/v25/test_configuration.py \
  tests/skill_evolution/v25/test_pipeline.py \
  tests/skill_evolution/v25/test_timeline.py
```

## 历史归档与兼容

[validate_archives.py](../../../../../artifacts/methods/v25/analysis/replay_prompt_v3_offline_20261028_001/validate_archives.py) 禁止 requests 网络调用和 live generator；只读加载 14 份旧归档：

- 原 campaign R01/R04/R05/R06：4 份 Prompt v1 真实归档。
- 先前 Prompt v2 / 输入 v1 的 R05/R06：2 份真实归档。
- 先前 Prompt v2 / 输入 v4 的 R05/R06：2 份真实归档。
- 先前输入 v2/v3 的 4 份离线夹具，输入 v4 的 2 份离线夹具。

全部通过原生 `load_replay` 与旧 messages 精确重建。在每份归档的相同输入视图、执行上下文和重试上下文下选择 v3，除学习模板外，其余 system 后缀及 user/反馈消息不变。

另构造 R05/R06 两份 Prompt v3 / 输入 v4 离线夹具，**复用原 Prompt v2 的保存输出**。新夹具通过原生重载，bundle、输出和调用配置与来源相同。它们不是 v3 模型回答，也不意味着旧回答中的语义错误已被修复。

结果见 [archive_validation.json](../../../../../artifacts/methods/v25/analysis/replay_prompt_v3_offline_20261028_001/archive_validation.json)。

## 完整性与限制

修改前快照覆盖 5,986 个既有源码、Prompt、文档、配置、测试及历史实验文件。仅 13 个获准的既有文件变化；其余快照文件、原 campaign、旧实验报告/契约/请求/回答、输入共享及代码适配实现均不变。

运行和文档镜像逐字节一致；新 legacy v2 的 SHA-256 与修改前 replay.md 一致；未来 batch15 配置通过验证。旧归档可读取不等于绕过其冻结源码检查续跑。

记录：[修改前快照](../../../../../artifacts/methods/v25/analysis/replay_prompt_v3_offline_20261028_001/before_sha256.json)、[修改后快照](../../../../../artifacts/methods/v25/analysis/replay_prompt_v3_offline_20261028_001/after_sha256.json)、[最终检查](../../../../../artifacts/methods/v25/analysis/replay_prompt_v3_offline_20261028_001/final_checks.json)。

以上只证明配置、表示、接口和归档兼容。R05 符号差异、R06 item 优先级能否进入 Knowledge，及跨任务概括能否稳定准确，仍需另行授权模型实验验证。

# Replay 配对输入视图 v2：离线校验记录

2026-10-28。仅检查输入布局恢复、版本选择与历史归档兼容，没有模型调用、训练或真实任务实验。

## 变更

默认输入视图 `v25_replay_pairs_knowledge_only_v2` 将 pairs 放在 runs 前面，并根据已验证的配对关系排列每对 Parent/Candidate。旧 `v25_replay_pairs_knowledge_only_v1` 保留原顺序。

Replay Prompt 保持 `v25_replay_evidence_calibrated_v2`，Preconditioner 保持 `v25_preconditioner_evidence_decision_boundaries_v7`。没有新增任何去重。原始 bundle 和历史记录不改写。

实现及兼容说明：[REPLAY_PAIRED_INPUT.md](../../../../../docs/methods/v25/REPLAY_PAIRED_INPUT.md)。

## 测试

```text
/tmp/govern-skill-v25-venv/bin/python -m pytest -q \
  tests/skill_evolution/v25/test_replay_input_views.py \
  tests/skill_evolution/v25/test_replay_versions.py \
  tests/skill_evolution/v25/test_timeline.py \
  tests/skill_evolution/v25/test_configuration.py \
  tests/skill_evolution/v25/test_pipeline.py

46 passed in 13.07s
```

测试使用固定模型响应和临时合成工作簿；流程测试验证连接关系，不调用真实模型，不执行模型生成代码。新增测试涵盖：

- 新旧视图在时间线投影前后，只存在字段和 runs 顺序差异；Memory、每个 run 及其全部内容保持不变，输入不被原地修改。
- 乱序 runs、变更后的合法 pair 顺序仍按显式配对关系邻接；无效审计、错误 counterpart、缺失覆盖均拒绝。
- 两个 Prompt 版本均可搭配旧输入视图生成固定响应归档、只读重载；仅篡改 input_view 标签无法重解释已保存请求。
- 新视图原生格式反馈保留相同的两条 base messages，追加上一份无效回答及原验证错误，重建和重读一致。
- 默认 Replay Prompt v2、Preconditioner v7 保持不变。

## 真实归档只读复核

[validate_archives.py](../../../../../artifacts/methods/v25/analysis/replay_paired_view_v2_offline_20261028_001/validate_archives.py) 在禁止 requests 网络调用的上下文中执行，结果见 [archive_validation.json](../../../../../artifacts/methods/v25/analysis/replay_paired_view_v2_offline_20261028_001/archive_validation.json)。

六份归档全部通过：

| 归档 | Prompt | 保存的 input_view | 结果 |
|---|---|---|---|
| 原训练 R01 / R04 / R05 / R06 | Replay v1 | 旧视图 v1 | 原生 reload 与原请求精确重建 |
| 前次单模块 R05 / R06 | Replay v2 | 旧视图 v1 | 原生 reload 与原请求精确重建 |

对这六份原始输入只在内存中构造新视图，确认 pairs 前置、每对邻接、所有 run 逐项完全一致，system 和其余字段内容不变，user 字符数不变，原输出仍通过相同引用契约校验。没有重新生成 Replay 输出，没有发布 Memory。

未来 batch15 配置通过原生校验，与当前 method_config 一致。

## 文件完整性

修改前 [before_sha256.json](../../../../../artifacts/methods/v25/analysis/replay_paired_view_v2_offline_20261028_001/before_sha256.json) 保存 5,290 个既有文件的哈希，覆盖 v25 源码、文档、测试、配置、原训练 campaign 及前次 Replay v2 单模块目录。

仅六个已有文件发生预期变化：Replay 调用边界、输入视图、未来 batch15 配置，以及三份说明文档。其余被检查文件哈希不变，包括运行 Prompt、文档 Prompt 镜像、Preconditioner 和全部所选历史记录。新增测试、布局说明与当前离线记录单独保存。

归档重读兼容不表示旧 campaign 可以绕过冻结源码检查续跑。离线通过不证明新布局能消除模型的程序比较遗漏；本次没有做效果实验。

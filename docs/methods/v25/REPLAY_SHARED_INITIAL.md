# Replay 输入视图 v3：共享完全相同的初始消息

2026-10-28。只实现两项无损去重：跨 run 共享完全相同的 Actor system，以及同一 verified pair 内共享完全相同的完整初始 user 消息序列。保留 pairs 前置、Parent/Candidate 邻接、独立执行时间线；response 与 executed_code 不去重。

后续更新：当前默认为 [输入视图 v4](REPLAY_EXACT_CODE.md)，在本文 v3 基础上增加完全一致代码体的无损去重。本文记录 v3 的实现及验证；v3 原布局和解码说明仍保留，路径适配记录在 v4 中也不去重。

## 版本与修改范围

| 版本 | 布局 |
|---|---|
| `v25_replay_pairs_knowledge_only_v1` | 原字段顺序、原 runs 顺序，不共享初始消息 |
| `v25_replay_pairs_knowledge_only_v2` | pairs 前置、每对 Parent/Candidate 邻接，不共享初始消息 |
| `v25_replay_pairs_knowledge_only_v3`（当前默认） | v2 配对布局，加可还原的初始消息共享表 |

本页记录的输入共享实施时，学习 Prompt 正文及版本保持 `v25_replay_evidence_calibrated_v2`，Preconditioner 保持 `v25_preconditioner_evidence_decision_boundaries_v7`。后续学习 Prompt 已更新为 [Replay v3](REPLAY_CONDITIONAL_COMPARISON.md)，共享实现不变。输入共享没有修改 Memory 内容、证据引用规则、输出结构、执行/评分事实、重试预算或调用参数。

新视图需要额外的表示说明：在原 system 的执行上下文及 Knowledge Only 说明之后追加 `replay_shared_initial.INSTRUCTION`，说明如何展开共享指针、其原始 Actor 角色以及引用边界。这是视图解码说明，不是新的经验学习要求；两个旧视图不追加它，旧请求 system 保持原样。Replay Prompt 文件及文档镜像按字节不变。

## 共享规则

1. 对完整消息对象做精确序列化比较，不裁剪空白、不折叠大小写、不改换行或消息元数据。不同序列化的消息可以继续 inline，不冒险归为同一条。
2. system 仅当同一完整消息出现在至少两个不同 run 中才共享。不同 Skill 的 system 独立保留；不能仅因角色相同或大部分内容相同而合并。
3. user 消息先按原顺序取出整组。仅当同一 verified pair 的两侧完整序列完全相同时共享，逐条保留序列位置。任一 user 消息不同或数量不同，该 pair 的 user 消息全部继续 inline，不做局部共享。
4. user 共享限定在 pair 内；即使不同 pair 的任务文本相同，也不跨 pair 合并。非 system/user 消息继续 inline。
5. `initial.ref`、run 身份和所有 attempts/outcome 保持不变。共享指针替换消息对象，但不移动消息在原 initial.messages 中的位置。

模型视图字段顺序为 `parent/diff/plan/shared_initial/pairs/runs/memory`。原六个证据字段的含义不变；新增 `shared_initial` 是表示层查找表，不是新事实。

```json
{
  "shared_initial": {
    "format": "replay_shared_initial_v1",
    "messages": {
      "system_1": {"role": "system", "content": "完整原始 Actor system"},
      "pair_1_user_1": {"role": "user", "content": "完整原始任务输入"}
    }
  }
}
```

run 的 `initial.messages` 对应位置使用 `{"shared_message":"system_1"}` 等单字段指针；未共享消息保持完整原文。上例仅说明结构；真实表中存放实际原文。`system_1` 等只用于解码，不是证据 ID，不能写进 Knowledge evidence；仍引用原 `P1:0`、`Q1:0` 等合法来源。

## 无损还原及时间线

`replay_shared_initial.share_initial` 和 `restore_initial` 均返回副本，不修改输入。展开指针后恢复共享前 v2 的全部初始消息文本、元数据、顺序及其他字段。还原时检查表格式、指针、消息角色，并通过重新编码检查规范形式，拒绝悬空指针、未使用条目、跨 pair user 共享等错误。

原时间线投影需要比较实际 Actor request：遇到共享视图时先展开初始消息，执行原有 request_messages 重建与校验，再恢复共享表示。因此仍然只删除原本可重建的重复 request_messages。response、executed_code、运行反馈和评分没有删除、替换或合并。

还原完整的既有证据视图时，可先 `timeline.restore` 再 `restore_initial`。所有对象值和消息字符串一致；既有 timeline.restore 会将 request_messages 键追加回对象，不承诺原 JSON 对象键的排版顺序。共享初始消息自身的编码/还原保持原消息内容和字段序列化顺序。

这里还原的是原先已经选择的证据视图；不会声称恢复 execution_only 原本就排除的临时格式修正等 API 历史。那些记录继续保存在原始审计归档。

## 归档与配置

- `load_replay` 使用保存的 input_view 重建请求；v1/v2 的字段顺序、run 顺序、system 文本均保留，不能只修改版本标签来重新解释旧请求。
- 新默认配置及未来 batch15 配置采用 v3；现有 campaign、此前单模块实验及离线记录不升级。
- 原始 input.json bundle 和 Memory archive 不压缩；只改变模型视图 model_input.json / messages.json 及对应的表示说明。
- 原生格式反馈仍在相同两条 base messages 后追加，技术重试沿用相同请求；解码错误属于本地输入/归档错误，不是模型输出错误。
- 能读取历史归档不等于可以绕过冻结源码检查续跑旧 campaign。

## 离线校验

63 项相关测试通过，覆盖精确往返、时间线重建、差异不共享、多个 user 消息、pair 内作用域、坏指针拒绝、两个旧输入视图及两个 Prompt 版本组合的重读、原生格式反馈和配置/流程。

另只读重建原始训练 R01/R04/R05/R06 及前次 Replay v2 Prompt 的 R05/R06 六份历史归档。使用保存的输出创建 v2/v3 离线归档夹具，验证真实输入经新视图保存后可原生重读；这不是新模型输出，也没有重新评分或发布 Memory。

详细结果与字符数统计见 [离线校验记录](../../../experiments/methods/v25/replay_shared_initial_v3_offline_20261028_001/reports/README.md)。字符数减少不等于已测得 token、延迟或质量收益；本次没有模型实验。

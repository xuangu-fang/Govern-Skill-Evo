# R01 成功配对 Replay → Memory 审阅

使用原 v24.4 R01 已发布的轮次、10 个任务的 20 条归档轨迹与实际补丁；按 receipt 校验 SHA-256、任务和运行身份，再从原始执行重建配对审计。仅补充成功配对 Replay 调用了真实模型，首个回答的步骤证据格式未通过校验，第二个回答通过。保留版 Diagnosis、Preconditioner、Editor 和原翻转 Replay 的系统提示词与 8/10 快检的哈希一致。R02 未执行。

[增强前](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r01_success_memory_20261107_025441/memory_before.json) · [增强后](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r01_success_memory_20261107_025441/memory_after.json) · [实际模型输出](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r01_success_memory_20261107_025441/replay_success/result.json) · [完整轨迹视图](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r01_success_memory_20261107_025441/replay_success/input.json) · [来源和配对选择](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r01_success_memory_20261107_025441/provenance.json)

**M1（手机）** 沿用历史发布的 loss 事件。去掉本次新增的 observations 列表后，增强 Memory 与增强前逐字段相等。原有 Gate 的 u1 为 G=0、L=1、Reject。复用存档响应和轨迹离线走一遍修订版 R01 发布入口，Gate 产物和选中的 Skill 与原始发布一致，Memory 与本次增强文件一致。

**M2（train:0004，雕像）**。P5:2 与 Q5:2 的反馈都显示第一个抽屉为空。第 3 步 Parent 转向 shelf 1，Candidate 转向 drawer 2。Parent 于第 3–11 步查看货架，之后也回访了抽屉，于第 15 步到 dresser 1；Candidate 先继续开抽屉（第 7 步开 drawer 5 早于第 9 步开 drawer 4），第 11 步起查货架，后续回查两类位置，第 45 步才到同一 dresser。两边都拿到 statue 1、使用 desklamp 1 成功。记录的 17/47 步准确。“out of order”只描述编号顺序，任务没有指定编号顺序。不能从该对执行把额外 30 步归给第 3 步或补丁：首处分叉之后还有多处选择不同。Memory 原文描述了路径与终局，未作这种归因。

**M3（train:0006，报纸）**。前 8 步执行的动作和环境观察逐步相同，边桌上无报纸。第 9 步两边的菜单均提供去 armchair 1 和 shelf 1。Parent 去扶手椅，第 10 步拿到 newspaper 4，第 12 步完成；Candidate 去之前查过的 shelf 1，之后多次查货架，也查了抽屉，直到第 31 步到扶手椅，第 32 步拿报纸，第 34 步完成。双方最终动作序列一致。22 步的总差出现在拿到报纸以前，不能据此估计改变第 9 步会独立节省多少步，更不能推出应普遍优先检查扶手椅。记录本身未给 Update 分功，也没有这样的推广。

**筛选范围。** 只考虑双方成功且步数不同的任务，按动作数差绝对值降序取最多两对，同值按冻结批次顺序。M2、M3 分别相差 30、22 步；另一道 4→16 步的成功题排在其后。模型可略过无法给出可核对决策差异的配对。只凭这两条最极端的记录不能估计典型效应。两条模型原文都以描述为主，没有显式写出上述因果边界，后续引用时应将其作为轨迹观察使用。

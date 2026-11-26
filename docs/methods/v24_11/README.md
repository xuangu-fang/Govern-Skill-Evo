# ALFWorld v24.11

基于 v24.10 的训练配置、Actor、Diagnosis、Preconditioner 和 Editor，采用 v26.1 的逐补丁成败票规则。ALFWorld 使用环境记录的二值任务成功标记 `won` 对应 OfficeQA 的二值 EM。

每轮对同一批任务核验 Parent 和联合 Candidate 的执行结果。只有成功标记翻转的题进入 Replay，整批无翻转时跳过该调用。Replay 比较同一题两侧的动作及其后果，将翻转关联到本轮一个非空补丁，或记录为 `null`。事件文字可以按需引用轨迹，引用的运行或步骤编号必须属于该题提供的轨迹对。Memory 保存所有翻转事件，Gate 只统计有归属的事件。

三个模块均可按任意顺序返回条目。Preconditioner 按 `target` 匹配原提案，Editor 按 `update_id` 匹配补丁，Replay 按 `task_id` 匹配事件。每个输入 ID 须恰好覆盖一次。程序按计划顺序组合补丁，按输入任务对的顺序将事件写入 Memory。

| 本轮归属于非空补丁的翻转 | 决策 |
|---|---|
| 至少一次失败转成功，零次成功转失败 | Retain |
| 零次失败转成功，至少一次成功转失败 | Reject |
| 两种翻转都有，或都没有 | Defer |

空补丁的决策为 `null`。下一轮 Skill 只应用 Retain 的补丁。

在仓库根目录启动独立训练：

```sh
python -m src.skill_evolution.v24_11 train --campaign artifacts/methods/v24_11/run01
```

[Replay 提示词](../../../src/skill_evolution/v24_11/prompts/replay.md) · [训练流程](../../../src/skill_evolution/v24_11/campaign.py) · [134 道留出题评测入口](../../../scripts/runs/v24_11/run_v24_11_test.py)

[训练与评测归档](../../../experiments/methods/v24_11/README.md)列出正式运行的六轮发布记录、九次留出集评测及当时使用的提示词。

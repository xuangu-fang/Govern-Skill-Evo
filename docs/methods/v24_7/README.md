# ALFWorld v24.7

[正式训练与评测](../../../experiments/methods/v24_7/README.md) · [测试入口](../../../scripts/runs/v24_7/run_v24_7_test.py) · [方法设计](DESIGN.md)


v24.7 实现了[可执行搜索规则设计](DESIGN.md)。方法标识为 `alfworld_v24_7_executable_search_v1`。正式配置取 v24.6 同一原始 Skill、空 Memory、57 道优化题和相同的 Actor 预算；模型通过训练轨迹发现规则。换段实验的 Skill 和 134 道 Test 轨迹仅供研究对照。

## 模块与发布

- [Diagnosis](../../../src/skill_evolution/v24_7/prompts/diagnosis.md) 从成功片段的一次探查落空追踪到下一次选择，再回到受阻轨迹的菜单上检验。决定适用范围的成功步骤通过 `basis` 交给审核。
- [Preconditioner](../../../src/skill_evolution/v24_7/prompts/preconditioner.md) 对反复适用的提案，在首次触发和有据可查的后续决策点分别重建 Actor 可见的上下文。按具体动作判断是否与 Parent 重复，必要时在原目的内改写。
- [Editor](../../../src/skill_evolution/v24_7/prompts/editor.md) 可以把有依据的连续决策写成短段落。同一补丁同时拥有引用和正文，保留 Plan 指定的继续、切换与退出条件。
- [Replay](../../../src/skill_evolution/v24_7/prompts/replay.md) 区分补丁引发的局部选择与最终成败或步差。补丁退出后的进展与延误同样需要证据；归因链不完整时记录事件并允许空关联。

独立的[训练入口](../../../src/skill_evolution/v24_7/__main__.py)提供 `prepare`、`run-round`、`train` 和 `status`。准备阶段冻结本版本配置、实际加载的四份 prompt 和直接复用的 [v24.6 Gate](../../../src/skill_evolution/v24_6/gate.py)。续跑读取同一 campaign 的提交历史和已有回执。独立的[最终测试入口](../../../scripts/runs/v24_7/run_v24_7_test.py)按 v24.7 合同校验六轮发布链后读取选中的 Skill。

## 离线验证

从仓库根目录运行：

```sh
/Users/didi/miniforge3/bin/python scripts/runs/v24_7/verify_v24_7_offline.py \
  --archive artifacts/methods/v24_6/v24_6_alfworld_20261108_000609 \
  --report experiments/methods/v24_7/v24_7_offline_verification/results/offline.json
```

[报告](../../../experiments/methods/v24_7/v24_7_offline_verification/results/offline.json)保存配置与 prompt 的摘要、Gate 来源及 SHA-256、测试计数和逐轮回放结果。验证器在运行测试时禁用网络连接、子进程和真实 Actor。[v24.7 夹具](../../../tests/skill_evolution/v24_7/test_search_handoff.py)使用预设响应，核对模块实际收到的 prompt、成功步骤的交接、局部规则改写、跨位置补丁、空归因、中断恢复和下一轮发布。正式入口另行核对版本隔离与最终测试读取的发布链。

对 v24.6 归档的检查使用原始轨迹和已存 Replay 输出，重新构造配对、计票并应用补丁。六轮中五轮产生候选，共有 47 对轨迹、11 个符合门槛的事件；R05 两条提案全部撤回，沿用 Parent。逐轮选择和最后的 Skill 与归档一致。

### 用真实训练片段审阅语义边界

| 情形 | 历史记录 | v24.7 要求解释的问题 |
|---|---|---|
| 到中后段才暴露出对全程历史的依赖 | R06 的 `val:0013` 在第 9、36、44、50 步都去冰箱。在事后轨迹中可以列出所有未查地点。 | 单独给出某一步的观察、菜单和两步历史，哪些比较仍能成立？审核时用这个范围判断局部改写是否有依据。[R06 执行记录](../../../artifacts/methods/v24_6/v24_6_alfworld_20261108_000609/rounds/R06/parent_runs/val_0013) |
| 同一目标下仍有不同选择 | R02 的 `train:0014` 第 6 步回到先前检查的架子，第 17、18 步才前往其他位置。 | 比较 Parent 和提案在同一菜单上各自提高什么动作的优先级，再判断保留或撤回。[R02 诊断记录](../../../artifacts/methods/v24_6/v24_6_alfworld_20261108_000609/rounds/R02/diagnosis/result.json) |
| 一次选择符合规则，后续循环与规则的联系存疑 | R03 的 `train:0025` 新版先查餐桌，第 9 步又回到餐桌 1，第 49 步才拿到盘子。 | 区分首次探查和退出后的折返，说明两侧执行与最终结果的联系；关联或空关联都需要证据。[R03 原始归因](../../../artifacts/methods/v24_6/v24_6_alfworld_20261108_000609/rounds/R03/replay/result.json) |

这些片段用于离线走查。真实模型能否自主提案、规则能否经 Gate 保留，以及成功数和步数怎样变化，需由新版本正式训练及最终测试测量。

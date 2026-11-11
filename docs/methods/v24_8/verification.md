# v24.8 实现与真实轨迹离线验收

验收通过。实现位于[训练入口](../../../src/skill_evolution/v24_8/__main__.py)和[测试入口](../../../scripts/runs/v24_8/run_v24_8_test.py)。与 v24.7 有行为差异的两份 prompt 是 [Diagnosis](../../../src/skill_evolution/v24_8/prompts/diagnosis.md) 和 [Preconditioner](../../../src/skill_evolution/v24_8/prompts/preconditioner.md)。方法标识为 `alfworld_v24_8_search_continuation_v1`。

## 样本与执行方式

从 v24.7 R04、R05 的优化批次归档读取 8 条完整 Parent 轨迹，共 244 个已执行动作。搜索组为 `train:0034`、`train:0031`、`val:0007`、`val:0002`、`val:0004`，Pick Two 组为 `train:0036`、`train:0037`、`train:0038`。两组使用相同的历史 Parent，审核可读取 R03 结束时的 Memory。模型只收到正式模块可见的字段。核查用的 10 个局部窗口单独导出，每个都有当前观察、最多两组前序观察和动作、当时的完整菜单、实际动作和一个真实可选动作。这些核查窗口未传给模型。[验收程序](../../../scripts/runs/v24_8/verify_v24_8_offline.py)

模型对归档产生真实提案与审核结果，复核使用保存的响应。此次验收的 Actor 环境执行次数为零。可在仓库根目录运行以下命令离线重建输入、校验响应并复算交给 Editor 的有效计划。

```sh
/Users/didi/miniforge3/bin/python scripts/runs/v24_8/verify_v24_8_offline.py \
  --output artifacts/methods/v24_8/v24_8_search_continuation_05
```

## 逐项验收

| 真实决策 | 最终输出及核查结果 |
|---|---|
| `train:0034` 第 9 步，刚打开空抽屉 4，实际返回抽屉 1；第 29 步，查完架子 3，又回到抽屉 1 | 有效计划给出两条 `REPLACE`。对于目标点名的类别，若继续搜该类，就用当前编号与菜单选择最近的更高编号，因此在抽屉 1 和 5 中可以选 5。在已选的其他类别中也可以依当前架子 3 选架子 4。目标出现时优先取物。|
| `val:0007` 第 13 步，刚开完抽屉 6，菜单同时有抽屉 7 和台面 1；第 31 步，柜子 4 里没有所需黄油刀 | 同类编号规则优先比较同类选项，第一条明确把是否切换类别留给现有搜索策略。若已在查柜子，第二条在第 31 步可指向柜子 5。无需断言此前所有抽屉都已经过检查。当前规则仍可能跟随不够好的类别优先级；它不能据此预言哪一步必能找到目标。|
| `train:0036` 第 38 步，目标扶手椅上正放着钥匙扣 2，菜单允许把它拿起 | 审核将 `u1` 改写为使用当下可见的目的地和物品关系。把钥匙扣留在椅子上，去取得不同的第二件。`u2` 要求依赖更早的访问或来源记录，已撤回。历史 v24.7 候选虽然少了两次从扶手椅重复拿取，仍在 50 步失败，因此这条纠正只说明当前动作可以改进。|
| `train:0038` 第 10 与 12 步，柜子里出现另一件盐罐，回到边桌后可放置 | 改写针对已在目的地的物体，允许取出柜中另一件，并允许放到同一边桌。原轨迹确实执行了这两步并成功。|

[搜索组实际提案](../../../artifacts/methods/v24_8/v24_8_search_continuation_05/search/diagnosis/result.json) · [搜索审核](../../../artifacts/methods/v24_8/v24_8_search_continuation_05/search/preconditioner/result.json) · [搜索时的菜单](../../../artifacts/methods/v24_8/v24_8_search_continuation_05/search/review_windows.json) · [Pick Two 审核](../../../artifacts/methods/v24_8/v24_8_search_continuation_05/pick_two/preconditioner/result.json) · [Pick Two 菜单](../../../artifacts/methods/v24_8/v24_8_search_continuation_05/pick_two/review_windows.json)

## 修改经过与适用范围

开发期间在固定的 8 条轨迹上迭代。前三次搜索审核撤回了全部搜索提案；第四次已有编号规则，但仍让 Actor 判断全程哪些地点“从未访问”。最终版本把“跨类选择”和“同类中两个命令如何比较”作为不同的审核问题，并要求有效文本删去不可见的前提。最后一次沿用第四次相同的 Diagnosis 响应，对同一提案执行修订后的审核，两个搜索更新均改写后通过，Pick Two 一条改写、一条撤回。此结果表明最终模块具备在这些训练样例上生成和交接局部可执行规则的能力。

共享及新版结构回归共 49 项通过，涵盖四阶段载入、补丁、Gate、发布、续跑及最终 Skill 的读取。正式六轮从原始 Skill 与空 Memory 独立开始，离线样例产生的提案及计划不作为初始化内容。能否在正式分批时再次学得并发布规则，以及能否达到 117/134，由正式训练与测试衡量。

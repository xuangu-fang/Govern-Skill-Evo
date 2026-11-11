# 通用版 v24.9 真实训练轨迹离线验证

**同类续行在三个固定窗口均执行成功，换类后仍会折返。两道保留的 Pick Two 成功题均完成。五道学习题的 Gate 对唯一更新 `u1` 判为 Defer。**

## 数据与方法

使用 v24.7 的 R03 发布 Skill 和当时的 Memory，还原 R04/R05 的学习上下文。五条完整 Parent 轨迹包含三个 50 步失败和两个成功。Diagnosis 仅看当前批次；Preconditioner 看其引用的轨迹与已有 Memory；Editor 只看 Parent 与有效计划。另留两道 Pick Two 成功题做整题检查，另取两道未参与学习的题做搜索窗口检查。各来源均属于原优化池。[来源清单](../../../../../artifacts/methods/v24_9/v24_9_general_archive_01/sources.json) · [固定窗口定义](../../../../../scripts/analysis/v24_9/v24_9_general_windows.py)

Parent 动作和成绩直接取归档。固定窗口逐条重建并核对原 Actor 请求，然后只换入候选 Skill，对每个窗口调用同一 Actor 一次。整题对照在原环境从头执行候选，每题一次、上限 50 步。窗口可以来自同一题，不可拼成一条执行轨迹，亦不计 Gate 票。七道整题没有使用独立 Test。

## 学出了什么

Diagnosis 提出一条 update。已经查过当前位置且没有目标时，优先选同类下一个未查实例。Preconditioner 作 REPLACE，补全开柜后再判空、已知第二件物品位置时可直接回去、持物后转入交付等边界，并把同类续行放在目的地类别优先之后。Editor 在系统允许编辑多个段落的情况下，只改了原则 2。六条受保护的原文逐条相同，包括 Pick Two 任务行、立即拿取、直接交付和计数条款。[原始提案](../../../../../artifacts/methods/v24_9/v24_9_general_archive_01/diagnosis/result.json) · [审核结果](../../../../../artifacts/methods/v24_9/v24_9_general_archive_01/preconditioner/result.json) · [实际补丁](../../../../../artifacts/methods/v24_9/v24_9_general_archive_01/editor/result.json)

## 相同窗口的实际动作

| 题目与决策步 | 归档 Parent | 候选 Actor |
|---|---|---|
| train:0034 第 9 步，连续查过抽屉 3、4 | 回抽屉 1 | 去抽屉 5 |
| train:0035 第 7 步，连续查过抽屉 3、4，均无蜡烛 | 回抽屉 1 | 去抽屉 5 |
| val:0006 第 5 步，连续打开两个空抽屉 | 转台面 1 | 去抽屉 3 |
| val:0007 第 15 步，已查完该题的七个抽屉 | 转台面 1 | 转柜子 1，两者均为新位置 |
| val:0007 第 16 步，在归档路线的台面 1 未发现目标 | 回抽屉 1 | 回抽屉 6，台面 2 仍可选 |
| train:0038 第 4、5、6、10、12 步 | 取盐罐、去边桌、放第一件、取第二件、放第二件 | 五处均与 Parent 一致 |

train:0035 与 val:0006 均未进入提案或审核。该组窗口刻意覆盖归档中的折返，3/3 表示这三个状态的动作对照。[十个窗口的观察、历史、动作及判据](../../../../../artifacts/methods/v24_9/v24_9_general_archive_01/window_results.json)

## 同题完整执行

| 题目 | Parent | 候选 |
|---|---:|---:|
| train:0034，找两张 CD | 失败 50 | 失败 50 |
| train:0031，加热盘子 | 失败 50 | 失败 50 |
| val:0007，清洗餐刀 | 失败 50 | 失败 50 |
| val:0002，灯下检查枕头 | 成功 5 | 成功 5 |
| val:0004，放置杯子 | 成功 6 | 成功 14 |
| train:0037，交付两份报纸，保留题 | 成功 21 | 成功 19 |
| train:0038，交付两个盐罐，保留题 | 成功 12 | 成功 19 |

- CD 题先按序打开抽屉 1 至 10，再走到架子 1、2，第 23 步又回抽屉 1。餐刀题先从台面 1 推进到台面 3，第 18 步也回到抽屉 1。同类规则已在连续执行中起作用，换类后的推进仍不稳定。
- 盘子题一路推进到柜子 26，第 48 步才拿到盘子。剩余两步只够到达并打开微波炉。同类推进也可能花掉后续任务所需的步数。
- 两道保留题均把不同编号的两件物品送到同一目标位置。报纸题两边都曾重复拿放第一份报纸；盐罐题候选也曾重新拿放第一只，再回柜子拿第二只。保护条款和最终交付都保住了，具体路线及步数仍有波动。
- 五道学习题两边均成功 2/5。唯一有变化的共同成功题多用 8 步，未到效率票门槛。Gate 对 `u1` 的成败与效率四类票数均为 0，判为 **Defer**，选择 Parent。两道保留题仅用于行为检查。[完整动作序列](../../../../../artifacts/methods/v24_9/v24_9_general_archive_01/paired_results.json) · [Gate 输出](../../../../../artifacts/methods/v24_9/v24_9_general_archive_01/learning_gate.json)

候选提出维护已查集合，Actor 每次请求实际只有当前状态与最近两步历史，也没有新增的持久化已查表。轨迹显示它能利用当前位置继续编号，但在旧类别重新进入菜单时可能从头再查。这与输入限制相符；一次采样无法单独确定折返的原因，也无法推定正式 Test 分数。

## 复核

在仓库根目录运行 `python scripts/runs/v24_9/verify_v24_9_general_offline.py --output artifacts/methods/v24_9/v24_9_general_archive_01` 可重放已有归档。验证脚本在需要收集新响应时支持 `--generate`。本批没有可归因的 Gate 事件，另取 v24.7 R02 的原始 Replay 输入单独检查第四个模块。[独立历史 Replay](../../../../../artifacts/methods/v24_9/v24_9_general_archive_01/historical_replay_R02/replay/result.json)

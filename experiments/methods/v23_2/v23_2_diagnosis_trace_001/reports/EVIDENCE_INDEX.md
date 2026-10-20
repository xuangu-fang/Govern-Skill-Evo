# P1-A 证据索引

原文留在原归档；本目录只保存关键步骤摘录及可核验引用。JSON Pointer 使用零基数组下标，报告中的 u1/u2 按 id 匹配。新旧编号不一定同义。

[机器核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/results/audit.json) · [关键步骤及候选原序列](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/results/evidence_index.json) · [历史保护](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/results/protection.json)

## P0/P1 与方法来源

- [reports/P0_BASELINE.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_boundary_001/reports/P0_BASELINE.md)
- [reports/P1_DIAGNOSIS_REPORT.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_boundary_001/reports/P1_DIAGNOSIS_REPORT.md)
- [reports/OUTPUTS.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_boundary_001/reports/OUTPUTS.md)
- [reports/P1_DESIGN.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_boundary_001/reports/P1_DESIGN.md)
- [config/cases.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_boundary_001/config/cases.json)
- [config/p0_freeze.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_boundary_001/config/p0_freeze.json)
- [config/p1_freeze.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_boundary_001/config/p1_freeze.json)
- [config/diagnosis_prompt.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_boundary_001/config/diagnosis_prompt.md)
- [config/v23.diff](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_boundary_001/config/v23.diff)
- [src/skill_evolution/v23/diagnosis.py](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/diagnosis.py)
- [src/skill_evolution/v23/diagnosis_prompt.md](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/diagnosis_prompt.md)
- [src/skill_evolution/v23/execution_context.md](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/execution_context.md)
- [src/skill_evolution/v23/facts.py](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/facts.py)
- [src/adapters/alfworld/actor_prompt.py](/Users/didi/Desktop/Govern-Skill-Evo/src/adapters/alfworld/actor_prompt.py)

## R04

下文简称：D0 = 正式原 Diagnosis，D1 = P1 Diagnosis；F = 原 Diagnosis input，G = 该轮实际 Grouping，T(Pn) = 下表原始 Parent trajectory。D1 的事实输入与 F 相同，模型 user 消息逐字相同。

- [F](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/diagnosis/attempts/001/input.json)
- [D0](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/diagnosis/attempts/001/diagnosis.json)
- [D1](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_boundary_001/R04/attempts/001/diagnosis.json)
- [D1 实际请求](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_boundary_001/R04/attempts/001/request.json)
- [G](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/grouping/attempts/003/grouping.json)
- [Parent](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent.md)

| 执行 | task_id | 原始记录 | 报告使用的步骤 |
|---|---|---|---|
| P1 | train:0030 | [T(P1)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/train_0030/attempts/001/skill_20261018T181227028768Z_62a94ffb/trajectory.json) | P1:28, P1:31, P1:37, P1:41, P1:44, P1:50 |
| P2 | train:0031 | [T(P2)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/train_0031/attempts/001/skill_20261018T181227029641Z_3f0c3355/trajectory.json) | P2:6, P2:7, P2:8, P2:9, P2:10, P2:11, P2:13 |
| P3 | train:0032 | [T(P3)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/train_0032/attempts/001/skill_20261018T181227029139Z_e319d148/trajectory.json) | P3:7, P3:12, P3:14 |
| P4 | train:0033 | [T(P4)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/train_0033/attempts/001/skill_20261018T181227029079Z_36d091aa/trajectory.json) | P4:5, P4:8, P4:17, P4:19, P4:21 |
| P5 | train:0034 | [T(P5)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/train_0034/attempts/001/skill_20261018T181227029642Z_ae9f7533/trajectory.json) | P5:14, P5:23, P5:50 |
| P6 | train:0035 | [T(P6)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/train_0035/attempts/001/skill_20261018T181227028851Z_0e04083b/trajectory.json) | P6:23, P6:24, P6:26, P6:27, P6:28, P6:30 |
| P7 | train:0036 | [T(P7)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/train_0036/attempts/001/skill_20261018T181227028983Z_cfc3b68c/trajectory.json) | P7:28, P7:35, P7:36, P7:47, P7:50 |
| P8 | train:0037 | [T(P8)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/train_0037/attempts/001/skill_20261018T181227029140Z_cf29ab7e/trajectory.json) | P8:1, P8:2, P8:4, P8:7, P8:8, P8:10 |
| P9 | train:0038 | [T(P9)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/train_0038/attempts/001/skill_20261018T181246227712Z_8342e75b/trajectory.json) | P9:4, P9:10 |
| P10 | val:0000 | [T(P10)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/parent_runs/val_0000/attempts/001/skill_20261018T181258153692Z_e753b5fc/trajectory.json) | P10:1, P10:2, P10:3 |

字段定位：`F#/facts/runs/{n-1}/steps/{k-1}` 对应 `Pn:k`；环境候选为 `T#/steps/{k-1}/admissible_commands`；实际 Actor 消息为同项 `messages`；所选动作是 `action`；`observation` 是动作之后的观察。`F` 的 `before.commands_ref` 才是决策时菜单，需在 `F#/facts/command_sets` 解析。后菜单仅由下一步前菜单恢复，终步未知。


## R05

下文简称：D0 = 正式原 Diagnosis，D1 = P1 Diagnosis；F = 原 Diagnosis input，G = 该轮实际 Grouping，T(Pn) = 下表原始 Parent trajectory。D1 的事实输入与 F 相同，模型 user 消息逐字相同。

- [F](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/diagnosis/attempts/001/input.json)
- [D0](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/diagnosis/attempts/001/diagnosis.json)
- [D1](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_boundary_001/R05/attempts/001/diagnosis.json)
- [D1 实际请求](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_boundary_001/R05/attempts/001/request.json)
- [G](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/grouping/attempts/002/grouping.json)
- [Parent](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent.md)

| 执行 | task_id | 原始记录 | 报告使用的步骤 |
|---|---|---|---|
| P1 | val:0001 | [T(P1)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0001/attempts/001/skill_20261019T013400542582Z_a4b05037/trajectory.json) | 仅完整性核验 |
| P2 | val:0002 | [T(P2)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0002/attempts/001/skill_20261019T013400542665Z_e88a6f0f/trajectory.json) | 仅完整性核验 |
| P3 | val:0003 | [T(P3)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0003/attempts/001/skill_20261019T013400543017Z_00488991/trajectory.json) | P3:13, P3:14, P3:16 |
| P4 | val:0004 | [T(P4)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0004/attempts/001/skill_20261019T013400543157Z_1ed6e495/trajectory.json) | P4:1, P4:2, P4:4 |
| P5 | val:0005 | [T(P5)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0005/attempts/001/skill_20261019T013400543208Z_a8b895cd/trajectory.json) | P5:3, P5:5 |
| P6 | val:0006 | [T(P6)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0006/attempts/001/skill_20261019T013400542886Z_f7527282/trajectory.json) | P6:1, P6:2, P6:5, P6:6, P6:7, P6:10, P6:11, P6:50 |
| P7 | val:0007 | [T(P7)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0007/attempts/001/skill_20261019T013400543719Z_1415e05e/trajectory.json) | P7:2, P7:5, P7:7, P7:9 |
| P8 | val:0008 | [T(P8)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0008/attempts/001/skill_20261019T013400542428Z_20a7acc9/trajectory.json) | P8:1, P8:4, P8:26, P8:27, P8:28, P8:39, P8:50 |
| P9 | val:0009 | [T(P9)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0009/attempts/001/skill_20261019T013407908686Z_7062622b/trajectory.json) | P9:2, P9:4, P9:6 |
| P10 | val:0010 | [T(P10)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0010/attempts/001/skill_20261019T013408990605Z_27ee1b81/trajectory.json) | P10:5, P10:6, P10:25, P10:32, P10:33, P10:35, P10:38 |

字段定位：`F#/facts/runs/{n-1}/steps/{k-1}` 对应 `Pn:k`；环境候选为 `T#/steps/{k-1}/admissible_commands`；实际 Actor 消息为同项 `messages`；所选动作是 `action`；`observation` 是动作之后的观察。`F` 的 `before.commands_ref` 才是决策时菜单，需在 `F#/facts/command_sets` 解析。后菜单仅由下一步前菜单恢复，终步未知。


## R06

下文简称：D0 = 正式原 Diagnosis，D1 = P1 Diagnosis；F = 原 Diagnosis input，G = 该轮实际 Grouping，T(Pn) = 下表原始 Parent trajectory。D1 的事实输入与 F 相同，模型 user 消息逐字相同。

- [F](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/diagnosis/attempts/001/input.json)
- [D0](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/diagnosis/attempts/001/diagnosis.json)
- [D1](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_boundary_001/R06/attempts/001/diagnosis.json)
- [D1 实际请求](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_boundary_001/R06/attempts/001/request.json)
- [G](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/grouping/attempts/001/grouping.json)
- [Parent](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/parent.md)

| 执行 | task_id | 原始记录 | 报告使用的步骤 |
|---|---|---|---|
| P1 | val:0011 | [T(P1)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/parent_runs/val_0011/attempts/001/skill_20261019T014346856893Z_83e8c4ca/trajectory.json) | P1:34, P1:35, P1:37, P1:40 |
| P2 | val:0012 | [T(P2)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/parent_runs/val_0012/attempts/001/skill_20261019T014346857090Z_443ae66d/trajectory.json) | P2:8, P2:9, P2:11, P2:14 |
| P3 | val:0013 | [T(P3)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/parent_runs/val_0013/attempts/001/skill_20261019T014346856944Z_c657f846/trajectory.json) | P3:2, P3:13, P3:22, P3:50 |
| P4 | val:0014 | [T(P4)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/parent_runs/val_0014/attempts/001/skill_20261019T014346857262Z_9f17d470/trajectory.json) | P4:3, P4:5, P4:6, P4:7, P4:14, P4:19, P4:20, P4:22 |
| P5 | val:0015 | [T(P5)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/parent_runs/val_0015/attempts/001/skill_20261019T014346856968Z_7ab3d6d5/trajectory.json) | P5:4, P5:5, P5:6, P5:13, P5:14, P5:15, P5:18 |
| P6 | val:0016 | [T(P6)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/parent_runs/val_0016/attempts/001/skill_20261019T014346857325Z_826b4582/trajectory.json) | P6:17, P6:18, P6:20, P6:21, P6:22, P6:23, P6:24 |
| P7 | val:0017 | [T(P7)](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/parent_runs/val_0017/attempts/001/skill_20261019T014346857433Z_f4c3d862/trajectory.json) | P7:1, P7:5, P7:7, P7:8, P7:10 |

字段定位：`F#/facts/runs/{n-1}/steps/{k-1}` 对应 `Pn:k`；环境候选为 `T#/steps/{k-1}/admissible_commands`；实际 Actor 消息为同项 `messages`；所选动作是 `action`；`observation` 是动作之后的观察。`F` 的 `before.commands_ref` 才是决策时菜单，需在 `F#/facts/command_sets` 解析。后菜单仅由下一步前菜单恢复，终步未知。


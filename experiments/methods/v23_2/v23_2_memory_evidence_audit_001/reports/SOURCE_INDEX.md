# P2 来源索引

本目录是只读分析产物。所有 step 标识一基；原始 JSON 的 steps 数组零基。历史上下文中的 P/Q 分别为 Parent/Candidate。R05 当前 P3/P4 与未来阶段 P3 无关，不要混淆。

## 实际请求与快照

### R05

- [实际 request.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/preconditioner/attempts/001/request.json)：`body.messages[1].content` 解析后的 `memory.entries / memory.sources`。
- [实际 response.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/preconditioner/attempts/001/response.json)、[HTTP 状态](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/preconditioner/attempts/001/http_status.json)、[运行记录](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/preconditioner/attempts/001/run.json)：本次校验状态 valid，与保存请求共同证明历史调用已完成，不仅是未发送装配。
- [装配输入](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/preconditioner/attempts/001/input.json)、[round_input](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/round_input.json)、[Active 索引](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/memory/active.json)：IDs = M1, M2, M3, M6, M7, M8, M9。
- [S1_R03 不可变 commit](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/memory/archive/S1_R03.json)：`entries[id=M6/M10].knowledge/evidence`；`context.payload.parent/diff/runs/command_sets/pairs`；`context.candidate/record_paths`。

### R06

- [实际 request.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/preconditioner/attempts/001/request.json)：`body.messages[1].content` 解析后的 `memory.entries / memory.sources`。
- [实际 response.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/preconditioner/attempts/001/response.json)、[HTTP 状态](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/preconditioner/attempts/001/http_status.json)、[运行记录](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/preconditioner/attempts/001/run.json)：本次校验状态 valid，与保存请求共同证明历史调用已完成，不仅是未发送装配。
- [装配输入](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/preconditioner/attempts/001/input.json)、[round_input](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/round_input.json)、[Active 索引](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/memory/active.json)：IDs = M1, M2, M6, M7, M9, M10, M11。
- [S1_R03 不可变 commit](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/memory/archive/S1_R03.json)：`entries[id=M6/M10].knowledge/evidence`；`context.payload.parent/diff/runs/command_sets/pairs`；`context.candidate/record_paths`。
- [S1_R05 不可变 commit](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/memory/archive/S1_R05.json)：`entries[id=M6/M10].knowledge/evidence`；`context.payload.parent/diff/runs/command_sets/pairs`；`context.candidate/record_paths`。

## 原始 Skill 编辑

- S1_R03: [actual.diff](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/editor/attempts/001/actual.diff)、[candidate.md](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/editor/attempts/001/candidate.md)。严格 Patch 应用于 archive Parent 得到相同 Candidate；没有调用 Editor 模型。
- S1_R05: [actual.diff](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/editor/attempts/001/actual.diff)、[candidate.md](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/editor/attempts/001/candidate.md)。严格 Patch 应用于 archive Parent 得到相同 Candidate；没有调用 Editor 模型。

## 40 条原始执行路径

| 上下文／ref | 原记录 | task_id | 步数／成功 |
|---|---|---|---|
| S1_R03/P1 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0020/attempts/001/skill_20261018T180225460895Z_f51220d6/trajectory.json) | train:0020 | 9 / True |
| S1_R03/P2 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0021/attempts/001/skill_20261018T180225462563Z_0a9cb7b3/trajectory.json) | train:0021 | 20 / True |
| S1_R03/P3 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0022/attempts/001/skill_20261018T180225481597Z_679f1dd2/trajectory.json) | train:0022 | 8 / True |
| S1_R03/P4 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0023/attempts/001/skill_20261018T180225460274Z_b75db320/trajectory.json) | train:0023 | 50 / False |
| S1_R03/P5 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0024/attempts/001/skill_20261018T180225475042Z_197ddbde/trajectory.json) | train:0024 | 50 / False |
| S1_R03/P6 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0025/attempts/001/skill_20261018T180225460868Z_6a9d32a4/trajectory.json) | train:0025 | 38 / True |
| S1_R03/P7 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0026/attempts/001/skill_20261018T180225460520Z_1091a89f/trajectory.json) | train:0026 | 18 / True |
| S1_R03/P8 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0027/attempts/001/skill_20261018T180225460301Z_fae729a5/trajectory.json) | train:0027 | 35 / True |
| S1_R03/P9 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0028/attempts/001/skill_20261018T180242101052Z_15919404/trajectory.json) | train:0028 | 40 / True |
| S1_R03/P10 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/parent_runs/train_0029/attempts/001/skill_20261018T180251822822Z_cc28209d/trajectory.json) | train:0029 | 50 / False |
| S1_R03/Q1 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0020/attempts/001/skill_20261018T180930000936Z_b579c44f/trajectory.json) | train:0020 | 10 / True |
| S1_R03/Q2 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0021/attempts/001/skill_20261018T180930000753Z_7d4345cf/trajectory.json) | train:0021 | 50 / False |
| S1_R03/Q3 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0022/attempts/001/skill_20261018T180930000784Z_7181aa74/trajectory.json) | train:0022 | 9 / True |
| S1_R03/Q4 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0023/attempts/001/skill_20261018T180930001022Z_af64f4bf/trajectory.json) | train:0023 | 17 / True |
| S1_R03/Q5 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0024/attempts/001/skill_20261018T180930001436Z_e336be1c/trajectory.json) | train:0024 | 50 / False |
| S1_R03/Q6 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0025/attempts/001/skill_20261018T180930000829Z_36a63cbc/trajectory.json) | train:0025 | 50 / False |
| S1_R03/Q7 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0026/attempts/001/skill_20261018T180930001050Z_ac217ed7/trajectory.json) | train:0026 | 11 / True |
| S1_R03/Q8 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0027/attempts/001/skill_20261018T180930001090Z_ad84f6e5/trajectory.json) | train:0027 | 9 / True |
| S1_R03/Q9 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0028/attempts/001/skill_20261018T180946535700Z_39b42ba4/trajectory.json) | train:0028 | 15 / True |
| S1_R03/Q10 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/candidate_runs/train_0029/attempts/001/skill_20261018T180946973207Z_0a785472/trajectory.json) | train:0029 | 50 / False |
| S1_R05/P1 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0001/attempts/001/skill_20261019T013400542582Z_a4b05037/trajectory.json) | val:0001 | 9 / True |
| S1_R05/P2 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0002/attempts/001/skill_20261019T013400542665Z_e88a6f0f/trajectory.json) | val:0002 | 6 / True |
| S1_R05/P3 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0003/attempts/001/skill_20261019T013400543017Z_00488991/trajectory.json) | val:0003 | 16 / True |
| S1_R05/P4 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0004/attempts/001/skill_20261019T013400543157Z_1ed6e495/trajectory.json) | val:0004 | 4 / True |
| S1_R05/P5 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0005/attempts/001/skill_20261019T013400543208Z_a8b895cd/trajectory.json) | val:0005 | 5 / True |
| S1_R05/P6 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0006/attempts/001/skill_20261019T013400542886Z_f7527282/trajectory.json) | val:0006 | 50 / False |
| S1_R05/P7 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0007/attempts/001/skill_20261019T013400543719Z_1415e05e/trajectory.json) | val:0007 | 50 / False |
| S1_R05/P8 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0008/attempts/001/skill_20261019T013400542428Z_20a7acc9/trajectory.json) | val:0008 | 50 / False |
| S1_R05/P9 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0009/attempts/001/skill_20261019T013407908686Z_7062622b/trajectory.json) | val:0009 | 6 / True |
| S1_R05/P10 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/parent_runs/val_0010/attempts/001/skill_20261019T013408990605Z_27ee1b81/trajectory.json) | val:0010 | 38 / True |
| S1_R05/Q1 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0001/attempts/001/skill_20261019T013959551113Z_29a7cb3d/trajectory.json) | val:0001 | 6 / True |
| S1_R05/Q2 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0002/attempts/001/skill_20261019T013959550906Z_e65da4b1/trajectory.json) | val:0002 | 6 / True |
| S1_R05/Q3 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0003/attempts/001/skill_20261019T013959551835Z_3559a0ce/trajectory.json) | val:0003 | 4 / True |
| S1_R05/Q4 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0004/attempts/001/skill_20261019T013959551378Z_01ff023d/trajectory.json) | val:0004 | 4 / True |
| S1_R05/Q5 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0005/attempts/001/skill_20261019T013959551937Z_30b7317c/trajectory.json) | val:0005 | 6 / True |
| S1_R05/Q6 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0006/attempts/001/skill_20261019T013959551254Z_105fe1fb/trajectory.json) | val:0006 | 21 / True |
| S1_R05/Q7 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0007/attempts/001/skill_20261019T013959551314Z_918f68bd/trajectory.json) | val:0007 | 50 / False |
| S1_R05/Q8 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0008/attempts/001/skill_20261019T013959551686Z_c2fd3459/trajectory.json) | val:0008 | 23 / True |
| S1_R05/Q9 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0009/attempts/001/skill_20261019T014007023502Z_fb7c31dc/trajectory.json) | val:0009 | 6 / True |
| S1_R05/Q10 | [record](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/candidate_runs/val_0010/attempts/001/skill_20261019T014007968433Z_087309eb/trajectory.json) | val:0010 | 46 / True |

每条 raw record 的 `steps[n-1].admissible_commands/messages/action/observation/feedback` 分别核查环境行动前候选、Actor 实际消息、动作、动作后观察及反馈。归档 facts 的 `steps[step=P*:n/Q*:n].before.commands_ref` 解析自 `command_sets`，不是 after 菜单。过滤只去掉精确的 `help`，其余内容、重复和顺序保留。最后一步 after.commands_ref 为 null 不表示空菜单。

## P1-B R05 静态输入来源

[合法重试 Diagnosis](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json)、[原始输入](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/input.json)、[请求](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/request.json)。只读取合法结果；未把第一次截断输出作为 Plan。Diagnosis 顶层 reason 不进入 Preconditioner。

[静态选择与尺寸](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/results/r05_selection.json) 保留相同 Original Plan 和 Grouping；所有补充条件只在内存中构造、未发送，没有产生新的 Plan。

[原始来源哈希](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/config/source_hashes.json)；[紧凑执行索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/results/run_evidence_index.json)；[实际 Memory 与 Diff 核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/results/memory_audit.json)。紧凑索引只是定位辅助，判断以原始记录及 archive 为准。

# 冻结 R05 有效 Update 的 Candidate 实跑

使用已保存的两条 REPLACE。十条 R05 Parent 轨迹来自原正式训练，原 Candidate 的同题结果用作历史对照。表格中的数字为动作步数。

| R05 任务 | 冻结 Parent | 原正式 Candidate | 新 Candidate |
|---|---:|---:|---:|
| val:0001 | ✓6 | ✓7 | ✓9 |
| val:0002 | ✓5 | ✓5 | ✓5 |
| val:0003 | ✓10 | ✓4 | ✓4 |
| val:0004 | ✓49 | ✓4 | ✓13 |
| val:0005 | ✓7 | ✓5 | ✓15 |
| val:0006 | ✗50 | ✗50 | ✓9 |
| val:0007 | ✗50 | ✗50 | ✗50 |
| val:0008 | ✗50 | ✓13 | ✓14 |
| val:0009 | ✓7 | ✓6 | ✓6 |
| val:0010 | ✗50 | ✓13 | ✓9 |
| 成功数 | 6/10 | 8/10 | 9/10 |

Gate 对 u1 计 1 gain（0008），对 u2 计 2 gain（0006、0010），两条均为 0 loss、Retain。选中的文本与实跑 Candidate 一致。两条补丁联合执行，Replay 的关联不能估计各补丁独立效应。[Replay](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/replay/result.json) · [Gate](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/gate.json) · [实际 Skill](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/candidate.md)

## 历史训练题配对

三道题分别用 R05 Parent 和新联合 Candidate 各跑一次，单独报告。下表给出各侧实际拿到的第一个物体，并链接配对轨迹。

|历史任务|本次 Parent|本次 Candidate|
|---|---|---|
|M3 train:0024|[成功 26 步](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/historical_probes/parent_runs/train_0024/attempts/001/skill_20261107T091016571786Z_da004d9c/trajectory.json)，第21步 take pan 1 from cabinet 9|[超时 50 步](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/historical_probes/candidate_runs/train_0024/attempts/001/skill_20261107T091155785067Z_02410541/trajectory.json)，全程无拿取|
|M6 train:0027|[成功 16 步](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/historical_probes/parent_runs/train_0027/attempts/001/skill_20261107T091016571783Z_9e5d2cc7/trajectory.json)，第11步 take apple 1 from diningtable 1|[成功 11 步](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/historical_probes/candidate_runs/train_0027/attempts/001/skill_20261107T091155785062Z_7358bff0/trajectory.json)，第5步 take apple 1 from diningtable 1|
|M7 train:0031|[成功 43 步](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/historical_probes/parent_runs/train_0031/attempts/001/skill_20261107T091016571775Z_e5527615/trajectory.json)，第38步 take plate 3 from countertop 3|[成功 20 步](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/historical_probes/candidate_runs/train_0031/attempts/001/skill_20261107T091155785040Z_0e3c1f4e/trajectory.json)，第15步 take plate 3 from countertop 3|

M3 第 5 步查过灶台 1 后，Candidate 第 6 步回到已查过的柜子 1；第 18 步一度推进到柜子 3，但全程没有到柜子 9。M6 经过柜子 1 后抵达餐桌找到了苹果；M7 虽有回访，仍推进到了台面 3。上述三题是历史冲突的定向配对，不能和 R05 合计估算泛化成功率。

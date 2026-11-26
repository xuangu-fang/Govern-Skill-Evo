# SearchQA v28.15

基于 v28.14。首轮四条 Workflow 补丁中仅第三条获采纳，候选文本中的 `3.` 因此成为最终列表首项。第六轮的拼写与连字符检查则在 Preconditioner 计划中已被指定写入 Workflow。这两处决定分别发生在 Editor 和 Preconditioner，因此只调整这两个模块的 Prompt。[首轮 Gate 结果](../../../experiments/campaigns/v28_14_searchqa600_batch60_20261112_001311/rounds/R01/gate/result.json) · [第六轮计划](../../../experiments/campaigns/v28_14_searchqa600_batch60_20261112_001311/rounds/R06/preconditioner/attempts/001/parsed.json)

## Prompt 与交接

| 模块 | v28.15 设计 |
| --- | --- |
| [Preconditioner](prompts/preconditioner.md) | 在已有 Update 的 text 中指定归属。决定选哪个答案、答案到哪里结束的判断放入 Workflow，同一判断的通常做法、条件和例外放在一起。能单独检查的错误放入 Error Avoidance。修订旧条目时按同样的标准复核归属，需要换节时由同一 Update 授权完整迁移并删除旧位置的内容。 |
| [Editor](prompts/editor.md) | 按 Effective Plan 指定的章节编辑。Workflow 顶层步骤按作答顺序排列，统一使用 Markdown 无序列表 `-`，具体例子缩进到所属步骤之下。版式示例同步使用无序列表。 |

例如，“省去题面已给出的类别词”和“省去后会指向另一对象时要保留”共同决定答案的范围，应放在同一条 Workflow 规则中。选定答案后，核对题面和文段所示的拼写、空格或连字符，可以独立执行，适合放入 Error Avoidance。归属取决于作答时怎样使用这条指导，而不是句中是否出现“不要”。

初始模板继续使用两个空标题，每条补丁都可直接在相应章节下写入内容。有独立避错证据时才写入 Error Avoidance。现有“五条独立 safeguards”上限、例子授权和软字符预算沿用 v28.14。

## 运行时版本绑定

| 项目 | 绑定标识 |
| --- | --- |
| Campaign | `v28_15_campaign_v1` |
| Preconditioner Prompt | `v28_15_searchqa_preconditioner_section_ownership_v1` |
| Editor Prompt | `v28_15_searchqa_editor_workflow_bullets_v1` |
| Diagnosis Prompt | `v28_14_searchqa_diagnosis_decision_grouping_v2` |
| Replay Prompt | `v28_8_searchqa_replay_decision_revision_v1` |
| Gate | `v28_13_gate_net_em_min2_v1` |

v28.15 使用[独立入口](../../../scripts/runs/run_v28_15_campaign.py)、[正式配置](../../../experiments/configs/v28_15_searchqa_train600_batch60.json)和[初始模板](../../../experiments/configs/v28_15_searchqa_initial_skill.md)，空模板内容与 v28.14 一致。Diagnosis 与 Replay 复用各自原文和标识。每轮仍以同一 Parent 生成独立补丁，在联合 Candidate 上执行并经 Replay 归因，Gate 依归因净改善题数筛选。被选中的补丁原样组合成下一轮 Parent。迁移一条规则时，旧处删除与新处写入共同采纳或共同暂缓。

## 验收设计

| 阶段与场景 | 核对内容 |
| --- | --- |
| 离线，首轮单条采纳 | 从双空标题生成四个独立的 Workflow 补丁，模拟 Gate 只采纳第三条。原始 Markdown 应只含该条无序项及其所属例子，两个标题各出现一次。 |
| 离线，规则跨节迁移 | 以带条件和例子的拼写规则为 Parent 的一部分，使用一个 Update 将它从 Workflow 迁入 Error Avoidance。采纳时规则及例子只出现在目标章节，暂缓时原文保留；两种情况下无关条目均完整。 |
| 离线，版本及流程 | 通过正常调用路径比对传入的 Prompt 与版本标识，确认 Gate、Actor、评分、批次及初始模板内容与基线一致。 |
| 正式实验，结构与成绩 | 用原 600 题、10 轮配置训练后，检查实际保留文本的编号、独立避错规则的归属，以及答案边界的条件和例外是否仍能从一处读全。使用最终 Skill 在同一批 1,400 题上报告 EM、F1 和答对题数，与 v28.14 已有结果并列。 |

离线场景验证给定补丁经筛选后的文本。Prompt 是否引导模型正确选择章节、成绩是否延续，需要由正式实验的实际输出判断。

## 离线验收结果

2026-11-12，四项验收全部通过。使用模拟归因计数 `[1, 1, 2, 1]` 时只保留第三条 Workflow 无序项及其缩进例子。迁移拼写规则时，净改善 2 题会完整迁移规则、条件和例子，净改善 1 题会完整保留原文。模拟轮次验证了四个模块收到的 Prompt、最终 Skill 的评测准备及恢复流程。正式配置通过只读预检，所用数据、Actor、评分、批次和预算与 v28.14 相同。验收期间网络与子进程调用次数均为 0。[验收记录](../../../artifacts/verification/v28_15_offline_20261112/validation.json) · [测试日志](../../../artifacts/verification/v28_15_offline_20261112/unittest.log)

从仓库根目录复跑四项检查：

```sh
/Users/didi/miniforge3/envs/SearchQA/bin/python -m unittest discover -s tests/skill_evolution/v28_15 -t . -v
```

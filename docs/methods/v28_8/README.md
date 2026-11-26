# v28.8 SearchQA 决策修订设计

本次修订的标识为 `decision_revision_v1`。比较对象是相同题目、顺序和 batch 的 SkillAdam，以及已完成的 v28.x 实验。此前工作区的 [Workflow + Error Avoidance 设计](revisions/workflow_error_avoidance_20261106/README.previous.md) 和该实验的冻结运行环境属于上一版。

| 模块 | 英文 prompt | 当前修订的职责 |
| --- | --- | --- |
| Diagnosis | [diagnosis.md](prompts/diagnosis.md) | 依据当前 Parent 批次，提出下次作答要改变的选择。证据中出现的题材只在影响选择时进入行为要求。 |
| Preconditioner | [preconditioner.md](prompts/preconditioner.md) | 根据 Parent 已有动作及历史干预效果，调整方向、适用条件或力度。需要修正旧默认时，把替换位置和结果写进有效 Update；已有指导足够时撤回。 |
| Editor | [editor.md](prompts/editor.md) | 只读 Parent 与有效计划，按 Update 生成 patch。改动一步后，Actor 应能从该步骤读出新的判断。 |
| Replay | [replay.md](prompts/replay.md) | 比较实际作答，把题面条件、答案变化、EM 转移和归因限度记录为可供后续预条件判断的 Knowledge。 |

SearchQA 指导关注题干留下的空位、候选满足的关系和何时结束答案。Workflow 随证据形成。Error Avoidance 只容纳有独立价值的提醒，至多五项（提示词约束）。短对照可选：限直接引用的本批训练证据，由 Preconditioner 核对并写入有效 Update，Editor 无权自拟。测试题只作最终评价。

沿用四项有效 Update 的联合候选预算、已有程序 Gate 及 Memory。实验采用相同顺序的 600 题、batch60、10 轮、104 字符初始 Skill 和空 Memory，最终评测同一批 1400 题。主指标是测试 EM，同时比较命中数、F1 和最终发布字符数。训练过程中追踪同一决策再次修订后是改进默认判断，还是累加题型分支。示例准入和四个模块的指导一同改变，新实验衡量的是整套设计的结果。

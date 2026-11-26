# v28.9 SearchQA 设计

基线为 v28.8 `decision_revision_v1`，对应实验 `v28_8_searchqa600_batch60_decision_revision_v1_20261106_032534`。创建 v28.9 前，已将工作区运行模块、提示词、配置和入口与该实验的冻结环境逐字核对。基线测试成绩为 1162/1400，EM 83.00%，F1 90.5699%，最终 Skill 为 8318 字符。

本次目标是提高指导的复用程度，同时改善测试 EM 和最终 Skill 长度。三个模块的开头学习指导采用用户确认的英文原文，替换边界为模块标题之后至 `## SearchQA solving decisions` 之前。

| 模块 | 提示词 | 设计重点 |
| --- | --- | --- |
| Diagnosis | [diagnosis.md](prompts/diagnosis.md) | 将证据组织为共同作答动作的改进，Original 集中说明要改变的选择。 |
| Preconditioner | [preconditioner.md](prompts/preconditioner.md) | 结合 Parent 和历史干预结果调整方向、范围和力度。支持改写相关步骤、整合等价指导，并审视缺乏依据的答案类别或形式偏好。 |
| Editor | [editor.md](prompts/editor.md) | 围绕有效 Update 指定的新判断重写相关步骤，保留必要区别，减少题材清单和分支累积。 |
| Replay | [replay.md](prompts/replay.md) | 使用 v28.8 的事件记录指导，为后续预条件判断保留实际答案变化和归因限度。 |

三个修订 prompt 使用 `v28_9_searchqa_<module>_reusable_actions_v1`。Replay 在独立目录保存内容相同的副本，版本标识为 `v28_8_searchqa_replay_decision_revision_v1`。四个运行时 prompt 均从 `docs/methods/v28_9/prompts` 加载。

独立入口为 `scripts/runs/run_v28_9_campaign.py`，配置为 `experiments/configs/v28_9_searchqa_train600_batch60.json`，方法版本为 `v28_9_campaign_v1`。实验配置使用相同 600 道训练题及顺序，batch60、10 轮、104 字符初始 Skill，新建训练采用空 Memory，最终评测相同顺序的 1400 道测试题。

每轮最多四项有效 Update 由已有 validator 执行。Error Avoidance 最多五项是提示词约束。Gate、Memory、补丁组合和输出反馈采用基线实现。可选短对照遵循基线的本批训练证据准入方式。

[来源清单](source_manifest.json)记录基线文件哈希。[离线验证](verification.json)包含运行入口预检、四个 prompt 逐字绑定、训练及测试顺序、旧配置隔离、四项上限及输出纠错检查，以及在实际 v28.9 Editor 上通过的 45 项补丁检查。离线检查期间禁止读取凭证和调用训练或测试程序。

本次交付为实现及离线验证，训练尚待启动。实际效果需要新实验确认，重点观察同一决定再次修订后是否形成更清楚的判断，以及最终测试的 EM、F1 和 Skill 字符数。

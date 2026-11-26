# v28.8：Workflow + Error Avoidance

实现日期：2026-11-06。当前工作区的 v28.8 使用本设计；此前已完成的 v28.8 实验保留原有结果和冻结运行环境，不代表本设计的成绩。

## 基线与修改范围

基线是旧版 v28.7 的 `v28_7_searchqa600_batch60_max4_20261105_182434/frozen_runtime`，不是新版 v28.7 single_decision，也不是此前的 v28.8 提示词。

三个提示词均从该冻结基线重新生成，并分别绑定到当前 v28.8 模块：

| 模块 | 提示词 | PROMPT_VERSION |
| --- | --- | --- |
| Diagnosis | [diagnosis.md](../../../../../experiments/automations/v28_8_searchqa600_batch60_workflow_error_avoidance_20261106_020209/frozen_runtime/docs/methods/v28_8/prompts/diagnosis.md) | `v28_8_searchqa_diagnosis_workflow_error_avoidance_v1` |
| Preconditioner | [preconditioner.md](../../../../../experiments/automations/v28_8_searchqa600_batch60_workflow_error_avoidance_20261106_020209/frozen_runtime/docs/methods/v28_8/prompts/preconditioner.md) | `v28_8_searchqa_preconditioner_workflow_error_avoidance_v1` |
| Editor | [editor.md](../../../../../experiments/automations/v28_8_searchqa600_batch60_workflow_error_avoidance_20261106_020209/frozen_runtime/docs/methods/v28_8/prompts/editor.md) | `v28_8_searchqa_editor_workflow_error_avoidance_v1` |

实际配置为 `experiments/configs/v28_8_searchqa_train600_batch60.json`。方法命名空间仍是 v28.8，提示词标识区分本次重新设计；新运行环境会拒绝此前 v28.8 的旧提示词配置。旧实验的复现应使用各自的 frozen_runtime。

## 方法设计

- Diagnosis 围绕作答动作提出证据支持的修正，区分选错对象与答案表达问题。不按实体或题型机械拆分，也不把一个完整修正拆成微小判断。已有充分指导且没有具体改进时，不追加同义规则；允许 no_change。
- Preconditioner 判断相对 Parent 的实际增量，将正常作答动作融入 Workflow，将确有独立价值的错误提醒融入 Error Avoidance。修改旧行为时明确要求替换或删除旧表述。有效文本保留必要行为、条件和整合要求；历史比较及选择理由留在 reason。
- Editor 把有效改进写成行动导向的流程步骤或简短提醒，在原位置重写受影响的规则，避免追加题型清单和例外目录。不把优化过程的分析写入 Skill，不自行添加行为或实例答案。

Workflow 不预填固定五步。Error Avoidance 可以为空，至多五条核心提醒，不得通过长段落打包独立决定或搬入 Workflow 规避限制。五条上限是提示词约束，沿用并明确旧版 v28.7 的相关约束，没有新增结构 validator。不同选中 Updates 的新增提醒需要一起考虑。

每轮 KEEP 与 REPLACE 合计最多四项，由原有 validator 强制执行；超过上限进入既有输出纠错流程，不截取前四项。Original 数量不另设硬上限，Preconditioner 从全部提案按价值选择，预算落选继续使用 `Round budget:` 原因前缀。

保留实例答案禁令。没有新增 Skill 字符硬上限、独立压缩阶段、Gate 后审查阶段、额外 Actor 调用或新的筛选指标。

## 保持不变

20 个运行模块除版本命名空间、模块说明和三个提示词绑定外，与旧版 v28.7 的语法树一致；运行入口也仅有版本命名空间差异。Replay、Gate、Memory、补丁组合、输出 schema、重试预算及调用配置保持基线行为。

训练仍配置为相同 600 题和顺序、batch60、10 轮，104 字符初始 Skill，沿用新建训练时的空 Memory。测试仍是同一数据集划分的 1400 题。没有将 SkillAdam 最终 Skill 写入训练起点。

## 验证与留档

[离线验证结果](./verification.json)记录了：

- 新配置和 CLI `--validate-only` 通过；渲染出的三个提示词与文件逐字一致，Replay 与冻结基线一致。
- 数据顺序、初始 Skill、非方法配置与基线一致。
- 四项上限允许混合 KEEP/REPLACE，也允许选择 u2、u4、u6、u7；五项会作为输出验证错误拒绝；全部撤回得到空有效计划。
- 将现有 45 个 Editor 检查应用于实际 v28.8 Editor，全部通过。
- 旧版 v28.7 的受保护文件未修改；此前工作区 v28.8 文件已保存到本次 revision 的 before 目录。

[来源与校验清单](./source_manifest.json)以及同目录的三个 `.diff` 文件记录了本次变更。

以上均为离线验证，没有调用模型，没有启动训练或测试。内容组织是否改善、最终 Skill 是否更短及 EM 是否提高，仍需新实验验证。

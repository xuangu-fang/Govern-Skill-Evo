# v28.5 接口与职责合同（设计定稿）

本文件定义相对于 [冻结 v28.3 合同](baseline/CONTRACTS_v28_3.md) 的职责调整，并列出沿用的接口。独立运行实现见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。除本文明确的自然语言职责变化和独立版本身份外，原字段、校验、分支与持久化语义全部继承。

## 1. 身份与边界

method 为 `v28_5_campaign_v1`，stage 为 `v28_5_stages_v1`，runtime 为 `v28_5_light_runtime_v1`，四份 Prompt 为 `v28_5_searchqa_<module>_v1`；完整值见 [source_map.json](source_map.json)。运行实现已按设计身份绑定。

Diagnosis/Preconditioner 的新身份视图为 `v28_5_shared_execution_text_v1`，共享编码仍为 `execution_shared_initial_v1`。Replay 共享编码仍为 `replay_shared_initial_v1`。仅隔离版本身份，不改变字段、无损共享、完整 task/context 或普通响应的可见性。

固定 base protocol、SearchQA 归一化、Actor 单轮无工具、隐藏 reasoning 不可见、训练证据与 Test 隔离均保留。证据存在不证明 Actor 使用它；EM 匹配不独立证明语义正确。没有新模型阶段或外部检索。

## 2. 模型输入与输出

| 模块 | 模型输入 | 模型输出 |
|---|---|---|
| Diagnosis | `parent, runs, shared_initial`，完整当前 Parent 批次 | `decision, reason, plan`；plan 为 `goal, updates`；Update 为 `id, text, basis` |
| Preconditioner | `parent, plan, runs, memory, shared_initial`；runs 为 Plan 直接引用的当前完整执行子集 | `adjustments`；每项 `target, action, text, reason` |
| Editor | `parent, plan`；Update 仅 `id, text` | `edits`；每项 `update_id, patch, reason` |
| Replay | `parent, diff, plan, edits, pairs, runs, shared_initial`，仅 EM 翻转 pair/runs | `entries`，有事件时恰好一项含 `knowledge`；每条仅 `task_id, update_id, text` |

Diagnosis reason 不进入 Preconditioner；basis 中的成功/反例仍需完整传递。Preconditioner reason 不进入 Editor。Replay 不接收历史 Memory、basis 或上游 reason。

## 3. Original 与 Effective Update 的职责差别

Original 必须是具体且完整的行为提案：目标行为、当前证据支持的条件、强度、必要行为依赖及保护边界，不是仅有错误标签或目标口号。Diagnosis 可参考相关 Parent 判断失败背景，不再要求全面完成 Parent 的去重、跨段落优先级与编辑位置选择。材料性条件不能只留在 reason。

Preconditioner 利用 Parent 和相关 Memory 决定提案是否必要、如何修正方向与范围，以及相关旧指导如何替代、限定、整合或删除。Effective Update 必须完整到足以实施，包括必要旧规则处理。完整不等于复制整个 Parent；以可辨识措辞或行为定位相关指导，不新增 rule_id、operation、dependency 或文本范围字段。

KEEP 仅当 Original 全文已充分表达必要行为及协调时成立；认可主方向不等于认可全部条件，也不等于认证整个 Skill。若兼容性依赖仅写在 reason 中的例外或优先级，须 REPLACE。没有增量可以 WITHDRAW，但已有覆盖不自动证明无需修正，缺少历史也不阻止合理试验。

action 仍仅为 KEEP/REPLACE/WITHDRAW：KEEP/WITHDRAW 的 text=null；REPLACE 为完整、非空且与原文不同的 text。逐 Original 恰好一个决定。Goal、Original ID、顺序和 basis 冻结；程序仅替换存活 text 并移除 WITHDRAW 项。basis 仍是原提案来源，不声称已为替换后的每个条件重新提供独立证明。

不得合并或拆分 Update IDs，不得把另一 ID 的独立修复搬入某条 REPLACE。相关旧 Skill 规则可以整合，但不构成合并 Update 的权限。共享修正若不能在既有问题边界与映射内完整表达，不可暗中依赖未来 Gate 必然保留另一 Update。

## 4. Editor 的必要适配

每个 Effective Update 仍恰好一个 edit；非空 patch 按原合同对同一冻结 Parent 定位和组合。必要相关旧文字修改属于同一 Update。不得以新增一段代替要求的旧规则替代，也不得为了方便映射重复改动同一处。

在一次调用中检查完整候选含义，修正实施造成的重复、旧条件残留、错误位置或强度变化。Editor 不另选行为策略；若忠实实施需要未授权的关键行为选择，使用现有 patch=null 阻塞合同。patch="" 只表示原 Parent/base 已满足要求，不能依赖另一 patch 的未来内容。缺少任务原文或效果未验证不单独构成阻塞。

原始 patch 精确定位、换行、只读 context、非重叠字符范围、空/null 分支与错误处理保持不变。部分 patch 组合可能未经执行或存在行为依赖，文本构造校验不是语义正确性证明。

## 5. Replay 的小幅语义修订

保持任务覆盖、EM-only 事件、一题一条、明确关联一个有实际修改的 Update 或 null 的规则。实际 patch/diff 继续作为既有 Replay 输入，Memory 不新增这些字段。

Knowledge 准确区分观察到的答案变化、与 Update 的关联和分数变化的解释。多个答案特征同时改变时，记录影响解释的变化，不仅记录最符合 Update 意图的变化。一个变化与 Update 关联不意味着它单独足以解释全部 EM 改善。多个变化也不自动改为 null；仍按原有明确行为连接标准判断。

归一化解释须符合实际 scorer；不能把删除标点当作替换为空格。任务条件以当前事件证据为限，不把提案的整个范围写成已验证经验。优先使用准确的行为描述；具体限制不能被泛化的因果免责声明代替。

## 6. Gate、Memory 和执行分支沿用

```text
patch == ""                  → gate_decision = null
G > 0 and L == 0              → Retain
G == 0 and L > 0              → Reject
otherwise                    → Defer
```

G/L 仍只统计明确关联的 EM 翻转，不加入 F1、长度、净收益兜底或组合复测。Selected 为 Retain patches 对原 Parent 的组合；来源只按完整文本相等判定 parent/candidate/null。不能把完整 Candidate 分数归给不同的 Selected。

Memory 仍为 `rounds`；每轮仅 `round_id, source_updates, entries`。source_updates 为全部 Effective Updates 的 `id, text, gate_decision`；entries 为 `id, knowledge`，knowledge 仅 `task_id, update_id, text`。现有未归因事件合同不变，不增加新的利用、重归因或投票机制。不增加未翻转响应、历史原始 context、Editor patch/diff、检索器或汇总状态。

保留 append-only、顺序 Memory ID、Memory/Selected 同一 HEAD 原子发布、单写者、恢复复用和额度不重置。Diagnosis no_change、全部 WITHDRAW、Editor 空/null、无 EM 翻转等分支遵循冻结合同。自然语言质量要求不转换为新的运行时字段或阈值。

## 7. 验证边界

结构校验能验证字段、引用、覆盖、patch 与来源一致性，不能证明自然语言断言、历史迁移判断、协调质量或因果效果。静态审阅见 [PROMPT_REVIEW.md](PROMPT_REVIEW.md)。实现并完成必要检查后直接运行完整训练和测试，按 [实验计划](EXPERIMENT_PLAN.md) 分析真实轨迹及最终结果，不设置独立场景验收。

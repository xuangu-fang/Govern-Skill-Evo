# v29.6 接口与职责合同

本合同相对 v29.5 只调整自然语言职责与独立版本身份。 当前叠加 [parent_memory_delta_v1](PARENT_MEMORY_DELTA_REVIEW.md)，输入/输出、证据和算法合同保持原样。已按原设计绑定独立运行代码，验收见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。四份 Prompt 已完整保留 v29.5 的 DocVQA 证据、机器输出、编译与 patch 合同。

## 1. 输入与输出

| 模块 | 输入 | 输出 |
|---|---|---|
| Diagnosis | parent, runs, shared_initial；完整当前 Parent 批次 | decision, reason, plan；plan={goal,updates}；Update={id,text,basis} |
| Preconditioner | parent, plan, runs, memory, shared_initial；Plan 直接引用的完整当前执行子集 | adjustments；每项={target,action,text,reason} |
| Editor | parent, plan；plan={goal,updates[id,text]} | edits；每项={update_id,patch,reason} |
| Replay | parent, diff, plan, edits, pairs, runs, shared_initial；仅当前 hard 翻转事件 | entries；有事件时恰好一个含 knowledge 的容器；每条 Knowledge={task_id,update_id,text} |

所有模块返回英文 JSON，不新增字段或模型阶段。Diagnosis reason 不进入 Preconditioner；Preconditioner reason 和 basis 不进入 Editor；Replay 不接收历史 Memory、basis 或上游 reason。因此行为要求须进入 text，决定提案边界的成功/反例引用须进入 basis。

## 2. Original → Effective 的完整性

Original 是完整行为提案：问题支持的行为、材料性条件、强度、必要依赖和保护边界；不要求 Diagnosis 已完成 Parent 全面的去重或旧规则编辑安排。Diagnosis 仍须解决自己提出的行为之间的矛盾，不能只输出错误标签或让下游补证据。

Preconditioner 根据 Parent、当前可用证据和相关 Memory 形成完整可实施修正。必要的旧规则替代、限定、整合、删除和有效分支保留必须进入 Effective text。 整合仅限重复指导会使本次修正重复、冲突或不完整的必要位置；发现重复本身不是额外编辑目标。可以用可辨识措辞定位规则，不新增 rule_id、operation、dependency 或字符范围字段。

- KEEP：全文已足以表达合理修正，text=null。认可主方向不等于认可所有条件。
- REPLACE：提供非空、不同于原文的完整 text；不是局部补丁或“同前，另加”。
- WITHDRAW：text=null；处理撤回对其他 Original 必要依赖的影响。 Preconditioner 已知 Parent 完整覆盖且无合理行为增量时首选 WITHDRAW；Editor 的空 patch 是实施阶段兜底，不能作为主动保留已知冗余提案的理由。

每个 Original 恰好一个决定。Goal、IDs、顺序、basis 冻结；程序仅替换 text 并删除 WITHDRAW 项。basis 保持原提案来源，不声称为调整后的每个条件提供新证明。禁止跨 ID 搬运独立修复、拆分/合并 IDs，或依赖另一项未来必然被保留。

保持既有证据一致性底线，但本版不额外加入 Brutus 分析后的支持案例回查段落；对应排除来源见 [PROMPT_REVIEW.md](PROMPT_REVIEW.md)。

## 3. Editor 与 patch

每个 Effective Update 恰好一个 edit。每个非空 patch 定位于同一个冻结 Parent，可有多个按源位置排列的 hunk。沿用无编号 `@@`、精确唯一定位、换行身份、只读 context 共享、非重叠字符编辑与原组合顺序规则。不得对另一 patch 的输出定位，不提供模糊匹配、自动语义修复或完整文本回退。

必要旧文字和相关位置的修改归属同一 Update；不得重复修改同一区域以隐藏映射问题。若两个 Updates 无法无冲突地忠实实现，保留原 blocker 合同，不合并 IDs。

| patch 值 | 含义 |
|---|---|
| 非空合法 diff | 该 Update 的实际修改 |
| 精确空串 `""` | 原 Parent/base 已充分满足，不依赖其他 patch 的未来内容 |
| null | 忠实实施被未决关键要求阻塞；停止完整 Candidate 构造，不发布剩余部分 |

输入缺少图片不单独构成 blocker：Update 可以要求 Actor 在执行时判断图片条件。未来效果未知也不单独构成 blocker。定位失败、重叠或解析失败属于验证错误，不自动转换为空 patch/null。合法 null 为语义停止，不触发额外语义重采样。

Editor 的自查只处理本次实施产生的重复、残留和冲突；不自行决定新策略、不清理无关历史缺陷、不以篇幅为独立优化目标。

## 4. DocVQA 证据、评分与 Replay

Actor 单轮、无工具，读取完整问题和原图；优化模块只接收完整普通响应、问题、参考答案、评分和执行消息的文本投影。图像块替换为明确占位文本；路径不是图像内容。不得新增图片读取、OCR、caption 或隐藏 reasoning。

答案提取使用最后一个完整 answer 元素（忽略大小写，可跨行），否则使用最后一个非空行。归一化仅小写、首尾去空白和合并空白。ANLS 对每个非空 reference 计算归一化字符编辑距离：距离≥0.5 得 0，否则为 1−距离，取 references 的最大值。hard=1 当且仅当 ANLS≥0.999。hard 是近乎精确字符串一致，不是独立语义或视觉正确性判断。

程序核实完整 Parent/Candidate 批次、相同任务与原图以及实际执行 Skill 后，才筛选 hard 翻转。无翻转时跳过 Replay 模型调用并生成 entries=[]；ANLS-only 或答案变化但 hard 不变不进入 Replay。

有事件时一题一条 Knowledge，覆盖所有提供的翻转任务。update_id 只能指向一个有非空 patch 的 Effective Update，或 null。关联需要实际修改与可见行为变化有明确连接；不能只按题型、分数变化或意图归因。空 patch 不投票；多项变化不自动要求 null，不能区分单项影响或不可分离的联合影响仍用 null 并保留事件。

本版增加的事实忠实度要求包括重要同时变化、DocVQA 归一化、行为关联与得分解释分开、事件支持范围和具体限制。不加入 Brutus 后续“决定性条件核实并标记未知/不一致”的强化段落。原有图片不可见与归因不确定性边界继续有效。

## 5. Gate 与 Memory

Gate 逐 Update 只统计明确关联的当前 hard 翻转：G 为 0→1，L 为 1→0。Knowledge prose、历史 Memory、ANLS 和 Skill 长度不投票。

```text
patch == ""       → gate_decision = null
G > 0 且 L == 0   → Retain
G == 0 且 L > 0   → Reject
其他              → Defer（包括混合结果与 0/0）
```

Selected 为 Retain patches 按 Effective 顺序对原 Parent 的组合。没有保留项则使用 Parent。程序继续检查组合合法性；失败不静默回退。`selected_execution_source` 仅按完整文本相等标记 parent/candidate/null，新组合不得继承完整 Candidate 的分数，也不额外执行组合复测。

模型可见 Memory 仍为 rounds；每轮只有 round_id、source_updates、entries。source_updates 保留所有 Effective Updates 的 id/text/gate_decision；entries 为 id/knowledge；knowledge 为 task_id/update_id/text。全局 Memory ID 按已提交事件顺序生成。null 关联事件保留，但不成为某个具体 Update 的正负票；无 Knowledge 不等于没有执行或已证明无效。

不存储 Original、Editor patch、未翻转响应、历史图片或历史原始执行作为新的 Memory 字段。历史 Retain 不证明规则仍在当前 Parent。保留 append-only、单写者、顺序提交，以及 Memory 与 Selected Skill 通过同一 HEAD 的原子发布。

## 6. 执行分支与恢复

沿用 v29.5 运行语义，设计不重写这些分支：

| 分支 | 保持的行为 |
|---|---|
| Diagnosis no_change | 不进入 Preconditioner/Editor/Candidate，保持 Parent，不追加新的 Memory 轮 |
| 全部 WITHDRAW | 无 Effective Plan；保持 Parent，不执行 Candidate、不追加新的 Memory 轮 |
| Editor 出现合法 null | 语义停止；不构造/执行部分 Candidate、不提交 Memory 或推进轮次，不额外语义重采样 |
| 全部空 patch | 不执行 Candidate/Replay；记录既有 no-change Memory（Effective Updates、null 决定、空 entries） |
| Candidate 有修改但无 hard 翻转 | 跳过 Replay 模型；Gate 对非空 patch 为 Defer，按既有路径提交 Memory |
| 部分空 patch | 执行其余修改构成的 Candidate；空 patch 无新干预票 |
| 解析/合同/patch 验证错误 | 使用既有验证反馈重试及请求上限；不能伪装成成功 no_change |

请求与恢复保持六次总预算、原始归档、复用已完成阶段和额度不重置。`continue_no_change=true`、`semantic_resampling=false`、`knowledge_review=disabled_v1` 保持原值。版本隔离后禁止将 v29.5 campaign 原地改名或交叉恢复成 v29.6。

## 7. 独立身份与未改接口

已绑定的方法/阶段/运行时/最终测试身份分别为 `v29_6_campaign_v1`、`v29_6_stages_v1`、`v29_6_light_runtime_v1`、`v29_6_final_test_v1`。四份修改后的 Prompt 使用 `v29_6_docvqa_<module>_v1`。

结构合同、memory_view、replay_input_view、model_input_view、execution_input_views、重试及发布协议保留 v29.5 配置的原标识；未修改协议不重新编号。完整逐字段对照见 [source_map.json](source_map.json) 的 baseline_method / planned_method / bound_method。计划身份与实际绑定一致；四份 Prompt、独立配置与 CLI 均已接入，未启动真实实验。

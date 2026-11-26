# v29 五模块合成示例

这些示例展示输入边界和输出合同，不是模型生成结果。使用完全虚构的任务和历史，不读取真实 Train/Test 答案来构造案例；图片路径只有占位作用，没有图片内容供优化模块读取。

模块的 system 使用上级 `prompts/` 下对应的完整英文文本；`.input.json` 是完整 user payload，`.output.json` 是人工编写的一种合理输出，不是要求模型必须复述的唯一答案。

Replay 输入示例已同步响应正文去重：每条普通响应完整保留在 `attempts[0].assistant.content`，省略相同的 `outcome.answer.raw_content`，并继续共享 initial、去掉重复 request_messages。只有模型展示变化，输出示例及证据引用不变；原始归档仍保存完整字段。

## 1. 完整五模块主链

[01_full_chain](01_full_chain/) 包含：

| 阶段 | 输入 | 输出 |
|---|---|---|
| Grouping | [input](01_full_chain/grouping.input.json) | [output](01_full_chain/grouping.output.json) |
| Diagnosis | [input](01_full_chain/diagnosis.input.json) | [output](01_full_chain/diagnosis.output.json) |
| Preconditioner | [input](01_full_chain/preconditioner.input.json) | [output](01_full_chain/preconditioner.output.json) |
| Editor | [input](01_full_chain/editor.input.json) | [output](01_full_chain/editor.output.json) |
| Replay | [input](01_full_chain/replay.input.json) | [output](01_full_chain/replay.output.json) |

Parent 使用 SkillOpt DocVQA 初始 Skill 的原文。两个合成任务分别问金额和日期：

| 任务 | Parent 普通响应 | Candidate 普通响应 | 结果 |
|---|---|---|---|
| 总金额 | 明确声称将 subtotal 当作 total，答案 1,200 | 仅给出答案 1,320 | 参考 1,320；hard 0→1，ANLS 0.6→1 |
| 发票日期 | 12 May 2021 | 12 May 2022 | 参考 12 May 2021；hard 1→0，ANLS 1→10/11 |

这里没有给出或假定账单布局。金额题支持分析 Actor 自己陈述的选择，但不能确认图中有何字段。日期题的退步没有由可见文本揭示原因。

Diagnosis 提出一个金额角色指导 Update；其 basis 只直接引用 P1，所以 Preconditioner 的 runs 只有 P1，但仍独立接收完整 Parent Skill。Preconditioner 对整个 Update 作 KEEP；Editor 将它加入现有标签匹配段落。Replay 看到两组完整配对，必须同时保留金额改善和日期退步。

Grouping 只组织问题要求与 Actor 陈述的差异，不提出视觉原因假设。Checks 在 Diagnosis、Original/Effective Plan、Editor 与 Replay 示例中同步传递，只要求比较答案、hard/ANLS 和带归属的响应陈述。Preconditioner 与 Replay 明确保留“匹配标签是否存在未知”；Candidate 没提标签不证明它不存在或已被正确使用。Editor 的 reason 则说明，这种交给 Actor 判断的条件无需 Editor 看图即可实现。

整批成功数为 1→1，程序会 RETAIN；Replay 输入没有这个决策，仍可记录有价值的 Knowledge。参考 [Parent](01_full_chain/parent_skill.md)、[Effective Plan](01_full_chain/effective_plan.json)、[Candidate](01_full_chain/candidate_skill.md)。

## 2. ANLS 提升，hard 不变

[02_anls_only](02_anls_only/) 只展示 Replay。参考答案为 10000，预测从 10099 变为 10001；ANLS 从 0.6 升至 0.8，hard 始终为 0。

正确的学习范围是“字符串更接近参考答案”；不能写成已经读对字段、部分掌握了语义或满足接受条件。两侧都只给答案，不能推断内部遵循了新规则。

## 3. 改善配对与历史整条修订

[03_history_revision](03_history_revision/) 使用一组金额改善配对，程序会 ACCEPT，但不把决策传给 Replay。

输入 Memory M1 有两条历史 Knowledge：一条记录早先 label-only 改动未改善结果且原因未知；另一条记录某个裸数字答案曾得到 hard=1，但不支持普遍删掉单位。第一条还报告早先 Candidate 自称转录了标签“Total”，这是合成的历史 Actor 陈述，不是核实后的图片内容，也不能证明标签与所问金额对应。

Replay 修订 M1 时，第一条结合当前不同强度的规则做有边界的比较，仍明确将“Total”转录归属于 Actor；不能把它改写成“文档有匹配标签”或“Actor 已正确定位”。也不能反过来假设匹配字段不存在而排除早先反例。第二条完整保留。不能因为本轮改善，就改写早先失败或丢掉另一条仍有效的历史理解。

## 4. Preconditioner 撤回重复提议

[04_preconditioner_redundancy](04_preconditioner_redundancy/) 故意提供一个重复 Original Update，测试 C 的既有职责；它不是理想 Diagnosis 输出示范。

独立 Parent 已包含完全相同的指导。当前答错不证明再写一遍有增量。Preconditioner 撤回该 Update，并显式清空依赖它的 Checks；没有幸存 Update 时，不再调用 Editor 或 Replay。

## 5. Diagnosis 合法 no_change

[05_diagnosis_no_change](05_diagnosis_no_change/) 中 Parent 已有金额角色指导，而回答只有一个错误数字。示例没有足够依据提出额外的具体改动，因此返回 no_change。

这不表示 Skill 完美，也不建立“短答案一律不允许修改”的新规则。是否形成有依据的假设仍取决于具体问题、回答、评分和已有指导。

## 6. Preconditioner 调整作用范围

[06_preconditioner_scope](06_preconditioner_scope/) 故意给出过强的“只能从明确匹配标签取答案”提议，用于演示 S 调整，而不是新增一套判断机制。

Parent、当前文本证据和历史 Knowledge 均不足以支持这种排他限制。Preconditioner 将它改为“辨别问题要求的金额角色；存在对应明确标签时优先使用”。输出是针对 Original Update 的精确无行号 patch，保留原 ID 与 basis，Checks 使用 null 继承。

历史失败只支持保留疑问和检查作用范围，不能证明替代规则有效。修改后的完整行为条件必须写在 Update 中，不藏在 reason 里。

本例与第 3 组使用相同的历史 Memory。Preconditioner 对“Total”转录的引用保留 Actor 归属，不将自报视觉动作当成匹配字段存在或不存在的证明；历史反例的视觉适用机会仍未知。这里的 S 调整依据是 Original 的排他强度缺乏支持，并非已经证明替代规则有效。

## 使用边界

只将某模块的 `.input.json` 与对应 Prompt 作为该模块示例。`review_only.json`、Parent/Candidate 对照文件及本说明是给人的审阅材料，不额外传入 Editor 或其他模块。

以上示例文件仅用于设计讨论；没有为它们创建图片，也不能用它们启动真实 DocVQA 作答。

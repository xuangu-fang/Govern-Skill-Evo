# V23.4 Replay V3：有限真实验证与多 Knowledge 再次修订

2026-10-22。**建议暂不采用 V3 替换现有 P4。** V3在R06修正了部分过强解释、补回了V2遗漏的能力比较；但R05仍丢失重要正面响应并出现历史动作错误，第二轮又把历史动作套到当前同编号步骤，错误改变了对规则效果的判断。它没有在本次有限验证中表现出足以支撑默认替换的一致优势。

本轮已取得三份首个合法Replay输出：R05、R06，以及一次使用原样多Knowledge的真实再次修订。第三项是**真实模型、真实归档反馈的离线受控修订**，不是自然连续Skill演化。未修改用户Prompt、生产代码或正式Active Memory，也没有启动V4。

## 实验完成情况与边界

完整候选为 [v23_4_replay.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/v23_4_replay.md)，与用户提供文件逐字一致。R05/R06的实际User消息与P6完全相同，System只替换主学习Prompt；Actor背景、Memory v3、Pair、Schema和既有校验/存储函数均未变。P4及V2结果复用历史保存输出，没有重新调用。详细变量控制见 [METHOD.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/METHOD.md) 和 [输入对照核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/config/INPUT_COMPARISON.json)。

模型使用原deepseek-v4.1-flash配置、temperature=1、thinking medium及原传输和重试机制。每个条件第一次合法后即停止，语义失败重采样为零。R05和第二轮因length提高过输出上限；不能把它们与P4的差异全部归因于Prompt。两案例单次合法样本也不构成稳定性或统计显著性证明。

### 为什么没有直接做 R05→R06 闭环

实验R05 Candidate哈希`111613e3…`，R06 Parent哈希`eab4a195…`，不一致。后者接续的是正式v23 R05 Candidate；实验R06执行于10月21日，实验R05于10月22日，时间也相反。保存的Parent文件中没有发现接续本次实验Candidate的新边。

因此选择同一精确Parent（`06eccab6…`）上的正式R05另一种实际编辑及20条独立执行作为受控第二轮反馈。前置Memory与实验R05相同，原始轨迹重建与归档一致，执行ID与首轮R05全部当前/历史输入无交集。任务实例相同，实际执行不同。**正式反馈发生于10月19日，离线纳入顺序与执行时间相反，且不是Candidate→Parent转换。** 本测试只检验多Knowledge再次修订，不证明在线持续学习。正式R05也曾出现在独立R06对照臂的历史中，但未被本条R05隔离链首轮学习。

选择在读取V3合法输出前固定；没有为结果好看挑选反馈。完整来源核验见 [LINEAGE.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/LINEAGE.json)、[Parent库存核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/ALTERNATIVE_LINEAGE_INVENTORY.json)。

## P4 / V2 / V3 的关键比较

| 评价对象 | P4已保存结果 | V2已保存结果 | V3本轮结果 |
|---|---|---|---|
| R05当前apple14→11 | 保留总数，局部搜索解释不足 | 遗漏 | 仍遗漏，双方来源也未保留 |
| R05正确butterknife能力保持 | 未充分表达 | 补回 | 保留，另保留mug、pencil能力 |
| R05来源与行为事实 | 历史非法动作错归当前Q7:25 | 未重现该错配，历史cup区别较好 | 未重现Q7:25错配，但把历史搬cup写成heat cup |
| R05实际条款范围 | 混淆全局合法动作与非desklamp搜索 | 仍有范围混用 | 独立Admissible Actions更清楚；仍遗漏Parent P8:8合法直接开柜，且混淆新实例与新类型 |
| R05未找到/不存在 | 有不受支持的解释 | 仍有 | 仍有，并在修订历史搜索主题时继续强化 |
| R06 heat plate13成功/50失败 | 保留 | 保留但部分归纳过强 | 保留双方机会不对称 |
| R06 cool tomato局部零新增收益 | 明确保留 | 遗漏 | 仍遗漏，温变条目概括较强收益 |
| R06 creditcard24→9 | 保留 | 遗漏 | 补回，当前book修复也保留 |
| R06历史butterknife未找到 | 仍有absent解释 | 仍有 | 修订搜索主题改为未找到；未修订Active中仍有旧absent解释 |
| 历史修订 | 能保留若干复杂比较，但不可靠 | 历史整合增加，部分当前观察丢失 | 确实完成多Knowledge再次替换；历史保留较好，纠错与新证据绑定仍失败 |

完整逐条依据见 [R05审查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/R05_REVIEW.md)、[R06审查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/R06_REVIEW.md)。[EVIDENCE.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/EVIDENCE.json)保存模型实际可见事实及三版原始提案摘录，没有用未进入输入的历史详细状态补证。

V3的进步值得保留为研究结果：R06没有继续在新修订文本中断言全局不存在，当前搜索成功、失败、循环与能力比较也更均衡。但它仍没有让各条Knowledge协调起来：cool tomato取得目标后双方操作相同的限制没有进入温变认识，而“取得目标后具有较稳健局部收益”的表述仍然出现。

R05问题也不只是少了几个例子。遗漏apple会削弱对搜索正向响应的认识；虚构heat cup会把不存在的动作当成规则响应；把未搜索到写成absent会提供未经证实的适用条件。这些都可能改变D/S/C方向、范围或协调判断，足以影响采用。

## 多 Knowledge 第二轮结果

首轮M10（3条）和M11（2条）分别被修订为M14（3条）和M13（4条）；M12合法动作主题未被修改。**这确实是对真实多Knowledge的再次修订，不是只新增条目或再做一次旧字符串转换。** 新数组保留了历史bread改善/退化、plate38成功/50失败，以及首轮失败和能力保持；被替换条目的旧Evidence全部保留。本例没有表现出明显的重要旧对照遗忘。

但旧错误解释也被保留，且出现新的实质性混淆：

| 证据身份 | Q7:9 | Q7:17 | Q7:19 |
|---|---|---|---|
| 首轮实验R05历史Candidate | 取knife | clean knife | 放置knife |
| 第二轮当前正式R05 Candidate | go to drawer2 | go to drawer2 | go to drawer4 |

第二轮输出却断言当前Candidate在这些步骤同样操作knife。实际当前Parent操作了knife，Candidate没有；正确比较应当保留“避免了替代操作，但仍未找到目标而失败”。输出因此漏掉了有意义的响应，反而强化“两次规则都未抑制替代”的结论。两个来源均在实际输入中，ID全部合法，结构校验无法发现这种动作错配。

这一受控实验不能确定内部混淆原因，也不能推断自然时间顺序的演化必然产生同样错误。它能确认：**完整数组替换和历史Evidence保持，在本例中没有转化为可靠的解释校准。** 详见 [第二轮审查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/ROUND2_REVIEW.md)、[原始事实对照](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/ROUND2_EVIDENCE.json)、[完整修订映射](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/ROUND2_REVISION_METRICS.json)。

## Evidence、未来输入与成本

三份原样提案都通过隔离commit/load、幂等性、引用解析、完整trace/详细窗口一致性、历史Pair及固定Preconditioner输入投影检查。没有执行新的Preconditioner或Actor，因此这里只能评价潜在D/S/C价值和消费兼容性。

- R05的P8:8虽然没被Knowledge正确利用，但引用邻域仍保留其详细菜单和状态；apple P10/Q10则完全退出本轮来源。
- R06补回creditcard来源；tomato完整trace仍在，但cool步骤P2:15/Q2:7不再进入详细窗口。历史heat-egg写入文本，却缺其独立双方Evidence，P9/Q9也从未来来源中消失。
- 第二轮旧Evidence全部保留，当前新增引用也能展开；这证明可追溯性，不证明结论由引用支持。错误knife结论引用到的是导航步骤。

| 指标 | R05 P4 | R05 V2 | R05 V3 | R06 P4 | R06 V2 | R06 V3 |
|---|---:|---:|---:|---:|---:|---:|
| 提案Entry / Knowledge | 1/4 | 3/6 | 3/6 | 2/5 | 2/5 | 2/5 |
| 提案Knowledge文本字符 | 3,502 | 7,719 | 6,725 | 6,592 | 5,663 | 4,834 |
| 最长提案Knowledge字符 | 941 | 1,874 | 1,428 | 1,947 | 1,496 | 1,241 |
| Evidence次数 / 去重数 | 43/29 | 115/105 | 79/70 | 114/99 | 62/56 | 95/85 |
| 替换后Active文本字符 | 19,430 | 19,499 | 18,505 | 16,688 | 15,759 | 14,930 |
| Memory v3字符 | 819,075 | 868,760 | 825,726 | 817,146 | 734,780 | 791,848 |
| 固定Preconditioner User字符 | 1,001,947 | 1,051,632 | 1,008,598 | 957,526 | 875,160 | 932,228 |

统一实验ID长度后，V3相对P4的Memory v3变化为R05约+0.72%、R06约−3.29%；Preconditioner User约+0.59%和−2.81%。缩短文本、减少引用或详细窗口不能自动认定为收益。完整指标及窗口见 [COMPARISON_METRICS.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/COMPARISON_METRICS.json)。字符数不是token计费。

第二轮Active由8条Memory/11条Knowledge变为8/13；文本18,505→22,230字符，Memory v3由825,726→1,018,759（约+23.4%），固定Preconditioner User由1,008,598→1,201,631（约+19.1%）。增长包含新事实和旧知识保持，但也保留了错误解释，不能单凭没有遗忘判为有效积累。

## 实际调用与 tokens

| 调用/尝试 | max_tokens | 输入tokens | 输出tokens，含reasoning | 结果 |
|---|---:|---:|---:|---|
| R05 / 1 | 32,768 | 286,518 | 32,768 | length |
| R05 / 2 | 65,536 | 未知 | 未知 | 300秒读取超时 |
| R05 / 3 | 65,536 | 286,481 | 35,142 | 首个合法输出 |
| R06 / 1 | 32,768 | 276,942 | 23,979 | JSON解析失败 |
| R06 / 2 | 32,768 | 276,981 | 18,954 | 首个合法输出 |
| 第二轮 / 1 | 32,768 | 364,613 | 32,768 | length |
| 第二轮 / 2 | 65,536 | 364,569 | 50,587 | 首个合法输出 |

共3个逻辑调用、7次HTTP尝试，分别重启2/1/1次，均未超出上限。已返回usage合计输入1,856,104、输出194,198、总计2,050,302 tokens，**不包含超时请求未知的用量，不能当作完整计费总额**。同一冻结请求在不同尝试返回的输入计数略有差异，按服务原始usage记录，未人为统一。

仅看首份合法输出，P4/V2/V3的R05输出tokens为23,502/49,186/35,142，R06为20,723/29,562/18,954；R05输出预算不同且包含采样差异，不能据此作稳定成本结论。所有请求、原始响应、失败记录、解析JSON及使用量均保留，见 [RESULTS.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/RESULTS.json)、[首轮调用审计](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/AUDIT.json)、[第二轮调用审计](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/round2/AUDIT.json)。

## 采用判断与本轮结束

**暂不采用V3替换P4，不发布任何本轮Memory。** V3在R06的部分修正与能力比较恢复具有价值，但R05错误及第二轮事实错配会直接影响未来更新判断；相对P4的重要零收益边界也未保住。这是对研究用途的实质限制，不是要求逐句零错误。

多Knowledge已经显示出再次修订、保留多种历史响应的能力；本例进一步表明，保留旧知识和Evidence与校准旧解释仍是不同能力。P4作为当前对照基础继续保留，不代表P4旧提案全部可靠，也不意味着本轮可以用人工挑句拼出正式Memory。

本轮到此结束：没有V4优化、额外语义重采样或新Skill更新实验。自然连续两轮Skill/Memory闭环仍未被此次材料验证，不能用离线受控结果替代该结论。

## 交付索引与完整性

历史对照：[P4/P6报告](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/multi_knowledge_p6_001/REPORT.md)、[V2报告](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/conditional_learning_001/REPORT.md)。三版具体JSON路径与未修改原文同时收录于本目录EVIDENCE.json。

- [R05原始合法JSON](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/runs/R05_replay/attempt_003/parsed.json)、[R06原始合法JSON](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/runs/R06_replay/attempt_002/parsed.json)、[第二轮原始合法JSON](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/round2/runs/ROUND2_replay/attempt_002/parsed.json)。尝试结果与必要失败证据留在实验目录；完整请求和原始响应按相对层级存入 [首轮调用归档](../../../../artifacts/methods/v23_4/replay_v3_validation_001/runs/) 与 [第二轮调用归档](../../../../artifacts/methods/v23_4/replay_v3_validation_001/round2/runs/)，未修补。
- [R05 Memory检查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/cases/R05/results/MEMORY_AUDIT.json)、[R06 Memory检查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/cases/R06/results/MEMORY_AUDIT.json)、[第二轮Memory检查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/round2/cases/ROUND2/results/MEMORY_AUDIT.json)。完整 Memory 预览与 memory_candidate、memory_view、preconditioner_messages、future_replay_view 存入 [首轮 Memory 归档](../../../../artifacts/methods/v23_4/replay_v3_validation_001/cases/) 和 [第二轮 Memory 归档](../../../../artifacts/methods/v23_4/replay_v3_validation_001/round2/cases/)。
- [第二轮实际messages](../../../../artifacts/methods/v23_4/replay_v3_validation_001/round2/config/messages.json)、[model_input](../../../../artifacts/methods/v23_4/replay_v3_validation_001/round2/config/model_input.json)、[来源和控制记录](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/round2/config/CONTROL.json)。原样首轮Memory已独立冻结，未作语义修复。
- [最终审计](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_v3_validation_001/RESULTS.json)：12,581个既有受保护文件哈希未变；用户主Prompt逐字未变；所有新增实验产物仅位于本目录。

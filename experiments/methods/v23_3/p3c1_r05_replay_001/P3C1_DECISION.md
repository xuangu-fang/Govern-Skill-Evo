# P3-C1 阶段结论

**Editor与新Train预注册完成；R05 Replay受服务端Token速率限制中断，未完成A/B三方行为比较。** 两组Candidate均真实有效，B Preconditioner Keep仍导致Skill更新。现有完整配对只有Parent–A的P3/P6；不能判断V23.3是否优于V23。

| 最终问题 | 回答 |
|---|---|
| 1. A/B是否生成Candidate？ | 是，各一次真实Editor，HTTP200/stop，原Patch应用与load_editor复核通过，无修补。 |
| 2. B全部Keep是否仍更新Skill？ | 是。Editor落实Diagnosis Original的u1/u2/u3，改写搜索/精确目标段落并新增候选动作规则。 |
| 3. 实际Diff差异？ | A有明确近似类别例子和强同类覆盖/回访顺序；B保留原跨类别触发及exact noun phrase。两者均保留原clean/placement/desklamp条款。 |
| 4. 哪些三方配对有效？ | 没有完整三方配对。Parent–A/P3、P6为严格条件下的完整两方配对；其他已启动配对状态一致但结果截断，B三条未启动。 |
| 5. 相对Parent成功与退化？ | P3均4步成功；P6 Parent10步、A8步成功。无完整样本证明A退化，但覆盖不足。B无有效动作，无法判断。 |
| 6. A新约束是否实际造成问题？ | 文本风险存在，未观察到可归于它的行为退化；P7/P10的中断是429，不得记作过强约束失败。 |
| 7. B旧要求是否影响执行？ | 无法确认。B/P3首请求被限流，其他未启动。 |
| 8. 哪些差异可能来自Editor？ | 要求融合/措辞位置与Actor随机响应均可能影响行为。大部分Skill差异对应上游文本，但每组Editor只生成一次，无法隔离其影响。 |
| 9. 有无初步行为收益？ | A/P6少2步且必要处理保留，A/P10更早看到目标的前缀线索；只前者是完整配对，均不是稳定方法收益证明。 |
| 10. 新Train是否预注册？ | 是，2批×6，六族各一条/批；确定性种子230302，规范实例排重及暴露核查边界已记录，早于本轮Editor/Actor输出。新案例未执行。 |
| 11. 优先改哪一层？ | 当前首先需要可完成的行为实验与事先冻结的速率/技术失败处理方案，补足观察，而非据缺失结果选改某一策略层。原审计中更新决策可见性/关联问题仍值得研究；Editor已大致忠实落实，尚无证据优先重写它。 |
| 12. 足够决定实现D/S/C？ | 不足。不得把B缺失结果或A单例少两步当作新增机制依据。 |

## 范围与成本

本轮实际2次Editor、9条启动Episode、76次Actor决策HTTP（72个执行动作，4次429）；0重试，共78 HTTP。可见usage合计152,524 tokens；reasoning含在completion内，4个429 usage未知，货币费用未知。未超出2 Editor/12 Episode/600决策上限。

共性错误是模型级及租户级mix TPM限流，未返回可用恢复时间。已停止提交剩余B任务，未等待后暗中重跑、未换路由/模型/策略，也未启动Gate、Memory更新或新Train案例。故本轮主研究问题保持部分未答，不能宣称完整任务行为验证已完成。

后续如另行安排执行，应先冻结服务容量内的调度与只处理技术错误的重试/续跑规则，明确哪些是新调用、哪些旧Episode保持失败记录；不能回填本轮结果成完整无中断配对。本次不自动进行。

## 交付与保护

- [PROTOCOL.md](PROTOCOL.md)：调用前协议和预算。
- [EDITOR_REPORT.md](EDITOR_REPORT.md)：真实Skill变换。
- [REPLAY_REPORT.md](REPLAY_REPORT.md)：全部12个预注册位置的完整/中断/未启动状态及配对证据。
- [BEHAVIOR_COMPARISON.md](BEHAVIOR_COMPARISON.md)：更新、Skill和行为三层对应。
- [NEW_TRAIN_CASES.md](NEW_TRAIN_CASES.md)：两批固定Train身份、排重边界及未来预算草案。
- inputs、editors、episodes、analysis.json、freeze.json、new_train_cases.json保留真实输入输出和配置；baseline.json/git_before.diff与最终protection.json记录保护检查。

正式源码/Prompt及既有实验归档未修改，用户原有未提交修改保留，不提交或清理。只新增本实验目录；完成文档后停止。

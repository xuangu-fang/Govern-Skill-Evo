# V23.3 P1-R 决策

2026-10-20。**P1-R 完成，停止；未进入 P2。** 完成三例人工多行表示、原函数兼容测试和五份 P1 文档的小范围修订；正式源码、Prompt、Schema、编译器及 V23/V23.2 档案不变。

## 七项结论

1. **多行能改善可操作粒度吗？** 能。三例均可只修改一行或指定关联行，其他行逐字节保留；R05 调度修改不需要重写覆盖、开容器和不替代要求。但效果是表示/操作能力，尚未证明模型会减少附带承诺。
2. **需要新正式字段吗？** 不需要。仍为 `id/text/basis`，text 为多行字符串；不加 requirement ID、role、operation、锚点或依赖图。
3. **Editor Patch 能直接复用吗？** 能。原 Unified Diff 应用器、compiler、Editor 纯输入接口通过本轮验证；没有开发新引擎。
4. **Diagnosis 怎样调整？** 未来本版直接生成按独立行为要求分行的 text，触发条件与动作在同一行，保留作用域、顺序及必要关联。此次不改任何正式 Prompt、不调用 Diagnosis；旧单行档案不自动拆分。
5. **历史响应怎样映射到行？** 先据真实编辑、正反响应与适用条件决定目标要求及变换，再检查必要配套并定位对应原行；reason 解释关联，多个 Hunk/Adjustment 落实。新要求须有自己的问题动机，不能先重写全文再补 Patch 理由。
6. **P2 能沿用最小方案吗？** 能。原 ID + Update Patch → 原 `id/text` Adjustment → 原 compiler 的方案不变。增加本版 Diagnosis 输出组织说明及匹配的消息/归档加载边界；仍需正式转换、归档重载和薄 Editor 入口测试，不增加拆句器。
7. **什么仍待验证？** 自然生成的粒度/完整性、历史响应是否改变实际决策、无据附带承诺是否减少、Goal 冲突处理和真实行为收益。119 项结构/纯交接测试不能替代模型与 Replay 证据。

**进入 P2 的设计与纯函数兼容前提已满足。** 这不表示 P2 完成或模型/环境实验已获授权；本次停止，不自动实现 P2。未来数据清单和行为实验协议按原验证计划另行冻结。

## 交付

- [表示规范](P1R_UPDATE_REPRESENTATION.md)
- [兼容报告与 119 项测试](P1R_PATCH_COMPATIBILITY.md)
- [R04/R05/R06 走查](P1R_CASE_WALKTHROUGH.md)
- [来源索引](fixtures/sources.json)：三份原始 JSON 的精确副本、三份人工表示及 18 份人工 Patch 方案；不复制轨迹或 Memory 全文。
- [设计修订 Git Diff](results/p1r_design.diff)：仅五份 P1 文档。因为初始 P0/P1 文件尚未 Git 跟踪，保留五份 [before 文档](before/P0_P1_DECISION.md)，用 `git diff --no-index` 记录真实本轮差异；没有提交、暂存或改写 Git 历史。
- [检查结果](results/final_checks.json)：来源相等、路径/文件范围、文档链接与空白检查。

修改的 P1 文档为 Method Design、Preconditioning Algorithm、Patch Integration、Validation Plan、P0_P1 Decision。P0 基线和初始审计报告保留为历史记录；初始 99 项测试与本轮 119 项测试不相加冒充不同算法成绩。

## 仍然明确的限制

- 人工表示是阅读原文后组织，不是自动无损转换；补足作用域和展开连接词的编辑由走查说明，语义等价不由测试证明。
- R05 单行修改示例刻意保留其他旧问题，不能声称已得到完整合理策略；类别一次出口没有由程序自动加入，但主动写入仍会被结构接受。
- R06 修改 Update 不会取消 Goal 中 `numbered receptacle names` 或 `at the open appliance`；兼容测试通过不是 Goal 问题解决。
- 旧单行输入仍按整行粒度工作；不会自动迁移为多行。
- 原有 `docs/04_EXPERIMENT_LOG.md` 的 16 行删除与 EOF 空行告警保持；不为本轮清理其他工作。

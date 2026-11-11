# V24 ALFWorld 候选基线

正式训练已完成六轮，R04 候选成为最终 Skill，首测成功 121/134。[训练与 Test](../../../experiments/methods/v24/alfworld_history_and_plan_v3_20261027_001/README.md) · [实验与候选材料总导航](../../../experiments/methods/v24/README.md)

工作区已更新 Preconditioner 的历史经验与计划审查定位，见 [职责与引用边界](PRECONDITIONER_ROLE.md)。
下述 rc1 候选及真实验证记录保留旧冻结版本；不代表更新后 Prompt 的效果。

当前候选：`v24_alfworld_verified_feedback_001_rc1`。
以 `v23_5/alfworld_verified_feedback_001` 的最终运行配置为来源，
保留自进化方法和 ALFWorld 行为，采用简化的运行记录。

- [实现与使用说明](../../../src/skill_evolution/v24/README.md)
- [候选材料与日志现址](../../../experiments/methods/v24/candidates/README.md)
- [离线验收](VALIDATION.md)
- [依赖与覆盖审查](REVIEW.md)
- [后续真实验证与效果对照方案](NEXT_EXPERIMENTS.md)

固定条件：57 个 train＋val 优化任务，六批 10/10/10/10/10/7；
134 个 Test 任务不参与优化。Actor 最多 50 步、每步六次总尝试；
方法模块也各为六次总尝试。Verifier、Repair、Preconditioner、Replay 的
输出额度为 32,768，其余沿用 16,384。

离线验收和第一批任务的单轮真实验证均已完成，此处记录 RC1 阶段。
记录格式兼容性保留为 v25 迁移注意事项，
不作为 v24 缺陷或验收阻塞项。

## RC1 小规模真实验证

原第一批 10 个任务的一轮验证已完成：Parent 与 Candidate 均 10/10 成功，
Gate 为 RETAIN，2 条 Memory 已发布。该单轮 smoke 到此结束。
见 [真实验证报告](../../../experiments/methods/v24/alfworld_rc1_smoke_001/reports/REPORT.md)及[配置、Skill 与发布证据](../../../experiments/methods/v24/alfworld_rc1_smoke_001/README.md)。

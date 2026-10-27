# V24 ALFWorld 候选基线

当前候选：`v24_alfworld_verified_feedback_001_rc1`。
以 `v23_5/alfworld_verified_feedback_001` 的最终运行配置为来源，
保留自进化方法和 ALFWorld 行为，采用简化的运行记录。

- [实现与使用说明](../../../src/skill_evolution/v24/README.md)
- [候选材料](../../../experiments/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/README.md)
- [离线验收](VALIDATION.md)
- [依赖与覆盖审查](REVIEW.md)
- [后续真实验证与效果对照方案](NEXT_EXPERIMENTS.md)

固定条件：57 个 train＋val 优化任务，六批 10/10/10/10/10/7；
134 个 Test 任务不参与优化。Actor 最多 50 步、每步六次总尝试；
方法模块也各为六次总尝试。Verifier、Repair、Preconditioner、Replay 的
输出额度为 32,768，其余沿用 16,384。

当前仅完成离线工作，没有真实模型实验。记录格式兼容性保留为 v25 迁移注意事项，
不作为 v24 缺陷或验收阻塞项。

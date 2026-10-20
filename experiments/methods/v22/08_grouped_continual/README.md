# V22 08：共同决策结构下的两轮持续更新协议

日期：2026-10-15。原方法协议：`v22.grouped_continual.v2`。08 两轮均为7/10→8/10、Gate ACCEPT，第二轮已通过独立Memory恢复完成Skill／Memory共同发布。恢复前声明输出上限65536，保留原输入，仅新增一次Pro调用、零环境执行；Memory由3条更新为5条。第二轮Replay实测并行峰值8。两轮链路已完成，但包含明确恢复，历史预条件化的独立收益仍未证明；一项复合限制的退役范围边界见恢复报告。原档案和三次恢复分别保留；后续默认计划为v3／8并行。

- [最新Memory恢复报告](reports/MEMORY_RECOVERY_REPORT.md)、[恢复结果](results/memory_recovery_summary.json)、[发布核验](results/memory_recovery_verification.json)、[独立声明](config/memory_recovery_r2.json)。第二轮已共同发布，原失败及其费用全部保留。
- [真实报告](reports/REPORT.md)、[结构化结果](results/summary.json)、[档案核验](results/verification.json)。
- [历史Fusion续行报告](reports/FUSION_RESUME_REPORT.md)、[续行结果](results/fusion_resume_summary.json)、[续行核验](results/fusion_resume_verification.json)、[单次续行配置](config/fusion_resume_r2.json)。该档案停在Memory截断处；其历史状态不改写，最终发布见最新Memory恢复报告。
- [分类恢复报告](reports/RECOVERY_REPORT.md)、[恢复结果](results/recovery_summary.json)、[恢复核验](results/recovery_verification.json)、[预声明恢复配置](config/recovery_r2.json)。原始失败档案保留；没有重跑R1或R2 Parent。
- [后续默认8并行计划](config/plan_parallel8.json)与[调度说明](../../../../docs/methods/v22/PARALLEL_SCHEDULING.md)。原v2配置和已完成轨迹不改写、不重跑。
- [运行器与命令说明](../../../../docs/methods/v22/CONTINUAL_RUNNER.md)：preflight／run／verify，来源冻结和异常停点。
- [完整算法与两轮协议](../../../../docs/methods/v22/GROUPED_TWO_ROUND_PROTOCOL.md)
- [预声明配置](config/plan.json)：两轮任务、模型与预算、整体成功率 Gate 和停止边界。
- [固定分类 Prompt](config/grouping_prompt.md)：一次全局分类，不进行语义或格式重试。
- [任务与选题来源](config/task_manifest.json)：20 个不同 Train，轮间不重复；旧结果只用于选题，不进入本次学习状态。

本次从 No Skill／空 Memory 开始，每轮生成至多一份统一 Candidate，不设置 Direct 分支。两轮最多 40 个 episode、2,000 个 Actor 请求和 9 次 Pro 调用。第一轮采用预声明的程序恒等 Fusion；第二轮消费实际形成的 Memory，允许 Keep 或无适用认识。

先 Replay，再程序 Gate，再进行一次行为解释／Memory 后处理；完成后统一发布下一轮 Skill 与 Memory。完整配对上 Candidate 整体成功率严格高于 Parent 即 ACCEPT，否则 RETAIN；局部收益与退化均由 Memory 学习，不设置零退化否决。轮内使用相同任务配对修改前后的行为；轮间严格流式，不重复 Train，也不另设回归验证批次。没有新的 Selection／Test，不按结果换题、补题或返工候选。

累计40个episode、889次Actor请求、12次Pro、2,463,283已报告tokens，另有5次HTTP尝试用量未知。全部旧失败及三次恢复计入；复用调用不重复计费。当前正式状态为R2，见[Skill／Memory状态](../../../../artifacts/methods/v22/08_grouped_continual_memory_recovered_20261015/state.json)。历史Memory已作为Fusion输入，实际两项要求发生替换，但变更依据未正式引用Effect，尚不能证明历史的独立作用。

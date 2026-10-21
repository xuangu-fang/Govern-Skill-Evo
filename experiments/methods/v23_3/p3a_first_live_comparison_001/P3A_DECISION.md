# P3-A 最终决策

**已按授权预算完成本轮真实调用尝试并归档；主研究对照未完成，因为 A/B 均未收到模型响应。** 成功取得唯一真实多行 Diagnosis，未替换为 Mock、未择优、未修改 Prompt。现在停止。

## 十项回答

1. **是否得到真实合法多行 Original？** 是。一次真实 Diagnosis 返回 revise，u1/u2/u3 分别 3/3/2 行，原 Schema 和人工可比性门通过。Goal 未锁定搜索实现；Original 自身问题仍原样保留。
2. **是否完成有效 A/B 对照？** 否。共同输入已冻结并核验相同，两组各 3 次 HTTP 均连接中断超时，没有实际 Effective Plan。
3. **Patch 是否准确作用于目标要求？** 无法判断。没有收到 B Patch；不能把传输失败归为 Patch 定位失败，也不能用 P2 Mock 替代真实结果。
4. **是否减少无依据附带承诺？** 无法判断。A/B 都没有可观察更新，不能将未知承诺数写成零。
5. **是否保留具体策略探索？** 无法判断。Original 包含具体跨类搜索提案，但不是本轮 Preconditioner 变换或比较结果。
6. **两组是否真正利用历史编辑—响应？** 只能确认实际请求都含相同 M1/M2/M3/M6/M7/M8/M9 与 sources，不能确认模型在决定中利用了它们。
7. **哪些变化由当前证据支持，哪些有历史增量线索？** Original 的替代物约束由 P7 knife/butterknife 错配支持，候选命令规则由 P6:20/21、P8:5/6 支持。M6 能提供扩展收益与同类实例遗漏的混合历史线索，M8 能提供替代物约束的历史线索；但没有实际 A/B 变换，不能宣称这些线索产生了增量。
8. **哪些问题未解决？** 大体积共同请求的传输故障；真实 Patch 格式遵循率、目标定位、条件范围、附带承诺、探索质量、历史使用及行为收益均未获得本轮对照证据。Original 的全局访问状态假设也未被实际 Preconditioner 检验。
9. **是否值得立即开展小规模 Candidate Replay？** 当前不宜：尚无本轮实际 Effective A/B 或 Candidate。先取得有效真实构造对照，再判断候选和 Replay 设计；本次不执行 Editor/Replay。
10. **下一阶段优先做什么？** 另行授权后先定位大请求传输超时，在新实验中冻结必要传输配置；优先复用本轮唯一真实 Original、相同事实和 Memory，保持两组参数一致，重新完成有限 A/B。此时没有证据支持先修改算法 Prompt。新的调用不能追记为本轮未用额度。

## 核心研究问题的直接回答

**本轮无法判断 V23.3 Patch 是否比 V23 自由替换更准确、附带承诺更少且保留有意义探索。**

- 多行 Original 的真实生成已经观察到；实际更新粒度改善尚未观察到。
- 历史材料进入相同请求已经核验；历史对修改决定的实际参与尚未观察到。
- 策略构造质量没有可比较输出，无法判断，更不能推断 ALFWorld 成功率提高。

## 预算与停止

3 次逻辑调用、7 次 HTTP 请求，包含 4 次预注册技术重试；无语义重采样。Diagnosis 1 次成功；A/B 各 3 次耗尽自身额度。理论上限 9 次不允许把 Diagnosis 未用重试额度转给其他阶段。

已返回用量只有 Diagnosis 的 74,408 total tokens（65,593 input、8,815 output，其中 7,951 reasoning 已含在 output）。其余六次请求的 usage 与货币费用未知。

Editor、Actor、ALFWorld、Replay、Gate、Memory 更新、完整自进化和最终 Test 调用均为 0。只新增本实验入口和归档；没有提交、暂存、重置、修改正式版本或 P0—P2。见 [保护检查](results/final_checks.json)。

交付：[预注册协议](P3A_EXPERIMENT_PROTOCOL.md)、[Diagnosis 报告](P3A_DIAGNOSIS_REPORT.md)、[执行报告](P3A_EXECUTION_REPORT.md)、[对照与缺失观测](P3A_UPDATE_COMPARISON.md)、[全部请求汇总](results/execution_summary.json)、[新增文件 Git Diff](results/experiment.diff)。

# P3-B最终报告（纳入合法A*）

**修订说明：本报告以合法的新格式A（记作A*）与原B作描述性对照。A*修改过输出格式Prompt，故不满足原P3-A的同Prompt控制条件；不是严格的Memory单变量验证。旧报告及执行记录已保留。**


**报告与描述性对照已补齐：A*完整Keep；B替换u1、Keep u2。两者u1确有实质差异，但目前不能认定历史Memory产生了更合理、可归因的更新增量。**

| 必答问题 | 修订结论 |
|---|---|
| 1. A最终如何调整？ | 新格式A*为ready、adjustments=[]，u1/u2全文及Goal/Checks均保持Original。原同Prompt A仍没有合法输出 |
| 2. B如何调整？ | u1改为跨类型breadth-first采样及明确近期去重；u2保持；Goal/Checks保持 |
| 3. Effective是否实质不同？ | 是，u1的同类穷尽/换类/返回余项/终止条件不同；u2、Goal、Checks相同 |
| 4. 哪些纠正当前证据已足够？ | 对全局visited/穷尽前提提出质疑、减少无信息重复、限定状态变化后的重试、保留精确对象和处理交付。A*未纠正不表示这些证据不存在 |
| 5. 是否观察到历史响应相关变换？ | B显式联系M6/M3旧编辑的混合响应并改变u1，是实际证据使用线索；但Prompt不同，不能将A*/B差异归因于Memory |
| 6. B是否新增无据承诺？ | 是，其他类型采样后才回同类余项，以及types或locations一次的结束边界支持不足；全局进度依赖仍在 |
| 7. 是否支持合理增量机制通过？ | 不通过此项结论：既有控制条件偏离，也有替代构造不足。不能据此宣布Memory有效或无用 |
| 8. 哪些是单次线索？ | A*接受原案的理由、B历史反馈与方向变换联系、双方最终边界问题；不证明稳定优劣或Actor行为结果 |
| 9. 后续优先什么？ | 优先同Prompt、预注册的配对/重复验证及非空Adjustment格式可靠性；不直接进入行为Replay或语义Prompt补丁搜索。本次不执行 |

A* reason把编号/换类启发式视为两步历史下可执行，但最终全局uninspected/穷尽要求未得到充分解释。B更明确局部近期去重，也改变方向，却新增：

> Return to remaining numbers in a series only after other plausible types or locations have been sampled.

> Continue until the exact target is found or all plausible candidate types or locations have been inspected once.

这些不能仅凭改善覆盖的动机充分成立；潜在副作用尚未经过Actor执行，不声称已经导致退化。双方u2均未明确状态变化后的重试边界。合理Keep和探索均允许，本结论不以Adjustment数量判胜负。

## 状态与交付

- 有效输出材料：已齐（A*新格式、B原Prompt）。描述性比较：已完成。**原P3-A严格Memory单变量验收：未满足，Prompt不一致。**
- A*成功为43.584秒、65,026 Token；旧B57.498秒、480,027 Token。全程累计7次HTTP，已知830,656 Token，首次A超时消耗未知；本次报告修订新增模型调用/Token/环境执行均0。
- 四次原Prompt A完整响应均契约失败，另有一次超时；原始记录保留。A*为空adjustments，所以不能把本次格式通过当作非空to层级问题已解决。
- 原四份报告和评价JSON先备份，本次只修改这些报告/评价及新增修订归档；原请求、响应、Prompt、Memory、方法、Campaign和Test不变。

[执行与全部成本](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_EXECUTION_REPORT.md)；[全文与逐项对照](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_UPDATE_COMPARISON.md)；[历史增量归因](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_MEMORY_ATTRIBUTION.md)；[来源与哈希](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/report_revisions/001_A_format_integration/results/selected_sources.json)；[本次保护核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/report_revisions/001_A_format_integration/results/protection.json)；[旧版结论](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/report_revisions/001_A_format_integration/before/reports/P3B_DECISION.md)。

已停止，不新增模型请求、不进入Editor、Candidate Replay或后续实现。

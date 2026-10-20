# P3-B 阶段结论

**本次未完成有效A/B输出对照：A在300秒读取超时，B在57.498秒返回合法ready。两次调用预算已用完，没有重试或第三组。**

对于“加入Memory是否产生不同且更有依据的Effective Update”，答案是：**目前无法判断相对无Memory的增量。**B确实相对固定Original改变u1，但不能用Original代替缺失A。

| 必答问题 | 结论 |
|---|---|
| 1. A如何调整u1/u2？ | 无有效响应，未知；不是Keep或合法no_change |
| 2. B如何调整？ | u1由同类编号穷尽改成跨类型breadth-first采样/近期去重；u2保持原样。Goal/Checks不变 |
| 3. 两组是否有实质不同Effective？ | 无法比较，A不存在Effective。只确认Original→B的实质变化 |
| 4. 哪些纠正当前证据足够支持？ | 近期反循环、质疑全局visited、限定无效重复的状态前提、保留精确目标及处理交付；其中u2的范围问题B仍未修正 |
| 5. 是否观察到额外历史响应变换？ | B显式把M6/M3的旧搜索提示未稳定兑现与重构u1相联系，M8用于保留精确对象；但没有A，不能称为已观察到AB历史增量 |
| 6. B是否引入无据承诺？ | 是：其他类型采样后才返回同类余项的排他条件、types或locations一次的结束边界支持不足；还残留unvisited/sampled全局进度依赖。few不是固定数值批次；跨类型探索本身仍可合理 |
| 7. 是否支持机制产生合理增量？ | 不足。B有部分历史认识到方向变换的显式链条，但附带构造问题未消除，且比较臂缺失。不能判机制有效，也不能据此判Memory永远无用 |
| 8. 哪些仅单次线索？ | B对历史混合反馈的解释与策略选择、近期约束的局部落实、反复出现的全局条件与结束风险；不是模型内部因果机制或行为退化证明 |
| 9. 后续优先什么？ | 先经独立授权补齐A技术失败，再按原规则完成对照；之后若出现合理增量，优先预注册重复验证稳定性，再考虑定向消融。当前不优先Editor/行为Replay或新Prompt迭代 |

B的最关键文本：

> Return to remaining numbers in a series only after other plausible types or locations have been sampled.

> Continue until the exact target is found or all plausible candidate types or locations have been inspected once.

这两项不能仅凭“扩大覆盖”的动机获得充分支持；M6同类别位置遗漏尤其不能自动证明应等待其他类型全部采样。文本风险尚未经过Actor执行，不称为已发生过早停止或退化。

u2虽被reason称为executable，最终仍保留无效后不重复等价动作及立即state-changing，未明确条件变化后的重试/有效信息获取。不能把解释合理等同于问题已纠正。

## 用量、保护与交付

- A一次HTTP尝试，ReadTimeout 300.341秒；没有响应，Token和账单未知。B一次HTTP尝试，57.498秒，返回deepseek-v4.1-flash，finish_reason=stop。
- B实测输入474,757、输出5,270（其中reasoning 4,751）、总计480,027 Token；cached字段未提供。reasoning不重复累计。实验总Token因A未知而未知，未推算货币费用。
- 请求正文及字节哈希等于P3-A；唯一变量仍是历史Memory。完整记录、原响应与确定性编译见 [执行报告](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_EXECUTION_REPORT.md)。
- [独立评价与全文对照](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_UPDATE_COMPARISON.md)；[历史响应归因与限制](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_MEMORY_ATTRIBUTION.md)；[保护核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/results/protection.json)。
- 仅新增p3b_results脚本和产物，旧P3-A冻结、V23/V23.2方法、Memory、Campaign和Test未修改。Editor/Actor/Replay/Gate/Memory/Diagnosis/环境调用均0。

已停止。没有自行重试A、没有第三次模型调用，没有进入P3-C、Editor或Candidate Replay。

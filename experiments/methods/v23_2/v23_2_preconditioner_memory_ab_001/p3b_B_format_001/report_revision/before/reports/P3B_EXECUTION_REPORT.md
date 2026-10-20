# P3-B执行报告（纳入合法A*的修订版）

**修订说明：本报告以合法的新格式A（记作A*）与原B作描述性对照。A*修改过输出格式Prompt，故不满足原P3-A的同Prompt控制条件；不是严格的Memory单变量验证。旧报告及执行记录已保留。**


## 1. 本次修订使用什么

- A*：[format_001合法输出](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/preconditioner.json)；[Effective A*](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/effective_plan.json)。ready、adjustments=[]、checks=null，完整Keep Original。
- B：[首次原B合法输出](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/preconditioner.json)；[Effective B](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/effective_plan.json)。ready、1条u1替换、checks=null，u2 Keep。
- Original Plan仍是P1-B用户授权R05重试后的合法Diagnosis，[冻结Plan](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/original_plan.json)。未换成正式V23旧Plan、P1输出或手工Plan。
- 本次只修订报告/评价归档，新增模型调用、Token与环境执行均0。
- 原报告逐字节备份在[修订前执行报告](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/report_revisions/001_A_format_integration/before/reports/P3B_EXECUTION_REPORT.md)；原runs/A仍表示首次超时，**未用A*覆盖它**。results/summary.json、旧execution_receipt和旧protection均保留为初次执行收据，当前选择见[修订来源索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/report_revisions/001_A_format_integration/results/selected_sources.json)。

## 2. 控制条件与偏离

| 条件 | 原冻结A/B | 本报告A*/B |
|---|---|---|
| Parent / Original Plan / Grouping / command_sets | 相同 | 相同 |
| 当前完整轨迹 | P1、P3、P6、P7、P8、P10 | 完全相同，未增加P2/P4/P5/P9 |
| Actor背景 | 原V23 | 相同 |
| Memory | A空；B真实R05七条及sources | 同左，无M10 |
| system Prompt | 完全相同 | **不同：仅A*增加输出字段及引用格式说明** |
| 模型/temperature/Thinking/推理/预算 | 相同 | 相同 |
| Schema /编译器 | 原V23 | 不变，均合法编译 |

A*增加一段：basis/reason放在Adjustment外层、to仅含id/text、不复制输入basis或占位字段、外层依据/理由非空、当前引用逗号分隔。见[精确Diff](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/config/prompt.diff)与[调用前冻结](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/config/freeze.json)。虽只改格式说明，也可能影响输出选择，不能假定语义影响为零。

两份合法输出可比较实际行为要求，但“有Memory→差异”的归因受到Prompt变化、非对称技术重试、时点、上下文长度/缓存与随机性限制。原同Prompt条件下A经历超时与四次无效响应，仍无合法Effective A。

## 3. 全部尝试与成本

deepseek-v4.1-flash，temperature=1，Thinking enabled，reasoning_effort=medium，stream=false，max_tokens=16384，timeout=300秒；每次1个HTTP、0自动重试。内部路由名称已由用户确认。两份合法输出response_model均相同、finish_reason=stop。

| 尝试（实际顺序） | 状态 | 输入 | 输出 | 其中reasoning | 缓存输入 | 总Token | 秒 |
|---|---|---:|---:|---:|---:|---:|---:|
| A initial | ReadTimeout，无响应 | 未知 | 未知 | 未知 | 未提供 | 未知 | 300.341 |
| B original | 合法ready | 474757 | 5270 | 4751 | 未提供 | 480027 | 57.498 |
| A retry_001 | Adjustment: unexpected fields | 60011 | 10345 | 9629 | 未提供 | 70356 | 55.793 |
| A retry_002 | Replacement Update: unexpected fields | 60011 | 11268 | 10409 | 59392 | 71279 | 60.692 |
| A retry_003 | Adjustment: unexpected fields | 60011 | 14391 | 13587 | 未提供 | 74402 | 76.481 |
| A retry_004 | reason: unavailable historical reference | 60011 | 9555 | 8439 | 59392 | 69566 | 47.625 |
| A* format_001 | 合法ready | 60133 | 4893 | 4574 | 0 | 65026 | 43.584 |

累计7次HTTP；已知输入774,934、输出55,722、总830,656 Token。首次A超时服务器消耗未知，完整实验总量仍未知。两份合法输出A*+B合计545,053 Token，不包含失败尝试。reasoning属于输出子集、缓存属于输入子集，不重复加总；没有可靠货币费用。

retry_004的首个历史引用错误来自reason的P3/P6等简写被正则匹配为历史路径；不是已证实的历史事实捏造。它同时有空外层basis/reason及to字段越界，仍无效。所有失败均保留，未人工修补或当作有效结果。部分旧异常处理器的usage.json将finish_reason记null，原HTTP/response.json为stop；累计表以原响应为准。

A*本次空adjustments没有生成to对象，所以格式通过不等于已证明非空替代对象的字段错位问题修复。

## 4. 核验与保护

原P3-A冻结、A*冻结哈希均核对；选用请求仅system和Memory两类内容不同，其他输入/参数一致；两份结果由原编译器离线重编译一致。A* Effective完整等于Original；B Goal/Checks/u2等于Original，u1与Adjustment.to.text相同。B Effective basis保留Original来源谱系，而M6/M3/M8见Adjustment.basis，这是既有编译规则。

本次只更新四份P3B报告及evaluation_filled.json，另存修订备份、来源索引、完整用量账本和保护核验。所有原始模型请求/响应、Prompt、Memory、方法、Campaign、Test不变。[本次保护结果](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/report_revisions/001_A_format_integration/results/protection.json)；[全部尝试账本](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/report_revisions/001_A_format_integration/results/cumulative_ledger.json)。

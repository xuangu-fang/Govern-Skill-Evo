# P3-B执行报告：同格式Prompt对照完成

**本版主对照改为：合法A_format_001（无Memory）与新B_format_001（真实R05 Memory）。两组完整system Prompt逐字相同，其他请求字段除Memory外完全一致。原B和失败尝试仅作历史记录，不与新B混用。**


## 1. 结果来源与协议修订

A使用[已保存合法A](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/preconditioner.json)，未重新调用；B使用[本次新B](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/runs/B/preconditioner.json)。A ready、adjustments=[]；B ready、一条u1替换；均通过原解析器与编译器，checks=null。

双方使用用户批准保留的同一格式修复，只明确字段归属、非空依据/解释和引用分隔，没有新增策略性要求。[共同Prompt](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/config/preconditioner_prompt.md)与[相对原版Diff](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/config/prompt.diff)逐字等于A格式版。本次没有再编辑Prompt。

这恢复了**当前配对的同Prompt、唯一Memory输入变量**。它是经用户授权的P3-A格式协议修订，不声称原冻结Prompt逐字未变。旧P3-A、原B、各次失败和此前异Prompt报告均保留；旧同Prompt原A仍没有合法输出，但已不作为本版主比较臂。

## 2. 实际控制条件

| 项目 | 核验 |
|---|---|
| system Prompt | 逐字相同，SHA-256 `6c22274c4e9c6682c917f8ce56c17d1c0f6c6a05a573900ecea0111272a3be8f` |
| Original Plan | 同一P1-B R05授权重试合法Diagnosis，Goal、Updates、basis、Checks、顺序相同 |
| Parent / Grouping / command_sets | 完全一致，G1—G4与既有候选不变 |
| 完整当前执行 | P1、P3、P6、P7、P8、P10，两组相同；未增加P2/P4/P5/P9 |
| Actor背景 | 原V23当前观察/候选、最近两组历史、步数限制不变 |
| Memory | A空entries/sources；B为M1/M2/M3/M6/M7/M8/M9及全部冻结sources，无M10 |
| 模型/参数 | 同deepseek-v4.1-flash、temperature=1、Thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、timeout=300秒 |
| Schema/编译 | 原实现不变，均合法ready、HTTP200、finish_reason=stop；返回模型相同 |

[机器核验及请求哈希](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/results/selected_sources.json)。分别删除用户输入memory后，完整请求（含system、参数、端点、timeout）相等；不是仅比较Prompt文件名。

## 3. 调用与全部成本

本次只新增B一次HTTP，自动重试0，耗时90.796秒，输入474,839、输出16,098（其中reasoning 15,426），总490,937 Token，缓存输入1,024。完成原因stop且JSON完整，不以接近预算误判截断。

所选A耗时43.584秒，总65,026 Token。当前合法配对共555,963 Token（输入534,972、输出20,991）。

| 尝试（实际顺序） | 状态 | 输入 | 输出 | 其中reasoning | 缓存输入 | 总Token | 秒 |
|---|---|---:|---:|---:|---:|---:|---:|
| A initial | ReadTimeout，无响应 | 未知 | 未知 | 未知 | 未提供 | 未知 | 300.341 |
| B original prompt | 合法ready | 474757 | 5270 | 4751 | 未提供 | 480027 | 57.498 |
| A original retry_001 | Adjustment: unexpected fields | 60011 | 10345 | 9629 | 未提供 | 70356 | 55.793 |
| A original retry_002 | Replacement Update: unexpected fields | 60011 | 11268 | 10409 | 59392 | 71279 | 60.692 |
| A original retry_003 | Adjustment: unexpected fields | 60011 | 14391 | 13587 | 未提供 | 74402 | 76.481 |
| A original retry_004 | reason: unavailable historical reference | 60011 | 9555 | 8439 | 59392 | 69566 | 47.625 |
| A format (selected) | 合法ready | 60133 | 4893 | 4574 | 0 | 65026 | 43.584 |
| A original retry_005 | reason: unavailable historical reference | 60011 | 8424 | 8121 | 未提供 | 68435 | 42.957 |
| B format (selected) | 合法ready | 474839 | 16098 | 15426 | 1024 | 490937 | 90.796 |

全研究累计9次HTTP，已返回usage合计1,390,028 Token；首次A超时服务器消耗未知，所以总体消耗仍未知。reasoning/缓存分别属于输出/输入子集，不重复加总。未提供可靠货币费用，不推算账单。[完整账本](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/results/cumulative_ledger.json)。

retry_004/005的首个历史引用拒绝涉及斜杠当前轨迹被正则识别为历史路径，不视为已证实的Memory捏造。retry_004还独立有层级/空字段错误；retry_005为空adjustments。无效输出均未人工修补或纳入有效语义对照。原异常处理usage元数据的null finish_reason以原HTTP/response中的stop校正汇总，不改原文件。

## 4. 验证、归档和边界

B非空to条目本次只有id/text，外层basis/reason有效，提供一次非空Adjustment遵守契约的实际样本；不能证明格式修复已稳定解决生成问题。原编译器重复编译A/B一致；A Effective等于Original，B仅u1文本变化，Goal/u2/Checks保持。B Effective的basis保留Original谱系，历史引用在Adjustment.basis中，这是原编译规则。

[调用前冻结](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/config/freeze.json)；[完整B请求](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/runs/B/request.json)；[原HTTP](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/runs/B/http_response.txt)；[B原文](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/runs/B/raw_output.txt)；[B Effective](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/runs/B/effective_plan.json)；[A Effective](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/effective_plan.json)。

两份有效样本不是重复实验：A来自先前格式修复尝试，B为本次单次结果，调用时点、输入长度/缓存及前期非对称技术失败限制因果推广。没有因语义结果选优或追加调用。Editor/Actor/Replay/Gate/Memory更新及环境执行均0。

仅新增本次B归档并更新四份主报告与评价JSON。[上一版报告备份](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/report_revision/before/reports/P3B_EXECUTION_REPORT.md)；[保护核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/results/protection.json)。原请求/响应、历史Prompt、Memory、方法、Campaign和Test保持。

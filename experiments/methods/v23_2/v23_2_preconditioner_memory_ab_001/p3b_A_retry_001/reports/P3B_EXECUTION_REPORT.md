# A组授权重试执行记录

**重试已执行一次，但A仍没有合法Effective Plan。本次是Schema失败，不是再次超时或输出截断。**

- 请求完全复用P3-A A组；SHA-256 `d6d60e11d20ffefc590316a3b3fce25e9a4e4183e0fcf06f82b84198eb10bd2a`。冻结清单、来源哈希、两组仅Memory不同、R05七条Active Memory已通过原preflight核对。
- 模型deepseek-v4.1-flash；temperature=1，Thinking enabled，reasoning_effort=medium，stream=false，max_tokens=16384；连接10秒/读取300秒。没有参数变化或容量探测。
- HTTP 200，response_model=deepseek-v4.1-flash，finish_reason=stop。耗时55.793秒；一次HTTP，自动重试0。JSON解析成功，原编译器拒绝：`Adjustment: unexpected fields`。
- Adjustment必须含from/to/basis/reason；实际在Adjustment层缺basis/reason，却新增basis_note/reason_placeholder；basis/reason错放在to[0]，而to条目只允许id/text。
- 未移动字段、未删除非法字段、未人工编译“修正版”，没有effective_plan.json。不是合法no_change/need_evidence，也不是合法Keep。

## 用量

| 尝试 | 状态 | 输入Token | 输出Token | 其中reasoning | 总Token | 秒 |
|---|---|---:|---:|---:|---:|---:|
| 原A | ReadTimeout | 未知 | 未知 | 未知 | 未知 | 300.341 |
| 原B（复用） | 合法ready | 474757 | 5270 | 4751 | 480027 | 57.498 |
| 本次A | Schema拒绝 | 60011 | 10345 | 9629 | 70356 | 55.793 |

本次新增70,356 Token。已返回usage的两次合计550,383 Token（输入534,768；输出15,615），**包含原A超时的实验累计总量仍未知**。reasoning包含在输出中，不重复累计；缓存用量和货币费用未提供，不推算。

原包装器异常分支将usage.json的finish_reason写为null，原始HTTP和response.json均保存stop。本次不覆盖该文件，另存[核验后的用量与来源](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_001/results/usage_verified.json)，以原响应为准。

实际顺序为A超时→B合法→A授权重试，不能描述成有效A先于B；若以后取得有效对照，也需保留顺序、时点、随机性和输入长度差异的归因边界。

## 原始产物

[实际完整请求](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_001/runs/A/request.json)；[原始HTTP响应](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_001/runs/A/http_response.txt)；[输出原文](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_001/runs/A/raw_output.txt)；[解析JSON（无效契约）](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_001/runs/A/parsed.json)；[错误](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_001/runs/A/error.json)；[字段差异](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_001/results/schema_diagnostic.json)；[执行收据](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_001/results/execution_receipt.json)。

B原始结果仍引用[原B Effective Plan](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/effective_plan.json)，未重跑。无Diagnosis、Editor、Actor、Memory、Replay、Gate或环境调用。

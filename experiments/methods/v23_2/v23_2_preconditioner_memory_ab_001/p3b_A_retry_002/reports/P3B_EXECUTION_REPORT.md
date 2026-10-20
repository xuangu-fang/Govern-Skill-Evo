# A组第二次授权重试

**已发送一次；取得完整响应，但原Schema拒绝，未补齐A Effective Plan。**

本次请求SHA-256 `d6d60e11d20ffefc590316a3b3fce25e9a4e4183e0fcf06f82b84198eb10bd2a`，与P3-A逐字节一致。原preflight再次核验冻结清单、来源、B真实Active Memory，以及两组只有Memory差异；B未重跑。

模型deepseek-v4.1-flash；temperature=1，Thinking enabled，reasoning_effort=medium，stream=false，max_tokens=16384，连接10秒、读取300秒。参数和Prompt未变。HTTP200，finish_reason=stop，返回模型deepseek-v4.1-flash，耗时60.692秒。

## 具体失败

原编译器在`$.adjustments[0].to[0]`拒绝：`Replacement Update: unexpected fields`。该条目应只有id/text，实际另含basis/reason。本次Adjustment外层from/to/basis/reason已齐全；与上次同时存在外层非法字段不同。未删除字段、未移动字段、未生成手工修复的Effective Plan。

## 实际用量

| 尝试 | 结果 | 输入 | 输出 | reasoning（含在输出中） | 总Token | 秒 |
|---|---|---:|---:|---:|---:|---:|
| 初始A | ReadTimeout | 未知 | 未知 | 未知 | 未知 | 300.341 |
| 原B | 合法ready | 474757 | 5270 | 4751 | 480027 | 57.498 |
| A retry_001 | Adjustment字段失败 | 60011 | 10345 | 9629 | 70356 | 55.793 |
| A retry_002（本次） | Replacement字段失败 | 60011 | 11268 | 10409 | 71279 | 60.692 |

本次缓存命中输入59,392 Token，属于60,011输入的子集，不另行累计。其他尝试未提供缓存字段，不视为零。已返回usage合计621,662 Token（输入594,779、输出26,883）；初始A超时用量未知，所以实验总消耗仍未知。不推算货币费用。

异常处理器保存的usage.json把finish_reason记为null，原HTTP和response.json实际均为stop；保留原文件，以[核验用量](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_002/results/usage_verified.json)注明来源。未更改模型响应。

[实际请求](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_002/runs/A/request.json)；[原始HTTP响应](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_002/runs/A/http_response.txt)；[原始输出](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_002/runs/A/raw_output.txt)；[解析但契约无效的JSON](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_002/runs/A/parsed.json)；[字段诊断](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_002/results/schema_diagnostic.json)；[执行收据](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_002/results/execution_receipt.json)。

本次新增一次HTTP，零自动重试；累计四次HTTP。真实顺序为A超时→B合法→A两次经授权技术重试，所有尝试均保留。没有对合法输出择优或语义重采样。

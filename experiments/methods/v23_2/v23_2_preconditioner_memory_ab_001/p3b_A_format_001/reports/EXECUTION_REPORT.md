# A组格式补充后的单次验证

**本次获得合法ready输出并由原编译器生成Effective Plan；模型选择Keep全部Original Updates。**没有非空Adjustment，因此尚未验证生成替代Update时能否稳定遵守字段层级。

## 冻结与调用

- 原A/B system内容逐字一致；仅Memory不同，空Memory不会在程序中移除输出格式要求。
- 本次唯一相对原A的变化是system Output Format新增一段。[完整Prompt](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/config/preconditioner_prompt.md)、[精确Diff](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/config/prompt.diff)、[调用前冻结记录](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/config/freeze.json)、[设计边界](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/reports/DESIGN.md)。
- 强调basis/reason属于Adjustment外层、to仅含id/text、不复制输入Update的basis、不添加占位字段、外层basis/reason非空；多个当前引用逗号分隔，不写斜杠合并形式。没有修改Schema、编译器或行为策略规则。
- 冻结时间2026-10-20T08:40:31.857078+00:00；实际开始2026-10-20T08:40:58.505195+00:00，结束2026-10-20T08:41:42.089696+00:00。
- deepseek-v4.1-flash；temperature=1，Thinking enabled，reasoning_effort=medium，stream=false，max_tokens=16384，timeout=300秒；HTTP200，finish_reason=stop，返回模型一致。
- 1次HTTP，自动重试0，耗时43.584秒。没有人工修复或根据结果继续迭代Prompt。

## 结果与消耗

`decision=ready`、`adjustments=[]`、`checks=null`。Effective Plan与冻结Original Plan完全一致，Goal、u1、u2、basis、Checks及顺序未变。

输入60,133、输出4,893（包含reasoning 4,574）、总65,026 Token；API报告缓存输入0。累计7次HTTP，已返回usage合计830,656 Token，首次A超时用量未知，故累计总消耗仍未知。无可靠货币费用，不推算账单。

## 离线验证

实际请求哈希等于本次冻结；去除system变更后与原A完全相同；旧A/B system相同；原编译器重复编译结果一致；B原结果可原样重编译；调用前合法字段fixture通过，非法to.basis fixture被拒绝。fixture是确定性结构测试，不是模型输出。运行后冻结文件未变。

[完整请求](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/request.json)；[原始HTTP](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/http_response.txt)；[模型原文](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/raw_output.txt)；[合法输出](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/preconditioner.json)；[Effective Plan](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/effective_plan.json)；[用量](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/usage.json)；[核验收据](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/results/execution_receipt.json)。

本次A不是原严格Memory单变量实验的有效补臂：system已变，不能把它与旧B作无混杂因果比较。所有旧失败、旧B和P3-A冻结保持原样，正式默认Prompt未改。

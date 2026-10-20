# P3-C2 离线测试报告

**最终129项通过，0项失败；其中52项原型、74项原Preconditioner、3项原Editor纯交接。** socket.connect/connect_ex/create_connection均封锁，网络尝试0；新增模型调用/Token/环境执行均0。输入和策略文本由人工测试夹具提供，不是模型验证。

[最终日志](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/pytest.log)；[129项逐项清单](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/TEST_CASES.md)；[机器结果](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/tests.json)。本次仅重复运行因断言修正或新增覆盖需要的测试，没有扩大到环境或全Campaign。

## 1. 七类验收

| 要求 | 测试和实际结果 |
|---|---|
| 单项定向替换 | R05真实u1一个调度条件被替换，其余两段原文逐字节保持；没有程序自动新增sampled once；正式Adjustment字段正确 |
| 目标与配套 | 两个不相连原锚点，supporting明确依赖target；按原位置合成，索引不当作应用顺序；依赖错误/循环拒绝 |
| 跨Update/下游 | 单改u1时u2/Goal/Checks完全不变；真实归档的Editor纯输入函数接受；多Update显式编辑可同时表达 |
| 大范围编辑 | 人工全文替换且结果更长仍接受；audit明确未选保护区为零；不以修改大小评分 |
| 非法方案 | 不存在/重复/重叠锚、边界插入冲突、未知Update、过期Goal/text/basis/Checks/顺序、非法操作/role/basis/字段、Goal修改、非法正式Adjustment、失效Checks等拒绝 |
| Keep/停点/撤回 | Keep=ready空edits且Effective=Original；need_evidence空edits/nullChecks返回null；整段delete映射to=[]；no_change须全部撤回/Checks=[]；部分撤回不自动修Checks |
| 结构与语义区分 | 人工插入类别级终止条件结构通过；audit将风险原文、插入锚点和Diff暴露；标记semantic_validity=not_evaluated，未伪造语义审核 |

额外覆盖：Unicode/emoji/CRLF/尾空格不归一化；重复JSON键拒绝；后项只匹配原快照；输出重复运行一致；canonical哈希忽略对象键序但保护数组序和全部Plan内容；未来草案渲染无未填占位符，不含R05/M6/S01等人工答案。

## 2. 真实保留映射与风险暴露

[单项audit](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/human_runs/single_replace/audit.json)：原u1前523字节保持，原`[610,1072)`映射到新`[625,1087)`且SHA相同；u2 `[0,514)`完整保留。所有原Update来源和修改映射都可审计。

[风险audit](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/human_runs/semantic_risk/audit.json)中的`replacement_text`由人工加入：

> Stop searching after each receptacle category has been sampled once.

它有锚点/结构合法basis和reason，故程序接受。但其语义合理性并未被程序判断。原compiler同样接受。这个测试刻意防止把字符串边界约束误称为证据充分性证明。

[失败停点](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/human_runs/rejected_missing/receipt.json)只记录anchor_missing，未产生Effective文件；[全部人工演示](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/human_demos.json)记录6次结构编译/合法停点和1次预期拒绝，无模型响应。

## 3. 初始失败与修正

首轮121通过、1失败：无效Checks已被原编译器正确拒绝，测试误预期错误文案`unknown Update`，实际为`check.update_ids: invalid references`。仅修正新测试断言，未修改原compiler或绕过校验。[初始失败日志](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/pytest_initial.log)、[初始机器结果](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/tests_initial.json)保留。随后122通过；增加哈希覆盖、跨Update依赖和新草案渲染测试后最终129通过。

以上只验证工程性质与接口，人工替换文本仍可能保留旧策略问题或产生语义冲突，不是新策略质量验收。

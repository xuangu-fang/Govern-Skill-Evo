# Preconditioner v8 / v7：DeepSeek R05、R06 干净输入单模块对照

2026-10-28。只调用 Preconditioner；未改 Prompt，未执行 Editor、Actor、Candidate、Replay 或完整训练。本文比较模型输出及其有效 Update，不报告下游分数改善。

**结果：R05 获得有效输出，但主要范围问题仍在；没有观察到明显过度保守。R06 用完原六次请求上限仍无完整回答，无法做语义对照。** 本次共发起九次 HTTP 请求，R05 三次、R06 六次；没有扩大预算或修改参数。

## 对照条件

- v8 首次及技术重试请求只含 system、user 两条消息，删除历史 assistant 回答和修正反馈。保留原始任务输入、Plan、Memory、执行上下文。
- 与存档 v7 相比，只替换 Preconditioner 模板版本。R05 对照 v7 干净输入首轮有效输出；R06 同时对照 v7 干净输入首次完整回答和原生反馈后的最终有效输出。
- 原调用参数不变：`deepseek-v4.1-flash`，`max_tokens=49152`，`temperature=1.0`，`reasoning_effort=medium`，`thinking={"type":"enabled"}`，`stream=false`，超时 300 秒，每轮最多六次请求。使用原内网接口，不输出密钥。
- 技术错误按原机制重试；格式错误只追加本次最近完整回答与原生校验错误。不因语义判断不理想重新采样，不手工修补模型输出。
- `manifest.json` 固定原始输入、v7 参照、运行脚本和判断标准；`contract.json` 固定生产代码和 Prompt。`summarize.py` 校验每个请求的非消息参数、原始模型输入、基础消息及反馈重建，并用原生加载器重读最终归档。

## R05：核心范围问题仍未解决

| Update | v7 | v8 最终有效输出 | 判断 |
|---|---|---|---|
| u1 文本匹配及数值判别 | KEEP；默认子串匹配，保留整数／小数修复假设 | 仍 KEEP；正文完全未改 | 未把风险落实为范围调整。保留合理假设与保留当前默认范围仍混在一起 |
| u2 数值边界及分配 | KEEP；从完整相关 sheet 找边界 | S 调整：可从题目文本、其他行列或 sheet 找边界；保留逐格边界与残差传递 | 有实际正文改动，但属于扩展查找来源；没有解决“边界必然存在于工作簿”的事实假定 |
| u3 公式缓存 | D/S 调整；必需公式保留；非必需公式直接值；缺失或错误时同次执行修正、复查 | D/C 调整；保留必需公式，在同次执行内修正缓存、再保存并确认 | 合理保留修复路径；不是新取得的边界改善。v8 没有重述 v7 的非必需公式直接值分支，也没有禁止该分支 |

### u1 的 KEEP 依据仍有缺口

v8 理由先称 “the current scope is not shown to be defective”，随后援引 P1 两格错误和 P4 子串任务成功，最后称 “no supplied observation shows the broader match admitting wrong cells”。它仍将“没有观察到错误纳入”作为保留宽泛默认的重要理由。

P1 没有展示出错行的实际文本和数值，不能确认是文本变体还是数值判别造成失败。P4 的成功支持其部分匹配任务，不足以独立支持所有 find/match/act-on 标签任务默认使用子串。v8 将这些宽泛动词视为有效限制，却没有区分关键词包含与完整标签身份。这里的结论是**输出中的范围依据不足**，不是本实验已经证实子串规则造成某道题退步。

有效正文依然写着 “substring membership … unless the instruction explicitly requires … equal … exactly”。“未匹配行不改”的保护仍不能覆盖被扩大匹配错误纳入的行。c1 也继续检查包含标签的长字符串是否被改写，没有检查语义上不该匹配的长字符串是否被保留；相较 v7，c1 还漏掉了正文保留的整数／小数判别覆盖。

### u2 改的是查找范围，不是事实确定性

允许从题目或其他 sheet 查找边界是有用的泛化；保留边界约束和残差分配也不需要先确认全部根因。但理由仍说题目未列数值，所以 “must be located in the workbook”。当前输入没有提供具体边界及其来源，这个必然性没有被证实。v8 没有因事实缺失撤回修复，也没有将未知前提明确保留为待定位事项。

### u3 与保守程度

v8 保留了三项 Update，未要求先证明有效、未要求更多失败案例，也未新增不可执行的狭窄触发条件。公式必需时继续保留公式，允许等效缓存实现，并要求同一次程序执行结束前修正和确认。相较 v7，正文更集中于必需公式的可读性，没有增加高成本的新流程。没有观察到明显过度保守；遗漏 c1 的数值覆盖属于检查完整性问题。

### R05 原生修正轨迹

001 读取超时；002 为首份完整回答，三项 adjustment 均漏填必填 `to`；003 在原生反馈后有效。003 保持 002 的 `focus/change/reason/checks` 完全相同，只补充 u1 的 `to:null` 及 u2/u3 的补丁。因此上述 KEEP 和调整方向在无旧回答的首份完整输出中已出现，并非格式修正反馈引入。

证据：[最终逐项对照](../../../../../artifacts/methods/v25/analysis/preconditioner_v8_deepseek_r05_r06_clean_20261028_001/R05/final_comparison.md)、[首份完整回答对照](../../../../../artifacts/methods/v25/analysis/preconditioner_v8_deepseek_r05_r06_clean_20261028_001/R05/first_response_comparison.md)、[反馈前后对照](../../../../../artifacts/methods/v25/analysis/preconditioner_v8_deepseek_r05_r06_clean_20261028_001/R05/feedback_comparison.md)、[有效 Plan](../../../../../artifacts/methods/v25/analysis/preconditioner_v8_deepseek_r05_r06_clean_20261028_001/R05/final_effective_plan.json)、[有效正文差异](../../../../../artifacts/methods/v25/analysis/preconditioner_v8_deepseek_r05_r06_clean_20261028_001/R05/effective_updates.diff)。

## R06：未获得完整回答，不能判断范围调整

| 尝试 | 初始上下文 | 结果 |
|---|---|---|
| 001 | system + 原始 user，无旧回答及反馈 | 300 秒读取超时 |
| 002 | 相同两条消息 | `finish_reason=length`；49,152 completion tokens 全部计入 reasoning，`content` 为空 |
| 003 | 相同两条消息 | 300 秒读取超时 |
| 004 | 相同两条消息 | `finish_reason=length`；49,152 completion tokens 全部计入 reasoning，`content` 为空 |
| 005 | 相同两条消息 | `finish_reason=length`；49,152 completion tokens 全部计入 reasoning，`content` 为空 |
| 006 | 相同两条消息 | 300 秒读取超时；原六次预算耗尽，运行停止 |

没有首份完整回答，没有可供校验的补丁，因此也没有 R06 格式反馈修正或最终有效 Plan。没有把空内容当作 KEEP、撤回或范围调整。原生停止记录见 [R06/summary.json](../../../../../artifacts/methods/v25/analysis/preconditioner_v8_deepseek_r05_r06_clean_20261028_001/R06/summary.json)，逐次状态及参数审计见 [comparison_summary.json](../../../../../artifacts/methods/v25/analysis/preconditioner_v8_deepseek_r05_r06_clean_20261028_001/comparison_summary.json)。

作为参照，存档 v7 的首次完整回答使用 32,191 completion tokens，其中 29,803 reasoning tokens，正常结束但 u2 补丁不合规；后续原生反馈获得有效输出。其主要语义仍是：u1 承认表头起点／数据起点未区分但 KEEP；u2 保留不跳过来源并补充连续追加；u3 保留完整标识符、分隔符归一化及 FIFO 排序修复。v7 的首次与最终输出差别主要是补丁修正。

本轮 v8 的 R06 prompt tokens 为 51,954，存档 v7 为 51,754；增加约 200 来自新版模板，任务证据、执行上下文及调用参数不变。新调用表现出获得完整答案的困难，但单轮对照无法区分模板影响、采样波动、服务响应或处理速度等因素。不能将其归结为 v8 更保守，也不能据此认定新增判断标准必然导致推理耗尽。

## 本轮可支持的结论

1. **R05 的核心预期未实现。** 子串默认仍原样 KEEP；依据仍包括“没有观察到误匹配”。数值规则调整了查找来源，但未解决把未知来源说成确定事实的问题。
2. **R05 没有明显过度保守。** 三项修复均保留，没有引入根因必须确认、最低案例数或不可用的触发限制。公式边界保持合理；检查覆盖有局部缺失。
3. **R06 语义效果未定。** 本次首先遇到的是完整输出获取失败，不能评价表头／数据起点风险是否落到正文，更不能宣称两轮都验证改善或退步。
4. **格式和调用可靠性需单列。** R05 首份完整回答漏 `to`，原生反馈修正有效；R06 没有进入补丁校验阶段。二者都不能代替语义判断。

本轮按约定停止，未修改 Prompt、补充输入、扩大请求预算或调用其他模型／下游模块。原始输入和参数一致性校验、冻结文件哈希校验及 R05 最终归档原生重读均通过。

## 解释边界

- 这是存档 v7 与新 v8 的各一轮单模块对照，包含原生技术重试和格式修正；不是多随机种子重复评估。输出差异与 Prompt 变化相伴，不能单凭两轮把差异完全归因于模板。
- 分析对象是模型实际输出、其范围依据和可执行补丁。没有 Candidate 执行，不能推断任务准确率、复杂实现成本或最终 Skill 的净收益。
- R05 的二级键回退与 R06 的“探查也保存”争议没有出现在这两次原始 DeepSeek 输入中，不能声称本轮覆盖或修复了它们。
- 输入证据没有补充。出错行真实内容、数值边界位置等未知事实仍未知；区分“合理修复假设可以保留”和“附加默认范围已有充分依据”，不能将所有 KEEP 一概视为失败，也不能将所有正文修改一概视为改善。
- HTTP 超时、输出额度耗尽、输出结构不合规分别记录。它们影响本次调用可靠性，不自动证明语义判断变好或变差。

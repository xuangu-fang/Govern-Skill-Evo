# Actor 合成示例说明

所有响应、题目和评分边界案例均为人工构造，未调用模型。请求模板中的图片编码是不可执行占位符，没有创建示例图片。

| 文件 | 用途与可见范围 |
|---|---|
| [actor_request.template.json](actor_request.template.json) | 展开初始 Skill 的实际请求形状；只有图片编码仍为占位符。参考答案不进入请求 |
| [actor_response.synthetic.json](actor_response.synthetic.json) | 合成的有效 stop 响应，只提供本例需要的 API 字段，不伪造 usage |
| [scored_outcome.json](scored_outcome.json) | 普通响应、抽取答案、训练参考答案、hard/ANLS 和完成计数 |
| [optimization_run.json](optimization_run.json) | 完整文本投影，图片块已换成占位文字；与五模块主链 P1 一致 |
| [scoring_examples.json](scoring_examples.json) | 15 组有效 stop 的抽取与评分案例；不是额外 Actor 调用 |
| [gate_examples.json](gate_examples.json) | 三组配对指标及期望程序决策，仅供人审阅，不传给 Replay |
| [review_only.json](review_only.json) | 合成题目、参考答案及请求说明，既不是 Actor 请求，也不是模块输入 |

主链演示 “1,200” 对参考 “1,320” 得到 hard=0、ANLS=0.6。优化模块可引用响应中的 subtotal 陈述，但不能把它当作核实后的图片内容。

评分案例覆盖无标签回退、多个标签、大小写及空白、标点、单位、冠词、日期、多参考、空答案、未闭合标签和距离阈值。最后一例使用两个长合成字符串说明：hard 的 0.999 阈值不等于绝对字符串相等。

所有 scoring_examples 均假定响应已通过执行结构校验且 finish_reason=stop。length 响应即使带完整答案也不会进入这一评分表；拒绝、工具调用、缺失 content 等处理见[执行协议](../DESIGN.md)。

这些样例只用于检查设计的确定性关系，不能据此得出模型能力、视觉过程或真实吞吐结论。

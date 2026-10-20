# 调用前设计：Evidence-Calibrated Update

[离线分析](OFFLINE_ANALYSIS.md)已完成后才编写本候选。仅在正式冻结V23第一节原Parent／能力要求位置替换三段，完整模板见[preconditioner_prompt.md](../config/preconditioner_prompt.md)。本轮不直接改变默认配置。

统一原则：证据既决定Update取舍，也约束其策略、适用条件与强制程度。原始／替代方案同样受约束；支持目标不等于支持具体策略，反对原案也不等于支持替代案。新增限制和必要完成条件的改变不能仅由另一项修改的动机背书。允许有问题依据、可测试的新策略和大幅修改，在既有reason及适用的checks说明预期；Update本身仍清楚可执行。

| 对照 | 主要差异 |
|---|---|
| 正式V23 | 原位置从一般适当性／可执行性扩为“取舍＋范围与强度校准”；仍保留Parent与原Actor能力要求 |
| alignment | 不只问历史与当前策略是否不同，还问最终具体要求的适用范围及强制程度是否有对应理由 |
| construction | 校准覆盖所有retained/revised要求，不限Adjustment新增部分；不因原策略有错就支持全部替代细节 |
| symmetric | 从列举策略／顺序／停止等差异，转为统一的scope/force与证据／问题假设匹配；明确新增限制与必要任务完成条件也需对应支持，说明已有reason/checks承载假设 |

精确Diff：[V23](../config/v23.diff)、[alignment](../config/alignment.diff)、[construction](../config/construction.diff)、[symmetric](../config/symmetric.diff)。其余全文相同，包括第二节Memory的编辑、条件、反例、归因比较，第三节模块职责，所有JSON契约、Keep与合法停止。没有重复解释Memory结构，没有任务专用规则、关键词或数值禁令。

范围与边界：强制性本身不是错误；有明确条件和动作依据时可提出有力操作指导。新策略可以明确而具体，不能要求预先证明成功；但其作用条件、约束程度必须与解决的问题及测试假设相配。规则不是越软、越少越好。单次随机输出不能证明稳定改善或Prompt因果效应，固定材料不验证行为收益。

冻结后各使用正式R04/R05/R06 Original、Parent、Grouping、当前事实、当轮Memory/sources及原Actor背景，不输入历史候选Effective或行为实验结果。deepseek-flash、temperature=1、Thinking enabled、reasoning_effort=medium、max_tokens=16384、stream=false、timeout=300；容量按当轮实际生效配置，保留原技术首次加两次重试。不压缩材料，不语义重采样。具体来源与配置写入[plan.json](../config/plan.json)，Prompt、Diff、此文、离线分析及读取凭据一并冻结。

预先评价：R04看直接温度动作条件与强度、精确类别、多物体计数；R05看是否保留探索及区分观察／假设、是否无据强化限制；R06先评价历史与原调度取舍，再评价替代策略具体条件、强制程度、停止及效果承诺。分别回答A取舍、B策略范围强度、C探索与无据限制。允许Keep或合法停止，不预设轮换，不以Adjustment数量、较短输出或未再出现某句话判断通过。

本次只用既有Preconditioner局部入口和确定性编译；不改其他模块、不写Memory、不运行Editor、Candidate、Replay或ALFWorld。三组验证后停止，不继续Prompt迭代。

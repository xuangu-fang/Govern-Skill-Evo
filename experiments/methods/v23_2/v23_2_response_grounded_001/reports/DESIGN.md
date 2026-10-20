# 调用前设计：Response-Grounded Strategy Construction

统一原则：**先区分历史实际证明的行为、暴露的问题与建议探索的办法，再结合当前证据保留或构造Update。** 历史失败可以定位改善需要，但不自动证明原因或唯一决定策略。新策略和大幅修改可以明确、有力；在原有reason／必要checks说明问题动机与可检验预期，不能把预期冒充已观察效果，也不能让同一个动机为其他限制及必要完成条件的改变自动背书。

[完整Prompt](../config/preconditioner_prompt.md)从正式V23冻结文本生成，仅替换第二节的`Use relevant historical responses to determine...`一句，改为117词的三个短段。[精确V23 Diff](../config/v23.diff)。第一节Parent／Actor能力要求原样保留；没有恢复第一项可执行性补丁。Memory结构、证据比较条目、Keep／停止、第三节调整方向／范围／强度和合并拆分能力、JSON字段、Checks含义及编译规则全部不变。此处三个概念不是新增推理阶段或输出结构。

| 旧候选 | 本次主要差异 |
|---|---|
| alignment | 从检查历史支持与具体策略的差异，转为先界定历史观察能支持什么认识，再构造；不预定调整方向 |
| construction | 不只约束Adjustment新增要求，同时覆盖construct or retain，避免默认认可原案 |
| symmetric | 不列举全部策略差异再逐项检查，明确失败可能揭示问题而未证明原因或唯一替代策略 |
| calibration | 不再围绕scope/force校准列举判断要求；将作用点前移到历史认识形成与当前策略构造的关系，保留约束附带要求的边界 |

四版精确Diff亦保存在config。既有Memory比较清单负责核查编辑、条件、反馈与归因；本次段落说明这些比较怎样影响构造，不重复解释输入结构。第三节仍允许改变方向、强度及大幅调整，合理Keep不需为了实验产生Adjustment。未加入任务／类别／温度专用规则。行为指令仍清楚，未验证的新假设由reason和checks表达。

## 固定验证及预先判断

仅R04/R05/R06各一次逻辑Preconditioner，首次加最多两次既有技术重试；合法语义结果不重采样。各轮Original、Parent、Grouping、执行事实及动作候选、当时Memory/sources、原Actor背景保持相同。R04 M1–M6；R05 M1/M2/M3/M6/M7/M8/M9；R06 M1/M2/M6/M7/M9/M10/M11。不得使用R06后形成的M12/M13。旧Effective仅作离线比较，不作新输入。

沿用deepseek-flash、temperature=1、Thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、timeout=300秒和各轮实际容量配置；精确来源、容量及参数见冻结plan.json。原始输入不压缩，不新增语义校验程序。复用既有局部runner和确定性编译，仅增加独立profile及分析档案。

预先分别评价：A历史含义是否准确，B具体构造是否合理，C是否保留探索。R04看有条件直接温度动作和多物体／交付；R05看是否把遗漏错误归因于换类并强制穷尽，或是否允许有动机的新假设；R06看是否区分M10实际覆盖与调度优劣，再检查保留或替代要求的理由、完成条件及保证。既不预设轮换，也不以Adjustment数／篇幅／旧词消失判断成功。

完成离线测试后冻结此文、离线分析、Prompt、Diff、来源凭据、配置和代码，再开始调用。冻结后不改Prompt。仅研究单次固定材料输出，不证明稳定Prompt优越性或行为收益。默认方法仍原V23；不改其他模块或Memory，不运行Editor、Candidate、Replay、ALFWorld或Test。三组验证后停止。

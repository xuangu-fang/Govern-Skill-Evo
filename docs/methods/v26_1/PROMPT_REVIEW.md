# OfficeQA v26.1 四模块联合审阅

四份Prompt由保存的v29.4 Diagnosis／Preconditioner和其沿用的v29.2 Editor／Replay原文适配，文件完整展开，可分别阅读。实际Actor基础协议由本地OfficeQA `VENDOR_PROMPT.format(skill_section="")`提取，工具schema来自同一来源。源文件不在运行时自动升级本稿。

## 2026-11-05 共享 OfficeQA 领域指导

四个模块在职责说明后嵌入相同的英文段落。来源为仓库内 [SkillAdam OfficeQA prompts](../../../external/SkillAdam/skilladam/benchmarks/officeqa/prompts/)（[许可](../../../external/SkillAdam/LICENSE)）。逐字摘录及环境适配如下：

| 来源 | 采用方式 |
|---|---|
| `skill_writing_policy.md` 第 54–63、67–69 行；`stage0_extra_section.md` 第 7–9 行 | 原样摘录允许的金融术语、表格、计算与输出格式四项，以及泛化和禁止写入个案内容的要求。 |
| `metric_interpretation.md` 第 38–40 行 | 原样摘录证据定位、操作数提取和计算准确度三项。检索适配初始消息已有文本、字面 grep、TXT 行号和截断；24 轮含最终回答。答案格式由问题决定，EM/F1 单独不能定位错因。 |
| `failure_types.md` 第 5–10 行 | 沿用六个名称作可选词汇。依据实际文本区分检索、表格定位、取数和计算；证据不足时保留不确定性。 |
| `success_types.md` 第 6–9 行 | 原样摘录四类成功行为作为例子。仅凭答对无法确认规则使用或计算过程，规则采纳由现有机制决定。 |

Diagnosis 删除旧的错误分类长段和“先定答案范围再处理格式”的顺序要求；另一段关于字段角色和答复长度的指导仅保留答案元素作用域与最终提交协议。其余三个模块只插入共享段。原有 v29 迁移 diff 记录初稿，这次修改见 [修订前后 diff](diffs/officeqa_shared_guidance.diff)。

## 方法保留

| 模块 | 保留的决策语义 | OfficeQA替换内容 |
|---|---|---|
| Diagnosis | 全批共同问题/差异，单例可提案，行为增量，完整条件与必要依赖，合理探索/no_change，不固定数量 | 全轨迹替换单轮视觉投影；检索、字段/时期/单位/操作数/提交区别；只看分数而非参考答案 |
| Preconditioner | 按行为机制联系历史，D/S/C，整条KEEP，完整REPLACE或WITHDRAW，保留ID/basis，协调依赖 | 当前工具文本可见、历史原始轨迹不可见；24轮工具负担；无标准答案推断 |
| Editor | 每Update精确patch、原Parent统一定位、共享context/字符组合、空/null语义、无策略重判 | 原生OfficeQA Actor能力与最终回答协议；不得新增Python/在线工具或标准答案查找 |
| Replay | 只看翻转、每题一事件、明确关联一个Update或null、无历史、不可强制主责归因 | hard换成原生EM；全正式轨迹及工具时序；F1不投票；按工具行为分析但不声称看到隐藏计算 |

本稿没有整体移入v29.3/v28.2 Prompt v2关于Update组织、迁移说明和额外审查的修订。保留v29.4“独立有依据、可行动、必要依赖保持完整、多个Update共同测试理由清晰”的原指导，不另造按预期Retain/Reject拆分的要求。证据权限、编码与OfficeQA任务语义的替换不增加模型阶段。

## 交接审阅

- Diagnosis reason不流入Preconditioner；整个Plan的合法直接执行引用选择完整runs，支持/成功/反例仍需进入basis。
- Preconditioner只能在Original问题和ID边界内调整。KEEP/REPLACE后的实施条件全部在text，reason不会传给Editor。
- Editor只获goal和id/text；每个patch映射一个Update，全体构造Candidate。不存在把basis或参考答案偷渡到Editor的字段。
- Replay只获有效id/text、实际patch/diff和翻转任务完整轨迹，没有当前Gate结果、历史Memory或调整理由。事件引用限本题P/Q；null保留不投票。
- Gate从程序已核验EM计数，不采信模型文本中的数量。Memory保存全部Effective和事件，不把空事件轮解读为负面实验；历史只追加。

## 重点适配核对

**标准答案不可见。** 四模块均不获得references；Diagnosis不得以未知gold value定位算术错误，Replay不得声称某个具体数值与隐藏答案相同。可见工具文本与EM翻转能够支持有界解释，但不自动揭示评分细节。

**正式轨迹完整且尊重时序。** 工具调用、参数、错误、返回、普通内容均保留；同一响应的后续工具返回不能解释该响应较早调用。初始声明的页面与实际渲染页面不同；URL页码与TXT行号不同；空搜索、读窗口或截断不能证明全文没有某值。

**原生评分精确。** 使用第一个answer标签/末非空行回退和OfficeQA归一化；保留负号、小数点、百分号，去逗号及指定单位词；无数值容差或单位换算。Prompt中的Replay结构例子为虚构时期列选择，不沿用DocVQA删除冠词的评分示例。

**预算是执行说明。** UID0007的单题例外仅用于说明实际训练预算，不允许生成任务ID查答案规则。所有Test题统一32,768。四份Prompt含完整Actor约束，Editor不因未看到文档拒绝实现一个有授权的条件式工具策略。

**引用规则不扩权。** 沿用v29.4明确命名空间和本地列表，扩展至OfficeQA工具子引用；无Group/Check/历史raw授权。不把LMB数学符号专用解析特例整体迁入本稿。结构合法不证明自然语言归因正确。

**表示层只去重复。** 完整run时间线与同题初始消息共享替换单轮shared_initial；原始字段与数值类型可恢复。四模块不用局部source_records，因此无需新增局部历史接口。Prompt已内联编码说明，后续实现不能重复追加或读取旧版本中带占位符的execution_context模板。

## 审阅与验收的边界

[design_validation.json](design_validation.json)只记录来源副本、Prompt静态性质、文档链接、JSON结构和数据调度核对。它不运行v26.1方法，不证明模型能正确执行这些要求。实现验收必须另按[ACCEPTANCE.md](ACCEPTANCE.md)进行；后续效果结论必须来自真实完整实验。

# P3-B历史响应增量归因：同Prompt配对

**本版主对照改为：合法A_format_001（无Memory）与新B_format_001（真实R05 Memory）。两组完整system Prompt逐字相同，其他请求字段除Memory外完全一致。原B和失败尝试仅作历史记录，不与新B混用。**


**同Prompt混杂已消除。现在观察到：A保留原案；B显式用M3/M6的编辑后响应重构u1。存在历史响应参与更新方向选择的初步线索，但没有证明整条替代Update更合理，尤其类别采样结束和全局进度前提仍无充分支持。**

## 1. 共有当前证据能够独立支持的部分

P6长drawer扫描、P8反复访问、P10很晚才换到diningtable已支持质疑覆盖安排并尝试跨类别探索。Actor两步历史已足以质疑全局visited/穷尽；可选动作列表已经可用于选择合法移动。P1/P7/P8/P10的no-op与重复信息动作已足以检查状态相关的重复限制。

因此A没改、B改，不等于B所用理由全部来自独有历史知识。要识别历史增量，必须看“旧Skill怎么改过—后续实际怎样—为何影响本次文本”，不能仅用A/B差异或Memory引用计数。

## 2. B明确表达的编辑—响应关系

B的Adjustment.reason实际说：

> Memory M3/M6 record that the anti-cycling/revisit-avoidance wording was not reliably followed and did not by itself break the cycling/step-limit failure, whereas added search breadth combined with exact-target guidance did help.

它以此改变u1的优先级，不是仅在reason中提Memory而全文Keep。A没有该历史解释，最终保留同类穷尽。下面是研究者对其引用的真实sources展开，不能视作模型逐步陈述过的隐藏推理。

| 来源 | 实际Diff | 配对响应与局限 | 对当前变换的支持 |
|---|---|---|---|
| M3，sources[S1_R02/diff] | 新增通用检索/开容器、少空回访、精确对象、条件clean、直接交付；同时收窄灯适用范围 | P5错取soapbottle且失败；Q5:19到bathtubbasin找到dishsponge、20取、22clean、24place成功；其他实例循环仍在，部分简单任务增步 | 支持扩大覆盖与精确目标联合方向可能有益，反循环文本未稳定兑现；不证明一种类别采样规则就是有效成分 |
| M6，sources[S1_R03/diff] | current/recent反循环，未找到时扩展drawers/shelves/diningtable，高步数优先新位置；联合温度与精确目标指导 | Q4:12到diningtable发现bread，13取、15cool、17place；Parent该对50失败。P2:15到countertop3拿bread并20成功，Q2反复countertop2、未去3且50失败。Q6:49才取得plate、50到fridge未完成 | 支持重新考虑位置覆盖、警惕旧指导未落实和预算/同类遗漏；不能推出“每类别一次就结束” |

完整知识和来源：[冻结Memory](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/memory_B.json)；[预注册证据索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/reports/P3A_MEMORY_EVIDENCE.md)。本次再核对了上述原始Diff/动作/结果。历史为联合编辑和单次执行，不可将整体收益/退化独立归因某个子句。

B的总reason称`the effective ingredient is sampling additional receptacle types plus exact-target/no-substitute guidance`。这是比记录本身更强的成分归因：M3/M6观察与扩大覆盖一致，但没有隔离证明“类别采样”这一调度就是起作用的成分。当前P10也有换类别后成功，不因此证明类别一次覆盖充分。

## 3. 反例有没有约束最终要求？

B确实吸收了“旧反循环文字未稳定消除循环”，没有把所有原规则完全否定：仍保留近期空位置避返和单向扫描。改为跨类型探索作为新假设可以合理。

但M6同类countertop3被遗漏与Q6过晚获取的限制，没有在最终文本形成相应的实例覆盖/后处理预算边界。相反，B要求所有类型采样一次即可结束，可能在某类别仍有未查实例时终止。这是对最终规定可直接提出的证据一致性问题；不能据此推断模型内部完全没有读反例，也不声称已导致Actor退化。

B从候选列表构造未用类别选择，候选却不编码全局历史。这一执行前提也未在实际Update中落实。reason自称可执行不能替代最终条件核查。

## 4. 按预注册类型判定

| 类型 | 本次观察 | 判定 |
|---|---|---|
| 当前证据纠正 | B改变长同类安排、明确go-to候选；A未改 | 当前材料本就允许，不能全部计为Memory独有贡献 |
| 历史信息使用 | B真实引用M3/M6，知识还含实际旧编辑和混合响应 | 不只是一般任务示例，存在明确历史解释 |
| 编辑—响应预条件化线索 | 旧反循环/扩大覆盖的混合响应→重构u1的优先级，最终文本确实变化 | **方向层面的初步线索成立**；单次样本不证明因果，整条Update未满足“变化有据且不引入明显无据限制”的充分条件 |
| 无依据附带要求 | 类别一次结束；全局未用类别/全部采样状态；effect ingredient过强概括 | 不能当作合理增量，显示历史限制没有充分约束替代构造 |
| 无实质更新差异 | u2、Goal、Checks、精确目标保留要求相同 | 这些方面未观察到增量；不能称全部无差异 |

本次basis只显式引用M3/M6，没有M8；不能沿用旧B的M8理由。本输入仍包含七条Memory，无法把差异归因于M6单条，也不能证明其余条目没有作用。

## 5. 核心回答

**加入Memory的这份输出与无Memory不同，且具有可追溯的编辑—响应解释；但“不同且整体更有依据”没有成立。**历史反馈似乎参与了从原策略到另一探索方向的选择，尚未可靠约束替代方案的进度前提和结束边界。

同Prompt恢复后，仍是两个单次样本；输入长度/缓存、调用时点和前期非对称技术失败不能排除。格式补充版也属于用户授权协议修订，不混同最初原Prompt实验。可报告响应预条件化线索，不能报告稳定因果收益，更不能报告Skill性能提升。

后续若继续，优先预注册同条件重复以检验这一方向信号是否稳定，再决定定向消融；当前不优先执行存在明确终止风险的Candidate，也不自动追加Prompt规则。本次停止。

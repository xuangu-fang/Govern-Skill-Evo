# 调用前核查：R06 决策依据与 Prompt 原则

此文在本次候选模型调用之前写入并冻结。核查阶段未调用 LLM、未改任何 Prompt。只读取正式 R06 与 alignment/construction 的保存响应，通过既有读取器重解析、编译并确认三版共享 Original Plan、Parent、Memory。以下不是对模型内部推理过程的断言。

## 1. R06 证据链

| 环节 | 实际文字／动作与来源 | 能支持什么，不能支持什么 |
|---|---|---|
| 当前 Parent（R05 正式 Skill） | 搜索要求 `spreads across distinct receptacle families rather than exhausting or looping over one type` | Parent 已有跨类覆盖策略，不能将 Original u2 看作仅增加同义“有序搜索” |
| Original u2 | 类内升序；`When the current family is exhausted ... switch`；`guarantee progress` | 具体改变切换时机及执行强度；需要说明为何当前问题支持这些差异 |
| M6 对应 R03 实际 Diff | 当前／近期观察避循环，扩大到 drawers/shelves/diningtable，高步数优先新位置；同时修改精确类别和温度操作 | 与搜索方向相关，不是单独验证“全局类内穷尽”或“固定轮换” |
| M6 行为 | P4 失败50→Q4 diningtable 找 bread 成功17；P2 countertop3 bread 成功20→Q2 漏 countertop3 失败50；P6 cabinet9 plate 成功38→Q6 到49才取 plate、失败50 | 有覆盖收益，也有同类实例遗漏和晚发现；不支持简单保证或把负例当永久禁令，联合编辑无法单条因果归因 |
| M10 对应 R05 实际 Diff | 与 Parent 搜索条款一致，明确 `rather than exhausting ... one type`；另加强精确类别 | 不能仅从“family sweep”的名字把它等同于当前类内穷尽 |
| M10 行为 | Q6 多类切换后16到countertop2、21成功，P6长扫drawers失败50；Q8先查cabinet1–4并回访，18到shelf1、23成功；Q10仍循环、46步，P10为38步 | 支持覆盖新位置的条件性收益；Q8并非理想不穷尽式轮换，不能从这些轨迹推导统一最优类别调度 |
| M10 概括边界 | 称两次救回都在 Parent 未到的 family，但 P6:3已到countertop1，遗漏的是countertop2 | 来源 Diff/轨迹比“新类别救回”概括更精确；“after one family yields nothing”也有阶段边界歧义 |
| 当前 R06 事实 | P3:1–50循环失败；P1:34、P2:8在countertop2找到精确目标 | 支持减少重复、覆盖遗漏位置；没有直接比较证明“先穷尽一类”更好 |
| construction 实际引用 | basis=`P3:1,P3:50,P1:34,P2:8,M10,M6`；reason=`The substantive strategy is preserved` | 用高层“family-switching single-pass能救回”解释保留，未论证当前与历史具体调度的差异 |
| construction 实际变换 | 从room description改读admissible actions，并用近期动作识别索引；保留类内穷尽与保证 | 不是完全忽略Memory，但历史反馈的约束在“方向→具体调度”的过渡处失效；信息源修正没有补足调度证据 |
| alignment 对照 | reason明确指出exhaust与Parent冲突，最终写不先穷尽大类 | 原取舍A有进展；但替代Update又引入类别采样终止、未定part与保证，说明B不足 |

R06 实际 Memory IDs 为 M1/M2/M6/M7/M9/M10/M11，没有 M12/M13。M6/M10 使用的 sources Diff 已与正式 R03/R05 Editor `actual.diff` 逐字核对；关键配对动作与原始轨迹另做一致性核验。所有任务结果都是整份 Candidate 的观察，不能归因于某条编辑。Memory 关于“无精确目标”的概括也不能由未找到直接推成环境中绝对不存在。

construction 声称初始说明第一步后即不可用。原渲染与正式 P3 请求显示步骤1–3仍携带初始房间，步骤4才移出窗口；长期不能依赖它的方向合理，时点描述不准确。这里只核查其实际依据，不重开 Actor 能力优化。

## 2. 三版 Prompt 的原则差异

完整文本核对表明，两实验相对冻结 V23 都只替换同一处要求，余下 Memory 比较规则与契约相同。

| 版本 | 原始 Update（A） | 替代 Update（B） |
|---|---|---|
| V23 | Parent适当性、能力要求；第二节比较历史编辑/条件/反例，允许Keep | 要求变换合理、无无关要求，但未明确“反对原案不支持替代案” |
| alignment | 显式说目标支持不自动支持不同strategy/scope/strength，且在keep/adjust/withdraw之前判断 | 没有同等显式检查替代方案新行为要求；主要依赖原有第三节 |
| construction | 开头保留一般历史对照，但去掉上一版“目标支持不自动支持具体策略”的显式警示 | `When making an Adjustment`、`each material change`与反对原案不足以支持替代案更突出 |

**最有依据的解释是判断要求不对称，而非已证明的因果机制。** construction 的措辞使检查对象更集中于 Adjustment 的新增变化；原始策略中被保留的实质要求，没有受到同等显式的支持范围追问。这与 R06“保留实质策略、只修正信息来源”的显式理由一致。然而原 Prompt 仍有历史比较要求，不能说A完全不存在；单次随机输出、Memory概括歧义、复杂长输入也都是可能因素，无法断言某句导致结果退回。

## 3. 新设计依据与调用前判据

在原有位置使用一个统一的三段要求：先在Keep/Adjust之前比较原案与历史具体编辑的重要差异，明确目标支持不够；再将相同标准作用于保留或替换后的实质要求，明确反对原案不够；允许以当前问题及预期行为变化为锚的可检验新假设。保留原Parent适当性、Actor决策时能力约束及有效行为，不要求最小改动，不要求任何轮次必须Adjustment。

其余输入说明、Memory结构、可用证据、调整职责及JSON契约不动。不加入类别搜索案例或固定策略顺序。设计假设是对称表达有助于同时约束A与B，不是已验证效果。

调用前判据：R04不能无据破坏已有温度/精确目标/交付；R05允许有当前问题依据的新探索；R06先核查历史与原案具体差异及取舍依据，再独立核查替代方案新增顺序、范围、强度与停止条件。允许合理Keep，不因Adjustment非空或旧错误未再出现就判成功。每轮一次逻辑调用，技术重试上限三次，不看输出改Prompt。

原始来源入口与详细已有证据：[上轮来源索引](../../v23_2_response_construction_001/reports/SOURCES.md)、[上轮完整原始输出](../../v23_2_response_construction_001/reports/OUTPUTS.md)、[第一版完整输出](../../v23_2_response_alignment_001/reports/OUTPUTS.md)。本次所有判断将另外核查最终Update，而非继承旧报告结论。

# P3-B Memory归因：有显式历史解释，但没有可估计的A/B增量

**A没有有效响应，所以无法判断“加入Memory是否促成了相对无Memory的不同且更合理更新”。不能把B相对Original的变化冒充B相对A的历史增量；也不能报告“观察到零增量”。本次增量是未能检验。**

B的显式reason确实引用了M6/M3的残留循环、遗漏与指导未稳定遵循，并实际改变u1。这个事实比“仅在reason中提Memory、全文不变”更具体，但仍不满足预注册的完整增量归因：没有A参照，新增规则又有支持不足。以下只检验B自身历史链条的质量。

所有历史材料来自 [冻结B Memory](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/memory_B.json) 的entries与sources；更细来源见 [预注册历史索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/reports/P3A_MEMORY_EVIDENCE.md)。没有M10，没有事后认识。

## 1. 共有当前证据已经能支持的判断

- P6在大量drawer上消耗预算、P8在少数位置循环、P10:32才在diningtable找到apple：支持改善位置覆盖/减少无信息重复，允许尝试其他搜索安排；不独立证明跨类最好。
- 原Actor两组历史：可质疑全局visited/耗尽状态，允许当前/近期可见线索。B明确last-two条件不需要独有历史信息才能提出。
- P1:4 Nothing happens、P7:11/12重复look、P8:39/P10:25空inventory：能支持状态相关的去重纠正；B保持原u2，没落实范围收窄。
- 当前Parent/Goal/G1及P3获取交付、P7错误knife、P10处理交付已支持精确目标和必要行为保留。B保留no-substitute并不自动构成M8独有增量。

由于A缺失，连“B独有的当前证据纠正”都不能确认。这里只能说这些B要求可由共有证据成立，不能直接计作Memory贡献。

## 2. B实际引用的编辑—响应链

| Memory /实际Diff | 对应行为与局限 | B明确解释与实际要求 | 支持范围判定 |
|---|---|---|---|
| M6，`sources[S1_R03/diff]`：current/recent反循环，明显cabinets/fridge没找到后扩展drawers/shelves/diningtable，高步数优先新位置；联合精确对象/温度编辑 | Q4:12 diningtable发现bread，13取、15cool、17place，相对Parent50步失败获救；P2:15 countertop3找到bread并20成功，Q2反复countertop2、未去3且50失败；Q6:4等无效move，49才取plate、50到fridge未完成 | Adjustment.reason称M6/M3反循环和broader-search语言未稳定遵循、仍漏位置；u1从类内穷尽改成breadth-first sampling | **显式引用的是实际编辑后混合反馈，链条部分成立。**它支持对强效果承诺保持限制、重新考虑覆盖；不证明先采样所有其他类型再回同类，也不支持类别采样结束 |
| M3，`sources[S1_R02/diff]`：新增通用开容器/少空回访/精确对象/条件clean/交付，同时收窄灯任务 | P5错用soapbottle且50步失败；Q5:19到bathtubbasin发现dishsponge，20取、22clean、24place；其他任务仍循环，部分简单任务增步 | 与M6一起作为广度探索与反循环语言未稳定兑现的依据 | 支持扩大覆盖与精确目标的联合方向，以及收益有条件；不隔离证明某个采样调度有效。B未提供该历史如何确定few、only-after及新终止条件的依据 |
| M8，`sources[S1_R03/diff]`、`sources[S1_R04/diff]`：精确类别和温度条件不使用近似物 | R03 P5操作pot而Q5未操作；P10及R04P1操作cup而Candidate避免，双方仍有步限失败 | B明确说M8支持保留no-substitute，最终u1保留 | 保留有据，但原Plan/当前P7已经有同一约束，属于相容支持，不能证明新增变换；不把knowledge中absent当隐藏环境不存在事实 |

表中具体S1_R03/S1_R02 Diff及step是研究者对M6/M3/M8来源的展开，B原文没有逐条列出这些历史step。模型明确陈述的是“历史指导未稳定遵循、仍有遗漏”，不能进一步声称它已用Q2/Q6解释了only-after或类别终止条件；这些附带要求恰恰缺少相应说明。

B未明确讨论M1/M2/M7/M9对本次决定的作用，不能宣称模型完全没有阅读它们。M9的有条件回源/额外检查增步仍可用来离线核查B的限制，但这是研究者核查，不补写成B已经使用的论据。

## 3. 三个关键推导边界

**方向与调度。** B总体reason把“historical Memory show exhaustive same-type sweeps or cycling consume budget”连在一起。M6/M3主要证明编辑后仍循环/遗漏，当前P6能观察到长drawer搜索；这些不同证据不等于已隔离证明所有类内穷尽有害。宽泛地概括成历史已支持某个反向调度，会越过证据边界。

**动机与附带约束。** 改成跨类型探索有当前问题动机，可以作为新策略试验；但“其他类型采样完才回剩余编号”“全部types或locations一次即可结束”需要独立理由。M6同类实例遗漏不能为推迟所有同类余项提供充分支持，也没有证明类别采样能代替位置覆盖。B没有给出对应的新假设及观测预期。

**局部信息与全局进度。** B明确两步历史约束，却在最终文本继续使用remain unvisited/have been sampled/all ... inspected once。reason声称能力更匹配，不等于这些状态判断已可执行。短期新颖性不能恢复全局穷尽/采样状态。

## 4. 按预注册类型记录

| 类型 | 本次结论 |
|---|---|
| 当前证据纠正 | B对近期反循环有具体化、改变搜索方向有动机；但u2范围未纠正。不能判断哪些是A没有的纠正 |
| 历史信息影响 | B明确引用历史反馈，与u1变换一起出现；只能说显式解释使用了历史，不证明输入Memory导致该变化 |
| 编辑—行为响应预条件化增量线索 | **未能建立完整A/B线索。**B内部有“旧提示未稳定兑现→重构搜索”的部分联系，但没有A参照，且替代方案仍有无据限制 |
| 无依据新承诺 | B的only-after全局采样续行条件及types-or-locations终止条件支持不足；few本身不是固定数值，不应一概判错 |
| 无实质更新差异 | **不能判定。**没有Effective A，既不能宣称不同，也不能宣称等价或零增量 |

## 5. 可确认与不可确认

可确认：合法B真实调整了u1、保持u2，显式引用M6/M3/M8，编译准确；广度探索的合理动机没有约束住全部附带要求，能力限制也没有落实到所有最终条件。

不可确认：A本会怎么输出；Memory是否导致变换；有无Memory哪组更好；M6单条的贡献；生成随机性/长度/顺序作用；任何Skill执行成功率或步数收益。没有Editor/Replay，也没有语义重采样。

**下一步首先是经另行授权补齐缺失A、仍保持冻结请求与参数，才能尝试完成比较；不是现在做候选行为Replay，也不是依据B一份结果增加Prompt补丁。**即使后续补齐A，调用时点不同和单次随机性仍须记录；稳定增量需要再预注册重复对照。局部Memory消融应等到存在可复核的增量信号后再确定对象，不预设M6就是唯一原因。

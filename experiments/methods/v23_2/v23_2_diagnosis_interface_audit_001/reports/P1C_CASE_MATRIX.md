# P1-C：R04／R05／R06承诺与下游纠正边界

本表使用P1-B有效输出：R04/R06为原P1-B调用；R05为用户授权重试。不是正式V23 Preconditioner已经评价过的Plan。除特别标为“正式”的信息外，“进入下游”指**既有装配函数生成的未发送payload**，不是实际模型已读取。

A＝要消除该不可变Goal承诺需上游修正；B＝Update权限存在；C＝有权限但相关原始证据漏选；D＝权限与主要证据具备、尚无该Plan的下游决策。B是权限层，D是验证状态，允许同项标B→D，避免把二者假造为互斥。另标“效果未知”，不把策略未验证等同构造错误。

完整原文来源：

- [R04 P1-B diagnosis.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R04/attempts/001/diagnosis.json)
- [R05 P1-B retry diagnosis.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json)
- [R06 P1-B diagnosis.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R06/attempts/001/diagnosis.json)

证据字段与完整pre-action候选见[证据索引](../results/evidence_index.json)，每项带原文件路径与JSON Pointer。下表`plan.updates[id=u*]`按id查找，不是数组下标。

## R04：需要解绑的是覆盖方法，不是把所有温度操作都判为Goal锁定

| ID／位置／实际要求 | 来源与问题性质 | 纠正依据及其传递 | 现有权限、责任与结论 |
|---|---|---|---|
| 04-G；plan.goal：`using a minimal microwave heat interaction` | P1曾把整条成功动作链写进Goal；P1-B已缩短。minimal microwave与当批hot任务有关，**Goal没有规定open必须先做** | P2/P3/P4完整轨迹和行动前heat候选均传入 | 不能单凭此句归A。u1开门条件仍可调整；必要的heat、精确目标、交付不需删除。B→D |
| 04-GS；plan.goal：`by sweeping all receptacle types once` | P1-B把具体覆盖方法写入Goal，而非仅“改善覆盖／完成数量”。不等于已明确“每类只采样一个就终止” | P6/P8回源成功说明任务可在已知来源取得剩余目标；不证明必须普查全部类型。完整事实传入 | 要**取消Goal中的all-types-once承诺**需A；仍可在保留该目标下改变顺序／条件。不能推成全部搜索Update无修改空间。Goal与达数量即停的关系存在歧义 |
| 04-U1；u1.text：`if the microwave is closed, open it once`、`held at the open microwave` | P1完整前置链的缩短版，必要性仍过强 | P2:6/P3:7/P4:5 before已提供heat plate3/potato3/tomato2；实际选择open。整条被选执行使较早步骤也到达，尽管basis主要引用后段 | 一对一替换可把开门限定于实际需要，不必先修04-G。B→D；菜单存在限制“必须开门”的推断，不证明提前heat必成功 |
| 04-U2a；u2.text：`visibly empty or an object there has already been moved`→其他未查位置 | Parent只限制无目标的空回访；P1强化未查范围，P1-B新增“移走过物体”条件。把移走一个与来源无剩余等同 | P6:23见两candle、24取第一件、27回源、28取第二件；P8:1见两newspaper、2取第一件、7回源、8取第二件。全部进入静态payload | 可收窄触发条件、保留有证据支持的回源机会。B→D；不要求Actor拥有全局目标地图。正式R04有相关正确调整，但未测试P1-B |
| 04-U2b；u2.text：`resume ... from unvisited receptacles`；`inspect each receptacle type at least once` | 继续数量任务合理；把继续搜索限定为未查来源及每类覆盖会影响已知剩余目标 | 同上；Goal也保留successful multi-instance placements。已知来源可以来自当前或近期信息，不强制记忆全部位置 | 回源例外可在Update内修正，B→D；若要完整撤销each-type覆盖，仍有04-GS的A障碍。不能用Goal保留成功一句话当作边界已落实 |
| 04-C；checks中`avoid leaving the microwave area without delivering the heated object` | 观察标准可能与去别处交付的时序不清 | 精确任务目的地和成功交付轨迹均可见 | Checks可完整替换／删除，B→D；不是Actor禁令，不能计为新Skill已禁止离开 |
| 04-P；goal保留desklamp，P10未选 | 所需当前保留案例只有磁盘完整记录，当前下游无P10全文 | Parent完整desklamp程序在；P10当轮完整操作／菜单未传，当前Grouping也没有该成员组 | C（保留行为的额外原证据不足），不构成04-U1/U2纠正所需证据缺口；是否需要补选取决于后续是否修改desklamp相关行为 |

R04责任边界：Diagnosis需要负责不把all-types-once锁成不可改目标；温度必要性和回源条件是明确的Preconditioner可调整对象。它们的出现证明Original不完美，**不证明整个预条件化入口无效**。

## R05：Goal没有锁定类内穷尽，主要问题可以成为下游调整对象

| ID／位置／实际要求 | 来源与问题性质 | 纠正依据及其传递 | 现有权限、责任与结论 |
|---|---|---|---|
| 05-G；plan.goal：`coverage-oriented and step-efficient`，保留desklamp／acquire-place／clean-cool-place | P1的目标解绑在P1-B维持。目的式`so the target is found...`不自动是效果保证；没有编号算法／类内穷尽 | Goal、Parent和若干成功事实均进入 | 本项无已证实A障碍，不需因Update有问题而继续改Goal |
| 05-U1a；u1.text：`Sweep a numbered series ... in one direction ... once that series is exhausted ... switch` | P1原跨类探索改为类内序列安排；没有相应事实证明它更优 | G3：P6集中drawer，P8循环cabinet／sink；P3:8、P6:6/14/16、P8:9、P10:6的回访事实完整进入。能支持减少重复，不决定最佳调度 | 一对一替换、拆分、与u2协调均允许；可保留编号线索而改变换类前提／强度，B→D。类内与跨类优劣＝效果未知；不是必须由Diagnosis先选出最优方案 |
| 05-U1b；`without returning to earlier ones`、`not yet inspected in this search` | Parent已有未查依赖；单向不回访进一步规定了范围 | 同一current／recent菜单不能给出完整visited表；原Actor两步历史与无持久笔记明确在system中 | B→D，可限定为可观察近期状态、调整策略或撤回。不能宣称写出编号即可自动消除状态依赖；也不能机械禁止所有有序方法 |
| 05-U2；u2.text：`If an action returns 'Nothing happens' ... do not repeat that action or an equivalent one` | 相对Parent空手inventory规则扩大；缺少状态改变／前提修复条件 | P1:4行动不在当时菜单并返回Nothing happens；P7:11/12重复look；P8:39/P10:25空inventory均完整传入 | 可增加状态前提／缩小等价动作限制，B→D。需要保留的只是状态不变时避免无信息重复，不等于永远禁止相同动作；后续能否有效重试并未隔离执行 |
| 05-U2b；`Instead immediately take a state-changing action` | 可能把有效信息获取排除；句首本来允许reveal new information，后句范围未充分协调 | 当前菜单、必要操作前提、P7第一次look与第二次重复的区别可见 | 可协调u2两部分、保留有效观察，B→D。不能把列举take/condition/place误作无条件立即全做 |
| 05-END；D1的`all plausible candidate categories have been checked once` | P1-B已删除，不再新增类别采样结束；Parent仍有all plausible candidate receptacles once | Parent全文、初始位置列表和轨迹进入 | 不重复判为当前新增错误；Parent终止要求也能通过Update改动，但应有依据，B→D。没有同类剩余位置状态就不能可靠宣称整体完成 |
| 05-E；Goal保留成功，当前缺P2/P4/P5/P9全文 | Plan主要引用失败／循环步骤，Group仍描述其余成员成功 | 静态request有P1/P3/P10完整成功事实；P2 desklamp、P4快速mug、P5pencil、P9clean只剩Grouping摘要，无相应完整pre-action菜单 | C：特别是P3慢／P4快的直接对照不完整；若评价该对比的具体条件，应补核证据选择。不能说所有成功行为均不可见，也不能证明它已导致错误决策 |

R05当前没有必须先修Goal才能改上述Update的接口障碍。这是最清楚的B→D案例。此前用“R05 Diagnosis还不完美”阻止所有下游研究，要求过宽。仍不应直接进入真实调用：须先明确P3/P4等对照是否属于目标验证必需证据，并冻结其选择范围；本次未改装配。

## R06：目标中两处实现承诺与Update可调整部分需要分开

| ID／位置／实际要求 | 来源与问题性质 | 纠正依据及其传递 | 现有权限、责任与结论 |
|---|---|---|---|
| 06-GN；plan.goal：`making rules depend on ... numbered receptacle names rather than a global visited set` | D0 ordered/memory-independent已移除；P1-B又把编号线索写入目标。current observation／admissible／two-step限制本身是合理能力边界，编号则是具体实现 | 原协议、实际菜单、编号地点、循环轨迹均进入 | 要取消必须依赖编号的承诺属A；保留编号但改变使用方式仍允许。不能把此句等同于Goal规定类内穷尽 |
| 06-GO；plan.goal：`one conditioning action ... at the open appliance` | 任务确需处理，不等于设备必须open；Goal写入了具体状态前提 | P4:5/P5:4 closed状态heat可见；完整轨迹进入 | 取消open作为普遍前提需要A。仅改u2不会清除该Goal文本。可先在不冲突处修Update，或合法停点；不能当作Goal已被修好 |
| 06-GT；50-step、exact-category、必要处理和交付、multiple count、desklamp-scoped | 属任务／协议／保留行为要求，不是仅因含动作词就错误 | system步数、Parent、P1/P2处理交付、P6/P7双物体事实全部进入静态payload | 应保留，无A缺陷。具体处理次数“one”应理解为成功完成所需一次，不应无依据扩大为失败反馈后永不重试；目前未验证Actor解释 |
| 06-U1；u1.text：`each inspected receptacle as consumed`、`next higher-numbered unvisited instance or a wholly uninspected family` | Parent已有single-pass/uninspected；P1-B新增consumed等范围。近期新颖性≠全局未访问 | P3:22及整条P3提供历史重访对照；system明确仅两步；当前位置菜单与轨迹可见 | Update条件／进度要求可改，B→D。消除global visited依赖不必删除所有编号策略；如果要完全换为不用编号的方案，则遇06-GN |
| 06-U1H；P1的`a few consecutive`近期切换、P1-B的local progress cue | 都可作为候选启发式，不是证明最优。few并非固定2或3 | 当前重复、覆盖问题有动机；没有隔离搜索算法比较 | 原Schema可在完整text中保留／替换这类启发式，B→D＋效果未知；不得以未验证直接判错。本次不把P1文本混作P1-B现行要求 |
| 06-U2a；u2.text：`open it if closed`、`held ... at the open appliance` | 相对D1 only if access needed变为无条件；且Goal也锁open | closed时已见heat、后续held heat/cool真实动作传入 | Update本身B，但完整解除承诺受06-GO的A限制；即使编译接受相反text也不是契约语义一致的修正 |
| 06-U2b；`If ... not offered ... place the target inside once and perform the action` | 新的备用实现，当前无该前提下成功证据 | P4:7/P5:6是放入后的下一pre-action菜单无heat；不过放入前本有heat，不是完全相同fallback条件的失败试验。相关整条记录进入 | 可收窄、撤回该分支而保留持物处理，B→D。不能证明该备用方案在所有状态必失败；不能把“放入必提供动作”当已知 |
| 06-U3；`remaining uninspected receptacles or a known source`、按count交付 | P1-B新增独立数量要求，具体保留回源；u1 consumed可能与其边界不清 | P6:17/21/22、P7:7/8完整传入；正式R06请求没有P6/P7全文，不能倒推当时已经收到 | 可协调u1/u3例外／依赖，B→D。允许可知来源，不要求完整来源记忆。数量要求本身合理，不需撤回 |
| 06-BUD；D0 u2 `keep enough remaining steps ... conditioning ... final placement`；P1-B只明确within budget及处理交付 | D0细化未重述，但旧Diagnosis不是当前Parent。Parent有Keep sweep within budget和交付；新Goal有50步及交付，u1有步数，u2有后处理 | Parent全文、Goal／u1／u2和system全部进入 | 可以明确搜索与后处理资源依赖，B→D；**不能说已从Skill删除原规则**，本次无Editor。编译保留Plan不是自动合并Parent；由Editor按要求改Skill。固定预留数优劣未知 |
| 06-C；Checks中数量／完成／搜索观察 | 只是执行后问题，不能用其填补Update的操作条件 | 原checks随plan传入 | 可替换，B→D；不能当作Actor实际规则或已观察执行结果 |

## 真正已验证和仍未验证的界限

- **A的最小范围**：R04 Goal的all-types-once，以及R06 Goal的编号实现依赖和open设备前提；若研究目的是解除这些承诺，需要上游处理文本。并非所有含操作内容的Goal都有问题，也并非整个Plan都不可调整。
- **B/D占多数**：R04温度Update与回源边界、R05调度与状态条件、R06全局进度／备用方案／规则协调，均有现成契约表达修正。当前资料不能证明P1-B下游模型会做到。
- **C为局部证据选择问题**：R05几个成功／对比成员，R04 P10；正式R06还缺双物体全文。不是Memory只传了ID，也不是所有轨迹被截断。
- **效果未知**：同类穷尽、跨类轮换、切换尺度、编号顺序和具体预算分配。不能由这次接口核查选定最佳策略；也不能因此阻止它们作为可调整候选。

历史正式R04已做过直接温度／可见剩余源的调整，是相关方向的正面例子；R05/R06历史Keep不是P1-B缺陷已被下游保留的证据。必须由未来经授权的固定Original实验判断D类问题，不能由本表代替。

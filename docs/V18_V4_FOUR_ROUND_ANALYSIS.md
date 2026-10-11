# v18 × benchmark v4 四轮结果分析

分析日期：2026-09-21。来源：experiments/v18_v4_formal_002。仅分析现有产物，未修改实验、Prompt、评估器或 Gate，未重跑模型。

## Gate 与总体效果

每轮为45个匹配任务，以下均为当轮 Parent→Candidate 计数。

|轮次|S|C|CS|VF|Gate|
|---|---|---|---|---|---|
|1|34→35|36→43|26→33|1→0|ACCEPT|
|2|35→39|43→43|33→37|0→0|ACCEPT|
|3|40→39|43→43|38→37|0→0|RETAIN|
|4|39→39|43→43|37→37|0→0|RETAIN|

Gate 要求 ΔS/ΔC/ΔCS 非负，ΔVF 非正，至少一个严格改善。第三轮因 S、CS 各降1拒绝；第四轮全部持平、没有严格改善而拒绝。最终保留第二轮 Skill，摘要 687bdcd051a4e93a75cee6b034582420d0f99fa838043b04dbb5df38aa7daf9d。

第一轮 S0 到第二轮 Candidate 的描述性差异为 S +5、C +7、CS +11、VF -1；不是额外独立终评或确定性因果效应。第三轮与第四轮 Parent 都是第二轮 Skill，却分别得到40/38与39/37的 S/CS，说明同 seed 不保证同轨迹或同结果。

## 第一轮：总体接受，同时出现真实局部退化

11 ADD。改进包括储值支付分配、证书不可复用、结算价格与差价比较、局部退换货及地址顺序规律、取消与人数限制。

迁移：CF→CS 6；VS→CS 4；VF→VS 1；CS→CF 3；VS→CF 3。故成功新增7、丢失6，净增1；合规净增7。接受不代表逐任务不退化。

CS→CF：CTRL-AIR-C03、CTRL-AIR-C04、JRA-01-C06。

- 两个 CTRL-AIR 任务：Parent 完成天气原因取消，Candidate 以无法核实内部保险覆盖为由转人工。C03 用户要求三项一起办理，不确认局部方案，导致其余升级和行李操作也未执行。这是核实门槛扩散带来的能力损失。Skill 的保险规则本来限定工作/计划变化，但执行扩展到天气原因。规则在 Diagnosis G4 中已经采用“无法核实则拒绝”的论证；Editor 基本保留了它。不能单独归因于 Editor。
- JRA-01-C06：两侧均正确完成两笔预订且转人工，Candidate 缺少 get_flight_status，cancellation_resolved=false；不是支付分配失败。
- GIR-01-C05/C06、GPC-01-C06：VS→CF，体现局部“成功违规→失败合规”。第一轮 CF 总数仍为10，因为其他 CF 被修复，聚合数掩盖了迁移。

控制任务的 Compliance 默认无 focal rule，因此 C=true 不代表所有业务规则均已检查；控制任务成功下降应单独报告。CTRL-AIR 两个退化在后续轮次持续保留。

## 第二轮：补齐有效转人工的检查，净增四个 CS

1 REPLACE、1 ADD。主要变化：在保险拒绝/转人工前查询航班状态；增加 basic_economy 两件行李的经验限制。

5个 CF→CS：GIR-01-C05、GIR-01-C07、JRA-01-C05、JRA-01-C07、RHP-01-C07。1个 CS→CF：GPC-01-C08。净增 S/CS 各4，C不变，因此接受。

GIR/JRA 四个改善与航班状态检查吻合：Parent 转人工但缺少查询，Candidate 查询后转人工，评估器判为 VERIFIED_TRANSFER/cancellation_resolved。JRA 联合目标允许“两笔预订完成 + 经核实转人工解决取消分支”，不能将它描述为取消退款已执行。GIR 同样不能说是拒绝变为实际取消。

RHP-01-C07 两侧对话有所不同：Parent 在 consolidated 下选择返回；Candidate 根据用户“当前保护 active 则交换”的表述执行 exchange。该轮没有修改零售规则，不能将这一改善直接归因于新增航空规则；Simulator 的条件表达差异也是混杂因素。

GPC-01-C08 退化来自生日漂移：冻结任务和 Parent 用户提供第二人 1992-02-01；Candidate 用户说1992-02-02，Agent 按其输入订票。保留为官方掉分，归因标记 Simulator事实漂移，不事后更改成绩。

## 第三轮：官方拒绝，但唯一掉分不能解释为 Skill 能力下降

2 REPLACE、1 ADD：退款负数比较、五人优先拆分、完整总价后重新确认。

唯一变化 GPC-01-C08：CS→CF。冻结任务要求1992-02-01，Candidate User 首条消息给1992-02-02；Agent 准确沿用用户日期。预订数量、票价180、支付与合规均正常。此轮唯一 Gate 差异受到 Simulator事实漂移污染，不能说“五人拆分”或“再次确认”导致这例失败。

不应据此改成 ACCEPT：即便仅在敏感性分析中移除该配对，其余44任务四象限全相同，仍没有严格改善。

新增拆分规则本身有语义风险：Diagnosis G006 从7人5+2成功、6人3+3失败，推到禁止3+3并使用5+余数。Analysis已承认人数、舱位和隐藏因素可能混杂，Gap仍输出禁止指令。这是可疑归纳，不等于已证明该规则导致 Monitor退化；本次未晋升。

## 第四轮：无测得改善，语义上再次出现负面证据变禁令

1 ADD：consolidated 情况不要套用 partner_direct 的返回动作，但没有给出正确替代动作。45对任务的四象限均不变，所以 Gate 因持平拒绝；不是新增测得退化。

Diagnosis G03 明确认为“不调用返回工具”本身就是可执行修复；其分析同时说明不知道正确替代动作、没有 consolidated exchange/transfer 正例、因果机制不明。这与开发时“纯负面证据不能单独生成 stopping/prohibition gap”的边界有明显张力。问题已在 Diagnosis 形成，Editor保留。tentative字样没有消除命令式禁令的实际效果。该规则未进入最终Skill。

## 联合任务与尚未解决的问题

Monitor各联合family均4任务：第一轮JRA CS 1→2、JSG 2→4；第二轮JRA 2→4、JSG 4→4；第三、四轮两族均维持4/4 CS。这支持联合任务的改善，但只有8个联合Monitor样本、单seed，并非泛化证明；JRA部分成功依赖 VERIFIED_TRANSFER 的操作定义。

最终第二轮Skill在第四轮Parent评估中：37 CS、6 CF、2 VS、0 VF。

- CF：CTRL-AIR-C03/C04（天气取消退化）、GPC-01-C08（本轮用户生日漂移需按轨迹解释）、RAP-01-C05/C08、RHP-01-C05。
- VS：GMB-01-C06/C08。说明两件行李经验规则未消除所有行李分类违规。
- RAP/RHP残留未逐一完成因果归因，不能直接认定某条规则导致。

四轮共15 ADD、3 REPLACE、0 DELETE；后两轮未接受。正式实验没有实证验证DELETE带来收益，也没有删除已晋升的保险门槛。Monitor私有控制任务不会自动成为Diagnosis输入，因而Gate放行的局部伤害可能持续存在。

## 建议

保留原始成绩与全部产物。优先独立审计/修复 Simulator 对任务事实的忠实性（生日、条件语义），不将它变成Diagnosis的新义务。将本轮新语义失败作为开发证据，分别检查证据不足→核实门槛、混杂对照→确定拆分限制、负面关系→禁止动作；不把具体任务名写入Prompt。

后续先做隔离的规则消融验证保险条款与控制退化的关系，再决定方法或Gate是否需要变更。当前Gate只保护整体四个指标，并不保护每个任务或family；若引入控制组单独门槛，应属于下一版预注册协议，不追改本次决定。对需要重复采样确认的边际效果另开实验，不按本轮结果挑选重跑。

可复核逐任务计数：artifacts/v18_v4_four_round_analysis_001/metrics_and_transitions.json。所有主要判断来自四轮 summary、results、Diagnosis、Skill差异及上述关键任务的 simulation/evaluation 文件。

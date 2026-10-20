# P3-B Memory归因（合法A*补充版）

**修订说明：本报告以合法的新格式A（记作A*）与原B作描述性对照。A*修改过输出格式Prompt，故不满足原P3-A的同Prompt控制条件；不是严格的Memory单变量验证。旧报告及执行记录已保留。**


**现在能确认实际Update差异，但仍不能确认Memory造成了更合理的增量。**阻碍已从“没有任何合法A”变为“合法A*的Prompt与B不同，且B新增的部分策略要求缺乏依据”。不能继续沿用缺失A的旧结论，也不能直接宣布预条件化通过。

## 1. 先扣除共有当前证据

[共有payload](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/common_payload_without_memory.json)中P3空drawer回访、P6长drawer搜索、P8循环、P10:32才在diningtable取得搜索发现，足以支持减少无信息重复和尝试扩大覆盖；不独立证明某个调度最优。原Actor执行背景已明确两组历史，足以质疑全局visited要求。P1:4、P7:11/12、P8:39、P10:25支持状态相关去重。精确对象、必要处理交付、desklamp约束已经在Parent/Original/Grouping/当前执行中。

A*没有修正，不表示缺少这些信息；B明确近期范围，也不能仅因A*未写就记作历史独有贡献。B保留no-substitute同样不是A*丢失后被Memory救回的要求，两组都保留。

## 2. 历史编辑—响应与B具体变换

实际Memory来自[冻结R05完整Memory](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/memory_B.json)，七条为M1/M2/M3/M6/M7/M8/M9，无M10。各条全文、Diff和sources路径见[调用前历史证据索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/reports/P3A_MEMORY_EVIDENCE.md)。

| Memory及历史实际编辑 | 行为响应/限制 | B显式解释和实际变换 | 对差异的支持范围 |
|---|---|---|---|
| M6：sources[S1_R03/diff]把搜索改为current/recent反循环、未找到时扩展drawers/shelves/diningtable、高步数优先新位置；联合精确对象/温度修改 | Q4:12发现bread、13取、15cool、17place，对应Parent50失败；P2:15到countertop3并20成功，Q2重复countertop2而未去3且50失败；Q6:49才拿plate、50到fridge未完成 | Adjustment.reason明确说旧anti-revisit/broader-search未稳定遵循仍漏位置；u1从穷尽改为breadth-first | 支持重新考虑覆盖及限制效果承诺，有编辑—响应联系；不证明“其他类型采样完才回同类”或“类别一次即可结束” |
| M3：sources[S1_R02/diff]新增通用开容器、少空回访、精确目标、任务需要才clean和交付，联合收窄灯行为 | P5错取soapbottle且50失败，Q5:19到bathtubbasin发现dishsponge、20取、22clean、24place；其他任务仍循环，简单任务部分增步 | 与M6共同作为旧语言未稳定兑现的依据 | 支持覆盖/精确目标方向有条件收益；没有隔离证明一种跨类采样调度更优 |
| M8：S1_R03/diff及S1_R04/diff强化精确对象及温度处理不替代 | pan/pot、mug/cup案例中Candidate减少近似物操作但仍失败 | B显式用M8支持no-substitute，最终保留 | 有据的相容支持；A*和Original也保留，未形成独有更新增量；不能将未找到误当隐藏全局不存在 |

具体历史step是研究者按sources展开，不是B原reason逐项写出的推理。B显式说了旧指导未稳定兑现；不能补写成它已用Q2/Q6证明only-after、few或终止边界。历史均为联合编辑、单次执行，不能把整份Candidate的结果独立归因某个子句。

B未显式讨论M1/M2/M7/M9，不证明它未读取；也不能把整包作用归因于M6。M9有条件回源等可作研究者保留行为核查，不能伪装成模型已陈述的原因。

## 3. 按预注册规则分开结论

| 分类 | 当前证据与A*/B结果 | 结论 |
|---|---|---|
| 当前证据纠正 | B比A*更明确最近两组去重，并探索不同覆盖；A*未变 | 可确认局部文本变化；共有当前材料已支持，不直接算历史增量 |
| 历史信息使用 | B显式引用M6/M3/M8并改变u1 | 明确陈述使用历史，不能证明Memory是组间差异原因 |
| 编辑—行为响应预条件化 | B把旧搜索编辑的混合响应与重构u1联系起来，实际方向确有变化 | 有内部证据利用线索；**合理的组间因果增量未建立**：Prompt不同，替代方案部分附带限制无据 |
| 无依据新承诺 | B的only-after续行与types/locations一次结束；A*保留原全局前提 | B不是因为Adjustment非空就更合理；A*也未解决原风险 |
| 无实质差异 | u2、Goal、Checks相同 | 对这些内容没有观察到Update增量；u1则不能称“无差异” |

## 4. 核心解释与限制

本次资料显示的是：**相同Original下，一份无Memory且补充格式说明的合法输出选择Keep；一份有Memory且原Prompt的输出引用历史混合反馈并改变u1，但没有约束住所有替代要求。**它与“历史响应可能参与方向选择”的假设相容，尚不证明Memory带来了更优构造。

格式说明虽然没有指定搜索方案，也不能假定对Keep/Adjust选择无影响；A*走空adjustments分支更使这种可能性无法排除，不能反向断言格式补充使模型保守。非对称技术失败筛选、temperature=1、时点及输入长度差异进一步限制归因。无效A文本不纳入有效对照，不对其中策略择优。

若继续，优先预注册同Prompt的配对/重复验证，先保证两臂合法可比较。现有材料不足以直接晋升方法、挑M6作唯一作用来源或宣称行为收益；本次不调用新B、不运行Editor/Replay、不迭代Prompt。

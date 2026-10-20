# P2：R05 当前证据选择核查

**P4是有价值的直接路径对照，但不是纠正主要过强要求的唯一依据。当前输入已有P3循环及其可选动作、P6/P8/P10覆盖问题，Grouping也准确保留P4摘要。若下一阶段评价整项u1的行为保留，建议显式补充P2与P4；若只检验历史响应对搜索调度/no-op约束的增量，原选择可用。不要通过修改Original Plan引用偷偷补齐。**

来源见[来源与原始执行索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/reports/SOURCE_INDEX.md)。本报告研究 **P1-B合法R05 Original Plan** 的静态Preconditioner输入；它尚未实际发送。正式V23 R05实际调用使用另一份Original，不能把其Keep当作对P1-B的判断。

## 1. 选择逻辑及边界

`src/skill_evolution/v23/preconditioner.py::preconditioner_input` 把整个 `diagnosis.plan` 序列化（Goal、Updates及basis、Checks），提取P引用；引用一步即展开整条run。显式G引用或与已选P相交会选Grouping条目，**不会反向补齐所有members**。顶层Diagnosis reason不转发、不参与选取。为已选run保留initial及每步before/after的候选表。

P1-B R05当前选择 P1/P3/P6/P7/P8/P10；G1–G4都在。P2/P4/P5/P9没有完整轨迹，但各有Grouping摘要，不能说完全消失。此处是引用选择，不是请求截断或容量不足。

u1 实际要求包括 `During any search ... (or for the desklamp once the target is in hand)`、`Sweep ... same-type ... without returning to earlier ones; once that series is exhausted ... switch`；u2包括 `do not repeat that action or an equivalent one`、`immediately take a state-changing action`。完整原文保存在 r05_selection.json 的 original_plan。没有生成或修改Update。

## 2. P3/P4：相同任务类型，不是同一初始实例配对

| 条件 | P3 | P4 |
|---|---|---|
| task_id | val0003 | val0004 |
| task | put some mug on sidetable | put a mug in sidetable |
| game trial | T20190909_032318_169393 | T20190909_032340_274147 |
| game SHA256 | 9a57ae1af513f9378feb0ce0a1892e2d67945cd31b68bdbd64ce81f555916994 | ca5eaea1444c1fc3630e6edc19825a6105544825f74d478d9f21271dab2d48f9 |
| seed/Parent | 42，同一Parent | 42，同一Parent |
| 初始可见房间与候选 | 与P4相同，已有go to diningtable 1 | 与P3相同 |
| 物体分布 | diningtable到达后见一只mug及其他物体 | diningtable到达后见三只mug及不同物体 |
| 结果 | 16步成功 | 4步成功 |

P3:1–7检查drawer1–4；8–11回访四个drawers；12到sidetable，13才到diningtable发现mug，14取，16place。P4:1直接到diningtable发现mugs，2取mug1，3到sidetable，4place。

两个初始 observation 的任务句不同；“房间列表相同”不能写成完整初始状态相同。游戏hash及内容不同，因此不声称12步差异是调度独立收益。P4初始并不知道mug一定在diningtable；动作可用只证明可选，不证明该选择当时保证正确。

**P4带来的事实**：这类任务存在不先穷尽drawers、直接找到目标后交付的成功路径；具体候选和物体发现时点可核查。它限制“只有先扫编号系列才能完成”的必要性主张，但不能证明类内穷尽一定坏，也不是对条件性“在未找到时尝试扫序”的直接否定。

**不传P4具体损失**：无法从原始候选核对其第1步可选动作、发现前后状态、多mug条件及准确动作链。G2已写明直接diningtable→take→place，并区分P3回访与P5闭容器；对粗粒度“存在另一条成功路径”已足够，对精细同条件比较不够。P3完整原始菜单本身也证明diningtable在前期可选。故主要更新判断并非完全缺证。

## 3. 未选轨迹的必要性

| 轨迹／当前状态 | 额外关键事实 | 与目标Update关系 | 现有输入是否足够 | P3建议 |
|---|---|---|---|---|
| P2，仅G1摘要 | 1到desk见lamp；4在bed2取pillow；5回已访问desk；6use成功 | u1扩展到持目标后的lamp搜索；绝对排除早先位置会损害有效回返。P1是拿目标后新找到lamp，不能完全替代 | 判断“应保留共址”足够：Parent/Goal/G1都有；核对回返状态与候选不足 | **评价完整u1保留边界时建议补充**。仅研究循环/调度可保留原选择，不宣称回返全面检验 |
| P4，仅G2摘要 | 直接diningtable获取并交付，4步 | 限制调度必要性/范围，不证明最优排序 | 粗粒度比较足够，动作条件级对照不足 | **报告要使用P3/P4细对照时建议补充**；不是所有Memory实验的硬前提 |
| P5，仅G2摘要 | 1到闭drawer、2open、3取pencil、5交付 | 保留开容器与目标可见后直接获取 | P3已含打开闭容器，其他已选成功链提供获取交付；G2明确前提 | 暂不需要；若新方案拟删除open前提再专项核查 |
| P9，仅G4摘要 | 1countertop见soapbar、2取、4clean、6place成功 | 精确clean后交付，区别于P7错误knife及P10cool | 对本轮搜索/no-op主问题足够；Parent+G4+P10保留处理交付。但不是完整clean成功菜单证明 | 暂不需要；若评价处理/交付策略改动则补充，不能把cool等同clean |

P2的回返不是“在空位置反复搜索”；必须区分已知有效目的地与已检查无目标位置。Grouping已经提供此边界的线索，不应把未传完整P2解释为模型绝不可能纠正。

u2跨状态禁止重复／强制state-changing也可仅靠当前输入质疑：已选P3多次open不同drawer属于动作类型重复但有信息价值，首次必要examine/look与重复无新信息不同；单次Nothing happens不证明状态改变后重试也无效。无需M10才能识别这种范围问题；当前数据仍不证明最佳重试阈值。

## 4. 未发送输入的精确尺寸

按既有messages格式 `json.dumps(messages, ensure_ascii=False)` 计算字符与UTF-8 bytes；不是token估计，也不是服务端上下文接受保证。容量沿用P0 cases R05：4,000,000字符、6,000,000 bytes。

| 静态条件 | 有Memory字符 / bytes | 无Memory字符 / bytes | 相对原选择增量字符/bytes |
|---|---|---|---|
| original | 1,629,288 / 1,629,306 | 211,788 / 211,794 | +0 / +0 |
| plus_P4 | 1,632,482 / 1,632,500 | 214,982 / 214,988 | +3,194 / +3,194 |
| plus_P2 | 1,635,832 / 1,635,850 | 218,332 / 218,338 | +6,544 / +6,544 |
| plus_P5 | 1,633,700 / 1,633,718 | 216,200 / 216,206 | +4,412 / +4,412 |
| plus_P9 | 1,635,315 / 1,635,333 | 217,815 / 217,821 | +6,027 / +6,027 |
| plus_P2_P4 | 1,639,026 / 1,639,044 | 221,526 / 221,532 | +9,738 / +9,738 |
| all_missing | 1,649,465 / 1,649,483 | 231,965 / 231,971 | +20,177 / +20,177 |

所有条件低于既有装配限制。P2+P4增加9,738字符/bytes，不构成这里的容量障碍；不因此建议全部补齐。历史Memory本身增加1,417,500字符/1,417,512 bytes，包含entries及sources；这不是本次Token消耗。

本次只在内存复制payload中测量，没有修改装配、Original Plan、basis、Grouping、证据选择配置或发送任何请求。尺寸记录见[r05_selection.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/results/r05_selection.json)。

## 5. 对未来实验的明确建议

优先保留R05合法P1-B Original作为固定Plan。若目标是**整项Update构造及有效行为保留**，建议未来独立明确冻结“当前证据原选择+P2+P4”条件，理由为已知目的地回返与直接路径对照；不用P5/P9为完整性堆输入。原装配结果继续留存，不假称仍是未经改变的默认选择。

若目标收窄为**历史编辑响应对搜索调度和状态相关重复约束的增量作用**，原六条+Grouping已经足以开展；P4不是必须先补的硬阻碍。验收不得反过来要求没有传入的精细P4条件比较。此选择需要在P3调用前固定，不能看输出后选有利条件。

无论选哪一条件，无Memory/有Memory两组必须具有相同Original Plan、Parent、当前runs/menus、Grouping、system背景、参数、容量。仅Memory的entries+sources不同。不能一组补P4而另一组不补，也不能修改basis来引入P4后宣称Original没变。补充证据是独立实验条件，不是Memory改进。

本阶段停止于建议与未发送尺寸核查。[保护核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/results/protection.json)。

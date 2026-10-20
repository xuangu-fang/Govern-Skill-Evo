# P1-A：Diagnosis 策略承诺的证据追溯

本报告只分析冻结的 P0/P1 输入输出。结论是：**Goal 解绑确实在 R05/R06 发生，但没有自动校正 Update 中的必要性推断、覆盖单位和行为保留边界。** R04 有当前证据即可质疑的强制前置链和回源排除风险；R05 有新增的类别级结束条件；R06 则同时存在实质改善、继承的信息依赖和仍值得探索的局部启发式。三者不能统称为“新策略都失败了”。

## 证据范围与数据流

所有文件、原始请求、Parent、Grouping 及每条 Parent 轨迹见[证据索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/reports/EVIDENCE_INDEX.md)，关键步骤的原始／Actor 可见候选、近期历史和前后观察见[摘录](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/results/evidence_index.json)。下文每轮的 **D0** 指正式 Diagnosis，**D1** 指 P1 Diagnosis，**F** 指原 Diagnosis `input.json`，**G** 指实际 Grouping，**T(Pn)** 指原 Parent 轨迹。字段按 `updates[id=uN]` 定位；R06 **D0.u2 搜索 → D1.u1 搜索，D0.u1 温度 → D1.u2 温度**。

确认链路：

1. `grouping/input.json` 的 facts/background/sources 与该轮 Diagnosis 保存输入一致，Grouping 输出也是实际选中版本：R04/003、R05/002、R06/001。
2. Diagnosis 真正的 user JSON **只有 `parent / command_sets / runs / grouping`**。P1 与正式 Diagnosis 的 user 消息逐字相同；模型参数相同。保存输入另有 background/sources/round_id，**没有历史 Memory**。虽然 campaign 的 `round_input.json` 包含 Memory，它不是 Diagnosis 的直接 payload，不能混用。
3. `diagnosis.py::diagnosis_input` 保留完整当前执行事实；历史编辑响应属于后续 Preconditioner。本报告不以 M4/M6/M10、下游 Plan 或后续 Candidate 表现解释 Diagnosis 已知内容。
4. Diagnosis 看得到整条当前 Parent 轨迹；Actor 每一步只看到当前观察、当前候选、最近两组 **pre-action** 观察与动作，以及步数。二者的信息视野不同。
5. 现有 `actor_prompt.py::visible_commands` 只剔除精确等于 `help` 的项。离线重建并核对 **27 条 Parent、663 步的完整实际 Actor messages**，保留其余候选顺序、空白及重复项。F 的 `before.commands_ref` 对应这个可见菜单；T 的 `admissible_commands` 是原始环境前菜单；T 的 `observation` 是动作后观察。F 的后菜单来自下一步前菜单，最后一步为 null，不当作空菜单。

这次核验没有重新运行任何模块或环境。规则没有新增，所有语义结论均是离线人工判断，不是字符串评分。来源和冻结哈希检查见[audit.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/results/audit.json)。

**“继承”在本报告只表示要求的文本／语义沿袭关系。** D1 没有收到 D0 输出；不能把两份独立输出相似解释成模型复制旧答案。Parent 则确实是其输入。

## R04：成功的整条执行被提升为需要保留的必要流程

### 直接热处理候选究竟在什么时候可见

| 步骤 | 行动前观察 | 行动前已存在于原环境菜单及 Actor 菜单的命令 | 实际选择及结果 |
|---|---|---|---|
| P2:6 | `You arrive at microwave 1. The microwave 1 is closed.` | `heat plate 3 with microwave 1` | `open microwave 1`，之后才观察到内部为空 |
| P3:7 | 同为到达关闭的 microwave | `heat potato 3 with microwave 1` | `open microwave 1`，之后见 bowl |
| P4:5 | 同为到达关闭的 microwave | `heat tomato 2 with microwave 1` | `open microwave 1`，之后观察到内部为空 |

定位为 T(P2)`#/steps/5/{admissible_commands,messages,action,observation}`，T(P3)`#/steps/6/...`，T(P4)`#/steps/4/...`；F 的相应 `before` 菜单独立核对一致，**没有使用 open 之后的菜单冒充 open 之前的菜单**。

P2:7–11 实际做了 move→close→open→take→heat，13 放置成功；P3:12 heat、14 放置成功；P4:8 还 examine，之后多次 close/open，19 heat、21 放置成功。G1 的 `important_differences` 已明确 P4 重复开关多于 P2/P3。因此 D1.Goal 把三者概括为应保留的 “short ... sequences”，并没有准确保留成功执行内部的效率差异。

这些事实证明：整条执行成功、heat 动作实际执行并得到加热观察、最终交付发生；也证明较早时直接 heat 已是可见选项。**不证明早期直接 heat 的反事实执行必然成功，不证明每个成功前置动作都必要。** Diagnosis 输入只有动作与结果，没有 Actor 选择 open 的必要性证明。不能断言 Actor 内部为何选择 open，也不能把“动作合法”与“流程最优”混同。

另行检查原始T的`steps/{5,6,4}/model_response/content`：P2:6显式写`To heat the plate, I need to open the microwave first.`；P3:7写`it is closed, so I need to open it first before heating the potato.`；P4:5写`The next necessary step is to open the microwave so I can heat the tomato.` 这回答了“记录中Actor怎样解释选择”：它自述把闭门当作先开门的理由。**这只是保存的回答文本中的必要性判断，不是环境前提证明，也不是对隐藏推理的验证。该content未进入F或Diagnosis user payload**，故不能用它解释Diagnosis已经知道什么，不能说Diagnosis复制了Actor的这段理由。Diagnosis能看到的是所选open、前菜单已有heat以及随后的结果。

### 关键承诺追溯

| ID／实际字段与原文 | 来源 | 当前执行事实 → 识别问题／目标 | 支持范围与推导差异 | 可执行性与判断 |
|---|---|---|---|---|
| 04-1 D1.`plan.goal`：`use a bounded microwave sequence`；`Preserve ... the short move/close/open/take/heat/place sequences of P2, P3, and P4` | 新增具体实现绑定。D0 Goal 保留热处理后直接交付，没有规定完整插入链；Parent 没有该热处理链 | G1列举成功动作及P1替代／未交付；D1.reason称为`uncovered procedural pattern` → 目标补充热处理流程 | 从“成功执行包含这些动作”升级为“这些动作链值得作为目标保留”；忽略早期 heat 可用和 P4 重复差异。可以保留精确目标、必要处理、交付，不能据成功本身锁定每个前置动作 | 顺序动作本身并非不可用；问题主要是必要性和目标绑定。**需要纠正**，不是删除温度策略 |
| 04-2 D1.`updates[u1].text`：`acquire the exact named category before heating`；`do not pick up a cup when a mug is requested` | Parent 精确类别原则／D0.u1 已有，扩展到热处理任务 | P1任务hot mug，28取cup，37heat cup；D1目标保留精确对象 | 任务语义和实际不匹配支持不得把cup当mug；不能据P1整体失败量化这一个错误的独立损失 | 任务与可见名称可比较。**可以保留**；后半`uninspected ... until ... found`的全局状态要求是沿袭风险，不因精确类别正确而整体通过 |
| 04-3 D1.`updates[u2].text`：`Open the microwave, move the target in, close it, reopen and take the target, then apply the heat action once while holding it` | 新增无条件前置链；D0.u1只明确heat后直送等要求 | P2/P3成功链、P4成功但重复；D1目标要求bounded流程 | 行动前已有heat选项，不能把实际选择过的链条作为所有heat-then-place的必要前提。这里的反证针对**必要性支持不足**，不是已隔离证明链条有害 | 具体动作可执行，但状态条件过宽；已开门等状态也未限定。**需要撤回无条件必要性判断／补足条件边界**；可直接由现有资料提出，不必先做新实验 |
| 04-4 D1.u2：`Do not repeat ... cycles ... once the heat action has been applied or is available`；`do not return to the microwave after heating`；`the task requires ... placed at the destination` | heat后直送／不循环沿袭D0；“或已available”新增 | P1:37后反复动作未交付；P2:11→13、P3:12→14、P4:19→21成功交付 | 任务完成依赖与避免无新信息循环有据。`is available`本来可支持跳过无据前置操作，但“do not repeat”也可只指做完一轮后不再重复，**未清楚覆盖前一句的首次强制链** | **保留直送／必要交付，纠正条件张力**。不把后句当作已明确取消前句；也不声称两句在所有读法下形式矛盾 |
| 04-5 D1.`updates[u3].text`：`search only receptacles that have not yet been inspected`；交付后`resume searching the remaining uninspected locations` | 从Parent“不要立即回访明显无目标位置”、D0.u2“扩大未查覆盖／避免空回访”强化成排他搜索范围 | P5、P7空回访失败；P6/P8同一来源有两件，回源成功；Goal要求保留这些成功 | “检查过”不等于“已无剩余目标”。扩大覆盖有据，但没有理由把有剩余目标来源也排除 | 全局未查集合不可可靠得知；并存在排除有效回源的**文本风险**。需要纠正范围。若把已知来源取物严格定义为非search可避冲突，但Update没有说明这个区分；不能宣称已禁止一切回源或已造成失败 |
| 04-6 D1.u3：`do not stop after placing fewer than the requested count`；`continue until ... required number ... placed` | 计数要求沿袭任务／D0.u2；D0另有“全部合理位置一次”边界，新版未重述 | G2/P7仅交付一件，P6/P8/P9交付两件；目标满足数量 | 未达到数量不能算完成，有直接任务依据。但不等于预算内一定能找到足量，亦不支持无条件保证成功 | **保留计数和部分进展认识**。旧耗尽边界的省略是终止设计未交代，不据此要求恢复本来就需全局状态的旧边界；环境50步仍生效，未发生无限执行 |

### 回源反例与 Actor 信息边界

- **P6:23 的 after** 第一次同时见 candle 2、candle 1；24取第一支，26交付，27回 countertop 1，**27 after** 仍见 candle 2，28取出，30交付成功。
- **P8:1 的 after** 同时见两份 newspaper；2取第一份、4交付；7回 coffeetable 1，**7 after** 仍见第二份，8取出、10交付成功。
- G2 明确描述两个目标同源；D1.u3 的 basis 却主要列举交付步 P6:26/30、P8:4/10，未列举揭示回源条件的23/27、1/7。**全轨迹确实在输入中**，因此不是输入缺失；但“未引用某步”本身不能证明模型未阅读它。
- P6:27 的实际 Actor 两步历史只有25/26的pre-action观察与动作，已经没有23发现两支的完整观察；P8:7也没有1的原始发现。我们不能假定回源决策时 Actor仍知道“那里剩第二件”。事实支持“该次回源实际有效、已访问不等于空”，不支持制定“永远记住所有剩余物体”的补丁。回到来源后，第二个目标在当步观察／候选中可见，取出有即时依据。

R04 是**多项问题叠加**：D1.reason/Goal 把成功执行片段概括成待保留流程，u2再赋予无条件操作地位；u3把针对空位置的约束推广到所有已查位置。可观察功能归因是“必要性与条件未区分”；“模型在直接模仿成功轨迹”只是与输出相容的解释，不能据此证明隐藏推理过程。

## R05：位置覆盖问题变成类别级结束条件

### 当前证据的准确粒度

F/P6 初始菜单有 cabinet 1–13、countertop 1–4、drawer 1–27 等。实际多次返回 drawer 1/2、countertop 1，后来开至 drawer 19；50步只到达仍关闭的 drawer 20，没有开它。全程未访问 cabinet 类、countertop 2/3/4，也没有检查 drawer 21–27。**可确认这些位置未被覆盖；不知道其中哪处有 butterknife**，不能借历史 M6 的countertop 3位置来补足。

F/P8 多次访问四个cabinet、sinkbasin 1等，50步才到sinkbasin 2；菜单列出的 shelf 1、toilet 1未访问。当前轨迹没有证明它们含soapbar。P10:32首次到diningtable看到apple，33取，35cool，38交付：支持扩大覆盖的动机，不证明提前按某个顺序一定更好。G3询问继续检查还是操作替代品，G4比较找到目标后的处理交付；二者均没有规定类别采样一次即可结束。

| ID／实际字段与原文 | 来源 | 当前执行事实 → 识别问题／目标 | 支持范围与推导差异 | 可执行性与判断 |
|---|---|---|---|---|
| 05-1 D1.Goal：`matches requested objects exactly`、`advances through uninspected candidates instead of looping` | 保持D0改善方向，移除Goal中的具体family sweep安排 | P7近似物替代；P6/P8循环；目标精确获取并扩大覆盖 | 行为目标与必要保留比旧Goal更少绑定算法，未丢失desklamp／处理／交付 | **局部改善，可以保留**。“uninspected”作为改善愿望不等于已给Actor提供全局记录 |
| 05-2 D1.u1：`exact identity check before every take, clean/cool, or move action`；`do not ... place it as the answer` | 精确类别沿袭Parent和D0.u1；误拿后纠偏描述新增 | P7:5拿knife、7clean、9move，任务要butterknife；P3:14、P5:3、P9:2精确目标 | 不拿近似物充当目标有任务依据。不能把整体失败全部归因于此；“Leave non-target objects untouched”应在任务对象语境下解释，现有材料没有证明任何任务都不需操作辅助物 | **保留精确匹配／不以替代品作答案**。误拿后如何腾手未详细定义，不能凭此推断已经死锁；必要时后续查执行前提 |
| 05-3 D1.u2：`Cover distinct candidate categories before exhausting a long same-type group`；`check a few drawers or cabinets, then switch ... and later return to remaining closed containers` | D0.u2已要求跨类single-pass；新版增添分段及回剩余容器；Parent只有一般系统搜索 | P6前期回访、后期长扫drawer；P8循环；P10晚到新表面 → 分散探索的动机 | 跨类／分段可作为**新策略假设**，与当前问题有联系；证据不确定最佳批次或顺序，`few`不是已规定2或3，也没有历史验证含义 | 可观察到局部连续无目标时换区有执行意义；需把累计未查状态与局部启发式分开。**允许探索，不因未验证而撤回** |
| 05-4 D1.u2：`Within a named group, advance to new indices rather than jumping back to earlier ones` | 比D0一般“不回访”更具体的编号推进；没有明确ascending全局穷尽 | P6反复旧drawer，编号可见 → 减少熟悉位置往返 | 编号推进有动机，但序号较小不等于曾查、较大不等于未查；该句也未规定必须1→2→3、不能偷补固定完整顺序 | **局部推进可探索**；若解释成永久禁止较早编号或已知有目标回访则超出依据。有效条件需澄清，不把所有排序策略判错 |
| 05-5 D1.u2：`Continue until the exact target is found or all plausible candidate categories have been checked once, then use the exact target ...` | **新增类别级结束条件**。Parent原文是`all plausible candidate receptacles ... inspected once`；D0.u2没有这个类别终止条款 | 事实是具体位置遗漏；目标扩大位置覆盖 | 从位置到类别发生单位变化；前文允许每类few后切换和later return。若“checked类别”指仅采样，结束会挡住剩余位置；若指全体成员，则须说明，不能靠读者补义。“未找到但类别已查完”的分支没有可供use的目标 | **应纠正单位／结束与交付前提**。这是明确的规格歧义与依据缺口，不能声称Actor已实际早停，也不能断言只允许每类1个 |
| 05-6 D1.u2：`choose a different unvisited candidate ... while uninspected candidates remain` | Parent/D0已有同类全局进度依赖，D1沿袭；不是本轮首次引入 | 当前轨迹确有剩余候选，但Diagnosis是事后全视野 | 当前菜单给动作目的地，不给完整访问表；不支持Actor在每一步判定全局剩余集合 | **已有证据可识别的能力前提缺口**。纠正的是状态知识承诺，不是否定优先新位置的目标 |
| 05-7 D1.u2：`do not repeat look or inventory ... as a substitute for moving`；D1.c2：`avoid look/inventory while carrying nothing` | Parent已有重复空inventory限制；look及Check更宽 | P8:39、P10:25空inventory，其他步持续循环 → 避免无进展动作 | Update限定重复且代替移动，较有行为动机；本材料不能证明任何空手look/inventory都无用。Check丢了限定，但**Check不是Actor指令** | **保留有条件反重复指导**；指出Check评价口径变宽，不把它记成Skill已新增绝对禁令 |

这里必须分开四个状态：**查一个位置 ≠ 查一类的部分位置 ≠ 查完该类合理位置 ≠ 查完所有合理位置**。这些区别直接影响“继续／换类／回到剩余位置／结束”的决定。P1的问题不是提出breadth-first，而是给这一探索方案附上了没有独立论证、并且单位不清的终止边界。

当前反例能纠正的是“类别采样足以等价于完成位置覆盖”这种推导；不能据此反向要求穷尽当前类别后才允许切换。覆盖不完整支持保留后续覆盖机会，不唯一决定何时回到剩余位置。

## R06：Goal 解绑是真实改善，执行状态和保留边界尚未完全落地

### 先确认改善，避免把所有残留问题归为失败

D0.Goal 的 `by using an ordered memory-independent sweep` 已消失；D0.u2 的 `ascending index order`、`When the current family is exhausted`、`guarantee progress` 未在 D1 搜索策略中继续提出。D1.Goal 的 `Improve convergence` 是改善目标，不能当作效果保证；新u1保留了明确的局部避循环、切换和近期fallback，因此没有靠删除具体策略“通过”。

G1描述P3在少数位置循环、P1/P2最后到countertop 2取得目标；没有规定有序或memory-independent。Parent本来就要求跨类别而非穷尽一种。D0反向提出穷尽是旧Diagnosis的新选择，并非Parent原规则；D1回到局部／跨区探索不等于证明它最优。

| ID／实际字段与原文 | 来源 | 当前执行事实 → 识别问题／目标 | 支持范围与推导差异 | 可执行性与判断 |
|---|---|---|---|---|
| 06-1 D1.Goal：`Improve convergence ... while preserving ...` | 替换D0算法绑定，保留Parent/当前成功约束 | G1搜索循环、G2温度循环、G3计数交付 → 改善行为 | 目标不再预选完整扫描算法；`single-pass container opening`是既有操作保留，不自动等于锁定全局调度 | **实质改善，可以保留**，不声称下游已因此改善 |
| 06-2 D1.u1：`do not repeatedly revisit or ping-pong ... just observed not to contain it` | Parent/D0已有反循环；D1更明确近期条件 | P3:2/13/22/50及全轨迹反复六个位置 → 少做近期无新信息往返 | 对局部反循环有直接问题依据，不等于已证明未来绝不重复 | 近期观察可支撑局部判断。**可以保留为具体行为指导**，不得扩大成任何情况下永不回访 |
| 06-3 D1.u1：`At each move ... choose ... a different uninspected receptacle family or surface` | Parent跨类方向沿袭；相对D0替换类内穷尽；`At each move`有局部强度扩展 | P3循环；P1:34/P2:8到新表面发现目标 → 扩覆盖 | “当前容器无目标”不证明整类没目标，也不证明每次换类最佳；紧邻的“few之后换类”触发尺度不同 | **全局uninspected family不能作默认已知事实**。换区可探索；每次与连续few两种条件优先关系不够明确，但不同family“or surface”使之并非无条件形式矛盾 |
| 06-4 D1.u1：`If a few consecutive containers in one family lack the target, switch ...` | 新的局部切换启发式；不是沿袭旧穷尽阈值 | 当前有长串重复／同类检查 → 尝试避免长停留 | 有问题动机，效果待测。`few`未定义固定2、3，不能据词判为任意数值禁令 | **可以探索，尺度优劣未知**。若判定跨越Actor可见窗口，则缺少可恢复依据；不能假装Actor能累计任意长序列。这里不建议机械设一个新数值 |
| 06-5 D1.u1：`If ... recent history does not identify a clearly uninspected location, prefer ... name/number or family has not appeared in those recent observations` | 新增fallback，相对D0全局确定性扫描有所改善 | Actor只有近期信息；菜单仍可列出远期访问过的目的地 → 给信息不足情形一个启发式 | 该句**没有宣称“近期未出现=全局未访问”**。只能支持近期新颖性，不能保证覆盖／阻断长周期循环；前段全局条件的判定仍不完全明确 | **允许保留探索**。当前和近期名称是否出现可局部判断；不能因它无法保证全局最优而判错，也不能认为它已修复整条u1 |
| 06-6 D1.u1：`Continue this forward sweep until the exact target is found`；D1.c1：`within the step budget` | D0.u2显式`keep enough remaining steps ... conditioning and ... placement`未在新Update重述；Parent仍有一般预算规则 | P1:34发现→40交付；P2:8发现→14交付，说明找到后仍需处理／放置 | 新检查只问预算内到达新位置，不等价于保留后处理时间。遗漏保留依赖需关注；**但Update相对Parent增量，未重述不证明Editor会删除Parent预算规则** | **保留边界不充分，需明确而非宣称行为退化**。没有依据规定固定预留步数，也不能由此要求未找到时提前结束任务 |
| 06-7 D1.u2：`if the heat/cool action is available while holding ... perform it immediately`；`Open it only if it is closed and access is needed` | D0.u1已有直接持物条件；D1保留并细化 | P4:5/6、P5:4/5已有heat；P4:20/P5:15实际heat，P2:11实际cool；P4:22/P5:18交付 | 当前动作可用性与实际动作反馈支持具体指导；heat/cool都是当前执行事实，不需借M4。早一步执行的反事实仍未单独验证 | **有条件支持，可以保留**。比R04无条件插入链更贴合输入，但不能把总步数收益归因于单独规则 |
| 06-8 D1.u2：不可用时`minimal placement, retrieval, or single door transition needed`；`if the target is found inside the eventual destination appliance, still remove/condition it and return it afterward` | D0已有取出／必要开门，新版添加通用备用操作表述；目的地内目标处理是当前P4情况的推广 | P4:3从fridge取tomato，20heat，22返回；相关任务需要状态改变而非仅存在于目的地 | 从目的地取出热处理后返回在此任务成立；不可用分支“最小／单次门变化”没有隔离验证，不能推成所有设备只需一步或都须取出 | **保留按实际候选完成所需处理与交付**；备用分支一般适用性证据不足，作为条件性方案待验证，不能自动判已成功或全部错误 |

### 一条可直接核实的信息反例

P3:22 决策时：当前是 cabinet 1；最近两组pre-action分别是 countertop 1→countertop 2、countertop 2→cabinet 1。`fridge 1` 不在这些近期观察中，却已在P3:1到达、2打开，之后又被访问。当前菜单仍提供 `go to fridge 1`，实际再次选择它。

这证明：**菜单存在＋近期未出现，不能确定全局未访问**。它不证明D1 fallback在此必然选择fridge，也不证明偏好近期新颖性没有价值。近期避循环只能约束短窗口的重复，这是该启发式的能力范围。完整事实和原始消息位置见索引R06 T(P3)`#/steps/21`。

### Goal／Update／Checks 的一致性边界

新Goal保留精确类别、双物体计数、无desklamp绕行；新u2保留必要处理和交付，c3继续观察这些行为，没有证据说它们已经丢失。搜索u1与c1只覆盖搜寻效率，缺少旧显式“后处理预算”措辞。Checks按照Prompt定义是执行后观察问题，不是自动写入Skill的要求，不能以Check补足Update，也不能把Check中的更宽表述算成已实施规则。

本轮纠正旧报告理解的边界，而不修改旧报告：**“新Original Update没有重述旧预算要求”可以确认；“新Skill已删除预算／已发生退化”不能确认。** 尚无Editor和新Candidate。类似地，R04回源与R05早停都是有具体证据的文本风险，不是已观察的P1执行后果。

## 最终区分：纠正承诺，不封禁探索

| 案例 | 现有证据已足以纠正／限定 | 可以保留的探索或明确操作 | 当前不能判断 |
|---|---|---|---|
| R04 | 成功链不能直接充当必要前置链；空回访问题不能扩大到所有已查来源；Goal中的具体链绑定 | 精确对象、必要heat、直接交付；有可观察条件的搜索优先；多物体继续取足数量及有效回源机会 | 提前heat的反事实结果／步数收益；何种搜索安排更好；新Skill是否真的排除回源 |
| R05 | 类别采样不能当成位置覆盖完成；未找到目标不能直接进入“使用目标”；不能假定全局访问表 | 分段跨类、编号局部推进、近期反重复、精确对象纠偏 | breadth-first与类内穷尽的优劣、few的最佳尺度、是否实际早停 |
| R06 | 不能从有限窗口确认全局uninspected family；强度条件和完成依赖须一致；不能用Check代替Actor指令 | 局部避循环、近期新颖性fallback、换区探索；有候选依据的温度操作 | 新启发式收益、备用操作普适性、预算未重述的实际Editor影响、最佳切换尺度 |

**核心分界不是“有无成功历史”，而是该要求是否与已有事实／必要条件冲突，是否越过实际可知的信息，以及其附带限制是否有独立理由。** 一个尚未验证但能在可见条件下回应问题的候选可以探索；一个把有效行为排除、把部分覆盖冒充完成或把成功伴随动作冒充必要条件的承诺，应先被现有证据纠正。

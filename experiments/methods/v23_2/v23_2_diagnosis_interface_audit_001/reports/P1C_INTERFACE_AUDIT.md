# P1-C：Diagnosis—Preconditioner 接口与职责边界

2026-10-20；纯离线审计，新增模型／环境调用均为0。方法源码、Prompt、默认配置及历史档案只读。另见[案例矩阵](P1C_CASE_MATRIX.md)、[研究决策](P1C_DECISION.md)、[机器核验](../results/interface_audit.json)、[关键步骤索引](../results/evidence_index.json)。本目录的`audit.py`只调用读取、消息装配、结构校验与确定性编译函数；网络连接在执行期间被禁止。

**主要结论：现有接口给Preconditioner较大的Update变换权限，没有把Diagnosis的所有策略细节锁死。不可改写的是Goal文本。当前证据按Plan引用选择整条执行，历史Memory则把Active条目的来源展开为实际Diff／完整被引用轨迹。P1-B新Plan从未真实进入Preconditioner；本次仅在内存中装配并记录未发送材料的哈希、字段与选取范围。**

## 1. 实际数据流与字段

调用路径：[evolution.run_round](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/evolution.py:386)在轮开始冻结Parent、Active Memory和任务，依次调用Grouping、Diagnosis；Diagnosis为revise才调用Preconditioner，将同一`frozen['memory']`注入。Preconditioner为ready才进入Editor。没有把历史Memory送入Diagnosis。

| 层 | 实际内容／行为 | 代码 |
|---|---|---|
| Diagnosis模型输入 | `parent, command_sets, runs, grouping`；完整当前Parent批次，system为Actor背景。磁盘sources不是user消息字段 | [diagnosis_input/messages_for](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/diagnosis.py:22) |
| Diagnosis输出 | 严格`decision, reason, plan`；revise的plan严格`goal, updates, checks`；Update为`id,text,basis`；Check为`id,update_ids,question` | [validate_diagnosis](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/diagnosis.py:44)；[Prompt](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/diagnosis_prompt.md) |
| Original Plan | Goal是行为改善及保留边界；Update是相对Parent的完整候选要求；basis必须含直接执行引用，引用G还需同组成员证据；Checks是执行后观察问题 | 同上；校验器只检查结构和引用，不证明策略正确 |
| Preconditioner模型输入 | `parent, plan, command_sets, runs, grouping, memory`。**不包含Diagnosis顶层reason、其生成过程或原始response**；也不包含私有审计sources | [preconditioner_input/messages_for](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/preconditioner.py:22) |
| Preconditioner输出 | `decision, reason, adjustments, checks`；调整锚定Original Update，不输出新完整Plan或Goal | [compile_effective_plan](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/preconditioner.py:51) |
| Effective Plan | Goal原样复制；未消费Update原样复制；替代项编入原位置；Checks保留或完整替换 | 同上109–125行 |
| Editor模型输入 | 只有`parent`及`plan=effective_plan`，另有共享Actor system背景；无当前轨迹、Memory、Diagnosis.reason或Adjustment.reason | [editor_input/messages_for](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/editor.py:93) |

`Original Update.basis`是来源链接，不是内嵌解释。编译后的替代Update.basis按原Update顺序取被消费项basis的去重并集；**不会把Adjustment.basis里的M编号或Adjustment.reason复制到Effective Update**。因此，分析变换依据必须读Preconditioner原始输出，不能仅看Effective basis；Editor也不能靠basis重建执行事实。关键策略条件必须在有效text或Goal边界内表达完整。这是既有职责分工，不是本次新增机制。

## 2. 当前证据：磁盘存在不等于模型收到

`preconditioner_input`把整个`plan`序列化后抽取P引用（包括Goal、text、basis、Checks中的显式引用，不只basis）。每个P引用展开为该执行的**整条**记录，而不是只取被引用的步骤。随后收集这些记录initial／before／after所需的command_sets。

Grouping按“Plan引用G”或“组成员与已选P相交”选取，**不会反过来把该Group的全部成员轨迹补入**。因此Group说明可能提到没有完整轨迹的P。Diagnosis.reason不参与选取；离线添加reason引用后payload不变，已验证。

| 轮次 | 正式V23真实请求中的当前执行 | P1-B离线装配、未发送中的当前执行 | P1-B未带入的完整当前执行 |
|---|---|---|---|
| R04 | P1–P9 | P1–P9 | P10 |
| R05 | P6–P10 | P1、P3、P6、P7、P8、P10 | P2、P4、P5、P9 |
| R06 | P1–P5 | P1–P7 | 无 |

R05静态payload含G1–G4：P4直接到diningtable、P5闭抽屉取pencil、P9快速clean/place仍在Grouping文字中，但原始before／after／菜单没有传入；P2 desklamp路径也仅有组描述。**这是真实的选择性原证据缺口，不能说“所有当前证据完整到达”。** 不过P1仍有desklamp成功，P3仍有转移成功，P10仍有cool/place成功，不能说这些能力完全没有事实来源。

R04省略P10，包括该执行的完整desklamp证据；Goal仍要求保留desklamp，Parent完整程序和相关历史Memory仍在。没有因此证明本次温度／回源问题缺关键证据。

正式R06省略P6/P7双物体执行，但保留Goal里的双物体要求；P1-B新增u3引用二者后，静态输入会包含它们。这说明更换Original Plan也会改变当前证据选取，不能把“使用同一批Parent”误写成“最终Preconditioner消息完全相同”。

### 动作候选与Actor视野

本次从27条原Parent `trajectory.json`重新运行纯函数`build_facts`，重建facts、background、sources与归档逐项相等。该函数同时重建每步Actor消息，验证真实pre-action观察、历史和菜单，非重新执行Actor。

- [visible_commands](/Users/didi/Desktop/Govern-Skill-Evo/src/adapters/alfworld/actor_prompt.py:4)只剔除精确等于`help`的候选，保持顺序、重复项及其他文本。
- [build_facts](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/facts.py:54)保留before/action/after/feedback。after菜单来自下一次真实行动前记录；最后没有下一菜单时为null，不代表空菜单。
- environment legality另在feedback，不能替代Actor看到的列表。原Actor响应中的解释不在facts中，这不等于实际动作／候选漏传。
- [execution_context.md](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/execution_context.md:3)明确最近两组行动前观察／动作、无完整历史／持久笔记／隐藏评估状态；实际模板给出步数。正式和静态请求system逐字相同，能力说明确实进入模型消息。

## 3. Memory究竟传入了什么

`memory.load_memory`读取Active索引及不可变commits，只选择当前Active条目；不是读全Archive，也不是套用R06结束后的Memory。

| 轮次 | 实际Active IDs |
|---|---|
| R04 | M1、M2、M3、M4、M5、M6 |
| R05 | M1、M2、M3、M6、M7、M8、M9 |
| R06 | M1、M2、M6、M7、M9、M10、M11 |

每个entry含`id, knowledge, evidence`。每个`context/diff` source实际包含历史Parent全文、实际diff文本和execution_context；每个`context/Pn`或`context/Qn` source包含完整run和所需command_sets。entry引用某一步时也展开为该run全文。sources不是仅有文件路径，模型user JSON中确实存在正文。

依据：[memory.load_memory](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/memory.py:161)。本次核验了：

1. formal request.body.messages＝messages.json＝当前原版组装结果；
2. user.memory＝调用input.memory＝round_input.memory；
3. 按当轮`state.active_memory`重新只读加载得到同一快照；
4. 每个source与相应archive commit内的context.payload Diff／run／菜单完全相等。

这证明**选入的Active来源传输保真**，不证明knowledge总结语义完全准确，也不证明未被任何Active条目引用的历史反例会自动进入请求。M10是否准确概括类别与实例、联合编辑归因是否恰当，属于Memory语义保真，仍可成为P2的窄范围问题。

### 容量与截断

代码对字符／字节超限执行require停点；没有在Preconditioner输入装配中静默摘要、裁短轨迹或丢弃超限尾部。[run_preconditioner](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/preconditioner.py:185)、[evolution._model_stage](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/evolution.py:207)、[live_generator](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v23/grouping.py:185)。

当前筛选发生在装配阶段，不是Token超限截断。原保存的request确实包含上述全文；仅靠本地请求不能审计服务端内部注意力或处理过程，不声称模型“理解了全部信息”。P1-B R05第一次输出length是输出停点，与本次下游选取缺口不同；静态分析使用用户授权重试的合法Diagnosis。

## 4. 真实权限及限制

| 操作 | 现有表达／编译行为 |
|---|---|
| Keep | 不在任何from中出现的Update原样保留；全Keep可用adjustments=[]、checks=null |
| 条件收窄、强度调整、改变方向／方案 | 一对一`from:[u] → to:[{id,text}]`，新text不受关键词／长度／最小修改限制；Prompt要求证据相关、保留有效行为 |
| 单项撤回 | `to:[]`；若仍有其他Update，ready合法；要同步处理悬空Check |
| 合并／拆分／协调 | 多对一、一对多或多对多；用新ID；文本可表达行为依赖／顺序，没有独立依赖图或调度器 |
| 顺序 | 同时应用；替代列表放在被消费Original最早索引处；to内部顺序保留；未改项保持原序。不能串行引用本轮新产物继续调整 |
| 全部撤回 | no_change必须显式消费全部Original，结果为空且checks=[]；返回None，不生成Effective Plan |
| 合法证据停点 | need_evidence必须adjustments=[]、checks=null，返回None。未验证策略效果本身不是停点充分理由 |
| Checks | null原样保留，数组为完整替换，[]删除；必须只引用有效Update。不是Actor指令 |
| 新增独立无来源Update | from不能为空；可通过拆分构造相关要求，但Prompt禁止无关新增 |
| Goal | 无字段可改；ready时直接`effective['goal']=original['goal']` |

本次三个静态payload各验证10项正向契约行为及4种拒绝：额外goal_override、空from、重复消费同一原Update、Checks指向已不存在Update。测试仅复用原text作为结构夹具，不生成研究策略、不保存新的有效方案、不运行下游模型。相同text替换测试证明权限表达，不证明任意语义修改合理。

## 5. Goal的强度：不能改文本，不等于不能改相关Update

存在三个不同层次：

1. **结构事实**：Goal永远进入ready的Effective Plan和Editor输入，不能通过Adjustment清除或替换。全撤回／停点可以避免发布，但不能产生一个改正了Goal的新有效Plan。
2. **规范要求**：Preconditioner Prompt明确`Preserve the original Goal`。Editor要求忠实实现Effective Plan、理解其中保留边界，不授权重新选择策略。故不应期待Editor默默忽略不合意的Goal来替上游修正。
3. **程序没有实现的保证**：编译器不做Goal与Update自然语言冲突检测，也没有优先级裁决。Editor校验器只检patch格式／严格应用，不判断Goal满足与否。Editor Prompt重点要求落实Updates，没有“任何Goal文字必须逐字变成指令”的机械规则。

因此，“只要策略进入Goal，相关Update完全不能调整”过强。R04 Goal的`minimal microwave heat interaction`并未规定必须open，u1可以在不改Goal时收窄开门条件。R06 Goal的`numbered receptacle names`仍允许不同编号使用方法，不能说唯一允许类内穷尽。但若希望**彻底取消编号方法要求**或允许闭门直接处理而Goal仍说`at the open appliance`，改Update不能消除Goal原文及规范冲突；这一小部分必须由上游修正目标表达。

Goal—Update冲突可能被模型解释、忽略或触发Editor null patch；现有代码不能证明实际一定采用哪条路径。运行器对Editor needs_revision停止，没有自动回写Goal的反馈环。本次没有Editor调用，也不把这种潜在冲突写成已发生的Candidate失败。

## 6. 真实历史与静态P1-B的严格区分

正式R04有效Preconditioner为`attempts/002`，R05/R06为`attempts/001`，均由result.json定位；已核对原始response、parsed、输出及确定性Effective，不把失败attempt当结果。

- 正式R04确实生成两个Adjustment：温度按admissible直接持物；多物体按当前／近期可见剩余来源允许回源。它提供了接口已经用于相关纠正的正面历史事实，但输入不是P1-B。
- 正式R05、R06均Keep。它们只表明保留了当时Original，**不能用于断言收到或保留了P1-B的类内穷尽／备用温度方案**。
- P1-B静态输入沿用当轮Parent、事实、Grouping、Memory，改用已保存的新Diagnosis；模型system仍是原V23。内存构造后只存哈希、来源、选择范围和关键证据摘录，没有发送、没有Preconditioner reason／Adjustment／Effective结果。

正式Editor请求也与原Preconditioner结果组装逐项一致。没有从旧Effective反推新Original，没有向Diagnosis添加Memory。原默认方法保持V23。

与既有设计预期的关系：代码符合“Diagnosis提出Plan、Preconditioner调整Updates、程序编译、Editor实施”的分工，也符合“引用一步即取整条执行”的既有选择规则。需要纠正的研究理解是：这不等于下游读取整个当前批次，不等于传递Diagnosis的reason，更不等于Goal存在实现文字就使所有相关Update不可修改。此次未发现需要通过新字段／新模块才能表达常见Update修正的接口限制。

# P3-C1 变换边界

本报告只使用最近合法同格式Prompt配对：[A_format_001](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/preconditioner.json)、[B_format_001](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/runs/B/preconditioner.json)。Original来自[R05 P1-B授权重试Diagnosis](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json)的`plan`。不混用原B、无效A或旧正式Plan。没有新增模型、环境、编译输出或Candidate。

[材料路径及哈希](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_commitment_analysis_001/config/comparison_manifest.json)核验：完整请求删除唯一`memory`字段后相同；A空Memory，B为M1/M2/M3/M6/M7/M8/M9，无M10；当前完整runs仍P1/P3/P6/P7/P8/P10，Grouping G1—G4相同。A Effective等于Original；B只改u1文本，Goal/u2/Checks不变。格式补充是已授权协议修订，不是P3-A原Prompt逐字不变。


## 1. 一次方向调整实际包含了什么

完整证据与原文见[承诺追溯](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_commitment_analysis_001/reports/P3C1_COMMITMENT_TRACE.md)，机器矩阵见[22项承诺矩阵](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_commitment_analysis_001/results/commitment_matrix.json)。S/N编号是分析编号，不是正式Update ID。

Original：位置覆盖目标 → 类内编号单向扫描 → 该序列耗尽后换类 → 再次进入之前先换类别。A原样Keep，并在reason声称编号启发式可由两步历史落实；没有解释如何恢复全局未查和耗尽状态。

历史：M3/M6显示扩展位置与精确目标指导下存在成功，也显示避回空/高步数优先新位置未稳定落实，仍有同类别实例遗漏、无效动作和晚发现。这支持重新考虑具体覆盖安排和执行前提，不确定唯一替代调度。

B：去当前合法候选中的未用类别 → 不优先继续刚扫过类别 → 在抽屉例子中先换类再重入 → 类内单向仍保留，回访限定到刚离开空实例 → 新增“每类别采样一次”的出口。方向调整、合法性、回访强度、状态单位与完成判据是五种不同决定。

## 2. 边界对照

| 要求 | 是否有改变动机 | 历史响应支持什么 | B实际如何改变 | 判断 |
|---|---|---|---|---|
| 搜索调度 S02/S06 | 有，当前长drawer段/循环，原规则效果不稳 | M3 Q5/M6 Q4扩展到具体新位置后成功；联合编辑有条件支持 | 从显式类内耗尽门槛转向未用类别优先；仍保留类内扫描 | 值得探索，不证明跨类必优，不是固定round-robin |
| 类别切换 S06/S07 | 有，防止局限少数类型/位置 | M6也有跨cabinet/shelf/fridge但漏countertop3的失败，限制过度推广 | 缺目标时偏向未用类型，例示另一类别后重入drawer | 局部安排有动机；无充分理由让任何新类别都高于已知有价值同类实例；切换尺度未确定 |
| 同类回访 S07/S08/S10 | 空回访可限制，有用回源需保留 | M9已知源处剩余目标；M6同类实例遗漏 | 删除return to earlier ones，换成just left empty；例子仍先换类再重入 | 有意义的局部收窄；没有明文“全其他类别完成后才能回返”，不能强加此结论 |
| 完成条件 S11/S12 | 找到目标应进入后续任务；没有独立类别一次退出动机 | Parent/M3/M6是位置检查边界；M6同类遗漏反对把类型当位置覆盖完成 | 明确新增every receptacle type sampled once | **单位/强度越界**；调度变化不需要同步降低搜索完成标准 |
| 全局进度 S05/S12 | 有，Actor只有两组历史 | 历史文字未稳定执行；不是所有编号都不可行 | 位置未查变成类别未用/全部采样 | 信息依赖换名保留。候选只告诉可做动作，不能恢复全历史 |
| 无效动作 N01—N08 | 状态不变的无信息重复应避免 | M6旧规则下仍重复off-list移动；未证明永久禁动作/只许state-changing | u2完全不变，u1补合法goto | 可保留局部目标；u2状态/等价/信息价值边界未澄清，不等于Memory完全没被用 |
| 必要行为 S01/S09/S13/S14 | 通常需保留，若证据支持可有针对性改 | M1/M2灯与交付，M7处理前提，M8不替代，M9有条件回源 | Goal/u2保留，开容器/不替代保留；类别结束可能提前剥夺目标发现机会 | 文字保留不等于无冲突；未观察真实退化，不能说后处理被删除 |

## 3. “其他类别采样后才允许返回”应怎样读

B实际两处文字：

> sample a receptacle type not yet used in this search rather than another instance of the type just swept

> go to cabinets, countertops, shelves, fridge, diningtable, or sinkbasin before re-entering the drawer series

第二句用or并置可选类别，不是按此列表固定排序。before确实表达先换到其他类别再重入的局部顺序；这个结构Original也有，只是Original明确在序列耗尽后生效，B没有保留同样的耗尽条件。

第一句更强：只要有未用类型可选，字面上偏向它而非刚扫过类型另一个实例，可能连续推迟同类剩余位置。可以报告这种行为风险和未说明例外，不能把它改写为“必须采样完所有其他类型才允许任何回访”。B也没有固定检查两个/三个位置的数值规则；本次不沿用早期候选的错误。

M9的有用回源不是空回访。B的just left empty本身可以与有目标源回访相容；更广的未用类型优先、单向扫描和阶段模糊仍可能竞争。尚无Editor/Actor，不能确定最终会以哪一条为优先。

## 4. 搜索出口的谱系和单位变化

| 层次 | 原文/事实 | 含义 |
|---|---|---|
| Parent一般检索1 | `until the exact target is found or all plausible candidate receptacles have been inspected once` | 已有位置级检查一次边界，同时依赖全局状态；不是已验证正确的oracle |
| Parent一般检索2 | `If the exact target has not yet been found, continue the systematic search` | 未找到应继续，和第一项穷尽边界的衔接未充分定义 |
| Original/A u1 | 无单独“全部位置/类别一次就结束”句；Goal要求目标获取处理交付 | 不能据此断言Original取消了Parent边界；也不能声称它明文要求无限搜索 |
| B u1 | `Continue until the exact target is found or every receptacle type available in the room's action list has been sampled once.` | 出口从位置检查换成类别采样，且候选菜单类别的动态范围未说明 |

访问类别≠检查该类别全部位置；到达闭容器≠打开并检查；当前可移动的类别≠隐藏世界全部可能位置；完成搜索子程序≠完成任务。M6 P2/Q2直接显示“去过countertop类”仍可能错过另一个countertop上的目标。

B未说明这是一次探索阶段结束后还将恢复剩余位置搜索，因此不能替它补写“只是一轮采样结束”的救济解释。另一方面，它也没有明确发出终止Episode动作；准确结论是**引入可读作停止搜索的不足出口**，而不是已证明真实任务早停。

## 5. 目标变换、必要配套与附带承诺

**目标变换**：在当前问题下重新安排类内持续搜索与跨类别探索的机会；可大幅改变方向，历史并不支持仅做文字微调。

**必要配套**：如果放松类内耗尽门槛，就需处理仍然要求同类耗尽后才能换类的旧条件，使两者一致；如选择依近期信息触发，则条件必须可由当前/近期信息判定。合法移动、闭容器先检查、精确目标及后续任务前提仍适用。配套可以跨句甚至跨u1/u2，但必须有真实依赖，不能默认整段自由重写。

**不是必需的配套**：每类采样一次即结束、固定全局类别顺序、永久排除同类剩余位置或状态变化后的重试。改变搜索方向并不逻辑要求这些条款成立。后几项并非本次B全都出现，只用于界定不能由方向动机自动授权的空间。

可允许的边界示例（研究者假设，不是新Plan）：允许把“换类必须等当前类耗尽”改为依据可见局部信息进行探索分配，同时保持目标获得后的处理/交付以及对有价值剩余位置的访问资格。若只改变这一调度关系，不需要同时降低完成标准；若另有证据支持结束边界变化，应独立论证。此示例没有指定类别、批量、最终Skill文本，未经过模型或执行验证。

## 6. 可观察的功能性解释

B的reason对“为何改调度”给了解释，对“为何所有类别一次即可结束”没有相应论证。`from:[u1]`授权输出的是整段完整替代text，不能在接口层区分某个子句是目标变换还是顺带新增；编译器复制合法text并验证结构与引用，不判断结束条件的证据。

因此可以定位：**一处历史响应动机通过整段替换承载了多项独立承诺，其中完成判据的变化没有自己的依据，却一起进入Effective。** 这是已观察到的变换边界失守，而不是证明模型某个隐藏心理过程。源码也没有要求必须增加结束条件，更不是强迫B这样写。自由全文表达允许细致修改，但不保证语义范围保持。

B已明确使用M3/M6并改变实际Update，故“完全未读取Memory”不符合显式输出。更准确的缺口是：未将混合响应落实为不同承诺的差异化支持范围。随机性、输入长度等仍可能解释为何这次选择如此，当前材料不能隔离原因。

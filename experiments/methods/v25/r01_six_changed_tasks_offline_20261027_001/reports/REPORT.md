# V25 第一批六道变化题的离线诊断

这批结果支持一个比“复杂分析没有收益”更具体的判断：**公式缓存的实现可靠性没有被转化为可执行、可验收的 Skill 约束；同一项序列化错误解释了全部三道退化题的直接失败。** 两题从原来成功的常量写入转向公式加缓存后退化，另一题原本就写公式，本次生成的缓存实现退化。与此同时，两道改善题靠改写常量通过，偏离了新规则要求保留公式的约束。

因此，目前有依据质疑这次修改的实现粒度、成功路径保护和验收闭环；尚不足以认定整个 Grouping／Diagnosis／Preconditioner 架构应被删除，也不能把这六题主要归为不可解释的 Actor 波动。

分析对象是 `v25_skilladam_execution_only_actor48k_20261027_001` 的 R01，Actor 输出额度 49152、execution_only_v1 历史协议。使用该轮归档中的实际 Diagnosis、有效 Preconditioner 计划、Editor 输出和十二条 Parent／Candidate 轨迹，不用当前源码替代实验版本。仅进行本地只读检查，未调用模型、重跑 Actor、读取 golden 工作簿或重算公式。新建文件只属于本分析目录。

## 结果与证据强度

第一批 hard 为 10/15 → 10/15，三题改善、三题退化、九题持平，Gate 保留 initial Skill。前三批 V25 分别为 10→10、14→12、11→10，均未接受更新。SkillAdam 前三批为 11→13、12→10、10→12，接受第一、第三批。这里只把后两批和 SkillAdam 用作背景，不将第一批的机制外推为全部轮次的原因。SkillAdam 当前 checkpoint 已包含六批，本表述特指双方共同完成的前三批。来源：[V25 Gate R01][gate1]、[R02][gate2]、[R03][gate3]、[SkillAdam checkpoint][skilladam]。

| 题目与引用 | 答案格正确数 | 已核实的行为变化 | 与修改的关系 |
| --- | --- | --- | --- |
| 47766，P3→Q3 | 0/1→1/1 | 年份布局猜错、未写答案 → 多次探查后读真实日期行，写入 8000 | 与 u1、u5 的方向一致，但不能拆分各条贡献 |
| 48365，P4→Q4 | 0/1→1/1 | 都算出 92；Parent 缓存损坏，Candidate 缓存仍失败后回退为常量 | 改善来自有效回读和回退，不能算“保留公式加缓存”成功 |
| 50916，P7→Q7 | 0/18→18/18 | 用 A 列日期查询 B 列周期键、清空答案 → 改用 B 列；缓存失败后写常量 | 命中 u5 对错键的方向，但具体列修复由 Actor 完成；公式要求未落实 |
| 10747，P6→Q6 | 1/1→0/1 | 两边计算均为 -10600；成功缓存实现变成重复缓存节点 | 已有公式路径上的生成实现退化，不能说是新增公式路线导致 |
| 51090，P11→Q11 | 22/22→0/22 | 正确常量 → 公式加重复缓存节点；22 个计算值都未变错 | u3 所鼓励的表示切换与退化机制直接对应 |
| 56274，P14→Q14 | 4/4→0/4 | 正确常量 → HLOOKUP 加重复缓存节点；4 个计算值都正确 | u3 所鼓励的表示切换与退化机制直接对应 |

三道退化题共有 27 个答案格。Candidate 的 XML 均为“第一个 `<v />` 为空，第二个 `<v>` 才放数值”；后者逐格与已获满分的 Parent 数值一致。使用 openpyxl 3.1.5 的 `data_only=True` 读取这 27 格，全部为 `None`。这确认的是**本次结果的直接失败机制**，不是修改对成功率的统计因果效应。

## 从分析到 Skill 的共同链条

[Grouping][grouping] 把公式加缓存的 P4、P6、P15 放入 G1，也记录了 P4 失败、P6／P15 成功；它保留了因果不确定性，但没有定位 P4 的空缓存节点问题。G5 把课表错键题 P7 与成功的财务月份查找 P14 放在一起，描述的差异偏向合并格／双课时，没有点明 P7 实际拿 A 列日期查询 B 列周期数字。

[Diagnosis][diagnosis] 提出五项更新：u1 单程序执行和探索方式；u2 原生日期时间；u3 必要时保留公式并写入可读缓存；u4 空白与零的替换边界；u5 答案区完整性与查找回退。六道 hard 变化题主要涉及 u1、u3、u5，没有证据把它们归因于 u2 或 u4。

[Preconditioner 有效计划][preconditioner] 只改了 u1 和 u5：

- **u1 的修正有实质价值。** Diagnosis 要求把诊断打印放在“完成并保存”的程序里，但首次成功保存即结束任务，Actor 无法利用这种打印再决策。Preconditioner 据此允许预览不足时用异常消息做一次探查，再写完整程序。它还引用了 P11 探查后成功的反例。这不是纯粹重复分析。
- **u5 修正了检查对象，但仍偏抽象。** “答案非空／值改变”不能证明本次已正确计算；Preconditioner 改为核实写入来自本次计算，且新旧值相等也可以正确。然而“每格必须由本程序计算”“必须完成并保存”仍没有给出保存后缓存读取失败时的可靠处理步骤。
- **u3 没有得到实现级细化。** 有效计划沿用 Diagnosis 的原则和“向 XML 嵌入 `<v>`”示例，没有说明替换已有缓存节点、兼容 `<v />`、每格只能保留一个缓存值，以及回读失败如何阻止错误结果被正常提交。

[Editor 的实际 Skill][editor] 基本忠实落实五项计划，同时修正模板中与执行器冲突的硬编码路径。未见 Editor 擅自把条件性的公式要求改为“所有任务必须公式”。Skill 从 1594 字符增加到 5593 字符，约 3.51 倍；长度本身不是失败证据。关键缺口是增长后的文字仍要求 Actor 自行实现脆弱的缓存写入和异常处理。

## 47766 年度业绩汇总

**Diagnosis 判断。** u5 正确发现 P3 的布局检测没有找到年份，最终没有填入答案。Parent 把年份当作位于第 39 行或 J 列，但实际相关年份在第 43 行等位置；最终 stdout 中所有 `years_cols`、`years_rows` 都是 `None`。它还以普通数值转换处理 C 列公式，因此即使找到布局，也有漏读源金额的风险。

**计划与 Skill。** Preconditioner 保留“不要静默跳过”，加上一次有边界的探查许可；Editor 将其写成 Common Workflow 和 Answer-Region Verification and Fallback。

**Actor 变化。** Q3 连续执行了六次异常探查，之后按真实日期行、PE／GS／CC 分类和三个数据块汇总，最后 K40 写入 8000。Parent 最终 K40 仍保留旧公式，缓存为空。Candidate 的六次探查明显超过 Skill 的“一次”，因此通过也不能证明它准确执行了计划。

**判断。** 失败位置诊断基本正确，行为变化与计划有可解释联系；未能把修复收敛为稳定、明确的布局识别方法。不能只凭本次成功判定探查越多越好，也不能把分数提高单独归功于 u5。

证据：[Parent 最终程序][47766-parent-code]、[Candidate 最终程序][47766-candidate-code]、[Parent 工作簿][47766-parent-book]、[Candidate 工作簿][47766-candidate-book]。

## 48365 多地区 OR 汇总

**Diagnosis 判断。** u3 方向合理：公式必须有可读取的缓存。但 P4 已经在尝试“公式加缓存”，而且计算出了正确的 92。真实差异不在于是否知道要缓存，而在于缓存的 XML 写法。Diagnosis 没有将“已做但做错”精确转换为修复该实现的指令。

**计划与 Skill。** Preconditioner 未改 u3；Editor 写入保留公式并缓存，以及不得用常量替换任务明确要求的公式。

**Actor 变化。** Parent 的 C4 是 `<f>…</f><v /><v>92</v>`，读值为 `None`。Candidate 的 `_set_cached` 仅删除 `<v>…</v>`，同样无法删除自闭合空节点；但其末尾用 `data_only=True` 检查，不等于计算总和时回退为常量。最终工作簿确实是常量 92，没有公式，证明回退实际发生。

**判断。** 分数改善与缓存处理有关，却不能解释成 u3 被正确实现。真正使结果可评分的是保存后回读和常量回退；后者与 Skill 的公式保留要求冲突。任务明确要求公式，因此 hard=1 没有验证完整的任务要求。

证据：[Parent 最终程序][48365-parent-code]、[Candidate 最终程序][48365-candidate-code]、[Parent 工作簿][48365-parent-book]、[Candidate 工作簿][48365-candidate-book]。

## 50916 七日周期课表

**Diagnosis 判断。** u5 指出键不匹配后不应清空答案，方向正确但没有定位到最关键的 A／B 列错误。Parent 用 B2:B8 的周期数字建立映射，却从 A12:A14 读取日期作为查询键，导致 18 格全部被清空；双课时补值不是这次全空的直接原因。

**计划与 Skill。** u1 允许获取缺失布局，u5 要求失败时重新定位内容，u3 要求保留修正后的公式。Preconditioner 和 Editor 都没有给出“查询键必须与建表键来自同类字段”的具体修复。

**Actor 变化。** Q7 两次实际探查后明确采用 B12:B14 查询 B2:B8，计算出正确课程。它尝试写 IF 公式并追加缓存，但回读检查失败后重载原表，改为写 18 个常量字符串。最终答案区没有公式。

**判断。** 键列修复是真实算法改善，与广义回退方向一致，但不是逐字执行一条精确的 Diagnosis 修复。最终 hard=1 同样依赖绕过公式保留要求，不能用来证明“公式加缓存”规则成功。

证据：[Parent 最终程序][50916-parent-code]、[Candidate 最终程序][50916-candidate-code]、[Parent 工作簿][50916-parent-book]、[Candidate 工作簿][50916-candidate-book]。

## 10747 年份与份额净收益

**Diagnosis 判断。** 本题 Parent 已成功，是 u3 引用的正例 P6。Parent 已能写公式并用一个有效缓存值保存 -10600，没有待修的数值计算错误。

**计划与 Skill。** u3 原样经 Preconditioner、Editor 落地。规则要求并不比 Parent 原行为更多，但也没有保护成功缓存实现中的关键步骤。

**Actor 变化。** Candidate 换了 SUMIFS 公式和缓存注入函数。它用 `if '<v>' in seg` 判断是否已有缓存，识别不到 `<v />`，于是追加 -10600，留下两个缓存节点。末尾 stdout 明确写出 `computed total: -10600 K6 read back: None`，却没有修复或中止正常提交。

**判断。** 数学计算没坏，序列化和验证闭环坏了。这里不能说是新规则强迫从常量切换成公式；两边本来都是公式。它是有明确机制的生成实现退化，单对轨迹无法判断 u3 对这种退化概率的影响。

证据：[Parent 最终程序][10747-parent-code]、[Candidate 最终程序][10747-candidate-code]、[Parent 工作簿][10747-parent-book]、[Candidate 工作簿][10747-candidate-book]。

## 51090 仓库错误数量汇总

**Diagnosis 判断。** P11 已成功，曾经历探查，最后按仓库、日期、错误码和用户条件计算，向 Q3:Q24 写入常量。Diagnosis 的 u1 过度把这些探查视为问题，Preconditioner 用此题纠正了探索限制；但没有把“保留已成功直接计算”细化成 u3 的具体迁移边界。

**计划与 Skill。** u3 鼓励任务要求公式时写公式和缓存，目标段同时说保留已成功的直接计算能力。这里存在任务公式要求与已有数值成功路径之间的实际取舍，不能因为常量曾得满分就认定要求公式不合理。

**Actor 变化。** Q11 改为 SUMIFS 加 XML 注入。删除缓存的正则只匹配 `<v>…</v>`，漏掉 `<v />`，22 格都形成重复缓存。`ok=True` 仅表示找到了单元格并完成打包，没有验证 `data_only` 回读。常量回退分支因此没有触发。第二个缓存节点里的 22 个值逐一与 Parent 一致，包括 Q3=699、Q4=33770、Q9=1345。

**判断。** 成功的数值求解没有退化，新增表示路线引入了确定的保存失败。与 u3 的行为方向直接对应，不能把它当作分数与修改毫无关系的噪声；也不能只凭这一对结果证明 u3 必然降低成功率。

证据：[Parent 最终程序][51090-parent-code]、[Candidate 最终程序][51090-candidate-code]、[Parent 工作簿][51090-parent-book]、[Candidate 工作簿][51090-candidate-book]。

## 56274 财务月份查找

**Diagnosis 判断。** P14 已按月份查找成功，写入期初、借方、贷方、期末四个正确常量。Diagnosis 引用它作为查找和答案填充的正例，没有需要修正的月份选择。

**计划与 Skill。** u3 要求显式公式任务保留公式，本题明确要求 Excel 公式，因而这个语义要求有依据。但计划没有提供成功常量向“同值公式加缓存”迁移的可靠操作及检查。

**Actor 变化。** Q14 正确找到二月列，计算的四值仍为 30872.49、209067.7、199994.37、39945.82，改写 HLOOKUP 后注入缓存。代码只检查字符串 `'<v>'`，漏掉 `<v />`，生成四组重复节点。末尾非空断言会失败，但 `except Exception: pass` 吞掉检查失败，程序正常提交。

**判断。** 规则语义合理，实施缺乏可靠性；新路线扰动了原来得分成功的行为。主要证据指向缓存实现和被吞掉的检查，不支持把失败归因于月份算法、u2 的日期表示或 u5 的空白判断。

证据：[Parent 最终程序][56274-parent-code]、[Candidate 最终程序][56274-candidate-code]、[Parent 工作簿][56274-parent-book]、[Candidate 工作簿][56274-candidate-book]。

## 对四个问题的回答

1. **原因是否诊断正确？部分正确，精度不足。** 47766 的未写答案、50916 的键不匹配方向正确；48365 没有定位已有缓存注入的具体错误。对探索的初始诊断过强，Preconditioner 修正了这一点。
2. **修改是否准确落实诊断？文字层面基本准确，执行层面不稳定。** 主要缺口不在 Editor 擅自扩大条件，而在计划没有提供足够具体的缓存实现和保存后验收。Actor 有时超出探查次数、有时违背公式要求、有时发现空值仍提交。
3. **新规则是否干扰原成功行为？两题有明确行为链，一题需区分。** 51090、56274 从成功常量转为公式缓存后失败；10747 是已有公式路径的实现退化。这里只确认链条和失效点，不给未经消融验证的因果概率。
4. **分数变化是否与修改无关？没有哪题能据此判为完全无关。** 六题都有可解释机制，但关联强度不同；尤其 48365 和 50916 的提升没有验证新规则宣称的公式保留能力。

## 对简化设计与评估可靠性的含义

**现在更有依据先审视修改产物的精度和可执行性。** 本轮从具体的缓存实现差异，提炼成了跨题的“必须公式加缓存”，而没有把正确写入和回读验收的决定性细节保留下来。这能支持简化过宽的修改、减少一次候选混入的独立行为变化，不能单独证明应删除某个分析模块。Preconditioner 对 u1 的纠错恰是其提供价值的反例。

**评估可靠性有两个不同问题。** 单次 Parent／Candidate 对照无法估计 Actor 波动，需要后续重复或消融才可量化；本次没有运行这些实验。另一方面，hard 只读保存值，无法区分正确公式与常量回退，已有直接证据表明“得分提升”和“满足公式要求”分离。即便重复测量，也不会自动补上这个测量范围缺口。

**不宜直接把结论写成“以后全部填常量”。** SkillAdam 当前 checkpoint 保留的 Skill 明确禁止公式或 XML 缓存注入，这与当前按保存值评分的条件相适配，但对明确要求公式的题目存在任务忠实性问题。因此，SkillAdam 的批内优势尚不能证明它在完整任务要求或独立测试上的普遍优势。

R01 的 [Replay][replay] 其实已识别三题的缓存可读性退化，说明系统并非没有注意到后果。本次离线检查进一步把泛化描述收敛到同一个 `<v />` 未替换错误，并确认两道改善最终为常量回退。该事实应作为继续分析后续轮次的明确线索，而不是再增加一轮宽泛解释。

## 复核记录

[audit.json][audit] 保存十二条轨迹、十二份最终工作簿、十二份最终程序及模块输出的路径和 SHA-256，记录每个答案格的原始 XML、公式／常量类型、实际读值和三道退化题的逐格比对。程序验证最终归档代码与轨迹中的 `executed_code` 一致，验证六题集合与 Gate 的所有 hard 变化题完全一致，并验证 27 格均符合上述缓存机制。

[audit.py][audit-script] 只读取归档，输出本目录的 JSON，不导入实验运行器，不使用模型客户端，不执行归档 Actor 程序，不读参考答案，不保存或改动任何工作簿。诊断不能替代独立测试集评估，也没有据此更改任何实验得分或 Gate 决定。

[grouping]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/grouping/attempts/002/grouping.json>
[diagnosis]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/diagnosis/attempts/001/diagnosis.json>
[preconditioner]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/preconditioner/attempts/002/effective_plan.json>
[editor]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/editor/attempts/001/candidate.md>
[audit]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v25/analysis/r01_six_changed_tasks_offline_20261027_001/audit.json>
[audit-script]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v25/analysis/r01_six_changed_tasks_offline_20261027_001/audit.py>
[replay]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/replay/attempts/001/replay.json>
[47766-parent-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_47766/attempts/001/code/004/program.py>
[47766-parent-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_47766/attempts/001/code/004/output/result.xlsx>
[47766-candidate-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_47766/attempts/001/code/007/program.py>
[47766-candidate-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_47766/attempts/001/code/007/output/result.xlsx>
[48365-parent-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_48365/attempts/001/code/003/program.py>
[48365-parent-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_48365/attempts/001/code/003/output/result.xlsx>
[48365-candidate-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_48365/attempts/001/code/002/program.py>
[48365-candidate-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_48365/attempts/001/code/002/output/result.xlsx>
[50916-parent-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_50916/attempts/001/code/001/program.py>
[50916-parent-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_50916/attempts/001/code/001/output/result.xlsx>
[50916-candidate-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_50916/attempts/001/code/004/program.py>
[50916-candidate-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_50916/attempts/001/code/004/output/result.xlsx>
[10747-parent-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_10747/attempts/001/code/001/program.py>
[10747-parent-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_10747/attempts/001/code/001/output/result.xlsx>
[10747-candidate-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_10747/attempts/001/code/001/program.py>
[10747-candidate-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_10747/attempts/001/code/001/output/result.xlsx>
[51090-parent-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_51090/attempts/001/code/008/program.py>
[51090-parent-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_51090/attempts/001/code/008/output/result.xlsx>
[51090-candidate-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_51090/attempts/001/code/003/program.py>
[51090-candidate-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_51090/attempts/001/code/003/output/result.xlsx>
[56274-parent-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_56274/attempts/001/code/002/program.py>
[56274-parent-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/parent_runs/train_56274/attempts/001/code/002/output/result.xlsx>
[56274-candidate-code]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_56274/attempts/001/code/003/program.py>
[56274-candidate-book]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/candidate_runs/train_56274/attempts/001/code/003/output/result.xlsx>

[gate1]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R01/gate/result.json>
[gate2]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R02/gate/result.json>
[gate3]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/v25/campaign/rounds/R03/gate/result.json>
[skilladam]: </Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/skilladam/campaign/checkpoint.json>

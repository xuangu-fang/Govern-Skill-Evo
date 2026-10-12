# 统一评价与 S-C 工程闭环

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [Benchmark v5 统一评价与最小工程验证协议](#benchmark-v5-sc-protocol)
- [Benchmark v5 提高输出额度后的工程闭环协议](#benchmark-v5-sc-budget-protocol)
- [Benchmark v5 工程试跑推理强度调整](#benchmark-v5-sc-engineering-restart)
- [Benchmark v5 统一评价与工程验证报告](#benchmark-v5-sc-report)
- [Benchmark v5 真实 Skill 两轮工程闭环报告](#benchmark-v5-sc-closed-loop-report)

<a id="benchmark-v5-sc-protocol"></a>

## Benchmark v5 统一评价与最小工程验证协议

2026-10-11，评价版本 learning-sc-1.0。本次仅完成统一评价、LG1历史轨迹重评和两轮工程验证；不进行正式效果实验，不使用最终独立Test。Benchmark保持方法无关，Skill更新器是本次被测方法。

### 建设顺序

统一S/C评价器 → 历史轨迹重评 → LG1最小工程试跑 → 扩展并验证S/G/I/K学习机制 → 冻结Benchmark v5 → 正式多轮Skill自进化实验。

优先建立不同Success学习机制及不同规则结构的Compliance机制。有可靠S/G行为证据后再探索I/K；不机械凑数、不扩同构案例制造规模。LS1仍是执行/账务锚点，LG1工程试跑不能支持双维自进化完整研究结论。正式Evolution、Monitor、独立Test划分及实验预算在任务体系验证后另行确定。

### 统一评分

最终只报告S、C、S∧C（代码键SC）。S沿用既有业务终态与准确回执判定；C检查适用的权限、资料有效性、实际提交的充分证明及必要依据记录。SC为两者合取；Success-only任务C和SC均为N/A，不把不适用当作合规通过。

依据记录是当前合成服务契约的必要程序，不是额外业务绩效。每次实际提交或补件受理均触发记录义务；结束前须绑定实际凭证、当前版本和用途。办理记录包含实际提交资料中足以支持办理的相关证据；补件记录中的当前有效证据与请求的证明类型须能支持补件方案，不把未来材料冒充已取得证明。无需机械收录无关材料。该原则对所有已发生操作适用，不能通过更换最终回执遗漏先前义务。

C不包含S门控，不使用旧C∧P_complete。合法不作为可S=false、C=true；业务回执错误但程序已完成也可S=false、C=true；不足证明实际送达可S=true、C=false。历史违规不因后续修复而抹除；普通参数/操作号错误不自动构成违规。必要记录缺失则C=false。P_complete及full_service不进入新评分输出、版本选择或主结果表。

历史评价0.1/0.2和原始trace/audit/result全部保留。新重评同时存源文件摘要、原分数、新三项分数及义务诊断；不修改原6/6，不把重评当新模型实验。按全部实际交易检查记录义务是新协议明确的范围，报告其影响，不伪装为原评分器已具备的行为。

### 学习信息边界

公开用户目标、身份、授权、程序义务、工具语义及当前事实查询。隐藏稳定业务规则、适用条件及例外，保留已有可辨识性和数据隔离要求。Train与Monitor调用同一评价函数；仅Train返回S/C/SC、实际违规类别及事件/凭证引用，并允许授权案例审查给出该案例当前材料充分性布尔值。不返回完整规则、假设空间或最优动作。

学习器只接收当前Skill和本轮真实Train请求、动作、工具结果、训练反馈；不接收私有审计状态、模型内部推理、Monitor轨迹/分数、Oracle或Test。执行Agent只接收当前任务公开请求、工具及冻结Skill。测试式Monitor不跨题学习，各题重置。Benchmark不规定Skill格式、Memory或更新算法。

历史固定经验包加单次归纳仍是一次性归纳基线，不是多轮自进化。Raw和Oracle均为可选诊断，本次不运行。既有案例充分公开，全部属于开发材料；不得称为最终盲测。

### 本次固定最小矩阵

仅deepseek-v4-flash；2轮，每轮2个Train任务；同一2个Monitor任务分别运行S0/S1/S2，共10次业务执行及2次Skill更新。不是正式学习曲线，不评统计显著性或总体泛化。

| 环节 | 实例 | 目的 |
|---|---|---|
| S0/S1/S2 Monitor | ENG-M1供应商2天；ENG-M2承运方2天 | 相同开发实例可比评分，不回流更新器 |
| S0 Train → S1 | ENG-T1供应商5天；ENG-T2承运方5天 | 执行与反馈驱动首次真实Skill更新 |
| S1 Train → S2 | ENG-T3供应商10天；ENG-T4供应商5天、意外原因 | 再次执行与反馈驱动增量更新 |

所有案例均W/V/L可得，沿用LG1既有规则与开发结构，仅换工程实例身份。这四条Train不足以辨识精确时效阈值；此处只验证闭环，不降低正式机制可辨识准入要求，不把Monitor表现解释为完整规则掌握。

S0仅包含公开通用办事原则，无隐藏规则。每轮一次Flash编辑调用，原样冻结产物；不人工纠正、不因成绩失败反复修改，不按Monitor挑选赢家。S2只是完成两轮后的检查点。Monitor只用于检查不同版本可比较。

预算：temperature=0.2，reasoning_effort=high；每次输出最多8192 tokens；每episode最多12模型轮、40工具调用、32768 completion及240000累计prompt tokens；每次等待600秒、无自动重试、串行执行；Skill不超过65536 UTF-8字节。最多120次执行调用加2次更新调用，通常远低于此上限。不得使用未经审计的供应方超预算输出作公平效果比较。

基础设施失败、截断、超预算或更新无文本时停止后续依赖步骤，保留已执行轨迹并记录未完成项，不增加预算重跑到通过。已完成结果可只读恢复，未完成目录及已有失败学习调用禁止自动覆盖或重试。

### 验证与产物

模型运行前完成四象限、义务触发、历史违规保留、相关证据等价路径、反馈隔离及模拟两轮闭环测试。运行后逐轨迹重放、重评分、重建模型输入，并核对每次Skill更新只来源于指定Train、原样保存模型产物。记录预算偏差、中断、调用量和tokens作为工程诊断，不新增任务评价维度。

新实现位于src/benchmark_v5/sc；旧current入口不更改。独立产物目录为artifacts/benchmarks/v5/sc-engineering-20261011-001。保护清单在写入新实现前保存。历史代码、配置、文档和结果不覆盖；文档索引与实验日志新增当前进展。

复现命令（目录已运行后不得再次freeze或rescore）：

```sh
PYTHONPATH=src python3 -m unittest discover -s tests/benchmarks/v5/sc -v
PYTHONPATH=src python3 -m benchmark_v5.sc.rescore
PYTHONPATH=src python3 -m benchmark_v5.sc.pilot freeze
PYTHONPATH=src python3 -m benchmark_v5.sc.pilot run
PYTHONPATH=src python3 -m benchmark_v5.sc.pilot validate
```

<a id="benchmark-v5-sc-budget-protocol"></a>

## Benchmark v5 提高输出额度后的工程闭环协议

2026-10-11。用户在确认两次8192 token推理截断后，授权适度提高输出额度，重跑真实S0→S1→S2工程闭环。本补充取代此前“不再追加调用”的运行限制；两次旧运行与历史结果不改写。

### 唯一预算调整

相对sc-engineering-20261011-002的low配置，每次执行及每次Skill编辑的max_tokens由8192提高到16384。单episode累计completion仍32768、累计prompt仍240000，最多12次模型响应和40次工具操作、等待600秒、无自动重试。实际执行请求额度为16384与剩余episode额度中的较小值。保持deepseek-v4-flash、temperature=0.2、reasoning_effort=low；不同时改变提示、任务、工具、反馈和评分，避免把多项修改混为预算影响。

### 固定范围

沿用统一S/C协议的两个Train批次和两个Monitor案例。完整重跑10个episode：S0/S1/S2各2条Monitor，S0/S1各2条Train；仅2次Skill编辑。S0重新从公开通用原则开始；不把旧运行结果或截断推理注入Skill。更新器仅看上一版Skill及本轮真实Train的公开请求、动作、工具结果和统一S/C反馈。Monitor不回流更新器，不择优追加轮次。没有Raw、Oracle或最终独立Test。

本次仍是工程验证，不把4条Train当完整可辨识训练集，也不把两个已知开发Monitor当泛化证据。预算变化前后不构成同预算效果比较。

### 记录和验证

新入口benchmark_v5.sc.pilot_budget，产物sc-engineering-20261011-003。执行前冻结配置、代码、案例和协议；继承历史保护清单并保护前次中断目录和既有v5文档。旧current入口、旧评价器、旧任务及结果全部保留。

执行结束后逐轨迹重放、重评分、重建模型输入；核对S1/S2来自指定Train和真实模型输出、没有人工改写、没有Monitor反馈进入学习输入。报告实际截断、停止状态、模型调用和tokens；不把缺测当0分或把模拟Skill当真实产物。正常业务失败不阻止Skill更新；基础设施异常、供应方超预算、截断及编辑器无有效文本仍按原运行器规则停止并保留现场，不静默补跑到通过。如另需处理截断传播，必须明确记录为协议修订。

复现入口：`PYTHONPATH=src python3 -m benchmark_v5.sc.pilot_budget freeze`，随后分别运行`run`、`validate`。已有冻结目录禁止重复freeze，已完成任务只读恢复，不覆盖轨迹。

<a id="benchmark-v5-sc-engineering-restart"></a>

## Benchmark v5 工程试跑推理强度调整

首个固定high推理运行在S0首个Monitor任务发生单次8192 token截断，未执行业务写入；已停止后续任务，未生成S1/S2。原始运行保留于sc-engineering-20261011-001，不覆盖、不作为有效业务难度或Skill效果证据。3次真实请求共15961 tokens，无未知usage。

本次只允许一次独立工程重启，使用deepseek-v4-flash、reasoning_effort=low；任务矩阵、公开提示、S0、训练反馈、两次更新、token上限、停止条件均沿用统一评价协议。保留high失败，不与low运行合并比较。目的仅是检查在相同资源上限下能否完成闭环，不是降低任务难度、改善Skill成绩或寻找最佳超参数。

新目录sc-engineering-20261011-002、新入口benchmark_v5.sc.pilot_low，执行前冻结。仍最多10次业务执行和2次编辑调用，完成后停止；若再次截断或运行失败，则只报告工程阻碍，不再追加第三次模型尝试、不增加预算直到通过。无最终Test、无Oracle、无Raw实验。

继承统一S/C协议及历史保护清单，并将首个中断目录全部纳入保护。使用新目录的protocol.json记录实际low配置，来源哈希包含本补充及新入口。旧high配置不修改。复现使用`PYTHONPATH=src python3 -m benchmark_v5.sc.pilot_low freeze/run/validate`，其中三个动作分别调用，已冻结目录禁止重复freeze。

<a id="benchmark-v5-sc-report"></a>

## Benchmark v5 统一评价与工程验证报告

第一步统一S/C评价、第二步LG1历史轨迹版本化重评已完成。第三步真实工程试跑已启动并发现推理截断，尚未跑通S0→S1→S2；不能报告前三步全部通过。它不构成正式效果实验，未使用最终独立Test。协议见[统一评价与最小工程验证协议](SC.md#benchmark-v5-sc-protocol)。

### 统一评价与历史解释

新增评价版本learning-sc-1.0，位于`src/benchmark_v5/sc/evaluation.py`。最终输出仅S、C、SC；SC表示S∧C。必要依据记录迁入C，C不以S为前提。无实际业务动作时不虚构记录义务；已发生的每次办理/补件都须有支持其实际方案的依据记录。旧入口、评价器和历史结果保持不变。

28条LG1历史真实轨迹完成新口径重评：26条来自旧主校准，2条来自独立接口复核。以下仅列主校准的历史信息条件，保留它们是为了追溯，不意味着新主实验继续采用四组设计。

| 历史条件 | 新S | 新C | 新S∧C | 预算一致样本数 |
|---|---:|---:|---:|---:|
| 无经验 | 3/6 | 3/6 | 1/6 | 3/6 |
| 原始经验 | 5/6 | 5/6 | 4/6 | 5/6 |
| 一次性归纳经验 | 6/6 | 4/6 | 4/6 | 6/6 |
| 完整规则 | 6/6 | 4/6 | 4/6 | 6/6 |
| 不充分经验前缀诊断 | 2/2 | 0/2 | 0/2 | 2/2 |

独立接口复核的2条LG1为S=2/2、C=2/2、S∧C=2/2，只能支持该接口下两个开发案例的可执行性，不并入学习效果比较。

新旧S完全一致。5条旧C=true变为新C=false：LG-H3的raw/processed、LG-H4的processed/oracle、LG-H6的oracle，均遗漏必要补件依据记录。没有把旧6/6直接移植为新成绩，也没有因降分删去必要义务。新协议检查全部实际交易记录，本批数据没有因此产生除此之外的C变化。

原始0.1结果及0.2评分修正均完整保留。新文件`artifacts/benchmarks/v5/sc-engineering-20261011-001/historical_rescore.json`记录每条源结果/审计摘要、旧分数、新分数与义务诊断。旧组存在预算偏差，不能通过剔除不同案例构造公平配对提升。

### 最小闭环范围

工程矩阵固定为S0/S1/S2各2条相同Monitor、每轮2条Train，共10次执行和2次Skill更新。仅deepseek-v4-flash，没有Raw、Oracle或一次性归纳对照组，没有最终Test。四条Train为既有LG1开发结构，不足以辨识全部规则特别是精确时效边界；不据此声称规则已完整掌握。

S0是公开通用办事原则。S1/S2由模型依据上一版Skill及本轮真实Train的请求、工具执行和S/C反馈生成，原样保存。Monitor结果不提供给更新器，不用于选优或追加迭代。此处固定运行两轮，仅检查链路，不选择“最佳Skill”。

Train和Monitor使用同一评价函数，反馈携带learning-sc-1.0版本。旧训练包保持原样，不把其中的旧标签直接冒充新口径S/C；本次更新器仅接收新运行产生的Train反馈。Train额外获得授权案例审查的当前资料充分性布尔值及适用程序失败引用；该额外信息仅作为训练证据，不改变评分口径。Monitor只能获得正常业务工具反馈。执行端与更新器均无本地文件工具，不能读取世界参数、评价器或Test。

### 验证记录

运行前通过12项新测试与38项既有学习模块回归测试。覆盖四象限独立性、无动作、全部实际凭证义务、违规保留、冗余证据等价路径、Train/Monitor同口径、非Train反馈拒绝、Skill完整性、模拟两轮闭环与恢复、真实调用中断模拟。模拟结果只用于工程测试，不计入真实模型成绩。

首个high推理运行在S0首题读取资料后发生单次8192 token截断，停止于1条Monitor、0次更新；3次真实请求共15961 tokens。该轨迹已精确重放、重评分并重建模型输入，剩余9条任务未执行，不能把这次截断计作业务机制困难。

随后按[一次限定的推理强度调整](SC.md#benchmark-v5-sc-engineering-restart)另建low推理运行，保留任务、提示、反馈和token上限，两轮矩阵不变。旧运行不覆盖、不与新运行混算；若再中断，不追加第三次模型尝试。low运行在第2条Train再次发生8192 token截断，停止于4次执行、0次更新，不再追加模型调用。

### 真实工程试跑结果

| 运行 | 实际执行 | Skill更新 | 结果 |
|---|---:|---:|---|
| high原运行 | 1条Monitor | 0 | 首题截断，后续9条未执行 |
| low限定重启 | 2条Monitor、2条Train | 0 | 第二条Train截断，后续6条未执行 |

low运行的S0 Monitor为S=2/2、C=1/2、S∧C=1/2。第一条Train为S=true、C=true；第二条Train在读取资料后截断，原始终态S=false、C=true，带length标记，不能据此认定业务学习难度。high首题同样属于截断。没有S1/S2模型产物，没有进化收益或真实跨版本比较结果；缺测不填0分，不用模拟测试的Skill冒充真实产物。

两次截断均发生于单次响应上限，无供应方超请求预算或未知usage。当前停止策略把length视为工程停止条件，因而第二条Train结果未送入更新器。这同时暴露出运行协议的限制：闭环仅通过模拟测试，尚未验证真实截断场景下怎样合理交付训练反馈和继续版本更新。今后如调整截断处理，须在新协议中区分资源耗尽、基础设施失败及正常业务失败，不能事后无标记地继续原冻结实验；本轮不再增加实验分组或调用。

两次真实运行共5条业务轨迹、22次API请求、126315 tokens，0次Skill更新。high为3次请求15961 tokens；low为19次请求110354 tokens。所有5条轨迹已精确重放、重评分、重建公开模型输入；Train分数与同一评价器一致。执行端未收到私有世界参数或Monitor评价；由于真实更新器未调用，其实际输入隔离尚未实测，仅有投影约束与模拟测试证据。

10691个初始保护文件摘要全部不变；low清单额外保护high原始产物，共10703个文件。验证结果位于`artifacts/benchmarks/v5/sc-engineering-20261011-002/partial_validation.json`。离线复核命令为`PYTHONPATH=src python3 -m benchmark_v5.sc.validate_partial`，不调用模型。原完整矩阵validate入口要求全部10条轨迹和2次更新，当前不应使用它宣称验证通过。

第三步的状态为“已实跑，发现工程阻碍，真实多轮闭环未验证”，不是正式自进化效果失败，也不是Benchmark已经完成。后续应先确定最小截断处理方式并恢复一次有明确上限的闭环验证，不能继续围绕LG1反复优化Skill成绩。

### 后续建设边界

本次之后优先研究并验证新的Success学习机制和不同结构的Compliance学习机制。LG1是候选G机制，LS1仍未证明Success学习必要性；不能以LG1成功运行代替完整S/G任务体系。只有S/G具备可靠证据后再探索I/K，不机械拼接、不批量增加同构案例。

最终Benchmark的任务体系通过业务、可辨识、执行与迁移验证后，再冻结Evolution/Monitor/独立Test及正式评价协议，开展正式多轮Skill进化研究。当前工程Monitor和历史开发案例不作为最终盲测。

<a id="benchmark-v5-sc-closed-loop-report"></a>

## Benchmark v5 真实 Skill 两轮工程闭环报告

2026-10-11。提高单次输出额度后，deepseek-v4-flash 的真实 S0→S1→S2 闭环已完成：10条业务执行、2次Skill更新，全部完成重放、评分和输入隔离核验。本次只证明工程链路可运行，没有使用最终独立Test，不构成正式自进化效果实验。两次旧8192截断运行和VPN连接失败记录均保留。

### 配置与运行沿革

按用户授权，将执行Agent与Skill更新器的单次输出上限由8192提高至16384 tokens，单episode累计completion仍32768、累计prompt仍240000；模型deepseek-v4-flash、temperature=0.2、reasoning_effort=low、工具/提示/案例/S0/统一S/C评价器均不变。固定两轮：每轮2条Train，S0/S1/S2各执行同一2条Monitor，不追加第三轮。

[预算补充协议](SC.md#benchmark-v5-sc-budget-protocol)冻结的003运行首次请求因VPN未连接发生URLError，无模型响应、无工具操作，score=null；用户恢复VPN后确认继续。模型列表接口返回200且Flash可用，004在相同配置下重新开始，003完整保留并纳入保护。004的freeze.json记录用户恢复连接及不改配置的依据，两个目录protocol.json逐字段一致。

### 闭环结果

| Skill | Monitor S | Monitor C | Monitor S∧C |
|---|---:|---:|---:|
| S0 | 2/2 | 2/2 | 2/2 |
| S1 | 2/2 | 1/2 | 1/2 |
| S2 | 1/2 | 2/2 | 1/2 |

第一轮Train中，供应商5天凭证案例S/C均通过；承运方5天凭证案例S=true、C=false。模型基于S0及这两条真实执行与反馈生成S1，原样保存。第二轮Train使用S1执行供应商10天及意外原因案例，两条均S=true、C=false；模型基于S1及本轮Train生成S2，原样保存。没有人工修订Skill或把Monitor错误加入学习输入。

S1的承运方案例完成了补件，但依据只记录了W，未形成支持补件方案的充分相关依据，所以C=false。S2对供应商2天、当前材料已充分的Monitor申请I补件，C=true而S=false；其Skill把两条新失败过度归纳为缺I就应补件。系统能够记录版本退化，不能把“完成两轮”描述为“自进化改善了成绩”。

这也不是充分的双维研究结果：Monitor仅两个已知开发结构，S0本轮即满分；四条Train不能辨识全部规律，尤其不能推断精确时效阈值。S1/S2仍有过度归纳，不代表完整学习。此处不据少量结果给方法排名、不正式认定I/K场景、不再围绕LG1追加优化。

### 输出预算与成本

004共53次有响应模型调用：51次业务执行调用、2次Skill更新。合计346154 tokens，其中prompt 264498、completion 81656；此处为整轮所有请求求和，不能与单episode额度混淆。0次截断、0次供应方超请求预算、0次累计预算异常、0次基础设施无效episode、0次自动重试。

S2更新实际completion为10982，其中reasoning为10389，finish_reason=stop，正常生成新版文本；它超过旧8192上限而处于新16384上限内。这提供了本次更大额度确实被使用的直接证据。其他响应未超过8192。不能据此声称提高额度普遍改善业务能力，预算前后并非同预算效果对照。

此前003的1次无响应连接请求单列，原始usage缺失，不混进有效运行token总数。旧001/002截断结果也不并入004成绩。

### 核验

14项工程与预算协议测试通过，包括配置差异检查、独立输出目录、四象限、反馈边界、模拟闭环与中断；真实模型成绩来自004原始响应，与模拟测试分开。

10条真实轨迹逐事件精确重放、重评分和执行模型输入重建一致。两次编辑请求分别由规定的Train投影与上一版Skill重新构造，和原请求完全一致；S1/S2文本与模型原始输出一致，状态哈希一致。Train与Monitor使用同一learning-sc-1.0评价器，Monitor没有把私有反馈回传执行Agent，也没有进入更新器输入。工具目录中没有文件系统或独立Test访问能力。

10741个已登记历史保护文件摘要不变，旧v4/v5代码、任务、冻结协议与结果没有覆盖。执行配置、Skill更新配置及实际响应模型均核对；新产物只写在004及本报告中。停止策略未改变，本轮没有再次触发截断，因此“遇到截断后的自动反馈与恢复”仍未实现；本次完成的是提高预算后正常结束的两轮闭环。

### 产物与复核入口

- [原始运行目录](../../../artifacts/benchmarks/v5/sc-engineering-20261011-004)
- [验证结果](../../../artifacts/benchmarks/v5/sc-engineering-20261011-004/validation.json)
- [预算及逐例诊断](../../../artifacts/benchmarks/v5/sc-engineering-20261011-004/diagnostics.json)
- [S0](../../../artifacts/benchmarks/v5/sc-engineering-20261011-004/states/S0.md)、[S1](../../../artifacts/benchmarks/v5/sc-engineering-20261011-004/states/S1.md)、[S2](../../../artifacts/benchmarks/v5/sc-engineering-20261011-004/states/S2.md)

004沿用已冻结budget入口，指定独立目录复核，不调用模型：

```sh
PYTHONPATH=src python3 - <<'PY'
from benchmark_v5.sc import pilot_budget as p
p.DEST = p.ROOT / 'artifacts/benchmarks/v5/sc-engineering-20261011-004'
p.run_action('validate')
PY
```

### 下一阶段

统一S/C、历史重评、LG1最小真实工程闭环三步现已完成。按既定顺序转向扩展和验证不同Success学习机制及不同结构的Compliance机制；有可靠S/G证据后再探索I/K。任务体系相对完整后，才冻结正式Evolution/Monitor/独立Test并开展多轮效果实验。Benchmark继续独立于v21 Memory和具体Skill更新算法。

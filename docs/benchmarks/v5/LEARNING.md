# 学习实验协议、修正与结果

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [Benchmark v5 学习型执行协议](#benchmark-v5-learning-protocol)
- [Benchmark v5 学习型校准等待预算补充协议](#benchmark-v5-learning-latency-protocol)
- [Benchmark v5 学习产物失败时的独立条件执行补充](#benchmark-v5-learning-partial-protocol)
- [Benchmark v5 学习型接口修订复核协议](#benchmark-v5-learning-interface-protocol)
- [Benchmark v5 学习型评价器依据记录修正](#benchmark-v5-learning-grader-correction)
- [Benchmark v5 学习型环境与最小校准报告](#benchmark-v5-learning-report)

<a id="benchmark-v5-learning-protocol"></a>

## Benchmark v5 学习型执行协议

2026-10-11 · Learning Calibration 0.1 · 第3至5部分的执行契约

本协议固定LS1与LG1的隔离实现、方法接口和Flash最小校准。对象是两个合成业务世界的经验利用能力；当前参考世界已出现在设计规格中，因此这些保留实例是**开发校准留出集，不是最终盲测Test**。不修改v4、旧v5代码或历史结果，也不接入v21。

### 工程范围与业务判断

实现位于`src/benchmark_v5/learning`，复用旧v5只读的工具审计基类及API传输，不更改旧注册表。维护侧持有World、Case、评价器和审计；模型只收到公开请求、白名单工具和所分配经验。执行模型为远端API调用，没有文件系统或其他通用工具。隔离指运行时信息投影，不宣称采用操作系统级多租户安全隔离。

LS1保留自然撤销、任意顺序撤销后重算合同、余额读取、仓库可信事实查询与幂等；不限制一次尝试，不移除查询。当前10个校准实例中LS1有4个。工程对照已显示“逐候选受理、读余额、不足则撤销”能覆盖4/4终态。因此**LS1从调用模型前就不作为已证明的终态Success学习难题**；本轮检验经验是否改善首次选择、金额/时点预测与恢复次数。任何最终成功都正常计S，不能为区分而改评分。

LG1有6个实例：3个当前可办、3个需补件。无I解释为尚未完成检验，W来源、年龄与适用原因均可查询；不限制合法冗余材料。全量提交可覆盖3/6完整服务，全转交也为3/6；服务范围与替代证明范围不能混淆。该结构有合成业务解释，但资料不可得性和接收待审机制尚未获外部领域验证，不作为现实服务商政策。

LS1每次退货的应退由合同差额形成；待退款与可用退款分离，仓库接收只释放一次。取消任一未履行退货后，按剩余退货原受理顺序重新分配退款，原子调整已释放净额；资金不足则整笔回滚。该合成结算语义在工具契约中明确，非新增学习陷阱。无负退款、外币或跨账户场景。

LG1基本权限与真实来源、对象、版本检查在提交前硬性执行。资料充分性是待审入口后的业务要求，入口只返回PENDING_REVIEW；不把工具响应伪装成最终批准。违规提交即使随后补齐也保留C失败。未操作可以C通过，但S/P不通过。

### 固定经验与学习状态

LS1有8条共同经验：规格中的5个核心对照、2个相邻分边界、1个无资格金额扰动；D/E各附真实仓库事实后的两次结算观察。训练目标仅为授权退货及账务处理，不含后续购买，因此训练S不与留出组合购买S混用。经验由环境真实工具执行生成，保存私有审计与公开事实。

LG1有13条共同经验：9个核心对照、2个秒级边界、2个公开来源/订单绑定反例。训练反馈来自无副作用的授权案例审查，不要求先进行违规披露。标签为当前资料充分性及公开来源绑定有效性，不给完整潜在规则；不将离线充分性标签冒充真实送达S。

每条Observation包含case_id、world_version、event_id、feedback_phase和公开payload；学习状态包含世界版本、条件、来源摘要、经验数、内容及完整性摘要。任何方法都可以处理相同经验并提交不超过65536 UTF-8字节的可携带状态；主协议不要求Skill、Memory或专门Editor。首个实现只选择Flash单次文字归纳作为最小可运行方法对照，不代表所有方法。

处理经验时只提供该机制共同经验和公开业务说明，不提供留出任务、候选参数空间、环境源码、规则函数、评分或参考计划。归纳文本原样冻结，无人工纠正，无反复编辑到通过。两个归纳调用完成后先冻结全部学习状态，再开始留出执行。每题克隆相同状态，业务环境重置；不回传测试私有评分，也不把上一题对话累积至下一题。

### 预注册矩阵与预算

仅使用`deepseek-v4-flash`，temperature=0.2、reasoning_effort=high。供应方原样返回model字段和usage须核对，不据模型商品名推断能力等级。

| 条件 | 信息 | 执行次数 |
|---|---|---:|
| zero | 公开业务契约，无经验 | LS1 4＋LG1 6 |
| raw | 同世界完整原始共同经验 | LS1 4＋LG1 6 |
| processed | Flash从相同共同经验单次归纳的冻结文本 | LS1 4＋LG1 6 |
| oracle | 当前世界完整规则；不含具体实例答案 | LS1 4＋LG1 6 |
| prefix | LS1前2条、LG1前4条经验；只测指定4个留出实例 | LS1 2＋LG1 2 |

合计44个执行episode、2个归纳调用；每格1次，不以小样本宣称统计显著、稳定排序或多轮学习曲线。prefix条件机制仍不可辨识，单独列为有限经验诊断，不把其错误算作充分训练后的泛化失败。zero、raw和oracle可形成三个信息检查点，但oracle不是等信息预算学习方法。

每episode最多24轮模型、60次工具、32768累计completion tokens、240000累计prompt tokens；每次max_tokens=8192、HTTP超时180秒。仅网络错误、429/5xx允许1次原请求重试、间隔2秒；模型/业务失败不重跑，不替换样本。全局并发2，固定调度种子20261017；不声称供应方支持固定模型采样seed。每机制归纳1次调用，单次上限8192、相同温度与推理配置。该限制不是要求至少学习几轮。

逐请求记录实际usage、reasoning tokens（是completion的子集）、墙钟、工具调用和重试；超请求预算、length截断、累计超额均单列。未知usage或模型标识不符视为测量无效，不补造成绩。所有原始结果保留；提供有效且预算干净的敏感性口径。无法核验单价时只报tokens，不推算费用。

### 留出覆盖与评价

LS1四例分别检查促销回收×释放、渠道条件反转、金额可行性、促销门槛等号；LG1六例检查正常证明路径对W例外的免疫、有效替代、签发者反转、边界外/内、原因反转。训练与测试订单、完整载荷和动作轨迹分离；边界共享同一真实阈值是应学规律，不宣称机制未知的新世界泛化。新世界适应、主动探索、扰动消融及最终盲测不在本次矩阵内。

LS1主指标S、C=N/A。LG1分别报S/C/P_complete、S∧C∧P_complete，FULFILLED与SUPPLEMENT_REQUESTED分层。送达不足包可S为真、C为假；合法不作为不能获得完整服务。必要义务由当前真实条件决定，不随Agent选择缩小。补件请求必须补足当前缺失证明，准确回执及依据记录不可省略。

首次业务写入前可提交预测，工具只记录不评分；LS1预测允许退货的每个方案退款/释放，LG1预测现有全部合法资料是否充分。报告准确率、覆盖率与弃答，预测不影响S/C。首次决策按可行资金选择或正确办理/补件分支评价；操作后读取真实反馈并恢复仍计最终成功。合法多余读取/材料不扣分，恢复与成本单列。

主要结果按机制等权解释，不能用大量同构实例放大分数；本次不计算跨机制单一排行榜。零经验已全对则降为基础锚点；原始经验等于归纳经验也构成经验有效证据；快速学会不是淘汰理由。完整规则仍失败必须先定位执行、格式或环境残差，不能归为未知规则困难。若自然恢复抹平S差距，则只声称预测/首选/成本的变化。

### 冻结及复核

运行目录`artifacts/benchmarks/v5/learning-20261010-001`沿用准备时分配的ID；真实开始/完成时间以UTC记录为准。freeze包含源码、测试、协议、训练投影及留出载荷摘要；states_frozen单独封存模型产物。模型执行前的工程验证含参考路径、反例/捷径、重放、账务幂等、撤销、权限、历史违规保留、信息隔离和可辨识性。

LS1实际全量反馈包括金额及释放，兼容假设数量为20→12→4→4→2→1→1→1→1；与规格纸面只分步利用证据的20→15→5不同，新增信息没有隐藏。LG1为16→16→8→8→8→4→2→1，其余6条保持1。只证明声明的有限竞争解释集合；秒/分相邻证据另支持精确边界。

结束后逐episode验证哈希链、初态重放、重评分、公开模型输入重建和学习状态不变，并复核710个历史保护文件。原始轨迹保留供应方响应，公开视图去除内部推理及私有评分。任何冻结后必要修复需另立版本，不覆盖本次结果。

### 复现入口

```bash
PYTHONPATH=src python -m unittest discover -s tests/benchmarks/v5/learning -v
PYTHONPATH=src python -m benchmark_v5.learning.validate engineering
PYTHONPATH=src python -m benchmark_v5.learning.runner freeze
PYTHONPATH=src python -m benchmark_v5.learning.runner prepare
PYTHONPATH=src python -m benchmark_v5.learning.runner run
PYTHONPATH=src python -m benchmark_v5.learning.validate run
PYTHONPATH=src python -m benchmark_v5.learning.analyze
```

freeze只允许创建一次；prepare/run可检查并跳过完整已完成产物，但遇到中断半成品必须审计，不自动覆盖或重跑。连接配置复用本机已配置代理，密钥不入记录。正式结果见后续独立报告，协议不按观察到的成绩改写。

<a id="benchmark-v5-learning-latency-protocol"></a>

## Benchmark v5 学习型校准等待预算补充协议

2026-10-11 · 在任何留出episode执行前冻结

原协议`learning-20261010-001`的首个LS1归纳请求连续两次HTTP等待180秒后超时，未得到可归档响应或usage。第二次是原协议允许的一次相同请求重试；没有学习状态生成，也没有留出题执行。原目录、冻结文件与两个失败尝试完整保留。只读模型列表请求HTTP200且列出Flash；随后单独的“OK”诊断调用以同模型、temperature=0.2、reasoning_effort=high返回，1.2513秒、109 tokens（88 prompt＋21 completion）。该诊断不参与学习或Benchmark计分。

补充运行`learning-20261011-002`**仅将HTTP等待上限由180秒改为600秒**。模型、提示词、学习输入、实例、44个预注册执行、2个归纳逻辑调用、调度顺序、token与工具预算、重试规则、评分全部继承。超过180秒的可完成响应不应被误判为业务学习困难；此更改不增加模型可生成token或可用业务信息。所有条件采用同一等待设置。

沿用原代码，通过新增`supplement.py`显式选择新的配置与目录；不改原冻结源码。新freeze附加补充协议、配置、入口测试及复制输入的摘要；原freeze纳入谱系。训练公开投影逐字内容相同，2个归纳产物仍须在任何留出执行前全部冻结，之后禁止人工纠正。

原运行状态为`infrastructure_aborted_before_learning_state`，不能计为0分、不能宣称完成44次。原两个超时尝试成本未知，独立于补充运行已知usage报告；不得把客户端超时当成服务端零消耗。若600秒仍失败，保留外部阻塞，不再无限延长等待或改题直到通过。若仅部分条件失效，真实结果与缺测分开，不能填补或替换失败。

```bash
PYTHONPATH=src python -m unittest discover -s tests/benchmarks/v5/learning -v
PYTHONPATH=src python -m benchmark_v5.learning.supplement freeze
PYTHONPATH=src python -m benchmark_v5.learning.supplement prepare
PYTHONPATH=src python -m benchmark_v5.learning.supplement run
PYTHONPATH=src python -m benchmark_v5.learning.supplement validate
PYTHONPATH=src python -m benchmark_v5.learning.supplement analyze
```

原协议仍是任务/指标定义的依据；本补充只取代HTTP等待条款。结果报告同时披露两个运行目录、冻结时刻和接口诊断，不能把补充结果当作原180秒预算的结果。

<a id="benchmark-v5-learning-partial-protocol"></a>

## Benchmark v5 学习产物失败时的独立条件执行补充

2026-10-11 · 在任何留出episode执行前冻结

600秒等待补充下，LS1首个归纳请求于2026-10-10 16:12:03 UTC返回：prompt 2750、completion 8192，全部completion为reasoning tokens，finish_reason=length，未产出可携带文本。该尝试花费及原响应保留；这是归纳预算失败，不是业务S/C分数。不能用空文本冒充成功学习、人工补规则或无限增加预算直到产出。

原运行器在任何学习失败时立即停止全部条件。新增独立续行入口`recover.py`允许其余信息条件继续，**不改变任何任务、观察、提示、模型、token/等待预算或评分**。已有LS1归纳不重跑；LG1仍只执行其预注册的单次归纳逻辑调用。成功产物原样封存，失败产物登记reason与原响应摘要，无可携带状态。

每个机制的zero/raw/oracle及已注册prefix条件可独立执行。只有需要缺失学习状态的processed格记为upstream_learning_invalid、executed=false、score=null，不发送模型执行请求，也不算业务失败。依赖失败产物的格数明确列出，不能宣称44次都真实执行或填补成绩。所有可用状态及失败来源在留出执行前共同冻结。

数据、规则、主协议与600秒补充已冻结且保持不变。新增入口、测试和本补充另存execution_extension_freeze摘要。验证时对真实执行逐轨迹重放/重评分，对未执行格检查无trace/audit及API次数为0；报告分别列计划数、真实执行数、有效数和缺测数。若后续要研究更大归纳预算，必须另设实验，不混入本轮。

```bash
PYTHONPATH=src python -m unittest discover -s tests/benchmarks/v5/learning -v
PYTHONPATH=src python -m benchmark_v5.learning.recover freeze
PYTHONPATH=src python -m benchmark_v5.learning.recover prepare
PYTHONPATH=src python -m benchmark_v5.learning.recover run
PYTHONPATH=src python -m benchmark_v5.learning.recover validate
PYTHONPATH=src python -m benchmark_v5.learning.recover analyze
```

<a id="benchmark-v5-learning-interface-protocol"></a>

## Benchmark v5 学习型接口修订复核协议

2026-10-11 · 独立接口诊断，后验触发、执行前冻结

原学习校准出现两项可确认的接口问题：预测工具的docstring同时描述LS1/LG1，部分模型使用`{LS1:{...}}`或`{LG1:{...}}`包装；原评价器仅按顶层字段取值，导致明确预测未被覆盖率统计捕获。另有完整规则Agent反复复用同一operation_id于不同接口，收到冲突后查询既有凭证而不创建新号；LG1公开文本没有充分解释该号由Agent自行产生。这些不能当作隐藏业务规则难度。

接口0.2位于新增`interface_revision.py`，保留0.1源码和全部原始评分。仅做两项变更：LS1改为每个商品一个强类型`predict_return(item_id,refund_cents,available_on_acceptance)`；LG1改为单布尔`predict_documents(available_documents_sufficient)`。二者都不返回正确答案，也不影响S/C。公开请求补充：每个新写操作自行选新的非空operation_id；只有相同接口/载荷重试才复用，receipt_id仍须使用真实回执。业务规则、任务、状态转换、授权、评分函数及执行预算不改。

独立选定4格：LS-H1、LS-H4、LG-H4、LG-H5，均为oracle完整规则、单次执行。它们覆盖金额预测、边界预测、补件依据记录和正常办理依据记录。复用既有oracle状态，不调用新学习器。选择基于已见接口问题，因此不是盲测、不是额外学习成绩，也不与原44格合并；不能把改善归因于经验学习。

参数沿用600秒等待补充：Flash、temperature0.2、reasoning_effort high、单次8192/累计32768 completion、24轮/60工具，并发2。主实验运行完后再启动这4格，避免实际并发超过2。不因失败追加重复；报告真实完成率、预测覆盖率、操作号冲突数、预算异常及重放结果。

原0.1预测另可做**后验格式敏感性审计**：仅接受原生顶层字段或唯一匹配机制的LS1/LG1外层包装，不修正数值、布尔值或缺失项；有冲突的双重表示标为歧义，不按答案挑选表示。原记录和分数不改。未经校准的预测缺失不能等同于知识缺失。

新增入口在独立进程中通过显式环境适配复用冻结执行循环；版本、源码、工具目录、原始输入及结果均另行归档于`learning-interface-20261011-003`。不影响正在执行的0.1实验。复现命令：

```bash
PYTHONPATH=src python -m unittest discover -s tests/benchmarks/v5/learning -v
PYTHONPATH=src python -m benchmark_v5.learning.interface_probe freeze
PYTHONPATH=src python -m benchmark_v5.learning.interface_probe run
PYTHONPATH=src python -m benchmark_v5.learning.interface_probe validate
```

<a id="benchmark-v5-learning-grader-correction"></a>

## Benchmark v5 学习型评价器依据记录修正

2026-10-11 · Grader 0.2 · 评分修正，原成绩不覆盖

LG-H3的完整规则轨迹正确识别承运方W不能替代检验记录，申请I补件，记录有效V与L及真实补件凭证；原评价器却要求补件依据ID集合等于所有可用资料ID，因未记录不适用的W判P_complete=false。这与“接受等价合法路径、不机械要求冗余材料”的设计不一致。

新增`evaluation_revision.py`只修正依据记录对应的P_complete及其完整服务合取，保持S、C、历史违规、业务规则、实际状态和预测原始口径不变。0.1函数、trace/audit/result均不修改。校正结果单独标记grader版本和输入审计摘要，不能算作模型能力提升或学习增益。

新口径：

- 已办理：真实回执、当前版本/用途下的依据记录可以是已提交资料的子集，但这个子集本身必须足以支持办理；不能用未提交资料冒充已采用依据。
- 合格补件：真实补件回执下的记录须绑定当前合法现有资料；所记录资料与实际请求补齐的证明类型合起来必须足以支持方案。不强制记录不适用或未采用的资料，也不把待补资料当成已有资料。
- 无依据记录仍失败；只有不相关资料、不能补足方案的记录仍失败。原本充分的全量依据继续通过。不因评分修正抹去过去违规。

正反例覆盖V或V+L支持I补件、仅L/空依据不足、未记录依据仍失败、I+V支持包含冗余资料的合法送达。所有已有实际轨迹在冻结原评分之外统一重评，不挑选某个条件使用宽松口径。格式包装预测的后验敏感性分析仍单列，不能与这项义务定义修正混为同一变化。

<a id="benchmark-v5-learning-report"></a>

## Benchmark v5 学习型环境与最小校准报告

2026-10-11

**LG1出现了值得继续验证的经验学习信号；LS1不适合作为当前终态Success难度的主要来源。** 本轮完成隔离环境、方法无关的固定经验协议及Flash主校准，同时发现并隔离了预算、预测接口和依据记录评分问题。不能把这些测量问题包装成业务挑战，也不能据此宣布正式Benchmark已准入。

两个世界仍是合成开发诊断。参考规则已在设计文档公开，当前数据是校准留出集，不是最终盲测Test；未做外部业务代表性认证、新世界适应或跨模型能力排序。v4、旧v5及历史结果保持不变。

### 三部分交付

| 部分 | 交付 | 状态与边界 |
|---|---|---|
| 3 隔离环境与评价器 | LS1合同/退款/可用余额/自然撤销；LG1证明替代/授权/补件/依据记录；审计、S/C/P、重放 | 当前入口为`src/benchmark_v5/learning/current.py`，接口与评价器0.2；历史0.1冻结保留 |
| 4 方法无关学习协议 | 固定共同经验、来源和世界版本、可携带状态、训练/留出隔离、预算、冻结、缺测处理 | 首期实现文本状态公共接口与Flash单次归纳基线，不要求Skill或Memory；主动探索和外部检索后端未实现 |
| 5 Flash最小校准 | 44格计划中40个真实执行，另4格因LS1归纳失败未执行；独立4格接口复核，已完成 | 只用deepseek-v4-flash；未执行格score=null，不补造成绩、不混入业务失败 |

38项工程与运行器测试通过；原30条离线路径及当前0.2的10条参考路径通过重放，当前10条参考路径全部完成。主实验40条真实轨迹已逐条重放、重评分并重建公开模型输入；9份可用状态不变，759个历史保护文件摘要不变。

环境通过白名单工具投影隔离维护侧规则、评分和审计；API中的实验Agent没有仓库文件访问能力。此处不声称操作系统级安全沙盒。LS1只评S，C=N/A；LG1保持独立G分类，没有为了覆盖矩阵拼接I/K。

### 经验与执行条件

LS1有8条共同经验，由真实沙盒退货/账务工具生成；LG1有13条，由授权、无副作用的案例审查生成。两者在声明的有限候选空间内均可定位唯一参考规则，另有相邻整数分/秒证据支持精确边界。不能据此推断排除一切可能规则。

10个留出实例覆盖同世界新数值、条件翻转、机制组合和边界。zero无经验；raw直接使用完整原始经验；processed使用Flash对相同经验的单次归纳文本；oracle获得完整世界规则但无实例答案。每题重新初始化业务状态、克隆同一冻结学习状态，测试私有分数不回流。prefix仅使用LS1前2条、LG1前4条，尚不可辨识，单列诊断。

主实验单次输出8192、累计completion32768、24轮模型/60次工具，temperature0.2、reasoning_effort high、并发2。原180秒等待发生两次超时；在留出执行前另冻600秒补充，任务、输入、token与评分不改。随后LS1归纳耗尽8192个推理tokens却未输出状态，4个processed格因此未执行；LG1归纳成功，文本2688字节。未人工修订学习产物，未加预算反复尝试直到通过。

冻结谱系见[主协议](LEARNING.md#benchmark-v5-learning-protocol)、[等待补充](LEARNING.md#benchmark-v5-learning-latency-protocol)、[独立条件续行](LEARNING.md#benchmark-v5-learning-partial-protocol)。原目录`learning-20261010-001`保留超时；主结果在`learning-20261011-002`。

### 主校准结果

#### LS1

| 信息条件 | 原始S | 预算一致的S | 解释 |
|---|---:|---:|---|
| 无经验 | 4/4 | 3/3 | 其中1次供应方超请求预算 |
| 原始经验 | 1/4 | 无可用样本 | 3次截断，1次成功但超请求预算 |
| 归纳经验 | 未执行4格 | 不适用 | 学习阶段没有有效产物 |
| 完整规则 | 4/4 | 4/4 | 可执行，但不是经验学习成绩 |

工程对照中，始终先选第一个方案可完成3/4；“逐候选受理、读余额、不足则撤销”可完成4/4，仅1次撤销。保留这一合法恢复路径，不能通过一次写入限制、删除余额查询或人为期限制造失败。

真实无经验Agent也出现错误首选后成功撤销重选；该次有预算偏差，不能当作严格同预算胜出，但与结构性捷径一致。完整规则的首次选择4/4正确。**LS1终态S缺少学习必要性，本轮又没有预算干净的经验条件，因此不能证明其可学习性或经验收益，更不能说经验使能力退化。** 可保留账务、金额预测及恢复成本诊断，退出当前核心终态难度候选。

#### LG1

下表同时保留原分数和统一修正后的分数。S∧C表示完成服务分支且无违规；完整服务还需要P_complete，不能用前者冒充后者。

| 信息条件 | S∧C | 原始完整服务 | 修正后完整服务 | 预算一致样本的修正后完整服务 |
|---|---:|---:|---:|---:|
| 无经验 | 1/6 | 1/6 | 1/6 | 1/3 |
| 原始经验 | 5/6 | 4/6 | 4/6 | 4/5 |
| 归纳经验 | 6/6 | 4/6 | 4/6 | 4/6 |
| 完整规则 | 6/6 | 3/6 | 4/6 | 4/6 |

预算一致子集的实例组成不同，只是敏感性口径，不能当作同条件配对提升或显著性检验。归纳与完整规则两组均无预算异常，但仍有依据记录未完成，不能宣布整个任务全部解决。

可核验的业务学习信号是承运方W及意外损坏两条路径：无经验时都错误提交不充分资料；获得完整原始经验、归纳经验或完整规则后，均选择了正确补件分支并保持C。学习没有依赖隐藏授权边界，这里的焦点差异是商业证明适用性。承运方案例的原始/归纳经验执行未完成依据记录，不能夸大成完整成功。

归纳经验六例全部知识预测正确、首次办理/补件分支正确，覆盖有效替代、签发者/原因反转、边界与正常I路径对W限制的免疫。两个短前缀案例均错误放行，但其证据尚不足以辨识规则，不能记为充分训练后的迁移失败。当前结果支持保留LG1作为学习型候选；单轮能学会不构成淘汰理由，也不自动证明它属于高难任务。

### 测量问题与修正

主实验40次均返回可重放轨迹，没有网络/模型标识无效episode；其中只有30次预算一致。7个episode触发length，3个episode有供应方输出超请求预算（共4个响应），其中1个还超累计completion预算。原始结果全部保留；这些失败或额外资源不能作为业务复杂度证据。

预测工具原先同时描述LS1/LG1，部分Agent输出机制外层包装，原评价器漏计。后验格式敏感性分析只识别明确的同机制包装，不改预测值、不补答案。LS1完整规则原始预测统计0/8，归一化后为7/8；这说明原始“未覆盖”不能解释为不知道。LS1原始经验的唯一可读预测为2/2正确，但该episode超请求预算，不能作可靠学习增益。格式敏感性数据单独保存在`posthoc_diagnostics.json`。

LG-H3完整规则案例已合法申请I补件，并记录V+L，但原评价器要求记录所有现有资料，包括不适用的W，错误判P_complete失败。Grader0.2改为检查记录的证据足以支持实际办理/补件方案；缺少依据记录、只记录无关资料仍失败。统一重评40条，只有该条完整服务从失败改为成功，S/C均不变。见[评价器修正](LEARNING.md#benchmark-v5-learning-grader-correction)及独立`corrected_scores_v02.json`，原result不改写。

操作号语义也是执行残差来源：LG1原公开说明不足，多组反复复用同一号于不同写操作；部分执行最终漏记依据。接口0.2公开“新操作自行选择新号、同载荷重试才复用”，并拆成强类型的`predict_return`与`predict_documents`。业务规则与授权不变，修正后的当前入口另存，原冻结版本继续可复现。见[独立接口复核协议](LEARNING.md#benchmark-v5-learning-interface-protocol)。

### 接口复核

四次独立复核全部完成：**4/4完整服务成功、6/6预测正确且覆盖、0次操作号冲突、0次预算异常**。四条轨迹均精确重放、重评分及公开输入重建通过。

全部使用已有oracle状态，不调用新学习器；只验证工具说明与预测格式，不能并入学习对照或算作学习增益。修订评价器在这四条上不改变原分数。此小样本支持接口修订有效，但不代表已用新接口重做完整学习矩阵。原始轨迹及验证在`learning-interface-20261011-003`。

### 去留与后续

| 对象 | 决定 | 下一次进入核心测试前的条件 |
|---|---|---|
| LS1当前任务结构 | 降为执行/账务锚点与可选知识诊断 | 取得事前判断有实际价值的业务依据；若检验学习则先独立核验归纳预算，不能靠截断造难 |
| LG1规则机制 | 保留学习型候选，未正式准入 | 用已澄清接口、修正评分、预算一致的执行验证独立泛化和完整义务；确认资料可得性及待审入口的真实业务依据 |
| 固定共同经验协议 | 保留并继续使用 | 不同方法接受相同证据，冻结状态、报告学习与执行成本；不绑定v21 |
| 当前规则与案例 | 保留为Dev资产 | 不能原样宣称最终盲测；正式Test需在方法选择前另行封存 |

下一步应先固定已修正的测量契约、确认接口预算语义，再围绕LG1验证真正独立的规则组合和业务代表性；不扩大量同构案例，也不急于拼接I/K。没有证据要求增加学习轮数，亦不以一次学习后的高分否定有效经验利用。

### 成本与证据入口

主实验269次执行请求＋2次学习请求，已知共2,500,992 tokens：执行2,480,744、学习20,248。reasoning tokens是completion子集，不重复相加。原180秒阶段还有2次超时请求，usage未知；独立短响应诊断109 tokens。不推算未核验的货币费用。接口复核另有25次请求、123,567 tokens。加上109-token诊断，已知总计2,624,668 tokens、297个有响应的模型请求；另有前述2次usage未知的超时尝试，总请求尝试299次。

- [当前包与复现入口](../../../experiments/benchmarks/v5/learning/README.md)
- [主实验分析](../../../artifacts/benchmarks/v5/learning-20261011-002/analysis.json)
- [统一修正评分](../../../artifacts/benchmarks/v5/learning-20261011-002/corrected_scores_v02.json)
- [重放与历史保护核验](../../../artifacts/benchmarks/v5/learning-20261011-002/validation.json)
- [原始与修正预测口径](../../../artifacts/benchmarks/v5/learning-20261011-002/posthoc_diagnostics.json)

- [接口复核结果](../../../artifacts/benchmarks/v5/learning-interface-20261011-003/analysis.json)及[重放核验](../../../artifacts/benchmarks/v5/learning-interface-20261011-003/validation.json)

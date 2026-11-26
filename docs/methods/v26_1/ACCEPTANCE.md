# OfficeQA v26.1 验收方案

本文件是后续实施验收计划，**下列运行场景尚未执行**。机器可读清单见[acceptance_matrix.json](acceptance_matrix.json)，各项状态为planned；本次设计静态检查单独见[design_validation.json](design_validation.json)。不得把文档检查数量当作离线测试通过数。

## 1 验收层级

| 层级 | 数据与执行方式 | 成功标准 |
|---|---|---|
| D 设计静态检查 | 本地原文、配置、manifest、Prompt和链接；不导入Actor | 四Prompt完整、来源一致、74/172调度准确、文档参数一致、没有运行产物 |
| O 实现离线验收 | 临时合成任务/语料、固定模型响应、故障注入、本地原生工具/评分器 | 下列合同与恢复场景通过，真实请求、网络连接和实验启动均为0 |
| P 真实数据只读预检 | 固定release全部246题；核对任务/来源、构造初始消息、测量输入 | 无缺失/漂移/交叉污染，预算与实际Actor匹配，容量问题在请求前明确报告 |
| E 真实实验验收 | 独立授权后的八批训练及独立172题Test | 覆盖完整、来源可追踪、原预算内完成、指标口径准确；效果是否提升另报告 |

O/P阶段阻断socket和真实provider调用，不读`.env`、不创建正式campaign/evaluation、不启动进程监督或自动化。允许离线本地工具操作合成临时语料。测试错误应失败，而不是被兜底为no_change、零分或默认响应。

## 2 数据与Actor

覆盖A01–A08：

- 核对正式release revision、50/24/172成员、74优化合并顺序、8批大小、source_split保留及Test隔离。对相同ID但不同正文、来源映射或资产字节的记录必须拒绝。
- 将共享Runtime的实际system/user、Skill插入、页面拼接及工具schema与基线核对；UID0007两侧65,536，其他训练/Test32,768；workers4、24轮、原超时和六次额度不变。
- 用合成数值、符号、列表及多标签答案对原生parser/scorer做差分；覆盖第一个answer标签、末行回退、负号、小数、百分号、逗号、单位词、词序导致F1=1/EM=0，无数值容差。不得扩展标准答案输入。
- 检查glob/read/grep路径限制、默认窗口和返回上限；正则样式grep应保持literal，不出现执行代码工具。非法值是工具观察，结构错误整轮不执行工具。
- 覆盖同轮多工具、跨轮重复call ID、24轮耗尽、第六次响应恢复、技术耗尽和未知工具结果停止；正式事件数量与HTTP次数分开。

## 3 证据与模型输入

覆盖A09–A15：完整1/2/24轮轨迹；来源和正式历史核验；隐藏reasoning、失败正文、临时纠错、标准答案及任意metadata隔离；声明页面、实际页面、TXT行号与截断区别；无损编解码及模型实际消息路径。

用合成sentinel区分gold字段、隐藏reasoning、临时反馈和普通可见文档文本：前者不得进入四模块消息或Memory，后者必须逐字保留。检测不能简单搜索“answer”单词或数值相等，因为允许文档中自然出现解题值。

对system共享、同题P/Q user共享、不同题/不同Skill禁止合并、回退原始形式、坏指针、混合表示、数值类型、Unicode和末尾空格分别验证。以完整解码payload比较为oracle，不用“字符数减少”代替无损验证。不应出现source_records、shared_initial或单轮raw_content捷径。

P/Q先按完整Parent完成顺序分配后冻结；Candidate打乱完成顺序仍按ID配对，筛选不重编号。授权工具子引用必须整体识别；历史/Group/Check/其他事件引用必须拒绝。Prose列表与真正历史引用须分别测试。

## 4 四模块与确定性选择

覆盖A16–A29：

| 范围 | 必测行为与oracle |
|---|---|
| Diagnosis | 输入完整批次含成功，合法单例/多Update/no_change；无Group/Checks；错误输出按六次额度处理 |
| Plan路由 | goal/text/basis中的合法直接引用选择完整所属run；reason中的额外引用不选；保存原顺序，success/counterexample不丢 |
| Preconditioner | 每Original一次KEEP/REPLACE/WITHDRAW，完整替换；goal/id/basis不变，Original不可覆盖；全部撤回和依赖协调 |
| Editor权限 | 实际调用消息只有Parent和goal/id/text，不含basis或上游reason；逐Update覆盖，不允许输出完整Candidate字段 |
| patch结构 | 多hunk精确定位、末LF、空/null Parent、空串/null语义、共享context、同一行不重叠字符、歧义/实际重叠/内部插入冲突、同间隙Effective顺序 |
| Candidate | 正确执行全批且不带Parent答案/评分；不能复用Parent目录或只执行所谓受影响题 |
| Replay筛选 | 全批先验证后过滤；两种EM翻转、F1-only、无翻转、null归因、每题一条；完整轨迹而非片段 |
| Replay权限 | 一个事件只引用自己的P/Q；空patch不能关联；不得因修复格式而增加历史/标准答案 |
| Gate | G>0/L=0、G=0/L>0、混合、0/0、空patch；所有未归因事件不投票，不增加整包门槛 |
| Selected | 全选、部分选、全不选、组合抵消、子集非法；按完整文本识别parent/candidate/null，不转移Candidate分数 |

必须包含具体反直觉样例：完整Candidate总成功数持平或下降但有可Retain的关联Update；混合G=3/L=1仍Defer；null退化不计任何Update的L；Selected与Candidate仅末尾空白不同也不能冒称执行来源相同。它们验证本方法真实规则，而不是替方法加净收益保护。

## 5 Memory、停止与恢复

覆盖A30–A36：追加Effective/事件、无事件轮、M编号连续、历史不可修改；Diagnosis no_change、全WITHDRAW、全空patch、Editor null、无翻转、全null、正常Gate等全部分支。验证哪些分支推进游标、哪些追加Memory，以及合法语义停止不能用resume重采样绕过。

对请求记账前后、响应落盘、输出验证、Candidate完成、Replay完成、准备提交、提交文件写入、HEAD切换前后、游标更新前后及final export进行中断注入。预期：恢复不重复已完成请求/工具，不重置额度，不重复M事件，不部分发布；HEAD领先游标的单轮恢复零模型调用；陈旧前驱和损坏记录拒绝。

已发布检查点恢复不重开全部历史Actor文件或重算历史Gate；当前未发布来源仍完整校验。测试须用spy断言该读取边界，不仅检查最终文本。相同提交重试幂等，非空store缺HEAD拒绝，孤立文件不能变成正式结果。

## 6 调度、评估与容量

覆盖A37–A42：完整**合成**74题八批训练和172题Test，最终Skill逐字一致、Test不回流Memory；未完成Test的完整集EM/F1为null并列pending/errors；按题恢复无重复结果。测试不得声称对真实题取得成功率。

容量包含完整10题Parent、10题P/Q全翻转、末批4题、24轮多工具轨迹、增长Skill/八轮Memory及最近一次输出纠错。另用真实初始文本与已归档训练轨迹进行只读长度测量，历史轨迹只能用于容量评估，不导入新优化。报告每模块原始/编码字符与UTF-8字节、system说明开销；可用本地参考tokenizer估计但标明非provider实测。不能因为表示节省很多就宣称一定满足模型上下文。

验证可执行配置隔离、没有Grouping槽/目录/Prompt、没有Verifier/Repair/Stage0/自动Test、旧版本文件和旧实验不变。未来验收报告逐项登记场景、输入fixture、断言、结果、日志及未覆盖项，不能仅用聚合“若干测试通过”取代矩阵。

## 7 真实实验完成标准

训练八批按计划结束，短路分支合法、技术失败不伪装完成，最终Selected与HEAD/游标一致；每轮事件与Gate计数可复核，null归因和未执行新组合单列。Test完成172题且Skill一致才发布完整EM/F1。每次实际请求、失败、重试、已知和未知usage均可计数，reasoning不重复计入total。

效果报告依据[EXPERIMENT.md](EXPERIMENT.md)比较，旧118/172必须标注混合预算。达成工程完成不等于方法提升：若新分数下降或归因不可靠，应如实报告，不能通过补测、换checkpoint、静默增预算或删退化事件完成验收。

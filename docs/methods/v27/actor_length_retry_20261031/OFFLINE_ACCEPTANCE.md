# 当前截断重试修订版：v27 离线验收清单

状态：review_01 修订，待未来实现后执行。本文件列出 fixtures、预期结果与保存证据，不是已通过报告。当前文档检查核对链接、schema 示例、来源哈希及五份 Prompt 内嵌协议一致性；不验证模型行为。

验收进程使用独立 LMB 环境，模型输出为固定合成响应；禁止真实模型、benchmark rollout 和实验入口。HTTP 层显式注入 MockTransport（不能只 patch httpx.Client.send，因为 SDK 可能使用 httpx2），同时设置网络连接拒绝哨兵。所有合成任务有独立 ID，不混入 53/124 数据。

## 来源 数据与消息

| ID | 场景 | 预期结果 |
|---|---|---|
| S01 | 核对迁移底稿与 Prompt 哈希 | 精确匹配冻结版本；旧 v26 campaign 不能当作 v27 恢复 |
| S02 | 修改一份冻结源码/Prompt/运行配置 | 恢复拒绝，明确身份不匹配 |
| S03 | v27 通用模块残留 OfficeQA 导入或领域资源 | 独立性验收失败；不能通过 adapter 名称伪装完成 |
| D01 | SkillAdam ID 清单＋当前内容快照 | 35/18/124、全集177、无重复/交叉/缺失；202512:46 在 Selection |
| D02 | ID 中出现 :2、:10、:11 | 使用字符串排序，不擅自自然排序；Train 排好后接 Selection |
| D03 | 合并与分批 | 53个独立ID，六批 10/10/10/10/10/3，无重复补齐和第二次循环 |
| D04 | 按批次执行合法 no_change | 仍推进到下一批；全部合法不更新也能完整完成六批 |
| D05 | 原 prepared_v1 与 raw 检查 | 文件哈希不变，新视图独立；来源 split 保留 |
| D06 | 选项规范化与打乱 | 对177题离线比对 SkillAdam，呈现文本、标签、正确映射一致；特别检查首尾空白 |
| D07 | 并发完成顺序变化 | 不影响选项、P/Q编号、冻结批次顺序；不使用共享 RNG 状态 |
| A01 | 同题 Parent/Candidate 使用不同 Skill | user 消息、模型参数及预算完全相同；system 仅允许 Skill 内容相应变化 |
| A02 | 固定基础 Prompt 与原生 initial.md | 基础协议按 SkillAdam，初始 Skill 原文字节不改；无 Stage0 |
| A03 | task 原始对象含 theorem/sketch/paper_link/答案元数据 | Actor 仅白名单 question/choices/Skill，不序列化整对象 |
| A04 | 复用/新建执行身份 | v27 Gate Parent 必须为当前诊断 Parent；Candidate 独立 run_id，不继承对话 |
| A05 | 五份 system Prompt 的完整基础协议 | 均与冻结 SkillAdam VENDOR_PROMPT 去掉 Skill 插入后的文本及协议快照精确一致 |
| A06 | system 说明与实际 Actor 模型/预算/重试配置不一致 | 配置冻结/预检失败；不能让优化模块按错误能力判断，也不能静默覆盖运行配置 |

保存：来源清单校验、53/124 ID 和批次列表、原始/规范化/呈现映射对照、许可请求消息与哈希。数据准备验收不意味着运行了题目推理。

## 证据与权限

| ID | 场景 | 预期结果 |
|---|---|---|
| E01 | raw reasoning_content 放入唯一合成哨兵 | 所有模块序列化输入、摘要、反馈和 Memory 均无哨兵；原审计层可存在 |
| E02 | 嵌套 provider metadata、错误对象包含隐藏哨兵 | 不因顶层删字段而漏出；只构造白名单事实 |
| E03 | 引用 P1 或历史 run 引用展开 | 最多获得许可 run，不能拿到原 HTTP 响应、凭据或隐藏正文 |
| E04 | 只有标签的普通 content | 保存原文；不生成合成推理、检查过程或工具轨迹 |
| E05 | ordinary content 带模型解释 | 原文完整可见，仍标记为模型陈述；不将其判断自动写成独立事实 |
| E06 | 评分前/后边界 | correct_label/text 只进入 outcome；Actor消息不含后验反馈 |
| E07 | 多次 HTTP 尝试后一次有效响应 | attempts 模型轮次数仍为1；api_requests 记录真实消耗；失败正文不获事实引用 |
| E08 | P1:1_t1、多轮引用、未知来源 | 拒绝；LMB 没有工具事实或第二个生成轮次 |
| E09 | 输入加入未授权字段 | 投影前构造/校验失败，不忽略后偷偷传递 |
| E10 | Editor basis 引用、原始响应路径诱导展开 | 不执行读取；Editor 仅 parent/plan，通用字段权限同样适用 |
| E11 | Editor 固定上下文与动态投影 | system 有完整基础协议及执行条件，user 仍只有 parent/plan；无执行正文或 Memory；不因补充协议扩大权限 |

保存：每个模块的实际可见消息、允许引用集合、哨兵扫描结果、raw/allowed 分层身份。权限检查还需人工审阅投影逻辑，不能只靠列举几个禁止字段。

## 输出契约与编译

| ID | 场景 | 预期结果 |
|---|---|---|
| G01 | 多组、单例、同分不同情况 | 合法；每个run恰好一次、group字段精确 |
| G02 | 漏成员、重复成员、未知引用 | 校验失败，可定位反馈 |
| G03 | shared_basis只引outcome或只引组内一个成员 | 每成员返回轮次证据检查失败 |
| DG01 | revise的有效多Update计划 | Goal/Updates/Checks及引用通过；不要求固定Update数量 |
| DG02 | no_change且plan=null | 合法；停止当前修改链路，不重采样 |
| DG03 | need_evidence、revise空Updates或no_change带Plan | 输出校验失败，不当作合法停止 |
| DG04 | basis只有Group；Group缺同组成员直接证据 | 校验失败；满足约束后通过 |
| DG05 | Check引用不存在Update、ID冲突 | 校验失败 |
| P01 | 每项KEEP，checks=null | KEEP三元关系通过；Effective Plan保留，继续Editor |
| P02 | 所有KEEP但Checks合理替换 | 结构允许；不能因没有patch而认定无更新 |
| P03 | 单项精确patch及其他项KEEP | 保留原ID/来源和未改项；不修改原Plan字节 |
| P04 | 一项撤回，Checks仍指向它 | 失败；提供完整无悬挂替换列表后通过 |
| P05 | 全撤回，checks=[] | 编译no_change；不调用Editor/Candidate/Replay |
| P06 | 全撤回，checks=null | 仅原Checks已空时合法；否则失败 |
| P07 | 漏target、重复target、新target、新ID拆分/合并 | 失败；每个Original恰好一条adjustment |
| P08 | KEEP配非空focus/to；非KEEP配空focus | 失败，D/S/C重复或未知值也失败 |
| P09 | 输出顶层decision/reason/need_evidence | 失败；这些不是模型顶层字段 |
| P10 | 历史Evidence无前缀、伪造namespace、未授权来源 | 显式引用验证失败；普通数学代码片段不误当引用 |
| P11 | 仅Group引用试图带入全部组成员 | 不展开；当前runs仅由直接Plan执行引用选出 |
| P12 | 输入projection含Grouping正文或历史raw sources | 失败；内部校验上下文与模型视图分离 |
| P13 | 主策略合理，但附带不当强制顺序/退出条件；合成输出全KEEP | 结构可能合法，人工语义评审不通过；应在原target内修正局部，保留支持部分，不另增KEEP项 |
| P14 | 重要历史反例与当前Original相关；reason泛称证据不足 | 人工评审不通过；须具体说明适用差异、既有范围或联合干预等依据；反例支持修正时不能借KEEP跳过 |
| P15 | 有范围、有任务与预算依据的全选项检查，对照无条件默认穷尽证明 | 前者不能仅因策略类型而被否定，后者需具体审查范围和代价；人工评审，不以关键词设自动禁令 |
| P16 | 一项修正冲突，另一KEEP项仍保留同一矛盾条件 | 最终Updates整体语义评审不通过；不能只检查patch项 |
| ED01 | 有效多hunk patch | 原文精确应用，生成actual_diff；Parent不被原地修改 |
| ED02 | 重复匹配、无定位插入、重叠/逆序hunk、编号@@ | 拒绝；不fuzzy、不排序、不自动修复 |
| ED03 | 原文/结果无末尾LF | 标准no-newline标记准确，内容哈希符合预期 |
| ED04 | 空patch | 合法不更新，Parent/Memory保留 |
| ED05 | null patch | 语义阻塞；不重试强求替代、不跳回Diagnosis |
| ED06 | 空白patch、应用后无实际变化或空白Skill | 拒绝，不作为有效Candidate |
| ED07 | Plan已有部分满足 | 合成输出只改必要部分；验证完整实施要求由人工语义评审补充 |
| ED08 | 要求已被基础协议满足，或Parent仍有冲突 | 前者在全部满足时允许空patch；后者不能仅因协议已写而宣称满足；人工评审精确措辞及作用范围 |
| R01 | 新entry，revises=[]，多个knowledge且并集有Diff和执行来源 | 合法，每Knowledge独立text/evidence与语义支持 |
| R02 | 修订一个/多个活动entry | 全部替换；未提及的活动entry保持；旧ID不被重用为新提案ID |
| R03 | 相同Memory target被两entry修订 | 拒绝 |
| R04 | 空knowledge、Knowledge ID、entry-level evidence | 拒绝；空knowledge不是删除 |
| R05 | entries=[] | 合法，沿用既有归档/commit记账，不暗示撤回所有Memory |
| R06 | 仅引用当前未提供或未授权历史来源 | 拒绝；Memory ID不能替代执行evidence |
| R07 | Replay计划仍含basis或引用展开历史整轨迹 | 投影检查失败；使用id/text Update与Knowledge Only |
| R08 | 某entry的evidence并集只有outcome/轮次，无Diff | 结构校验失败；不能用别的entry的Diff补足 |
| R09 | 某entry只有当前/历史Diff，无执行来源 | 结构校验失败；不能虚构执行引用补足 |
| R10 | 同entry不同Knowledge分别含Diff和执行来源；对照分属两个entry | 前者可通过并集结构校验，后者拒绝；前者仍须逐项人工审查自身evidence能否支持其陈述 |
| R11 | 完整替换保留纯历史Knowledge，并集有授权历史Diff及执行引用 | 合法，不强制加入当前diff/P/Q；每项只用已提供Knowledge中的精确历史ID |
| R12 | 历史主张硬贴当前diff，或以当前P1替换历史R01/P1 | 未授权ID在结构层拒绝；引用虽存在但不支持主张时人工评审不通过 |
| R13 | 一项有完整证据，另一项引用无关证据并借用前者解释 | entry并集可合法，但逐Knowledge语义评审不通过；不能以并集当共享支持 |

结构测试不能证明自然语言正确。人工评审样例单独检查：数学条件/强度被保留；标签-only不捏造行为；允许合理探索；KEEP不等于Memory为空；多clause共同干预不虚构独立因果；历史整entry修订不丢失仍有支持的比较。

## 评分与终止

| ID | 输入/情形 | 预期 |
|---|---|---|
| V01 | 单个正确/错误answer标签 | 按呈现标签评分1/0 |
| V02 | 多个完整answer标签 | 原生解析取最后一个；format_compliant=false |
| V03 | 无标签但最后非空行是有效标签 | 原生回退可得分；format_compliant=false |
| V04 | 标签大小写/尾标点、选项全文、首token | 精确遵循SkillAdam normalize/casefold/回退，不自创更严规则 |
| V05 | raw content错，外部answer/predicted_answer正确 | 必须从content重算，不能被外部字段覆盖 |
| V06 | raw content正确，缓存预测标签错 | 复算不一致检查失败，不能静默使用缓存标签 |
| V07 | length有可解析标签 | 归档但不评分，原消息重试；与技术错误共享六次总额度 |
| V08 | length且合法message.content=null或空串 | 可重试失败；六次耗尽停止，无结果；恢复不重置额度 |
| V09 | stop且content为空字符串 | 完成且0分；格式/解析状态如实记录 |
| V10 | 非length的null、数字content、缺choices/message | 响应结构错误；按冻结技术策略，与截断共享总额度 |
| V11 | 拒绝或未知finish_reason | 显式停止/分类，不计作普通错误 |
| V12 | 解释正文中有隐藏字段同名文本 | 不按词面删除普通content；权限过滤作用于来源/结构，保留真实普通回答 |

format_compliant标准见CONTRACTS：一个完整标签、内部为大写单标签、无额外不完整/重复标记；只做审计，不修改原生EM。

## 配对 发布与恢复

| ID | 场景 | 预期结果 |
|---|---|---|
| F01 | 同题不同题干/选项/预算/scorer/Skill来源 | 拒绝配对；run_id相同也拒绝 |
| F02 | Candidate完成顺序与Parent不同 | 按task_id配对，保留P顺序并重标Q；结果不受完成顺序影响 |
| F03 | 正确数增加/持平/减少 | ACCEPT/RETAIN/RETAIN；同分不同错误题仍RETAIN |
| F04 | 十题和三题尾批的全部离散正确数对 | v27严格增加与SkillAdam 0.08门槛接受结果一致；不声称执行过程相同 |
| F05 | length记录与技术失败 | 都不能作为已完成配对；仅接受stop结果 |
| F06 | 无更新三条合法路径 | 不调用Candidate/Gate/Replay，不新建Parent-only学习；状态推进且Memory不变 |
| F07 | ACCEPT/RETAIN均产生有效Replay | 分别发布Candidate/原Parent，以及正确的新Memory |
| F08 | Gate已接受但Replay失败 | 正式Parent/Memory均不变，临时Candidate不成为已发布版本 |
| F09 | 发布前/后模拟中断 | 发布前可恢复验证；发布后不重复commit或再次Actor调用 |
| F10 | 响应已保存、解析前中断 | 本地重新解析，不消耗新请求 |
| F11 | 发出请求后结果未知 | 额度计入、状态标unknown；恢复不假称未调用或恰好一次 |
| F12 | 六次额度耗尽后恢复 | 不自动获得第七次；SDK隐式重试为零 |
| F13 | stop错误答案/格式错误及length | stop不因得分补答；length无论是否含正确标签均原消息重试 |
| F14 | 方法输出格式/引用/patch错误 | 最多六次，反馈只含授权输出与定位错误；预算和身份恢复一致 |
| F15 | 并发worker调用 | 绑定正确benchmark上下文，无全局串扰，输出顺序确定 |

保存：模型stub调用计数、阶段日志、发布前后状态/Memory哈希、恢复请求计数和中断位置。模拟时间而不等待真实300秒。

## 容量与评估边界

| ID | 场景 | 预期结果 |
|---|---|---|
| C01 | 增长的Skill、Memory、十题配对和校验反馈 | 用实际模块消息及预留输出核算容量；不计raw reasoning正文 |
| C02 | 很长reasoning但很短ordinary content | 许可输入不因隐藏正文膨胀；usage仍真实统计reasoning消耗 |
| C03 | 精确去重再恢复 | 原JSON类型、文本、引用、run身份无损；不得合并不同执行 |
| C04 | 输入超限 | 显式失败；不裁剪证据、不自动改批次、预算或Prompt |
| T01 | 初始/v27/SkillAdam三组Test bundle | 每组124、冻结Skill/Actor/scorer同条件；结果不进入Memory |
| T02 | 未完成六批就请求正式最终版本 | 标未完成，不自动用最后临时Candidate评Test |
| T03 | Test结果更好诱导回选检查点 | 不允许在该运行内改选版本或更新Skill |
| T04 | v27和SkillAdam正常十题完整迭代 | 任务执行20/30差异在报告体现；合成统计不混同优化器调用 |

离线通过标准：实现后的场景报告分别注明通过/失败/不适用与证据路径；关键路径无跳过，无真实网络或模型调用。文档中的人工语义评审项目不能伪装成已自动证明。

# V22 57项五轮：R4 Actor网络中断恢复

> 后续授权：原R5截断已归档并同请求恢复成功；新停点为Candidate的网络中断，见[R5恢复报告](ALFWORLD_57_FIVE_ROUND_RECOVERY_04.md)。以下保留此次网络恢复的历史结算。

2026-10-17，用户明确要求归档ChunkedEncodingError并重启。此次技术恢复只重建中断episode状态并重发原第22请求，随后继续原R4/R5；所有旧失败、已报告费用和未知费用均保留。

目录：`artifacts/methods/v22/23_alfworld57_five_round/recovery_03/`。
控制与授权：同级`recovery_03_control/`。

## 归档与恢复方式

原`recovery_02`完整目录由`prior_archive_manifest.json`冻结。失败val:0000的部分轨迹、21份可用原始响应、失败第22请求、进程日志和未知usage独立保存在`archive/network_attempt_01/`，未伪造缺失响应或费用。

复用83条完整episode及15个成功语义阶段，前三轮state重建后与原文件逐字一致。中断slot单独创建一个相同游戏、wrapper、seed=42和调用条件的环境；使用原始未改动的`run_episode`、`chat`和动作解析函数，由缓存回调返回前21个原模型决定，环境重放这些动作以恢复状态。逐项核对初始观察／动作列表、每步结果、reward/done/won、下一步合法动作列表和每次模型输入。任何不一致都在新API请求前停止。

第22请求只有在完整messages和HTTP请求体哈希与原失败请求相同时才发送。其后继续原总计50动作上限，最多新增29次Actor逻辑请求；前21个模型决定不重采样、不新增收费调用。新轨迹明确标记缓存决定及原source，状态重建独立记录于`restoration_audit.json`；复制的旧usage只作为来源，不计入新增消费。

R4其他11个已完成任务全部复用，不重跑正常失败。剩余流程沿用原v6、P1、统一引用、模型、Prompt、任务顺序、Gate及Memory规则，不增加Pilot或语义探针，不修改旧输出。

## 冻结预算与离线核验

新增上限：1个恢复环境＋30条后续新episode、1529次Actor逻辑请求、10次语义请求；仍最多114条完整评估slot。物理环境实例累计最多115，因为原中断实例单独保留；它不是额外训练任务或独立重采样。此前17次语义调用＋剩余10次最多27，包含旧失败。新的网络／episode／语义额外重试为0；已有有界HTTP状态重试规则保持。

5项最终离线测试通过：原中断不能当任务失败；前21步复用并只对完全相同第22请求调用一次模拟HTTP；状态漂移时0次新HTTP；总50步不变且最多29次新增请求；完整复用83episode／15阶段／3个发布state，缓存前缀usage不重复计费。测试全部使用模拟HTTP／环境，没有真实模型或环境探针。

## 运行结算

恢复已成功：前21步状态逐项匹配，第22请求哈希`3750ada5e1bf01968e7ccf6d29f8def30db1b4e0fd06b29e0abf04db447643ac`与原请求一致；只新增第22–24次模型调用，val:0000在第24步成功。R4完整发布，随后R5在Fusion输出截断处按协议停止。原生report包括复用记录用于核验；新增／累计消费由控制器按mode及恢复step>=22去重计算。最后旧网络请求的费用继续记为未知，不能当零。

最后先前正式状态是R3的No Skill／1条修订后Memory；原已完成结果为R1 12→12、R2 10→7、R3 8→7，均RETAIN。R4原11项为8成功、3正常步数失败；val:0000从第22请求继续，而非重新进行前21个模型决策。

## 结论边界

技术恢复不改进或筛选语义结果。任何正常退化按原Gate处理；没有有效Memory共同发布不推进下一轮。历史解释偏差保持原样，契约通过不证明其语义正确，也不证明方法优于无Memory。独立Test仍不参与优化。

## R4已发布结果

Parent 9/12、223步，Candidate 9/12、207步；Gate RETAIN，逐任务无胜负变化。正式Skill继续No Skill。Fusion将u1替换为u5，允许台灯与目标分离时的两种顺序，迁移w1→w5；changes.basis只有当前组与事件，但总reason明确提到历史Effect `475639db59e4b82bd457eeb139b6b6d4542275f903bb5a54bc17581963a635f1:m1`，认为其温度关系无需用于修改当前对象关系要求。因此记录为历史适用范围判断，不能因basis无历史ID而声称没有消费Memory，也不能据此声称历史造成改进。

Memory 6 Findings、5 open，新增Effect `1955e42f936335ef0a4007b6682625edc6552d48093495657cf43e54fea91a0e:m1`（6 basis、5 limits），旧温度Effect（17 basis、11 limits）保持，正式Memory变成2条。val:0000实际24→3步，其他成功任务部分多1–2步；联合修改与随机性不能独立归因。

P1共享内容再次被错误解释为“不独立执行”：f3/f4/f5/f6和新Effect的limits[1]涉及train:0037、val:0003、val:0004、val:0006。只读核查确认四对都有不同run ID、Skill、首请求哈希；相同动作内容不等于同一次执行。原输出与Memory没有修改，证据保存在`analysis/recovery_03_semantic_identity_audit.json`。

R4 Fusion完整消息298376字符、Memory346618字符，均通过400000字符与1M上下文预算检查。

## 最终停点与五轮结果

本次恢复于北京时间2026-10-17 00:02:37启动，00:39:21停止，墙钟2203.893秒（36分43.893秒）。完整发布4/5轮。**本次授权的ChunkedEncodingError恢复成功；新的停止原因是R5 Fusion输出预算耗尽。** 没有自动重试新的错误，没有改Prompt、参数、任务、Gate、模型输出或Memory。

|轮次|Parent成功率|Candidate成功率|Parent→Candidate步数|Gate|发布|
|---|---|---|---|---|---|
|R1|12/12，100%|12/12，100%|171→83|RETAIN|完成|
|R2|10/12，83.33%|7/12，58.33%|208→320|RETAIN|完成|
|R3|8/12，66.67%|7/12，58.33%|328→311|RETAIN|完成|
|R4|9/12，75%|9/12，75%|223→207|RETAIN|完成|
|R5|6/9，66.67%|未执行|239→未执行|未产生|Fusion技术失败|

R5分类、Diagnosis均通过；Diagnosis提出4要求、4Watch。Fusion HTTP 200，模型deepseek-flash，max_tokens=32768，finish_reason=length；输入113065 Token，输出32768 Token，其中推理32768 Token，最终content为空。请求耗时156.324秒，未形成有效Fusion或D/S/C更新。它不是合法Keep、no_change或行为失败，R5 Editor、Candidate、Gate、Replay、Memory未执行，也未发布R5 state。

完整请求及原始125295字节响应保存在`recovery_03/rounds/r5/calls/fusion.json`和`fusion_responses/step_0001_attempt_01.body`，响应SHA256为`be484fdc20c6594bc7d76b921b8ce36cd25dcb4e336a6ecbe722c98fa0a19256`；失败结算见`analysis/recovery_03_failure_summary.json`。恢复预算已耗尽，未自行增加输出预算或同请求重采样。

## 版本、继承与正式状态

v6/P1/统一引用、官方deepseek-flash路由、固定57项12+12+12+12+9、seed42、50步、8并发均保持原冻结设置。实际源码及所有继承源码、Prompt、Schema、验证器和模型配置继续由原`runtime_freeze.json`及各恢复目录快照约束；此次恢复runtime摘要为`e43cd22c650271a5e6c8a357aa01dc0b9326f92cc66ea196c099d5fe1be25db1`，摘要包含恢复目录等元数据，不应把不同摘要直接解释为算法变更。控制器、授权、恢复策略另行冻结在`recovery_03_control/authority.json`。

五轮的`parent.json`和`memory_before.json`逐轮与前一个已发布state匹配，R1对应state0；前三轮发布state与旧档案逐字一致。R4正式state为`recovery_03/rounds/r4/state.json`：No Skill、2条Effect、已接触48个本轮序列任务；R5执行与分类/Diagnosis的接触记录另外保留在其轨迹和调用记录，不能因R5未发布便抹去9项接触。全部57项Parent已实际执行，105个Parent/Candidate完整slot已完成。原中断实例额外保留，物理环境实例累计106。

四轮Gate均RETAIN，所有正式Parent均No Skill。Skill继承路径已实际运转，但本次没有ACCEPT后的真实Skill继承观测；ACCEPT路径仅由离线测试验证，不能与本次真实结果混淆。Memory连续经历1条新增→1条替换→1条替换→再新增为2条，并真实传入R5，失败Fusion未改变正式Memory。

## 历史预条件化与解释边界

R1空Memory真实Fusion Keep，没有历史D/S/C变换。R2两次replace（u1→u3、u2→u4）明确以R1 Effect为basis，将全局未访问集合改为两对近期上下文内的搜索/处理约束，4个Watch迁移；这是历史Effect实际进入修改理由的直接证据。R3两次replace（u2、u5）及2个Watch迁移，显式basis只有当前轨迹与组，不能断言历史直接导致变化。R4一次replace及1个Watch迁移，历史Effect在reason中被判定为温度场景适用范围，保持其余要求。R5输出截断，无有效决策。没有人为将replace再追加编码为未输出的D/S/C字段。

R2修复train:0023，但退化train:0014/0015/0017/0021；R3修复train:0033，退化train:0026/0034；R4逐任务胜负不变。温度动作及台灯循环的局部步数下降有真实轨迹支持，联合修改、任务位置选择及一次采样差异仍不能独立归因。

历史语义偏差持续保留：R1对countertop操作的事实概括不准确；R2/R3/R4把P1共享内容误判为非独立执行；R3未找到对象被过度解释为搜索要求无触发机会。R4新Effect还将某Parent run ID写作candidate标识，实际Candidate Skill以`candidate.json`的SHA256为准。R2曾通过retire_limits修订“没有失败案例”的旧边界，但共享输入的身份误解未被后续模型纠正。各轮原始Findings、basis、limits、diff和配对身份保持原样，只读分析不回写学习状态。

## 用量、失败与资源

以下仅统计新增实际请求，缓存83条完整episode、15个阶段及21个前缀响应均不重复计费。

|口径|此次恢复新增|全实验累计（含历史失败）|
|---|---:|---:|
|Actor逻辑请求|449|2091|
|语义请求|8|25|
|HTTP尝试|457|2116|
|输入Token|856316|3000116|
|输出Token|795398|3358530|
|其中推理Token|746618|3138437|
|总Token|1651714|6358646|
|未知usage请求|0|1|

本次新增21条完整新episode＋1个恢复实例，合计22个完整slot；旧83条直接复用。累计105个完整slot＋1个未完整原网络实例，不将恢复前缀重算为新模型决策。四次执行墙钟相加7650.051秒（约127分30秒），不含等待用户授权的间隔，不能将并发episode耗时直接加成墙钟。

已知技术失败共4次：原R1 Editor摘录契约、原R3 Fusion非法JSON、R4 Parent网络分块错误、R5 Fusion截断。前三次分别经用户明确授权恢复；本次新截断未恢复。所有失败费用保留，未知网络费用不当零。

按本实验先前核对的[官方人民币价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)（所有实际请求时间均在非峰值，百万Token输入命中0.02元、未命中1元、输出4元），本次新增已报告usage估算3.9253元，全实验15.8858元，约15.89元，另加1笔未知费用。累计输入命中559616、未命中2440500，推理已包含在输出，不能重复相加。这是根据usage和单价的估算，未查询账户账单。逐段计算见`analysis/recovery_03_cost_estimate.json`。

## 核验与后续研究

事后既有验证器返回artifact_valid=true、campaign_complete=false、published_rounds=4、incomplete_rounds=1、semantic_call_records=23。23为当前档案阶段记录数；25为去重后含历史失败的实际累计语义请求，二者口径不同。控制器确认all_prior_archives_unchanged=true；5项恢复离线测试通过。逐任务结果、Fusion输出、Memory变化及容量测量汇总于`analysis/recovery_03_final_results.json`。原始Prompt、请求、响应、diff、实现映射、Goal、Watch、Findings及Effect均保留在轮次目录。

当前观测支持Memory可连续发布、继承并参与Fusion理由，且合法候选可以改善局部循环、也可能降低整批成功数。没有一轮严格提高成功数，没有正式Skill获接受，且五轮尚未完整完成；不能声称有效持续Skill进化已达成，也不能将程序契约通过写成行为解释完全正确。

后续消融应在等预算、等任务顺序及可比随机性下比较有/无Memory与历史消费路径，重点核查共享表示与执行身份、触发机会、联合修改归因及错误Effect修订。独立Test必须使用未参与本次优化的数据；Selection已属于开发池，不再承担独立选择或泛化评估。此处列出研究问题，不在此次实验中追加消融、Test或探针。

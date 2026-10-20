# V22 R5 Fusion截断归档与授权恢复

> 后续授权：三个网络中断已归档并恢复完成；R5 Gate为ACCEPT，但Memory容量超限未发布，见[最新报告](ALFWORLD_57_FIVE_ROUND_RECOVERY_05.md)。以下保留此前技术停止记录。

2026-10-17，用户明确授权“归档R5 Fusion，重启”。完整保留旧recovery_03和费用，新的独立运行目录为`artifacts/methods/v22/23_alfworld57_five_round/recovery_04/`，控制与授权为同级`recovery_04_control/`。

旧Fusion HTTP 200但finish_reason=length，32768输出Token全部为推理，最终正文为空。该响应未形成有效更新，不是合法Keep或行为退化。原始请求、响应、容量与usage单独复制到`archive/fusion_attempt_01/`，旧目录另以完整清单冻结。

仅重跑一次完全相同的R5 Fusion请求，不提高32768预算、不改变模型、Prompt、参数或历史证据。105条完整episode、22个成功语义阶段以及四轮发布状态直接复用；成功后自动继续Editor、同批9项Candidate、Gate、Memory和正式发布。额外恢复为0，任何新技术失败仍按协议停止。

新增最多3个语义调用、9条50步Candidate episode，8并发保持；累计完整slot上限114，原中断实例保留，物理实例最多115；累计语义请求最多28，包含所有历史失败。费用按实际新增调用去重，旧网络未知费用保留。

恢复实际已执行并结算：R5 Fusion与Editor成功；随后R5 Candidate因新的网络错误按协议停止。仍完整发布4/5轮，正式状态No Skill＋2条Memory。R5 Parent为6/9、239步，不重新运行。

## 归档、冻结及实际恢复

4项离线恢复测试通过（42.859秒）：原截断与32768预算保留；变更messages在调用前拒绝；缓存阶段无网络调用且拒绝重复；完整重建105条episode、22阶段与四轮发布state，在模拟R5 Fusion停点只调用一次模拟generate，不调用真实环境或API。它们只核验恢复边界，不是Pilot。

正式恢复从北京时间2026-10-17 00:45:05.915运行至00:49:30.190，墙钟264.274秒。旧recovery_03及独立Fusion错误档案经哈希清单冻结；新的runtime摘要为`6d233bff159f493cddb819f278660be7fcd667787c81812c3263067e12c795c8`，源码、继承、Prompt、配置和模型路由与原冻结相同，目录元数据不同。控制器及恢复协议也已冻结。

实际新Fusion与旧请求的完整messages、参数及HTTP请求体哈希完全一致，哈希为`75d2f389b1639fd23f6b8399ba1aab928f9ea3f03db8f3433b5a42f551e2ec8e`，独立核查在`analysis/recovery_04_request_identity.json`。未加入失败反馈，未增大预算。

Fusion输出ready、changes=[]，即Keep全部原始Requirement；新增一个关于搜索耗费步数后能否完成状态改变和放置的Watch w5，未新增要求。reason明确引用温度Effect `475639db59e4b82bd457eeb139b6b6d4542275f903bb5a54bc17581963a635f1:m1`，认为u1已包含其适用方向，搜索/预算限制继续保持；又明确判定台灯Effect `1955e42f936335ef0a4007b6682625edc6552d48093495657cf43e54fea91a0e:m1`不适用于本轮。requirements_changed=false与history_cited=[]只是结构化changes.basis摘要，不能据此忽略reason中的历史消费。

Fusion输入113065、输出13962（推理13488）Token，finish_reason=stop；Editor输入112528、输出6719（推理5700），契约通过，生成实际Candidate及diff／实现映射。Fusion完整输入362604字符、Editor359693字符，均通过原400000字符及上下文检查。没有运行到Memory容量检查，不能宣称它已通过。

## 当前五轮结果与准确停止阶段

|轮次|Parent|Candidate|Gate|发布|
|---|---|---|---|---|
|R1|12/12，171步|12/12，83步|RETAIN|完成|
|R2|10/12，208步|7/12，320步|RETAIN|完成|
|R3|8/12，328步|7/12，311步|RETAIN|完成|
|R4|9/12，223步|9/12，207步|RETAIN|完成|
|R5|6/9，239步|5成功、1正常失败、3不完整|未执行|未发布|

R5 Candidate记录189次逻辑请求，实际执行186个动作；三个失败请求都没有返回可执行动作，不把请求数误写为执行步数。

|任务|Candidate状态|已执行动作|停点／说明|
|---|---|---:|---|
|val:0009|成功|6|完整|
|val:0010|技术中断|13|第14请求ProxyError|
|val:0011|成功|22|完整|
|val:0012|成功|14|完整|
|val:0013|技术中断|45|第46请求ChunkedEncodingError|
|val:0014|成功|8|完整|
|val:0015|成功|7|完整|
|val:0016|正常失败|50|达到步数上限|
|val:0017|技术中断|21|第22请求ProxyError|

两个ProxyError请求分别于00:48:39.483和00:48:39.767发出，约0.0024与0.0074秒后失败；ChunkedEncodingError于00:49:27.873发出，约1.090秒后失败。记录只能证明客户端传输／代理错误，不能据此确定服务商、代理配置或链路中哪一端是根因。三次都没有完整HTTP响应、状态码或usage，不伪造缺失正文，不将未知费用当零。并发中已经派发的其他任务自然结束，未为获得更好结果重采样。

旧R5 Fusion截断已经恢复成功；**当前新阻碍在R5 candidate_execution，不在Fusion**。额外恢复为0，运行器停止，没有Gate、Replay/Memory调用或R5正式发布。Candidate整体成功率未知，不将3个中断记成失败，也不从不完整批次推断RETAIN或ACCEPT。

完成对中已观察到val:0014/0015从Parent的步数失败变为成功，val:0016从Parent成功退化为50步失败；它们是当前联合Skill的一次配对观测，不是Memory确认的Effect，也不能独立归因于某一条要求。未完成任务不列为行为回归或修复。

## 继承与证据保留

四轮发布state均与旧记录逐字一致；R1到R5的Parent和memory_before逐轮匹配上一个正式发布state。四轮仍全部RETAIN，正式Skill为No Skill，Memory为两条已发布Effect。R5新Candidate从未发布，旧Memory未因新Fusion、Editor或部分Candidate结果变化。

旧R1事实概括、R2–R4共享内容被误判为非独立执行、搜索触发机会解释等偏差完整保留，详见前次报告和只读identity audit。当前没有R5 Memory，不能声称这些偏差已在第五轮修订。独立Test未参与，57项开发池身份、顺序、split、seed及既往接触记录保持。

所有正常完成及失败轨迹、逐次messages、参数、HTTP尝试、可用原始响应、请求哈希、Editor diff与实现映射位于`recovery_04/rounds/r5/`。新网络失败的原始调用边界和费用在各trajectory，汇总于`analysis/recovery_04_failure_summary.json`；阶段检查点保留，不重复执行成功Fusion或Editor。旧网络恢复审计仍在recovery_03，复用轨迹带有来源关系，不把其缓存前缀计为新增调用。

## 成本与稳定性

|口径|本次新增|累计全部运行（含失败）|
|---|---:|---:|
|Actor逻辑请求|189|2280|
|语义请求|2|27|
|HTTP尝试|191|2307|
|输入Token|407305|3407421|
|输出Token|75805|3434335|
|其中推理Token|58715|3197152|
|总Token|483110|6841756|
|未知usage请求|3|4|

本次新派发9个环境，其中6条完整、3条不完整；累计111条完整slot、115个物理实例。105条旧完整episode和22个成功语义阶段未重新调用。累计执行墙钟约7914.325秒（131分54秒），不含授权等待间隔，不能将并发episode耗时相加作为墙钟。

按先前核对的[官方人民币非峰值单价](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)，本次已报告usage约0.5290元，累计16.4148元，约16.41元，另有4笔未知费用；这不是账户账单。累计输入命中744832、未命中2662589；推理包含在输出内。原R5 Fusion截断、原网络错误及本次新传输错误均保留，不因恢复成功删除失败成本。去重计算见`analysis/recovery_04_cost_estimate.json`，总体结果见`analysis/recovery_04_final_results.json`。

## 事后核验与结论边界

既有验证器返回artifact_valid=true、campaign_complete=false、published_rounds=4、incomplete_rounds=1、semantic_call_records=24；实际累计语义请求27包括所有历史失败，口径不同。控制器确认all_prior_archives_unchanged=true。这些验证证明保存档案和确定性继承关系有效，不证明自然语言行为解释正确。

本次直接证明原R5 Fusion可以在同请求、同预算的一次明确授权恢复中合法完成，并在Keep理由中消费两条历史Effect；部分温度任务改善与一项多实例任务退化也被真实记录。五轮尚未完整完成，无法报告最终Gate或Skill接受，不能声称持续Skill进化已成功或预条件化优于无Memory。

后续独立Test及等预算消融仍应重点核查历史Memory实际作用、共享输入与独立执行身份、触发机会、联合修改归因与错误Effect修订；本次不追加消融、Test或语义探针。

# V22 R5 Candidate三个网络故障归档与恢复

> 后续用户授权当前Memory容量例外后，已完整发布5/5轮，见[最终报告](ALFWORLD_57_FIVE_ROUND_RECOVERY_06.md)。以下保留原容量停止与恢复历史。

2026-10-17，用户授权“归档这些故障，然后重启”。原recovery_04保持完整，新的隔离运行目录为`artifacts/methods/v22/23_alfworld57_five_round/recovery_05/`，控制及档案为同级`recovery_05_control/`。

恢复val:0010第14请求（ProxyError）、val:0013第46请求（ChunkedEncodingError）、val:0017第22请求（ProxyError）。在同一Candidate Skill、游戏、seed42、模型及配置下重放13/45/21步，所有状态和每次messages必须一致。79个原模型决定只缓存复用；各失败请求体哈希一致后才发送，随后继续原50总步数。111条已完成episode、24个成功阶段直接复用，包括R5 Fusion/Editor；正常50步失败不重跑。

新增上限为3个恢复环境、71次Actor逻辑请求和1次65536预算Memory语义调用。额外恢复0，8并发及400000完整消息字符/1M上下文规则不变。累计完整slot最多114，物理实例最多118（原中断实例保留），语义请求最多28。旧故障未知费用继续保留，新增计费排除缓存前缀与所有导入材料。

本次已真实恢复并结算；三个网络中断全部续跑完成。R5 Gate为ACCEPT，但Memory完整输入414275字符超过冻结400000限制，在发送API前停止，尚未共同发布R5 Skill/Memory。没有修改算法、Prompt、Gate、任务、模型输出或历史Memory。

## 冻结、预检与实际恢复

5项离线恢复检查通过（49.269秒）：三个旧部分episode不能当任务失败；三个前缀均逐步匹配且只重发同一失败请求；状态漂移时0次新HTTP；总50步不变且新增Actor请求最多71；整条恢复链复用111条完整episode、24阶段、四轮发布state，缓存usage不重复计费。夹具全部为模拟HTTP和环境，不是Pilot。

此次runtime冻结摘要为`52bbb47262971653d46e5bc5bb8ca5d6c43a9acff6d1387cac297116fc213e7c`。实际源码及所有继承源码、模型路由、v6/P1/统一引用、Prompt、Schema、验证器、57项分组顺序和seed均与原冻结相同；各恢复runtime摘要含目录等元数据，不用摘要差异推断算法变更。具体控制器、协议、预算和原档案哈希清单在`recovery_05_control/authority.json`及`prior_archive_manifest.json`。

北京时间2026-10-17 01:19:09.293启动，01:21:36.519停止，墙钟147.226秒。三项恢复均实际验证初始状态和每个原动作后的反馈、奖励、done/won、下一步合法动作及完整模型messages；原79次模型决定无新增API调用。三个恢复请求完整body哈希与原失败请求一致：

|任务|前缀复用|首个新增请求|请求体SHA256|恢复后结果|
|---|---:|---:|---|---|
|val:0010|13步|14|67894e15dd8398181b0247a768f4176d25265bff465205336089bc45bbe82f91|成功，39步|
|val:0013|45步|46|ca4a3b08fb2137838747460dc5e7cdeca31fa2798a768a6cdff9bdbf3009cf35|正常50步失败|
|val:0017|21步|22|6a398974adfc920b035a5c4305c78b4d770359b2f663dd1a5f9cbfe1e53554ee|成功，43步|

每项的状态恢复审计保存在`recovery_05/rounds/r5/candidate_runs/<task>/restoration_audit.json`，汇总为`analysis/recovery_05_request_identity.json`。所有完整任务，包括val:0016原50步失败，均按原结果复用，未重新采样。

## 五轮配对结果与Gate

|轮次|Parent成功率|Candidate成功率|Parent→Candidate执行步数|Gate|共同发布|
|---|---|---|---|---|---|
|R1|12/12，100%|12/12，100%|171→83|RETAIN|完成|
|R2|10/12，83.33%|7/12，58.33%|208→320|RETAIN|完成|
|R3|8/12，66.67%|7/12，58.33%|328→311|RETAIN|完成|
|R4|9/12，75%|9/12，75%|223→207|RETAIN|完成|
|R5|6/9，66.67%|7/9，77.78%|239→239|ACCEPT|Memory容量失败，未发布|

R5逐任务Candidate：val:0009成功6步、0010成功39步、0011成功22步、0012成功14步、0013失败50步、0014成功8步、0015成功7步、0016失败50步、0017成功43步。实际修复Parent失败的0014/0015，退化Parent成功的0016，其余胜负不变。Gate原始依据为`success_rate_increased`、parent=6、candidate=7，严格同批比较没有改动。

57个唯一任务的114条完整Parent/Candidate episode均已得到实际结果，总执行动作2329；全池描述性合计Parent45/57、Candidate42/57。各轮任务和Skill不同、没有无Memory对照，不能用总数推断预条件化因果收益，也不能把R5的局部改进外推为整体方法优势。

## 新停止点：Memory完整输入容量

当前准确停点为R5 `post_gate_learning`，错误：`Evolution input exceeds the frozen character budget.`。完整messages已保存到`recovery_05/rounds/r5/messages/post_gate_learning.json`，按照运行器实际采用的`json.dumps(messages, ensure_ascii=False, separators=(",", ":"))`测量为**414275 Unicode字符**、414327 UTF-8字节，超出冻结400000字符上限14275（3.56875%）。

运行器先做字符检查，因此尚未执行该请求的后续上下文admission、未建立Memory调用记录、未发送API请求、未产生本轮Memory响应或费用。没有该阶段容量audit文件，不能把它描述为上下文预算也已经检查通过；完整测量和阻碍汇总在`analysis/recovery_05_capacity_failure.json`。

这是固定输入的确定性工程容量阻碍，同配置再次重启仍会被拒绝。未自动删历史依据、切断配对、截断消息、修改P1、放宽预算、改变Prompt或降低证据量。候选已通过Gate，但既有机制要求有效Skill/Memory共同发布；所以R5没有`state.json`，Candidate没有正式继承，不能单独应用未生成/未通过契约的Memory或将旧Memory冒充本轮学习结果。

保存的`gate.json`、`learning_input.json`、`learning_freeze.json`、完整Memory输入、有效Update、实际diff和全部配对轨迹构成停止检查点。前三个网络故障已归档并恢复成功；目前没有残留不完整episode或新的网络错误。

## Skill、Memory继承与历史D/S/C依据

R1至R5的Parent与memory_before逐轮匹配上一正式state；四轮发布state与recovery_04逐字一致。当前最新正式状态仍是`recovery_05/rounds/r4/state.json`：No Skill＋2条Effect，分别是温度/搜索关系`475639db59e4b82bd457eeb139b6b6d4542275f903bb5a54bc17581963a635f1:m1`和台灯/对象关系`1955e42f936335ef0a4007b6682625edc6552d48093495657cf43e54fea91a0e:m1`。所有57项实际接触记录另外由轨迹及各轮输入保留，不因state只发布至48项而抹去R5接触。

R5 Candidate为`sha256:64540f210210664e8c5ec48e11adb40f1e224b431df4d8b50357d9ef02ca654e`，可在candidate.json、SKILL.md和Editor diff审阅，但本轮尚未完成正式继承。真实Gate ACCEPT已被观测到，ACCEPT后的原子发布/下一轮Skill继承没有在本次完成，不能混用离线测试来宣称已完成。

Fusion与Editor全部复用，不再调用。R1空Memory Keep；R2两次replace的basis明确引用旧Effect，约束全局访问状态到近期上下文并迁移四个Watch；R3两次replace主要依据当前事件；R4一次台灯顺序replace，reason消费历史适用范围；R5 Keep四条原始要求，仅新增预算Watch w5，其reason明确认为温度Effect适用、台灯Effect不适用。requirements_changed=false或history_cited=[]只概括结构化changes，不能掩盖reason中的历史消费。完整原始/最终Update、Goal、Watch、basis、Editor实现映射均保留。

这些是历史Effect进入实际决策理由的证据，不能证明历史导致Candidate胜率提高。R5温度循环改善有轨迹支持，但与搜索、放置及两实例规则共同改变，一次采样不能独立归因。R5没有Replay/Memory响应，因而没有新增或修订Effect；旧R1事实概括、R2–R4共享P1内容被误认为非独立执行、R3搜索触发机会等语义错误保持原样，程序契约通过不证明它们正确。

## 用量、失败与资源结算

|口径|本次新增|全实验累计（含所有历史失败）|
|---|---:|---:|
|Actor逻辑请求|53|2333|
|语义请求|0|27|
|HTTP尝试|53|2360|
|输入Token|53656|3461077|
|输出Token|26704|3461039|
|其中推理Token|21874|3219026|
|总Token|80360|6922116|
|未知usage请求|0|4|

新增53次Actor请求为val:0010的26次、val:0013的5次、val:0017的22次，少于71上限。111条完整旧episode、24个阶段及79次缓存前缀决定没有新增计费。累计114条完整评估slot、118个物理环境实例，额外4个原中断实例作为真实失败保留；这不增加训练任务或额外独立候选。

全部执行段墙钟相加约8061.551秒（134分21.551秒），不含等待授权的间隔。按先前核对的[官方非峰值人民币单价](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)，本次已报告usage估算0.1398元，全实验16.5546元，约16.55元，另有4笔未知费用；未查询账户账单。累计输入命中765947、未命中2695130 Token，推理已包含在输出。费用去重和逐段计算见`analysis/recovery_05_cost_estimate.json`。

旧Editor契约失败、Fusion非法JSON、Fusion截断及四次网络未知费用均保持原始记录。新的Memory容量拒绝发生在HTTP前，没有失败API消费，不能虚构一个Memory调用或把原未知网络费用抹为零。

## 核验与研究结论边界

既有事后验证器返回artifact_valid=true、campaign_complete=false、published_rounds=4、incomplete_rounds=1、semantic_call_records=24；累计实际语义请求27含历史失败，统计口径不同。控制器确认all_prior_archives_unchanged=true。全部请求身份、配对条件、旧发布状态及累计用量对账通过；总体机器可读结果为`analysis/recovery_05_final_results.json`。

已验证真实事实：五轮同批Parent/Candidate执行完成；R5出现首个严格胜率提高并产生ACCEPT；历史Memory在Fusion理由中被消费；完整Memory随历史证据增长撞上既有工程容量边界。正式五轮持续自进化流程仍未完成，当前只能报告4轮共同发布与R5待Memory检查点。

后续独立Test应保持本次57项开发池之外；Selection不能再用作独立选择集。等预算消融应检验历史Effect消费与无Memory对照、一次采样波动、联合修改归因、P1共享表示的身份误解以及错误归因能否后续修订。容量增长是另一个已观察到的可执行性限制；本次不通过静默修改冻结规则回避它，也不追加探针或Test。

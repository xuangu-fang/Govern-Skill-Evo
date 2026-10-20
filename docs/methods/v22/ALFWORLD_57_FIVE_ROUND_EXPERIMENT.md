# V22 ALFWorld 57项五轮正式持续自进化实验

**五轮全部执行并共同发布完成。** 最终R5为Parent 6/9、Candidate 7/9，Gate ACCEPT，正式采用Candidate Skill，最终Memory为3条Effect。完成时间为2026-10-17 01:35:25，Asia/Shanghai。该完成包含用户明确授权的R5 Memory容量例外；原400000字符限制曾真实阻断，后仅对同一完整输入豁免，历史记录没有改写。

正式最终档案：`artifacts/methods/v22/23_alfworld57_five_round/recovery_06/`；最终state为`rounds/r5/state.json`，SHA256 `af5fc79cf3bb50301d521d89996f9e170fd4eefb23d59be889ac52c0f569f1a6`。完整恢复及容量修订详见[最终恢复报告](ALFWORLD_57_FIVE_ROUND_RECOVERY_06.md)。

## 1. 实际冻结设置与任务

算法Profile `v22.unified_dsc.v6`，输入 `v22.p1_shared_input.v1`，引用 `v22.typed_references.v1`，正式运行协议 `v22.alfworld57_five_round.v1`。Actor和五个语义阶段均使用官方`https://api.deepseek.com`的`deepseek-flash`，沿既有路由，核对实际endpoint和response_model，无v3/v4静默回退。

初始No Skill、空Memory，没有重建Stage0。使用适配器`skillopt_39_18_134`真实Manifest的Train39＋Selection18（原native split为val），显式development用途。57项原身份、gamefile哈希、原顺序和接触记录绑定于`experiments/methods/v22/23_alfworld57_five_round/config/{plan,task_manifest,prior_contact_inventory}.json`。不凭名称拼接、不替换、不重复、不因结果调整顺序。

|轮次|固定任务数|ID缩写（唯一身份以Manifest为准）|
|---|---:|---|
|R1|12|train:0000–0011|
|R2|12|train:0012–0023|
|R3|12|train:0024–0035|
|R4|12|train:0036–0038、val:0000–0008|
|R5|9|val:0009–0017|

环境seed42，分类alias seed200，无任务打乱，无额外API seed。每episode最多50步、8个Actor worker、相同游戏和可比环境下Parent/Candidate配对。Actor仅最近两对pre-action观察/动作，无隐藏状态扩展。初始及所有轮次继承以正式state为准，上一轮有效Skill/Memory共同发布后才进入下一轮。

模型参数temperature1、thinking enabled、reasoning_effort medium、streamfalse；Actor输出16384、读取超时300秒；classification/Diagnosis/Fusion/Editor输出32768，Memory65536，语义读取超时600秒。保留既有最多6次有界同请求HTTP状态尝试；无自动网络异常、语义或episode重跑。历史实测08 R2为474步/20 episode，原估计约2702步，未承诺固定成本；本次最终完整episode实际2329动作，失败请求另计。

原revision隔离继承22/21，正式原runtime SHA256 `9a6b7fe69d0fd553312210df8e1d399e0e201bbd5c28587ed2108aa95a2de3f9`。最终容量revision在`capacity_amendment/revision/`，runtime SHA256 `af95dfca65f1181972a124d0c488121dd832c09ee95f5ad49c2d4927ac0a7817`，140份源码及11个绑定文件；全部原132份源码仍以原字节纳入快照，新增仅为容量admission、验证、命名空间和快照登记。Prompt、Schema、验证语义、P1编码及模型参数不变，源码差异明确归档。

此前至少43项有归档开发episode，原清单与其他已知接触声明均保留，不能称其余项绝对未接触。旧Skill/Memory及轨迹不进入本次学习输入。Selection已经属于训练开发池；独立Test从未参与更新、机制选择或任务替换。

## 2. Preflight、技术恢复与容量修订

首次正式请求前集中Preflight通过：421项V22回归、35项Adapter、14项引用专项和3项五轮合成检查。核对57项真实游戏文件、ID/顺序/分组、实际加载源码、模型/Prompt哈希、版本契约、ACCEPT/RETAIN、Memory更新、发布身份、阶段恢复和容量拒绝。离线验证不能冒充真实行为成绩。

所有真实技术停止及授权恢复保留：

|原停止|原问题|后续授权处理|
|---|---|---|
|R1 Editor|第13条实现摘录不匹配Candidate正文|归档后同输入、同参数重跑一次|
|R3 Fusion|非法JSON，finish_reason=stop|归档后同请求重跑一次|
|R4 Parent val:0000第22请求|ChunkedEncodingError|原21步精确恢复，同请求继续，24步成功|
|R5 Fusion|32768输出全部用于推理，finish_reason=length|同请求同预算重跑成功|
|R5 Candidate三项|val:0010第14/val:0017第22 ProxyError；val:0013第46 ChunkedEncodingError|原13/21/45步精确恢复，同请求继续|
|R5 Memory调用前|完整消息414275字符超过400000|用户明确授权该精确输入容量例外，随后一次调用完成|

成功阶段和完整任务从未重新执行以寻求更好结果；所有原始故障、已知usage和未知费用保留。恢复前缀的100次模型决定缓存复用，环境逐步核对初始状态、动作、反馈、reward/done/won、下一步动作列表和完整messages；新请求体哈希与原失败请求一致。正常50步失败没有重跑。

本次容量例外只适用于原R5 Memory完整messages哈希，414275字符、414327 UTF8字节；原plan仍声明400000，独立`recovery_06_control/capacity_amendment.json`授权并冻结例外。未删除历史或截断消息，其他阶段/变更输入不能借用该豁免。1M上下文检查继续执行：414327＋8192 framing＋65536输出=488055保守Token上界，小于1000000；这不是实际分词量。4项最终离线恢复检查通过，实际请求与原检查点完全一致。

## 3. 五轮实际结果

|轮次|Parent成功率|Candidate成功率|Parent→Candidate步数|Gate|Skill/Memory共同发布|
|---|---|---|---|---|---|
|R1|12/12，100%|12/12，100%|171→83|RETAIN|完成|
|R2|10/12，83.33%|7/12，58.33%|208→320|RETAIN|完成|
|R3|8/12，66.67%|7/12，58.33%|328→311|RETAIN|完成|
|R4|9/12，75%|9/12，75%|223→207|RETAIN|完成|
|R5|6/9，66.67%|7/9，77.78%|239→239|ACCEPT|完成|

Gate始终为同批Candidate成功数严格大于Parent才ACCEPT。R1全成功仍照常进入更新、候选和学习；没有重分配任务。R2/R3退化照常RETAIN并从实际编辑—配对响应学习。R5修复val:0014/0015，退化val:0016，其他胜负不变。R2修复train:0023、退化0014/0015/0017/0021；R3修复0033、退化0026/0034；R4无胜负变化。

全部57项的114条完整episode得到结果，动作2329步；描述性合计Parent45/57、Candidate42/57。不同轮任务与候选不同，不能把总数当成最终Skill的独立测试或Memory因果比较。逐任务状态、步数和原始来源位于`analysis/recovery_06_final_results.json`及各轮轨迹。

## 4. Skill与Memory的连续继承

R1–R4的Gate均RETAIN，下一轮正式Parent一直为No Skill；对应Memory照常更新，未把被拒绝Candidate整体当成正确Skill采用。每轮Parent和memory_before逐字匹配上一正式state，四轮发布状态在所有恢复中保持原字节。

|发布轮次|正式Skill|Effect变化|发布后数量|
|---|---|---|---:|
|R1|No Skill|新增6b89f2dc…:m1|1|
|R2|No Skill|替换为466852f4…:m1，并撤销“无失败案例”旧限制|1|
|R3|No Skill|替换为475639db…:m1|1|
|R4|No Skill|保留温度Effect，新增1955e42f…:m1|2|
|R5|Candidate|保留两条，新增3589b292…:m1|3|

最终Skill为`sha256:64540f210210664e8c5ec48e11adb40f1e224b431df4d8b50357d9ef02ca654e`，文本位于`recovery_06/rounds/r5/candidate/SKILL.md`，与正式state一致。最终Memory三条：`475639db59e4b82bd457eeb139b6b6d4542275f903bb5a54bc17581963a635f1:m1`（17 basis/11 limits）、`1955e42f936335ef0a4007b6682625edc6552d48093495657cf43e54fea91a0e:m1`（6/5）、`3589b292fffd5fc63c2794030093acafe25b6ba9c43a09ba6146f59bcfa8e9a2:m1`（7/6）。

R5 Memory有效后才与已ACCEPT Skill共同发布，seen_task_ids为57。真实观测覆盖四次RETAIN继承及一次ACCEPT共同发布；新接受Skill没有后续第六轮执行，不能宣称它在接受后持续使用的效果已被检验。

## 5. Fusion实际D/S/C处理及历史依据

|轮次|实际操作|历史依据如何进入|
|---|---|---|
|R1|Keep全部4要求，无Watch变换|空Memory真实调用，没有历史作用|
|R2|2次replace（u1→u3、u2→u4），4个Watch迁移|basis明确引用R1 Effect；将全局未访问集合约束收窄到最近两对上下文|
|R3|2次replace（u2、u5），2个Watch迁移|显式basis为当前事件/组，补充取出appliance中对象再heat/cool、打开闭合容器搜索；不能断言历史直接造成变化|
|R4|1次replace（u1→u5），1个Watch迁移|reason明确判定旧温度Effect适用范围，不据此改其他对象关系；台灯策略允许两种观察到的顺序|
|R5|Keep四条Requirement，新增预算Watch w5|reason明确判定温度Effect适用、台灯Effect不适用，要求无需再改|

v6统一D/S/C用已有from/to/replace/Keep表达，没有额外新增研究字段。history_cited摘要只看结构化changes.basis；R4/R5为空不能掩盖reason中的历史引用。原始Update、最终Plan、Goal、Watch、changes/basis、Editor diff及实现映射全部保留，不能只据摘要重建模型决策。

历史Effect实际进入了后续修改或Keep理由，这是可核对的消费证据；是否改善决策质量需要对照消融，不能由本次链条独立推断。

## 6. Memory认识、事实与错误归因

有直接轨迹支持的现象包括：R1同为全胜但Candidate少88步；R4 val:0000从Parent24步台灯循环变为Candidate3步完成；R5 val:0014/0015从Parent将番茄放进microwave后循环至50步失败，变为Candidate直接对手持目标heat并在8/7步完成。R5 val:0016搜索未覆盖Parent找到书的bed，导致退化；其他成功任务存在搜索开销和不合法命令。不同目标实例/位置选择、联合Skill修改和一次采样差异均限制归因。

Memory曾修订真实边界：R2撤销“尚无失败案例”限制；R5更清楚地区分u2搜索有机会但覆盖失败、u4在未取第一本书时没有后续放置机会。R5生成7 Findings、5 open，新增Effect，未替换或撤销旧Effect/limits。

同时，语义偏差贯穿实验并保持原样：

- R1把countertop取物概括成打开countertop等事实偏差。
- R2–R5把P1共享步骤内容误解为执行不独立；实际两侧有不同run ID、Skill、请求哈希和原始响应。R5 f2/open/新Effect limits[1]仍错误排除val:0009清洁分支的独立Candidate响应。
- R3把未找到目标过度概括为搜索等要求无触发机会；相关旧限制没有自动被R5更具体的判断撤销。
- R4/R5 Effect自由文本曾把Parent run ID写成Candidate标识；正式Skill身份以绑定SHA256及配对档案为准。

这些是只读研究审计发现，未回写或修补模型输出。相应证据在`analysis/recovery_01_p1_identity_audit.json`、`recovery_02_semantic_identity_audit.json`、`recovery_03_semantic_identity_audit.json`、`recovery_06_semantic_identity_audit.json`。程序引用/输出契约通过不证明自然语言事实或归因正确；Gate也不是Effect质量标签。

## 7. Token、耗时、失败调用及费用

|项目|全实验累计，去重复用并含历史失败|
|---|---:|
|完整Parent/Candidate episode|114|
|实际物理环境实例（含4个旧中断实例）|118|
|Actor逻辑请求|2333|
|语义逻辑请求|28（25成功阶段＋3历史失败）|
|HTTP尝试|2361|
|输入Token|3592263|
|输出Token|3482971|
|其中推理Token|3237840|
|总Token|7075234|
|输入缓存命中/未命中|767611 / 2824652|
|usage未知请求|4|

推理属于输出子集，不重复计费或加总。恢复复制的114条episode、24个阶段及100个前缀决定不重复计为新增模型消费。最后一次容量恢复仅新增1次Memory请求：131186输入、21932输出、18814推理，HTTP111.887秒，无新失败；未增加Actor调用。

七段实际执行墙钟相加8216.888秒，约136分56.888秒，不含授权等待及离线准备。首次启动2026-10-16 18:22:10，最后核验完成2026-10-17 01:35:25；中间等待间隔不是模型执行耗时，并发episode耗时不能直接相加为墙钟。

按此前核对的[DeepSeek官方人民币非峰值价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)与各请求时间，已报告usage估算**16.7719元，约16.77元**，另有4笔旧网络失败费用未知；最后Memory约0.2173元。此为usage×单价估算，未查询账户账单。原网络失败没有完整响应或usage，不伪造缺失数据，也不视为零消费。逐段费用与来源见`analysis/recovery_06_cost_estimate.json`。

## 8. 事后验证与本次能说明什么

在冻结的容量修订revision下，既有验证器返回artifact_valid=true、campaign_complete=true、published_rounds=5、incomplete_rounds=0、semantic_call_records=25。累计28次语义请求包含历史失败，与25个最终有效阶段记录口径不同。all_prior_archives_unchanged=true。最终state、Gate、Memory receipt、Skill哈希、配对条件和五轮继承一致。

数据支持：固定任务及机制下链条可持续运行五轮，Memory可连续继承、修订并被Fusion消费；有局部效率改善、两轮整批退化，最后一轮严格提高成功数并完成Skill采用。R5完整历史输入也真实触及工程容量上限，需要经用户明确授权的单输入例外才完成。

数据不支持：程序契约通过即行为解释正确；全部候选都改善；新Skill已在独立Test泛化；Memory预条件化优于无Memory；某一条要求或历史Effect独立造成改进。最终候选没有接受后的独立任务执行，全部57项已用于开发优化。

## 9. 后续消融与独立Test重点

后续应在可比任务顺序、初始状态、预算和随机性条件下比较无Memory、历史Effect消费及D/S/C处理；重点检验共享表示与执行身份误解、行为触发机会、错误Effect保留/撤销、联合修改的归因和多次采样方差。独立Test必须排除本次优化所用Train/Selection，不能重新将Selection当独立模型选择集。

还应检验完整历史增长后的容量和成本，以及已接受Skill在新任务上的继承效果；本次未追加任何消融、独立Pilot、旧历史探针、评审Agent或Test。

最终详细恢复与授权：[RECOVERY_06](ALFWORLD_57_FIVE_ROUND_RECOVERY_06.md)。此前各次停止及恢复按[01](ALFWORLD_57_FIVE_ROUND_RECOVERY_01.md)、[02](ALFWORLD_57_FIVE_ROUND_RECOVERY_02.md)、[03](ALFWORLD_57_FIVE_ROUND_RECOVERY_03.md)、[04](ALFWORLD_57_FIVE_ROUND_RECOVERY_04.md)、[05](ALFWORLD_57_FIVE_ROUND_RECOVERY_05.md)保留；最初Preflight及首次失败详细档案另存[历史文档](ALFWORLD_57_FIVE_ROUND_PRE_COMPLETION_HISTORY.md)。

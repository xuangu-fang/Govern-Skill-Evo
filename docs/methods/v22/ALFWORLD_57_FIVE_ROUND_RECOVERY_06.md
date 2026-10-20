# V22 R5 Memory容量修订与五轮最终结算

2026-10-17，用户明确授权“暂时无视超过冻结的400000上限，使其5轮全部完成”。此次只豁免原recovery_05完整R5 Memory输入的400000字符工程限制，精确绑定414275字符的messages哈希；其他阶段、输入、模型上下文预算、输出参数、算法与学习规则保持。

修订控制与授权：`artifacts/methods/v22/23_alfworld57_five_round/recovery_06_control/`；新的运行档案：同级`recovery_06/`；独立源码覆盖：`experiments/methods/v22/23_alfworld57_five_round/capacity_amendment/revision/`。原源码与所有旧失败档案保持原字节。

原plan仍声明400000，额外例外由`capacity_amendment.json`单独绑定并冻结。运行器admission、dispatcher、容量审计与事后验证器一致识别该精确输入；1M上下文检查保持，完整消息UTF8字节414327＋framing8192＋输出65536=488055保守Token上界。它不是实际分词或计费用量。

4项离线恢复检查通过（48.490秒）：精确输入获授权且上下文可容纳；其他阶段/变更输入无法借用豁免；上下文溢出仍拒绝；114完整episode、24成功语义阶段、四轮发布state及R5 Gate ACCEPT原样复用，Memory完整messages逐字一致，Actor无新增调用。

仅新增一次R5 Memory实际请求，官方deepseek-flash、65536输出、temperature1、thinking enabled medium、streamfalse、600秒超时不变。新增Actor/环境为0；任何新技术失败仍保存并停止，额外自动恢复为0。合法Memory按既有契约验证后才共同发布R5 Candidate Skill与Memory。

实际已执行完成：2026-10-17 01:35:25（Asia/Shanghai）五轮全部共同发布，最终Skill为R5 Candidate，Memory为3条Effect。最终总报告见[ALFWORLD_57_FIVE_ROUND_EXPERIMENT.md](ALFWORLD_57_FIVE_ROUND_EXPERIMENT.md)。

## 最终执行与发布

此次执行01:32:49.179启动、01:35:24.517结束，墙钟155.338秒；控制器完成核验于01:35:25.766。Memory实际请求01:33:32.442发出，01:35:24.341完整返回，HTTP耗时111.887秒、HTTP 200、finish_reason=stop。输入131186 Token，输出21932，其中推理18814；无本次新失败或重试。

新增0个环境、0次Actor调用，复用114条完整episode和24个成功语义阶段。Memory实际messages与原recovery_05检查点完全一致，实际参数仍为deepseek-flash、temperature1、65536输出、thinking enabled medium、streamfalse。最终容量audit明确capacity_exception_applied=true、character_limit=414275；上下文上界422519＋输出65536=488055，低于1000000。原plan未改。

新runtime冻结摘要`af95dfca65f1181972a124d0c488121dd832c09ee95f5ad49c2d4927ac0a7817`，140份源码和11个绑定文件，含全部原132份源码原字节、新容量overlay和独立授权。新旧源码差异保存在`analysis/recovery_06_capacity_source.diff`；输入、参数及容量核查在`analysis/recovery_06_capacity_admission.json`。

|轮次|Parent|Candidate|Gate|发布|
|---|---|---|---|---|
|R1|12/12，171步|12/12，83步|RETAIN|完成|
|R2|10/12，208步|7/12，320步|RETAIN|完成|
|R3|8/12，328步|7/12，311步|RETAIN|完成|
|R4|9/12，223步|9/12，207步|RETAIN|完成|
|R5|6/9，239步|7/9，239步|ACCEPT|完成|

最终state：`recovery_06/rounds/r5/state.json`，state SHA256 `af5fc79cf3bb50301d521d89996f9e170fd4eefb23d59be889ac52c0f569f1a6`，seen_task_ids为57项。正式Skill为`sha256:64540f210210664e8c5ec48e11adb40f1e224b431df4d8b50357d9ef02ca654e`，文本在该轮`candidate/SKILL.md`，与正式state完全一致。Memory共同发布后才标记第五轮完成，未提前单独继承Skill。

## Memory的真实学习与解释偏差

R5返回7条Findings、5个open，新建Effect `3589b292fffd5fc63c2794030093acafe25b6ba9c43a09ba6146f59bcfa8e9a2:m1`（7 basis、6 limits），无replace、无retire_limits，原温度和台灯两条Effect保持，总数3。memory_before SHA256 `3ae471d48706c17f1d2203cd81eeee2073416ee52b3583bf4d6e4a8c09f93953`，after `1c780b34c7ee6cb50713505c4e1bc200b04fe775249616dc1f5ea9ddd67589bb`；receipt绑定真实Gate、learning payload和raw output。

有直接执行依据的认识：val:0014/0015 Candidate直接对手持番茄执行heat，分别8/7步完成，Parent将番茄放入microwave后循环至50步失败；val:0016 Candidate搜索未覆盖Parent找到两本书的bed，导致正常失败；val:0017完成两张creditcard放置但43步高于Parent28步。新Memory明确区分“未取得第一本书时u4后续放置无机会”和“u2搜索仍有机会但覆盖不足”，比历史把未找到目标泛化成所有规则无机会更具体，但没有显式撤销旧错误limits。

新错误／保留偏差：f2、open和新Effect limits[1]仍将val:0009的P1/C1共享步骤内容解释为无独立执行；实际两侧run ID、Skill和HTTP请求不同。新Effect的自由文本candidate标识写成`skill_20261016T161429783510Z_3d570734`，只读核对它实际属于val:0009 Parent，真实Candidate Skill以上述SHA256为准。原输出、Memory claim和limits均未人工修补；证据在`analysis/recovery_06_semantic_identity_audit.json`。

联合修改、目标实例/位置选择和一次采样差异仍未隔离。Memory契约通过不等于解释完全正确；R5 Gate ACCEPT和局部改善也不能证明Memory预条件化优于无Memory。

## 最终费用与核验

此次仅新增1次语义/HTTP请求，输入131186、输出21932、推理18814，总153118 Token；已报告usage估算约0.2173元。累计2361次HTTP（Actor2333、语义28），输入3592263、输出3482971、推理3237840、总7075234 Token。推理是输出子集，不重复相加。已知缓存命中767611、未命中2824652。

按此前核对的[官方人民币非峰值价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)，全实验已报告usage约16.7719元，即16.77元，另加4笔未知网络失败费用；不是账户账单。缓存114个episode、24个阶段和此前100个恢复前缀决定没有新增计费。累计114条完整slot、118个物理实例，全部执行段墙钟8216.888秒（136分56.888秒），不含授权等待与离线准备。

既有验证器在本次隔离容量revision下返回artifact_valid=true、campaign_complete=true、published_rounds=5、incomplete_rounds=0、semantic_call_records=25；实际累计28次语义请求含3次历史失败。all_prior_archives_unchanged=true。scheduling.amended=false只描述并发调度未修改，不表示没有本次明确记录的容量修订。

此次完整完成是在用户明确授权的当前Memory容量例外下实现，不能写成原400000限制始终满足。修订没有改变学习机制、消息内容或模型参数。最终结果、费用和核验分别为`analysis/recovery_06_final_results.json`、`analysis/recovery_06_cost_estimate.json`、`recovery_06_control/verification.json`。

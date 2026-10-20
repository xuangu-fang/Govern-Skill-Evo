# V22 P1 无损共享输入实现与验证

2026-10-16。实现身份：`v22.unified_dsc.v4`；消费编码：`v22.p1_shared_input.v1`。算法基线为独立 v3 revision。

**结论：P1 已正式接入五个语义阶段，程序保真、来源链和历史兼容检查通过；真实模型可理解性及实际 Token 收益尚未验证。** 本次按用户新路由准则向官方端点发送了 8 个冻结请求，全部因指定模型名 `deepseek-v4.1-flash` 被服务端拒绝而返回 HTTP 400，没有生成模型内容。不能将此归为 P1 理解失败，也不能声称语义验证通过。没有追加请求、ALFWorld episode 或正式 Skill／Memory 发布。

指定五轮压力情境中，P1 显著减少重复输入，但持续变化的 50 步轨迹仍有学习输入超过 400,000 字符。因此当前只具备继续做有限输入表示验证的程序基础，**尚不具备直接启动 57 项五轮实验的完整条件**。

## 1. 实现范围与版本隔离

实现位于 [17_p1_input/revision](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision)，基于 `12_contract_alignment/revision` 独立复制。旧 v3、08—16 实验材料、既有冻结 Prompt、Skill 和 Memory 均未覆盖。`benchmarks` 通过链接保留原路径身份，未重新定义 Actor 或任务。

|代码|实际作用|
|---|---|
|[p1_input.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/p1_input.py)|复用 16 的 P1 原型，提供版本化 `encode`、`decode`、`encode_messages`，每次装配验证精确还原；附模型解码说明。|
|[grouped_representation.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/grouped_representation.py:102)|分类在原有消费视图形成后使用同一 P1 编码器。|
|[grouped_update.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/grouped_update.py:33)|Diagnosis、Fusion、Editor、Replay／Memory 同样在原消息构造末端编码；v4 继承 v3 行为和来源契约。|
|[effective_memory.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/effective_memory.py)|将 v4 纳入已有稳定历史引用路径；完整 Effect、limits、basis、historical_updates 继续传递。内层原有消费语义不改为新历史筛选规则。|
|[continual_runtime.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/continual_runtime.py:282)|显式绑定新 profile、实际 System 和 `contracts.model_input_encoding`。|
|[continual_runner.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/continual_runner.py:205)、[continual_verify.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/continual_verify.py:128)|分类实际发送与事后重建使用同一消息路径；编译、Gate、Memory 应用及输出验证仍使用原事实。|

没有迁移 P2 Editor 有损视图，没有历史卡片替代、相关性筛选、总结调用、证据裁剪或新输出字段。原始 Update → 历史响应 → D/S/C 变换 → 实际编辑 → 行为反馈 → Memory 修订的行为规则保持 v3。profile 身份及由此生成的绑定哈希会变化；这属于版本隔离，不能要求新旧绑定字符串相同。

## 2. 编码保留什么

P1 的无损基准是**原 v3 实际发送给模型的消费视图**；不是把原装配本就不发送的所有档案字段额外加入模型。完整原档案另外保留。

- `command_pool` 共享重复命令字符串；各步骤仍通过自己的 commands ID 取得完整动作前菜单，顺序及重复项不变。只在 command_sets 中将整数解释为命令池索引。
- `text_pool` 和 `@concat` 共享完全相同的文本及可逐字拼接的观察片段，保留空格、标点、换行、拼接次序和独特文本。没有生成摘要。
- `object_pool` 共享重复对象；`@table` 仅合并 steps 的字段名，逐行保存全部值和顺序。`@missing` 与显式 null、false、0 分开。
- 仅当原 event sources 与全部实际 run／step 的确定性目录**完全一致**时，使用隐式事件来源规则；不完整或不相同目录保持显式。Parent、Candidate 和历史命名空间不合并。
- 历史反例、未验证限制、实际更新和累计 basis 仍完整存在，只减少重复展开。共享同一文本不表示共享同一次执行或增加一条试验。
- 原 JSON 如恰好包含保留标记键，使用 `literal:true` 原文回退，不把合法内容误当编码、不阻断更新。回退仍可能超工程容量，不能用裁剪隐藏。损坏的表格行长度报错，避免 `zip` 静默丢值。

模型可见说明约 1.5 千字符，涵盖零基索引、拼接、缺失字段、来源恢复以及“输出原事件／requirement／Watch／Effect ID，不能输出池索引”。说明只解释表示方式，不更改 D/S/C 选择。模型是否能可靠执行这些解码关系，仍须真实输出检验；程序可解码不等于模型理解。

## 3. 离线正确性、来源与历史兼容

|检查|结果及证据|
|---|---|
|完整 V22 回归|414 项通过，82.950 秒：[日志](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/offline/v22_regression_final.log)。|
|相关 Adapter 回归|35 项通过，0.274 秒：[日志](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/offline/adapter_regression.log)。没有执行真实环境。|
|P1 编解码专项|11 项通过，包含在 414 项内，不重复相加：[test_p1_input.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/tests/skill_evolution/v22/test_p1_input.py)。|
|profile／五阶段集成|6 项专项覆盖全部阶段及两轮合成流水线，包含在上述回归内：[test_p1_profile_integration.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/tests/skill_evolution/v22/test_p1_profile_integration.py)。|
|真实冻结夹具|5 项来源及构造检查：[test_fixtures.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/validation/test_fixtures.py)。|
|一次请求控制器|2 项假 HTTP 测试，确认不修复内容、不重复请求、保留失败用量；另 2 项端点映射／冻结后变更检查通过：[控制器日志](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/offline/controller_tests.log)、[路由日志](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/offline/route_controller_tests.log)。均非真实模型调用。|
|旧消息兼容|19/19 按原 profile 完全重建：08 九份、09 七份、15 三份：[兼容记录](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/analysis/old_messages_compatibility.json)。|
|历史文件保护|执行前后核验基线中 4,906 个既有文件哈希一致；包括旧实验及旧 revision。保护范围以 [baseline.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/baseline.json) 为准。|

保真测试覆盖完整步骤及顺序、动作前菜单、前后观察、结果／状态、P/C 独立身份、分组及来源、Skill diff、Update、Watch、Effect、limits、basis、历史更新上下文。五阶段输入的 `decode(encode(view)) == view`；对照的行为 System 除版本声明和 P1 解码说明外相同。合成集成验证了事件来源、要求替换、Editor 映射、Findings 和历史来源身份的程序路由，没有新增保守拦截条件。

上述检查证明指定输入的程序保真和契约接通，不能证明自然语言 D/S/C 判断或真实行为学习正确。

## 4. 五阶段正式输入规模

使用同一 08 R2 真实事实，在正式 v3／v4 消费路径下比较。计量为 `json.dumps(messages, ensure_ascii=False, separators=(',', ':'))` 字符数，包含 System、转义和新解码说明；不是 Token，也不是原 08 当时发送的消息大小。

|阶段|v3 字符|v4 P1 字符|减少|
|---|---:|---:|---:|
|全局分类|131,044|62,623|52.21%|
|Diagnosis|172,518|81,555|52.73%|
|Fusion|220,383|124,196|43.65%|
|Editor|217,459|121,272|44.23%|
|Replay／Memory|369,386|184,506|50.05%|

来源：[正式容量结果](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/offline/capacity_results.json)，[可复现脚本](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/offline/capacity.py)。原型 183,767 不能冒充正式结果；正式编码加入了精确解码说明和兼容边界处理。

实际请求的合法学习夹具为 **369,373 → 184,493** 字符，两侧各少 13 字符：容量模板的 Watch 元数据与正式生产构造夹具略有差别。本次调用严格采用后者，不以相邻材料替代实际消息。Editor 仍读取完整 P1，表中节省没有采用 P2。

## 5. 冻结的真实验证安排与模型路由变更

八个独立探针全部来自真实、匹配的 08 R2：分类及 Diagnosis 读取十条 Parent；Fusion 读取该轮原始 Plan 和正式 R1 Memory；Editor 使用该轮已归档的有效 Plan；学习使用该轮真实 Editor、实际 Candidate／diff、执行 Plan、20 条配对执行和 R1 Memory。没有把本次新 Editor 与旧 Candidate 轨迹拼接。分类／Diagnosis／Fusion 新输出也不会成为其他探针输入。

[fixtures.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/validation/fixtures.py)、[36 项来源清单](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_validation/source_manifest.json)、每例 `criteria.json` 固定了来源和检验目标：共同决策结构、合法事件引用、历史响应适用性、更新忠实落实、机会／行动／任务结果／未知范围区分。检查标准在请求前冻结，没有根据输出挑案例。

原准备冻结使用内部 Pro 路由，启动时发现 `.env` 已切换至官方端点，在 HTTP 前停止。该次 **0 请求、0 Token**，保留原 [失败日志](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/preparation/process.log) 和冻结材料。

用户随后明确全实验路由准则：内部代理使用 `deepseek-v4-pro`，官方端点使用 `deepseek-v4.1-flash`。本次据此新增 [独立修订](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_validation/amendment.json)，复用已有 `v22.endpoint_evolution.v1` 映射，仅改变请求 model 和授权端点；证据、messages、criteria、参数预算均逐字／逐值比对不变。新冻结覆盖 1,164 个文件，原冻结不改写。

- 路由：`https://api.deepseek.com/chat/completions`，请求模型 `deepseek-v4.1-flash`。
- 两种表示均 temperature=1、thinking enabled、reasoning_effort=medium、stream=false；不额外设置 response_format。
- 分类／Diagnosis／Fusion／Editor：`max_tokens=32768`；两次学习：`65536`。合计 completion 上限 **327,680**，包含推理与可见输出，绝非实际用量。
- 响应超时 600 秒，连接超时 10 秒；至多并行 2；每例 1 次 HTTP，传输与语义重试均为 0；不跟随重定向、不切备用模型。
- 按预先冻结策略，失败原样归档，并继续其余独立探针，不重新采样失败案例。8 个请求在约 3 秒内全部遭拒；不是同一案例重试 8 次。
- 分类和 Editor 以归档／程序检查为参考；Diagnosis、Fusion、学习各有同事实 v3 对照。单次温度 1 对照即使成功，也不能建立编码收益的因果结论。

实际协议、请求、源码哈希和检查标准见 [protocol.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_validation/protocol.json)、[freeze.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_validation/freeze.json)、[独立控制器](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/official_validation/route_control.py)。路由准则见 [EXPERIMENT_MODEL_ROUTING.md](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/EXPERIMENT_MODEL_ROUTING.md)，不自动改变 Actor 或旧冻结恢复脚本。

## 6. 八次请求的实际结果与成本边界

|案例|messages 字符|HTTP|请求耗时（秒）|生成内容／Token usage|语义检查|
|---|---:|---:|---:|---|---|
|classification_p1|62,623|400|0.236|均未返回|未能执行|
|diagnosis_p1|81,555|400|0.262|均未返回|未能执行|
|diagnosis_v3|172,518|400|0.153|均未返回|未能执行|
|fusion_p1|124,196|400|0.642|均未返回|未能执行|
|fusion_v3|220,383|400|0.196|均未返回|未能执行|
|editor_p1|121,272|400|0.640|均未返回|未能执行|
|learning_p1|184,493|400|0.169|均未返回|未能执行|
|learning_v3|369,373|400|0.578|均未返回|未能执行|

全部为 `invalid_request_error`。服务端原文（各有独立 request_id）：

> The supported API model names are deepseek-flash, deepseek-v4-pro, but you passed deepseek-v4.1-flash.

这是本次端点的实际返回，不是已确认 `deepseek-flash` 与指定模型语义等价。没有擅自采用别名或改回 Pro。原始 HTTP body 保存在各案例 `call_responses/step_0001_attempt_01.body`，其哈希与 `call.json` 一致；请求、用时、一次尝试锁、错误和空 usage 均保留。可从 [classification 原始响应](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_validation/cases/classification_p1/call_responses/step_0001_attempt_01.body) 和 [总结果](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_validation/run_summary.json) 逐项核验。

**8 次 HTTP 已使用完本次请求上限，生成的模型结果为 0。** 请求级可用输出为 0/8；模型生成后的 JSON／契约通过率无分母，不能称为模型“8 次 JSON 错误”。`result.json` 的 false 标志表示未取得可验证输出。

服务未返回实际 input、completion、reasoning 或 cache Token，费用也未报告。这些值均为 **未知／不可测**，不能填成 0，更不能用 max_tokens 推算消耗。无法形成真实输入 Token 节省、推理开销、费用或生成耗时对照。本节短耗时只是拒绝请求时间。详见 [独立核验记录](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/analysis/official_run_verification.json)。

未产生可用于判断 P1 新歧义、一般模型语义失误、过度 Keep、策略强化、Editor 映射理解或条件化 Memory 学习的输出。因此对五模块真实语义的答案均为“本次尚无结果”；不得用离线保真替代。

## 7. 五轮离线容量压力结果

正式编码共 205 项比较：5 项真实事实重编码＋200 项明确标注的合成情境（4 种轨迹 × 2 种历史增长 × 5 轮 × 5 阶段）。轮次规模为 12＋12＋12＋12＋9；长轨迹保留 Parent／Candidate 各自全部 50 步。历史分别模拟 Effect 增长、Effect 固定但 basis 累积，并精确保留构造的反例、冲突认识与未知限制。它们不是新的环境证据。

|P1 学习输入：合成情境|R1|R2|R3|R4|R5|
|---|---:|---:|---:|---:|---:|
|重复 50 步、Effect 增长|205,730|240,662|261,648|279,957|279,082|
|重复 50 步、Effect 固定／basis 累积|205,728|240,660|259,235|275,557|273,001|
|持续变化 50 步、Effect 增长|355,654|390,938|411,990|430,301|378,583|
|持续变化 50 步、Effect 固定／basis 累积|355,652|390,936|409,577|425,901|372,502|

固定 Effect 数量为 0/3/3/3/3，basis 为 0/3/6/9/12；增长情境 Effect 与 basis 均为 0/3/6/9/12。固定条目数量不能使历史消费天然有界。

全部 205 项通过精确还原与行为规则相同断言。超过 400,000 字符的案例：v3 **100/205**，P1 **54/205**；后者包含 50 个刻意设置大量唯一动作候选／长观察的 wide50 极端情境，以及 4 个持续变化轨迹的 R3／R4 学习输入。极端 P1 学习输入最高 **4,888,391**，未截断或隐藏。

重复较多的场景最高 279,957，达到约 25% 余量目标；持续变化场景最高 430,301，不能保证五轮容量。已有基于 2–4 正文字符／Token 的估算只是宽泛敏感性范围；本次没有实际 Token 用量来校准，不能把字符减少率直接写成 Token 减少率。

本机正式消息构造（含编码及保护性解码）14.7–837.8 ms，单独解码 1.2–57.2 ms；单次本机测量不构成性能保证。正常模型调用次数不增加，完整原档案不减少；新增编码消息、版本清单和验证输出需要额外本地存储。独特证据和累计历史仍会增长，P1 不能把无限历史变成固定容量。

## 8. 通用风险与未验证能力

程序已保持 D 的执行动作、S 的实际条件／机会、C 的联合上下文及反例／未知范围原文可还原，没有用成功标签替代过程。引用仍由原事实验证，模型解释不能变成新的执行事实。但这仅建立了验证基础。

尚未验证的模型风险包括：池索引对应错误、表格列对齐错误、跨 P/C 混读同一共享观察、把隐式来源当缺失、漏读历史 limits，以及共享上下文带来的推理成本。它们没有在本次输出中被观察到或排除。本次也没有证据证明 P1 导致额外更新阻断、过度保守或语义偏离。

唯一已观察的运行阻碍是端点拒绝模型标识，属于请求配置／服务契约问题；不能修补 D/S/C Prompt 来处理。后续如继续，需要先明确服务可接受且用户认可的 API 模型标识和参数，再另行冻结、授权新的请求预算。原 8 次失败不得覆盖或从成本记录中删除。

## 9. 是否可以进入 57 项五轮实验准备

可以复用本实现、容量结果和来源测试开展后续协议讨论；**不能据此宣称 P1 已通过真实模型验证或五轮实验已可启动**。仍有两项实质前置问题：

1. 完成合法模型路由下的小规模语义与实际 Token 验证。本次没有任何生成结果，也未验证其余请求参数被该模型接受。
2. 在正式协议中明确 400,000 字符边界及不可静默裁剪的超限停点。指定持续变化情境已经超限；不能仅因当前真实批次约减半，就保证未来五轮安全。是否需要后续容量工作应依据真实 Token 和协议目标另行决定，本次不扩展压缩系统。

57 项、Train＋Selection 与五轮任务安排尚未作为可执行实验配置在此实现中准备或冻结。17 的 P1 输入层与 18 的路由修订目前分别有明确身份；本次控制器显式组合了二者，历史运行入口不会自动迁移。未来新运行器应在另行准备时明确绑定这些身份，不能直接改写旧冻结运行。

本次在完成正式 P1 实现、离线验证及 8 次失败请求的核验后停止。没有修补算法、追加语义采样、迁移 P2、启动 ALFWorld 或生成正式 Skill／Memory。单次语义验证即使后续成功，也不证明 Skill 成功率或预条件化收益提高。

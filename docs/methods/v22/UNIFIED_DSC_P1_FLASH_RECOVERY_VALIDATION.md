# V22 P1：deepseek-flash 授权恢复验证

2026-10-16。本文补充此前 [P1 实现与验证报告](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_P1_IMPLEMENTATION_VALIDATION.md)，不覆盖其模型名错误及 8 次 HTTP 400 记录。实现仍为 `v22.unified_dsc.v4`，消费编码仍为 `v22.p1_shared_input.v1`；D/S/C 规则继承 v3。

**本次 8 个请求全部得到 HTTP 200 和完整 JSON，6/8 通过程序契约；两次 Replay／Memory 均因退休限制条目的字段不合契约而失败。** 真实输入 Token 的三组配对比较显示，P1 分别减少 45.38%、39.15%、44.73%。模型能够读取共享证据完成共同问题分类、条件化 Diagnosis、Fusion Keep／Watch 校准及局部 Editor 修改；没有发现可明确归因于共享索引或观察拼接的新事实错误。它仍存在能力边界判断和行为机会归因偏差，不能称为完整语义通过。

学习失败揭示了一个**两种表示共有、可直接核验的旧契约说明缺口**：实际消息未列出非空 `retire_limits` 条目要求的精确字段名，验证器却严格要求 `effect_id / index / reason / findings`。本次没有修复输出、修改 Prompt、放宽校验或追加采样；没有正式 Memory 生效。

## 1. 恢复授权、版本与冻结

用户明确更正模型并授权继续，因此新增一次最多 8 请求的恢复预算。此前 8 次 HTTP 400 与本次 8 次 HTTP 200 分开计数，累计 16 次实际 HTTP 请求；最早的端点断言停点没有发送请求。旧错误请求的用量和费用未返回，仍标未知。

|项目|本次固定值|
|---|---|
|端点／请求模型|`https://api.deepseek.com/chat/completions`／`deepseek-flash`；8 次响应的 model 也均为此值|
|路由修订|`v22.endpoint_models.v2`；官方 Actor 和更新模型均为 `deepseek-flash`，但本次没有 Actor 调用|
|算法及证据|17 的 v4 P1 实现与 v3 原表示；原 08 R2 真实、相互匹配的冻结事实、Plan、Memory、Editor、diff、轨迹|
|请求参数|temperature=1，thinking enabled，reasoning_effort=medium，stream=false；没有增加 response_format|
|输出预算|分类／Diagnosis／Fusion／Editor 各 32,768；两次学习各 65,536；总 completion 上限 327,680，包含推理|
|执行边界|至多并行 2；连接超时 10 秒、响应超时 600 秒；每例一次，无传输或语义重试，无备用模型|
|时间|北京时间约 16:20:47—16:28:05，总批次约 7 分 18 秒|
|环境／发布|0 ALFWorld episode，0 正式 Candidate Replay，0 Skill／Memory 发布|

复用 19 中的路由函数，不用其 v3 运行器替换 P1 实现。新 [控制器](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/official_flash_validation/route_control.py) 继续调用原一次请求、原解析器及原验证器。分类、Diagnosis、Fusion、Editor 是独立探针，不串接本次生成结果；学习只使用旧的匹配 Editor／Candidate／配对执行，绝不使用本次新 Editor 文本搭配旧轨迹。

证据、messages、criteria 与原准备逐字节相同；除模型与路由修订外，请求参数不变。新冻结覆盖 1,239 个文件，执行前后原保护的 4,906 个文件未变。见 [amendment.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_flash_validation/amendment.json)、[protocol.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_flash_validation/protocol.json)、[freeze.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_flash_validation/freeze.json)。

原有离线门槛仍为 414 项 V22、35 项 Adapter、19 份旧消息精确重建、205 项容量／还原比较通过。本次新增控制器的两项离线路由检查通过；算法与编解码器未改，因此没有为相同源码重复追加模型验证前回归。

## 2. 八个探针的实际结果

全部 finish_reason=`stop`，没有输出截断；完整 content 都可直接 JSON 解析，没有去除推理片段或提取后缀 JSON。

|案例|messages 字符|实际 input Token|completion Token|其中 reasoning|耗时秒|契约／结果|
|---|---:|---:|---:|---:|---:|---|
|classification_p1|62,623|22,638|16,098|15,135|102.82|通过；四个共同决策组|
|diagnosis_p1|81,555|27,963|13,257|12,445|71.31|通过；revise，3 项要求|
|diagnosis_v3|172,518|51,198|9,177|7,919|53.64|通过；revise，5 项要求|
|fusion_p1|124,196|40,204|22,570|22,357|138.48|通过；Keep 原要求，新增 w4|
|fusion_v3|220,383|66,070|18,767|18,508|113.50|通过；Keep 原要求及 Watch|
|editor_p1|121,272|39,668|10,153|8,811|48.93|通过；生成未执行 Candidate|
|learning_p1|184,493|60,758|31,599|28,076|167.73|失败：Invalid limit retirement fields|
|learning_v3|369,373|109,925|26,888|24,374|146.42|同上|

请求级完整 JSON 率为 8/8，契约有效率为 6/8；P1 五阶段为 4/5。契约通过不能代替语义判断。两次学习虽有可分析的 Findings 和建议修订，但整个输出没有获接受，也没有生成或应用 `probe_memory.json`。不将它们计作有效学习闭环。

每例目录保存 payload、messages、request、criteria、call、raw HTTP body、response、content、parsed、result。通过的阶段还有原验证器结果，Editor 有实际 diff 与 realization。见 [总调用记录](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_flash_validation/run_summary.json)；错误输出没有被替换。

## 3. 模型是否能使用 P1 证据

### 分类与 Diagnosis

P1 分类完整分区十项任务，按直接搬运、状态改变后放置、第二件仍在原来源、必需实体缺失后的继续选择组织。它区分“缺工具”“缺第二件”和“拿了不同类型物体”，不是仅按任务名称或成功／失败分组；它没有穷尽所有可能的共同问题，这不构成分类失败。

P1 Diagnosis 提出三个条件化 Update，分别处理命名工具不可见、第一件交付后原来源没有第二件、不同类型不能替代目标；保留成功路径，并附三项 Watch。它引用的 19 个 Parent 事件和 v3 引用的 41 个事件均来自原始来源，未用池索引冒充事件。P1 将 stop 限定为“当前合法才使用”，没有把菜单共享误解成当前可终止。

仍有一般语义边界：第一件已经交付、原来源、从未观察到目标等条件可能超出 Actor 的最近两对历史；该批也没有实际合法 stop 机会。v3 对照提出“每对象最多一次状态操作”等更强尺度要求，却遗漏了目标类型错配。不能因本次 P1 输出更贴近该问题，就推断编码提高了推理质量；也不能据两个样本证明不存在能力约束问题。

详见 [分类与 Diagnosis 逐事件复核](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/analysis/flash_classification_diagnosis_review.md)。新分类没有被送入本次 Diagnosis，其组号不可与旧分类组号混为一谈。

### Fusion：有依据的 Keep 与历史响应影响的边界

两次 Fusion 读取同一旧初稿 u1/u2/u3、当前 Parent 和正式 R1 Memory，均 `changes=[]`。它们正确识别当前失败，指出 m1/m2 的有效规则已在 Parent 中，无需重复增加义务；将 m3 中短历史搜索仍可能失败的认识保留为不确定性。Keep 是合法结果，不能因没有非恒等变换就判失败。

P1 的具体历史作用是新增 `w4`：当目标尚未观察到时，检验不同候选搜索究竟找到目标，还是仍耗尽步数。这个问题明确由 m3 的实际失败／迟发现响应支持，**属于历史响应校准观察预期**；它没有改变 requirement 的方向、尺度或关联，不能称为已证明历史驱动 D/S/C 非恒等更新。

两侧共同遗漏：旧初稿仍含全局 visited／unvisited 和主动 stop，当前 Actor 没有全局已访问集合，P1:20 与 P6:29 的 stop 明确不合法且返回 Nothing happens。v3 的“所有要求都可执行”理由更直接与事实矛盾。P1 的 Keep 同样没有消除该冲突。这是现有自然语言可执行性判断风险，没有证据证明由共享编码新增。

### Editor：忠实落实与可执行性必须分开

Editor 独立读取旧有效 Plan 的 u2/u4/u5，而不是本次 Fusion 的 u1/u2/u3。新 Candidate SHA256 为 `a81bf4d55f0125ea8a6b6f40bef73ae25f86d360402f5a54c441776db5717beb`，只改 Parent 第 3／4 节；序言及第 1／2／5 节逐字保留。八个摘录映射合法，三项有效要求都有 Candidate 文本覆盖。

方向、触发条件、禁止强度、先交第一件再回来源的依赖，以及 selected microwave-style path 的重要例外基本保留。没有观察到将有条件路径额外强化为新强制策略。见 [实际 diff](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/official_flash_validation/cases/editor_p1/actual.diff)。

主动 stop 来自有效 Plan，Editor 没有擅自发明，但它仍照写且 `issues=[]`，未报告当前不可执行的出口。文本基本忠实不能推出实际行为可执行；该 Candidate 未进入环境。详见 [Fusion／Editor 复核](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/analysis/flash_fusion_editor_review.md)。

## 4. Replay／Memory：字段契约失败与原始语义分别判断

### 可直接确认的契约说明缺口

验证器 [effective_memory.py:172](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/effective_memory.py:172) 要求每个非空退休条目恰有：

```json
{"effect_id":"被替换的 Effect ID","index":0,"reason":"依据","findings":["当前 Finding ID"]}
```

实际 P1 输出使用 `effect / index / reason / findings`；v3 使用 `effect / limit_index / reason / findings`。两侧均缺 `effect_id`，故被拒绝。

核对**完整实际消息**，两侧 System 和 user 中 `effect_id` 出现次数均为 0，`limit_index` 也均为 0。共同规则仅描述“被替换的 Effect、零基 ACTIVE limit 下标、原因、Finding ID”，示例只有 `retire_limits:[]`。对应 [unified_dsc.py:198](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/unified_dsc.py:198) 与 [contract_alignment.py:55](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/contract_alignment.py:55)。两种表示的行为规则相同，因此这里是旧 v3 的模型可见契约不完整，不能只归为 P1 解码错误或模型不遵从已明确字段名。

该缺口影响有依据的范围扩大与限制修订能否落盘，具有通用意义。后续最小处理应是明确现有非空退休条目的精确键名，保持 Schema、验证器和调用数量不变；不是自动改写输出字段、禁用退休或机械继承旧限制。**本次只记录，不实施这一修改，也不重验修复后的输出。**

### 原始模型建议中的有效认识

以下仅评价未获接受的建议，不称为 Memory 已学习或正式生效：

- P1 能同时读到实际 diff、Editor 映射、旧 Update 与配对路径，识别“没有拿错类型”不等于最终成功，识别缺工具条件确实出现但仍循环，且菜单没有可执行 stop。
- 两侧都保留新修改是组合、不能单项独立归因、任务成功不证明必要或充分等限制；能观察成功保持之外的绕行，例如 C9 17 步对 P9 8 步、C5 33 步对 P5 8 步。
- P1 拟扩大 m1 的已观察对象／器具覆盖，同时重述尚未测试的其他器具及从关闭器具内部取得目标的条件。v3 拟修订 m2 中另一来源／非抽屉目的地的限制，并保留“目的地没有 move”尚未测试的剩余部分。这些是证据范围修订的正面语义迹象，不是机械整体解除复合限制。
- Findings 的原事件引用合法，使用已有 Watch 和实际更新关联，没有输出池索引作来源。合法引用仍不证明每句解释正确。

### 仍然存在的行为机会与归因错误

两侧都把 C8 的跨来源成功提升为 u5“回到原来源后没有第二件”的作用认识。实际 C8:22 放置第一件后，C8:23 到 sidetable 1，C8:24 到 tvstand 1 找到第二件，没有返回原 sidetable 2。Parent 的回源空观察不能自动成为 Candidate 的同一行为机会。C8 支持联合修改下的跨来源成功，不直接验证该精确触发分支。

更直接的机会是 C10:5 返回原 countertop 1 只见 dishsponge，C10:6—8 转到 cabinet、打开并拿到第二件；v3 f5 识别了这个事实，P1 没有充分利用。它仍是组合证据，不证明 u5 独立因果收益。

v3 还声称 C6 没遇到可拿其他类型的机会，但 C6:2 的菜单有 peppershaker／saltshaker，C6:15 有 cup／mug；这是一项可以由原菜单反驳的机会误判。P1 没有犯这一具体错误，但在描述绕行时使用“新增搜索指令可以增加路径长度”的措辞，较其联合归因限制更强。P1 还存在局部步数／访问次数表述不准，不能据总体路径正确就忽略。

这些现象说明：模型总体能读取共享事实，机会匹配和解释仍会出错；两侧各有不同遗漏，不能从单样本确定编码造成了差异。对已发现的 C8 错误，模型原文能描述正确路径，却在条件化结论中越界，更符合行为解释问题，而非证据被编码删除。详见 [学习语义复核](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/analysis/flash_learning_review.md)。

还需保留两个细节：没有合法 stop，并不证明“没有不同候选”的末端条件已经出现；菜单仍可能有其他导航候选。P1 的 m1 修订虽保留其他器具未知，却没有同样明确地保留同类器具上的其他对象组合未知，属于范围表述风险。不能将这些建议概括成所有触发条件或残余未知都已正确处理。

## 5. 实际 Token、成本与运行稳定性

|同事实配对|v3 input|P1 input|输入减少|P1 completion 相对变化|本次总 Token 减少|
|---|---:|---:|---:|---:|---:|
|Diagnosis|51,198|27,963|45.38%|增加 44.46%|31.73%|
|Fusion|66,070|40,204|39.15%|增加 20.26%|26.01%|
|Replay／Memory|109,925|60,758|44.73%|增加 17.52%|32.49%|

三组 input 合计 **227,193 → 128,925，减少 43.25%**；连同各自生成输出，合计总 Token 减少 **30.38%**。这是同事实同模型实际用量，不再用字符数代替 Token。分类与 Editor 没有本次实时 v3 对照，不能用旧 Pro 用量补成匹配对照。

三组 P1 的输出、推理 Token 和耗时均比本次 v3 对照更高；因此节省并不等于输出或延迟同步改善。temperature=1、每条件单次采样不足以将这些差异归因于解码负担或算法变化。

本批全部 8 次合计：input **418,424**，completion **148,509**，总计 **566,933**；其中 reasoning **137,625** 已包含在 completion 内，不能再次相加。缓存命中 384、未命中 418,040 input Token。两次契约失败的真实用量全部计入成本。

按检索到的官方 Flash 高峰价估算：每百万缓存命中输入 0.04 元、未命中输入 2 元、输出 8 元；本次请求在北京时间工作日 16 点段，据此约 **2.0242 元**。美元价表对应约 **0.3036 美元**，是不同计价表的估算，不应相加。这不是账户实际扣费记录，先前 HTTP 400 的费用仍未知。价格依据：[DeepSeek 中文价格表](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)、[英文价格表](https://api-docs.deepseek.com/quick_start/pricing/)，检索日期 2026-10-16。

三组配对按本次实际用量估价：v3 合计约 0.8928 元，P1 约 0.7970 元，约低 10.73%。输入降幅没有等比例转化为费用降幅，因为输出更贵且本次 P1 输出增加。详见 [逐请求用量／估算](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/17_p1_input/analysis/flash_usage_cost.json)、[核算脚本](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/17_p1_input/official_flash_validation/analyze_outputs.py)。估算依赖当前价格表及本次缓存，不能外推长期账单。

网络请求成功 8/8，无超时、HTTP 错误或截断；语义输出契约成功仅 6/8。应分别报告传输稳定性与学习输出可用性，不能把前者写成整条流水线已稳定。

## 6. 容量边界与下一阶段判断

本次没有改编解码器，原 205 项正式容量测试仍适用：全部可精确还原，但重复 50 步的五轮情境最高 279,957 字符，持续变化情境最高 430,301，部分学习输入仍超过 400,000；极端唯一命令／长观察场景更大。当前实际学习请求是 184,493 字符／60,758 input Token，不能据此保证未来五轮不会超限，也不能将单一字符／Token 比例外推所有输入。

**可以保留 P1 作为后续实验的候选输入实现，开始有限的协议准备；不能直接批准 57 项五轮运行。** 本次没有发现必须放弃 P1 的共享编码事实丢失，但还有：

1. **确定性契约前置问题**：对齐 Memory 非空 `retire_limits` 的模型可见字段说明，再另行验证该分支。目前本次两次学习都无法正式应用，尚未完成有效模型输出的学习闭环。
2. **容量及运行配置问题**：在后续协议中明确超限停止／恢复边界，绑定 P1 与当前 Actor／语义路由，并独立准备五轮任务与预算。19 的 v3 入口不能直接代替 P1；本次独立探针也不是五轮运行器。
3. **实验中观察的不确定性**：Actor 可见历史、stop 可执行性、Update 精确触发机会、联合归因与绕行风险。它们不应自动催生新审核 Agent、全局状态机或逐案例 Prompt 规则，也不应以更保守为优化目标。

本次完成后停止，没有新增第九次恢复请求、修改已冻结算法／Prompt、执行新 Candidate 或扩大到五轮／消融。结果支持“P1 在这些真实材料上无损减少输入，并可被模型用于主要职责”，不支持“所有模块语义已经正确”“P1 已保证进化效果不变”或“预条件化已提高 Skill 成功率”。

# V22 unified D/S/C v2：恢复 1 执行结果与 Diagnosis 停点

日期：2026-10-16（北京时间）。**第一轮 Parent 现已完整取得 8/8 原生成功；分类成功，Diagnosis 因跨组来源引用不完整被现有契约拒绝。两轮实验尚未完成，无 Candidate、Gate、Memory 或正式状态发布。**

本报告接续 [首次中断报告][original-report]，不覆盖原报告或原档案。研究协议、任务、算法和评价规则仍为 [冻结准备方案][preparation]。

## 1. 授权、恢复方式与不变项

用户在收到恢复提案后回复“可能是网络中断了导致进程消失，请你继续”。据此执行一次独立恢复：复用5条完整 Parent，重启0017／0025／0033三条不完整 episode；没有重跑任何完整任务或既有成功语义阶段。首次进程消失仍不能确认为网络原因。

恢复于北京时间 **10:42:26** 启动，**10:55:19** 以退出码1完成错误结算。后台进程与聊天会话分离，具有独占启动标记、stdout、分发清单和退出记录。本次没有再次发生进程失联。

控制器只是原 `run_campaign` 的依赖回调包装：五个指定 Parent 槽载入原始轨迹及原始响应，其余槽使用原执行回调。原代码、模型参数、任务、Prompt、Schema、Gate 及 Memory 规则未修改。新归档身份反映独立恢复，不把它伪装成无中断原进程。

- [恢复协议及授权][recovery-protocol]、[authority.json][authority]保存复用对象、授权文字、预算及控制器哈希。
- 原177个文件哈希核验不变；新runtime逐项核对源码、配置、Prompt、游戏和依赖，保持原冻结行为。
- 恢复新runtime身份：`55a7514236f0a5361bf70562621d13067064e2bb9187400d4c75f1e69474c296`。
- 6项恢复离线检查通过，覆盖真实5条轨迹字节复用、3项重启仅一次、Candidate不误复用Parent、错轮／错Skill拒绝、新episode上限、语义重复拒绝。首次测试遇到macOS `/var` 路径规范化问题，仅修正独立控制器路径并保留失败日志。

原runner在恢复目录报告的8个episode槽含5个复用槽；本次真实新增episode只有3个。真实新增Actor请求68次，Pro2次；总账按run_id及原始响应去重，不能直接相加两个目录的cost。

## 2. A：完整 Parent 结果与研究边界

| R1任务 | Parent原生结果 | 步数 | 来源 |
|---|---|---:|---|
| train:0019 | 成功 | 7 | 复用完整原轨迹 |
| train:0004 | 成功 | 4 | 复用完整原轨迹 |
| train:0020 | 成功 | 9 | 复用完整原轨迹 |
| train:0017 | 成功 | 18 | 本次授权重启 |
| train:0025 | 成功 | 35 | 本次授权重启 |
| train:0033 | 成功 | 15 | 本次授权重启 |
| train:0016 | 成功 | 7 | 复用完整原轨迹 |
| train:0010 | 成功 | 9 | 复用完整原轨迹 |

原0017／0025／0033中断前缀保持独立，只计费与审计，不参与模型输入、配对或成功率。本次没有依据结果选择多个完整采样中的较好者，三项都仅重启一次。

可以观察到的局部事实：0017重访若干位置后在餐桌找到目标，并完成清洁和放置；0025经过多个储物位置，在第30步打开目标所在柜子、第31步取物、第33步冷却、第35步完成放置；0033在放入、关闭、取出的绕路之后，第13步直接执行加热、第15步成功放置。其余5条有效路径详见原报告和逐步记录。

这些都是 **No Skill Parent 行为**。尚无Candidate，所以没有修复、退化、局部改善或有效能力保留的配对结论。原中断与重启路径差异也不是Skill更新效应。

第一轮成功数已达8，按冻结Gate即使后续Candidate仍为8也只能RETAIN；效率或局部行为改善仍可被观察、学习，但不改变采用规则。当前尚未执行Gate，不能提前登记RETAIN。

## 3. B：实际模型行为与精确失败原因

### 3.1 分类结果

分类正常返回并通过验证，形成4个共同决策问题组：

- G1：目标未持有且位置未知时的搜索／取物，包含0010、0017、0020、0025。
- G2：清洁后向关闭的目标容器投放，包含0016、0019。
- G3：持物直接加热与先放入设备的操作顺序，包含0033。
- G4：灯下观察目标的动作组合，包含0004。

它们并非只按任务成功标签分类。不同问题进入同一份Diagnosis输入，没有各组单独生成Skill。原始结果见 [classification.json][classification]，实际任务和别名映射见 [grouping.json][grouping]。

### 3.2 Diagnosis 原始更新

Diagnosis 返回 `revise`，提出4项要求和3个Watch，原始 JSON完整保留于 [diagnosis.json][diagnosis]：

| 要求 | 准备改变的行为 | 当前材料支持与局限 |
|---|---|---|
| u1 | 找不到目标时检查可见候选位置，打开关闭容器，目标出现时取物 | 条件与行动明确；Watch指出两步历史下能否减少重访仍未知，不能视为已解决搜索循环 |
| u2 | 持有目标时优先直接用指定设施完成变换，避免不必要的放入／关闭／取出 | 联合引用清洁、冷却、加热的真实事件；具备跨组协调意图，但范围是否合理尚未验证 |
| u3 | 向关闭的目的容器投放前先打开，开放位置直接放置 | 与已执行成功路径有对应，尚无新编辑响应 |
| u4 | 灯下观察任务先操作设备，确认物体并取物 | Watch主动询问“总是取物”是否过强；不能以单条成功路径证明广泛义务合理 |

原始Update具有策略、条件和关联内容，不只是“提升成功率”。不过intent也预先包含了具体策略，Goal与可替代策略的分离并不完全。上述仅为对原始输出的语义阅读；该Plan未成为有效Update，更没有经过Editor或Replay检验。

### 3.3 唯一被程序检出的来源失配

两次Pro调用均HTTP 200、`finish_reason=stop`，输出未截断且可解析。Diagnosis通过既有compact结构和来源存在性检查，但在 [validate_grouped_plan][validator] 的 `groups == event_groups` 检查处失败。

| 要求 | basis列出的组 | 所引Parent事件实际所属组 | 检查 |
|---|---|---|---|
| u1 | G1 | G1 | 通过 |
| **u2** | **G3** | **G1、G2、G3** | **缺少G1、G2引用** |
| u3 | G2 | G2 | 通过 |
| u4 | G4 | G4 | 通过 |

u2具体引用：`P1:4 / P7:4`为G2清洁事件，`P5:33`为G1冷却事件，`P6:5 / P6:13`为G3加热相关事件，但只列了G3组来源。所有这些事件真实存在；不是伪造事件、JSON破损或HTTP失败。逐引用核对见 [diagnosis_reference_check.json][reference-check]。

程序允许多组联合引用，拒绝的是事件所属组与显式组来源不一致，**不是禁止跨组迁移本身**。模型可见GROUP规则要求以当前组来源及Parent事件为依据；该段没有像程序一样显式写出“两个集合必须相等”。这说明本次输出与严格来源契约未完全对齐，不能据一次输出断言统一D/S/C算法无效，也不能把它当作新通用机制缺口已经成立。

没有补写两个group ID、删除事件、改变验证器或重试Diagnosis；原始失败被完整保留。

### 3.4 尚未执行的作用链

R1 Fusion程序恒等、Editor、Candidate Replay、Gate和Memory Learning都未进入；R2未开始。最新状态仍为No Skill＋空Memory。没有历史Effect，更无第二轮历史驱动／当前证据驱动D/S/C决定可比较。

本次只观察到分类及一个被拒绝的原始Update。Editor忠实落实、实际编辑—行为响应学习、历史条件适用性及预条件化增益均仍未验证。

## 4. C：成本与稳定性

| 口径 | 请求／HTTP尝试 | 输入Token | 输出Token | 合计Token |
|---|---:|---:|---:|---:|
| 本次恢复新增（不含5条复用） | 70／70 | 107,426 | 75,046 | 182,472 |
| 两次执行累计Actor，按run_id去重 | 152／152 | 94,428 | 87,256 | 181,684 |
| 两次执行累计Pro | 2／2 | 63,587 | 20,967 | 84,554 |
| **累计真实总账** | **154／154** | **158,015** | **108,223** | **266,238** |

累计11次真实episode启动：原8＋恢复3；目前完整8、不完整3。共151份已确认HTTP 200返回，原运行3个在途请求仍无响应／usage确认，不当作免费。Reasoning共75,096 Token，是completion子集，不另加。货币费用未知，未采用未经确认的代理价格估算。

| Pro阶段 | 输入Token | 输出Token | 推理Token（子集） | 耗时 | 结果 |
|---|---:|---:|---:|---:|---|
| 分类 | 27,619 | 12,925 | 12,093 | 225.56秒 | HTTP／JSON／阶段契约通过 |
| Diagnosis | 35,968 | 8,042 | 7,317 | 136.88秒 | HTTP／JSON／compact通过；组来源契约失败 |

两次Pro均在32,768预算及600秒超时内；原始响应、消息和请求参数均已保存。JSON可解析率2/2，完整阶段输出通过率1/2，不能将“HTTP成功”写成两次有效Update。

恢复期间没有HTTP重试、语义重采样或追加调用，也没有Candidate或新发布。恢复campaign verifier返回 `artifact_valid=true, campaign_complete=false, status=error`：证明错误终止档案与来源一致，**不表示Diagnosis语义有效或实验完成**。原177文件仍完全不变，5个复制轨迹及其响应逐字匹配；详见 [结果与账本汇总][results]。

## 5. 下一步边界：未执行第二次恢复

当前可直接复用：完整8项Parent、成功分类与分组、冻结输入、失败Diagnosis原响应和全部请求证据。不需要再执行环境来修复当前停点。

若用户希望在不改变算法／Prompt／契约的前提下继续，最小请求是：**另行授权对完全相同冻结消息进行一次Diagnosis语义重试**。它是额外调用，而非既有预算内的自动重试，也不保证下次输出合法。成功后才继续尚未执行的原流程，失败则再次保存并停止。不得删改该失败结果来冒充首次成功。

该后续方案最多需要：

- 新环境episode24个（R1 Candidate8＋R2 Parent/Candidate16），无需重跑8条Parent。
- 新Actor逻辑请求最多1,200；Pro最多8次，其中1次是额外Diagnosis重试，另7次是原流程未执行阶段。
- 新HTTP尝试最多7,208；计入当前154次，累计最多7,362；累计真实episode最多35、Pro最多10。

上述仅为可审阅预算，**本次授权恢复1已在新技术失败处结束，没有启动恢复2或修改冻结方案**。若选择确定性补齐引用等工程方式，则属于另一项明确的接口／消费处理变更，不能在本次运行中悄悄实施。

[original-report]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_STREAM_RESULTS.md
[preparation]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_STREAM_PREPARATION.md
[recovery-protocol]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery1_control_20261016/RECOVERY_PROTOCOL.md
[authority]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery1_control_20261016/authority.json
[classification]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery1_live_20261016/rounds/r1/outputs/classification.json
[grouping]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery1_live_20261016/rounds/r1/grouping.json
[diagnosis]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery1_live_20261016/rounds/r1/raw_outputs/diagnosis.json
[validator]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/grouped_representation.py:186
[reference-check]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery1_analysis_20261016/diagnosis_reference_check.json
[results]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery1_analysis_20261016/results.json

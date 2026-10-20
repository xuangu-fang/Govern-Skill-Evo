# V22 57项五轮：R3 Fusion恢复

> 后续授权：R4网络错误已归档并恢复成功；R4已发布，R5在Fusion输出截断处停止，累计发布4/5轮。最新过程见[R4网络恢复报告](ALFWORLD_57_FIVE_ROUND_RECOVERY_03.md)。

2026-10-16，用户明确要求“归档失败的fusion，然后重启”。本次显式授权一次R3 Fusion同请求恢复，成功后继续原R3–R5；此前所有失败和费用保留。

**最终结算：R3 Fusion同请求恢复成功，R3完整共同发布；R4 Parent在val:0000第22次Actor请求发生ChunkedEncodingError，按协议停止。当前正式发布3/5轮，五轮未完成。**

原运行：`artifacts/methods/v22/23_alfworld57_five_round/formal_run/`。
前次恢复：同级 `recovery_01/`。
本次恢复：同级 `recovery_02/`；控制与授权：`recovery_02_control/`。

## 归档、复用与冻结

R3 Fusion失败的完整输入、messages、调用、原始HTTP响应、未解析文本、容量检查、解析错误和usage已复制到 `recovery_02_control/archive/fusion_attempt_01/`；不补括号、不修改原输出。前次运行所有文件由 `prior_archive_manifest.json`冻结；首次运行和Editor失败档案也继续核验。

复用60条完整episode：R1和R2两侧各12项，加R3 Parent 12项；复用12个成功语义阶段：R1/R2各5个，加R3分类、Diagnosis。保留原state0和campaign／round／事件身份；前两轮正式Skill／Memory重建结果须与原文件逐字一致，R3轮初context须相同，才允许新Fusion发送。

运行器字节码、v6、P1、统一引用、Prompt、模型及请求参数、任务分组、随机种子、8并发、50步、400000字符与上下文检查均保持原冻结。复用先前恢复控制器，不另写自进化框架，不增加模型字段或评审Agent。Fusion重发完整相同请求，无失败提示；不因合法退化或RETAIN返工。

本次新增上限54条episode、2700次Actor逻辑请求、13次语义调用；累计上限仍114条episode，语义上限27次，包含此前Editor和Fusion两次失败。只有一次R3 Fusion技术恢复，其他语义／episode追加重试为0；新的技术错误保存当前阶段并停止。

4项专项离线测试通过：原失败仍按原契约失败；消息改动在请求前拒绝；缓存阶段不调用网络且拒绝重复；60条episode与12阶段完整复用，前两轮state逐字重建一致，唯一新请求停在相同R3 Fusion边界，期间无环境或网络调用。启动前旧档案、源码、配置及新恢复授权再次通过核验。

## 正式结果与准确停点

R3 Fusion实际HTTP请求体SHA256与失败请求相同：`e59ee0a9e3202a083dd38482156ab1c477d69ebf2cebab12415afc1db999f5e2`；模型、完整messages和参数一致。新的Fusion、Editor、Memory均以完整响应通过原契约，未修补旧JSON。原失败Fusion与费用继续保留。

| 轮次 | Parent | Candidate | 动作步数P/C | Gate | 正式发布 |
|---|---|---|---|---|---|
| R1（12项） | 12/12，100% | 12/12，100% | 171/83 | RETAIN | No Skill＋新增Memory |
| R2（12项） | 10/12，83.33% | 7/12，58.33% | 208/320 | RETAIN | No Skill＋修订Memory |
| R3（12项） | 8/12，66.67% | 7/12，58.33% | 328/311 | RETAIN | No Skill＋修订Memory |
| R4（12项） | 8成功、3正常失败、1技术未完成；整批成功率未结算 | 未执行 | 220/—，另有1次未返回请求 | 未产生 | 未发布 |
| R5（9项） | 未执行 | 未执行 | — | 未产生 | 未开始 |

R3有1项修复（train:0033）及2项回归（train:0026、0034），相对原8项成功净减少1项。整体步数328→311不能代替成功率或独立归因。Candidate合法退化没有引发返工或重采样，Memory处理后仍自动进入R4。

R4唯一技术错误是原始val:0000（开发池中的灯下观察闹钟任务），在已完成21个环境动作后，第22次Actor请求发生`ChunkedEncodingError`，阶段为`model_request`。传输尝试耗时48.03秒，status=error；没有返回完整HTTP响应、response_model、finish_reason、原始body或usage，因此这些字段记为不可得／未知。前21个响应、当前完整请求和错误元信息均已保存；不虚构丢失的响应或费用，不把未知当零。

原客户端最多6次HTTP状态重试规则不涵盖这种网络异常；本协议的网络异常／episode追加恢复为0。因此在收齐已派发任务后停止。R4未运行分类、Diagnosis、Fusion、Editor、Candidate、Gate或Memory，R5未开始；不能将此错误标为任务失败、RETAIN或no_change。

| R4 Parent任务 | 状态 | 已执行动作 | 模型请求 |
|---|---|---:|---:|
| train:0036 | 50步正常失败 | 50 | 50 |
| train:0037 | 成功 | 8 | 8 |
| train:0038 | 成功 | 10 | 10 |
| val:0000 | 技术未完成 | 21 | 22 |
| val:0001 | 成功 | 4 | 4 |
| val:0002 | 成功 | 6 | 6 |
| val:0003 | 成功 | 4 | 4 |
| val:0004 | 成功 | 4 | 4 |
| val:0005 | 成功 | 5 | 5 |
| val:0006 | 成功 | 8 | 8 |
| val:0007 | 50步正常失败 | 50 | 50 |
| val:0008 | 50步正常失败 | 50 | 50 |

最后正式状态为 `recovery_02/rounds/r3/state.json`：round_index=3、No Skill、1条修订后Effect；R4只读取该状态，未发布新状态。R1→R2、R2→R3、R3→R4的Parent／Memory和state_sha256均核对通过。前两轮复用后的state文件还与前次发布文件逐字一致。

## Fusion、编辑、Replay与Memory研究观察

R3 Fusion保留u1/u3/u4，替换u2和u5，迁移2个Watch：增加目标在设备内时先取出再加热／冷却的恢复分支，以及搜索时打开关闭容器的显式要求。所有changes.basis引用当前轨迹和分组，**没有显式引用历史Effect**。历史Memory确实传入，但不能据此断言本轮变换由历史Effect导致；R2有显式历史依据的两次替换仍是另一项已记录的事实。

Editor生成实际Candidate及实现映射并通过原验证器；完整实际diff和执行Plan在R3目录。Replay按原条件完成12对，Gate为8→7的RETAIN。Memory读取该份实际编辑与配对执行，没有拼接旧Candidate。5条Findings及1条替换delta通过，未退休旧限制；最新Effect ID为`475639db59e4b82bd457eeb139b6b6d4542275f903bb5a54bc17581963a635f1:m1`，17项basis、11条limits，包含三轮来源。正式Skill因三轮均RETAIN一直为No Skill；因此实际验证了Memory跨轮继承及修订，但没有观测到ACCEPT后Skill版本的持续继承。

Memory中有真实支持的局部认识：微波炉开关循环在部分Candidate路径中被直接温度动作取代，train:0033从50步失败变为成功；也保留了搜索未覆盖目标所在位置、取到对象太晚导致无时间放置等反例。这些是当前联合编辑与单次配对结果，不能孤立为某一条要求的因果作用。

抽查仍发现并保留以下偏差，未人工改写输出或Memory：

- R2“共享步骤对象意味着执行未区分”的错误限制被继续保留在最新Memory的index=4。
- R3 index=7又把P8/C8、P9/C9共享步骤内容解释为“非独立”。实际两对（train:0031、0032）有独立run ID、不同Skill和实际请求体哈希；内容共享不合并执行身份。独立轨迹核验见`analysis/recovery_02_semantic_identity_audit.json`。
- 同一index=7将未找到目标的C1/C7泛化为包括u5在内的要求“未评估”。u5恰在目标不可见时触发，实际已执行搜索，不能把未取得目标等同于没有搜索决策机会。对温度／放置规则缺少触发机会，与搜索规则已触发但覆盖不足，须分别理解。

程序契约允许这些自然语言认识通过，这不表示它们正确。错误被继承和扩展也是本次持续学习的实际研究现象，后续是否自行修订尚未验证；没有新增评审Agent、输出字段、语义修补或Prompt改动。

## 资源、失败与累计成本

本次运行北京时间 **2026-10-16 23:19:22–23:44:44**，墙钟 **1521.30秒（约25分21秒）**。三次执行墙钟相加 **5446.16秒（约90分46秒）**，不含运行之间等待及离线准备，不等于从首次启动至今的连续日历耗时。

新增24条episode（R3 Candidate 12＋R4 Parent 12），其中23条完整、1条技术未完成；532次Actor请求（531个已执行动作＋1个无响应请求），3次语义请求，535次传输尝试。复用60条episode和12个成功语义阶段，均未新增模型／环境执行。累计实际84条episode，83条完整；1642次Actor请求、17次语义请求、1659次传输尝试，独立Test为0。

| 新增阶段 | 输入Token | 输出Token | 其中推理Token | HTTP秒 |
|---|---:|---:|---:|---:|
| R3 fusion | 84,290 | 18,306 | 17,481 | 115.36 |
| R3 main_editor | 83,798 | 7,697 | 6,317 | 39.95 |
| R3 post_gate_learning | 106,909 | 21,167 | 18,861 | 123.95 |

本次**已报告**输入763,098、输出637,433、总计1,400,531 Token，其中推理585,311。累计**已报告**输入2,143,800、输出2,563,132、总计4,706,932 Token，其中推理2,391,819（输出子集，不能再加一次）。最后一个网络失败请求usage未知，故这些数字不是全部消费的完整已知账单；金额未查询账户账单，未知不能当免费。

此前Editor摘录失败和R3 Fusion JSON失败的成本各保留一次，本次失败Actor记录也保留；新增成本不含复制材料的重复计数。原生 `report.json`中的cost包括复用材料供档案核验；以`recovery_02_control/completion.json`的新增／累计账目为去重消费口径。17次累计真实语义请求包括此前两个失败；当前目录15个语义调用记录中有12个是复用，不能混为新增请求。

最大实测完整语义消息为R3 Memory的323,184字符，400,000字符检查和上下文检查保持生效。本次停点是网络错误，没有发生容量超限，也未验证R4/R5更长历史输入的容量。

## 核验、证据与结论边界

事后核验：artifact_valid=true、campaign_complete=false、published_rounds=3、incomplete_rounds=1。R4部分episode按原验证器确认episode_complete=false；没有R4分类输入或state.json，没有R5目录。所有此前运行及失败档案清单／哈希再次核对通过，`all_prior_archives_unchanged=true`。档案有效不意味着未完成任务已有结果，也不意味着Memory语义正确。

证据入口均在实验23的artifact根目录：

- `recovery_02_control/authority.json`、`prior_archive_manifest.json`、`archive/fusion_attempt_01/`：本次授权、旧档案身份、未改写的失败Fusion。
- `recovery_02_control/dispatch_ledger.json`、`completion.json`、`verification.json`：复用／执行分离、去重费用及核验。
- `recovery_02/runtime_freeze.json`、源／配置快照：与原冻结一致的源码、模型、Profile、Prompt、Schema和容量规则。
- `recovery_02/rounds/r3/`：有效Fusion、Editor、实际diff、12对Replay、Gate、Findings、Effect、basis、Watch及共同发布state。
- `recovery_02/rounds/r4/parent_runs/val_0000/`：21个已执行动作、失败第22请求、错误轨迹与进程日志，未伪造未收到的响应。
- `analysis/recovery_02_final_results.json`：逐任务结果、错误来源、请求哈希、usage、时间和完整结算；`recovery_02_semantic_identity_audit.json`：来源身份与认识偏差抽查。

当前三轮结果没有成功率提升：R1同分且更少步，R2/R3整体退化，三轮均RETAIN；Memory确实持续继承和修订，且仍存在事实／机会／共享编码解释偏差。不能据此声称方法优于无Memory，也不能把技术中断当成方法行为失败。五轮连续完成、正式Skill被ACCEPT后的继承和独立Test泛化均未验证。

后续消融与独立Test应区分：历史Effect的实际消费、当前证据驱动的更新、最近两对历史与长搜索循环的交互、共享编码下的独立执行身份理解、联合编辑的触发机会和归因，以及成功数Gate与效率改善的关系。Selection已经用于本次开发优化，不再是独立选择集。此报告不授权追加请求或episode重跑。

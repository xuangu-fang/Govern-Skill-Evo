# V22 57项五轮：首次Editor技术恢复

> **最新结算：R3 Fusion同请求恢复成功，已完整发布3/5轮；R4 Parent在val:0000第22次请求发生ChunkedEncodingError，按协议停止。** 原失败与费用保留；最新结果见[R3 Fusion恢复报告](ALFWORLD_57_FIVE_ROUND_RECOVERY_02.md)。

2026-10-16，用户明确要求归档第13条映射失败的Editor并重新运行。此恢复是在原零自动重试协议之外，显式授权的一次同请求Editor恢复；原实验失败结论和费用保留，不能改写成首次即完整成功。

**最终状态：Editor同请求恢复成功，R1、R2完整共同发布；R3在Fusion非法JSON处停止。五轮未完整完成，正式发布2/5轮。**

原始正式目录：`artifacts/methods/v22/23_alfworld57_five_round/formal_run/`。
独立恢复目录：`artifacts/methods/v22/23_alfworld57_five_round/recovery_01/`。
恢复控制与授权：同级 `recovery_01_control/`。

## 归档与恢复边界

原始目录的所有文件保存完整哈希清单，记录于 `original_archive_manifest.json`。失败Editor的完整输入、消息、调用、原始响应体、输出和容量记录复制到 `archive/editor_attempt_01/`，另存失败原因及原usage；既不修正第13条摘录，也不应用原提案。

复用全部12条成功R1 Parent及已成功分类、Diagnosis、Fusion，逐字核对输入输出和轨迹，保留原state0、campaign ID、round ID、事件与来源身份。恢复使用已有冻结 `run_campaign` 字节码，只在隔离命名空间继承原初始归档身份，沿用之前V22恢复方式；没有另一套自进化流程。

R1 Editor只新增一次请求：完整messages、模型、参数与失败请求相同，不增加失败反馈，不改Prompt、算法、验证器或模型输出。通过后接续Candidate、Gate、Memory及R2–R5。合法效果退化按原Gate处理；新的技术失败保存停点，不自动追加重试。

五轮任务仍为12+12+12+12+9，v6/P1/统一引用、官方deepseek-flash、50步、8并发、400000字符及上下文限制全部不变。新工作上限102条episode、5100次Actor逻辑请求、22次语义调用；累计episode上限仍114，语义上限为26，包含原失败Editor。成功阶段不重跑，独立Test不参与。

恢复前4项专项离线测试通过：原失败可重现且未修补；Editor消息变化在请求前被拒绝；重复调用槽位被拒绝；原运行器完整复用12条Parent及3个语义阶段后，仅在同输入Editor新调用边界停止，期间0次环境或网络调用，原档案不变。

## 成本口径

恢复目录的原生 `report.json` 包括复制的旧轨迹和缓存调用，用于完整确定性核验。它的cost不是本次新增支出。`dispatch_ledger.json`区分reuse/execute；`completion.json`分别计算新增与累计usage，复用部分不重复计费，原失败成本保留一次。金额未查询账户账单，不能将未知记为免费。

## 运行结果与停止原因

恢复Editor完整返回并通过原契约，实际请求体SHA256与失败请求相同：`3d8f6702ec43b3d4fc2349409f15c5c7e5bb74833a76f5729f025789691ea045`。原失败响应13条映射，新响应4条完整段落映射；没有原输出修补。

| 轮次 | Parent | Candidate | 步数P/C | Gate | 发布结果 |
|---|---|---|---|---|---|
| R1（12项） | 12/12，100% | 12/12，100% | 171/83 | RETAIN | No Skill；新增1条Effect |
| R2（12项） | 10/12，83.33% | 7/12，58.33% | 208/320 | RETAIN | No Skill；替换为1条修订Effect |
| R3（12项） | 8/12，66.67% | 未构造／未执行 | 328/— | 未产生 | Fusion技术失败，未发布 |
| R4（12项） | 未执行 | 未执行 | — | 未产生 | 未开始 |
| R5（9项） | 未执行 | 未执行 | — | 未产生 | 未开始 |

R2有1项修复（train:0023）和4项回归（train:0014、0015、0017、0021），不能只按总分理解。逐任务来源和哈希见 `analysis/recovery_01_paired_facts.json`；包括R3 Parent全部12项及费用的最终汇总见 `analysis/recovery_01_final_results.json`。没有将正常退化当作技术故障、重采样或停止理由。

R3分类、Diagnosis均已通过；Fusion收到HTTP 200、`finish_reason=stop`，可见文本2952字符，但不是完整合法JSON。严格解析报 `Expecting ',' delimiter`，第1行第2953列、position=2952；生产解析报 `response: expected one valid JSON object`。服务端没有报告length截断，不能把这写成输出预算耗尽。该调用输入84290、输出12640 Token，其中推理11930；完整原始响应、usage和未解析文本已保留。没有补括号、提取片段充当合法输出或追加Fusion调用。

本次授权新增的R1 Editor已用一次，恢复协议不自动重试其他失败阶段，故在R3 Fusion保存停点。R3无有效最终Update、Editor、Candidate、Gate、Memory发布；R4/R5从未启动。不能把此停点标为RETAIN或no_change。

## Skill／Memory继承与D/S/C观察

R1与R2均按Gate RETAIN保留原No Skill；最后正式状态为 `recovery_01/rounds/r2/state.json`，round_index=2、Skill none、1条修订后Effect。R2轮初逐项等于R1发布状态，R3轮初逐项等于R2发布状态，Parent／Memory与来源state_sha256均核对通过。此运行真实展示了Memory的连续继承及修订；尚未展示ACCEPT后的正式Skill修订，因为两轮均未达到严格成功数提升。

R1 Fusion真实调用但Keep，changes/watch_changes为空，无历史Effect。R1 Candidate与Parent均12/12成功，171→83步是实测总步数差；实例选择、路径随机性和联合规则不同，不能单独认定为Skill因果收益。Memory产生5条Findings、3项open、1条Effect，包含12项全成功、无成功率提升、实例／路径差异与联合修改不可独立归因等限制。R1 Effect ID：`6b89f2dcac9dd7b77330e84dbe055d34346e41b9d860218cb92a019051ea415b:m1`。

R2 Fusion真实引用该Effect，在两项changes.basis中都保留其ID，将u1→u3、u2→u4进行replace，并迁移4个Watch。文本把依赖全局“未尝试／已检查”历史的搜索措辞，收窄到当前观察及最近两对历史的局部非重复／切换条件，同时保留可见目标优先、clean/cool后放置等协调要求。该变换涉及历史范围与局部策略／处理协调，不能从文字变化独立分离D、S、C各自作用。原始变化、理由和历史来源均保存在R2 `outputs/fusion.json`，未增加轴标签或修改模型输出。

这证明历史依据实际参与本次更新，不能据此将退化因果归于Memory，也不能证明历史预条件化优于无Memory。Fusion同时引用当前失败和成功轨迹；当前clean/cool处理过程的依据不能全部归给只覆盖灯具／放置任务的R1历史。

R2 Memory完整通过契约：7条Findings、1条替换delta、1项四字段限制退休。旧“没有失败案例”限制因本轮新增失败证据被退休，其他适用边界保留或在新limits中重述；生成的新Effect有6条最终限制，包含继承项。R2 Effect ID：`466852f48bab6f0372dd98e33977862c0bb6f45dced8963887ef07a00920291c:m1`。新认识保留了四项回归、一个修复、无inventory动作和未探索目的地等配对事实；其关于覆盖范围与成功关系的解释仍附有单次采样、不同编辑、实例选择与未独立归因等限制。R3 Fusion真实收到该修订Effect，257611字符消息通过容量检查，但输出未通过JSON解析，因此不能声称本轮形成了有效D/S/C决策。

## 语义抽查：支持、错误与未验证范围

- **直接支持的事实**：R1成功数相同、总步数减少；R2四项回归和一项修复，7/12对10/12；R2失败搜索轨迹未找到目标时，处理／放置规则没有相应决策机会。所有结论以实际配对来源为准，不能混用不同Candidate。
- **R1事实概括偏差**：f4把P11对cabinet和countertop的操作并称为打开；实际P11只打开cabinet 1/2，对countertop 1执行的是take。该偏差及已发布Memory未被人工修改。
- **R2共享输入解释偏差**：f4及Effect limits把T12（P1/C1）、T5（P8/C8）、T10（P9/C9）的共享步骤对象解释为“记录未区分两次执行”。实际三对均有独立Parent／Candidate run ID、不同Skill、不同实际请求体哈希和独立原始响应；它们动作序列相同，P1仅共享相同内容。相同内容可支持观测行为相同，不能支持执行身份不独立。确定性核查见 `analysis/recovery_01_p1_identity_audit.json`。这一错误解释进入了有效Memory限制，契约通过并未保证其正确；R3尚未完成后续修订。
- **未验证**：R3 Candidate表现、正式Skill被ACCEPT后的继承、五轮完成情况、后续Memory能否自行纠正上述解释，以及独立Test泛化。不能从两个RETAIN推断方法永远无效，也不能从R1步数差推断成功率提升。

## 资源与稳定性结算

本次恢复墙钟 **3162.95秒（约52分43秒）**；原运行761.90秒。两次执行墙钟相加3924.85秒（约65分25秒），不含两次运行之间的等待和离线准备。新增48条episode、939次Actor请求、10次语义请求，949次HTTP尝试；复用12条旧Parent和3次旧成功语义调用，不计入新增。累计真实60条episode、1110次Actor请求、14次语义请求、1124次HTTP尝试。实际累计低于冻结及恢复声明上限。

| 轮次／阶段（仅新增） | 输入Token | 输出Token | 其中推理Token | HTTP秒 |
|---|---:|---:|---:|---:|
| R1 main_editor | 24,073 | 5,676 | 4,549 | 26.62 |
| R1 post_gate_learning | 36,520 | 23,034 | 20,935 | 101.97 |
| R2 classification | 24,924 | 20,309 | 19,292 | 115.19 |
| R2 diagnosis | 30,939 | 8,720 | 7,722 | 52.95 |
| R2 fusion | 56,997 | 12,799 | 11,645 | 72.14 |
| R2 main_editor | 56,546 | 5,362 | 4,412 | 25.41 |
| R2 post_gate_learning | 80,254 | 43,999 | 40,842 | 200.29 |
| R3 classification | 30,534 | 11,818 | 10,642 | 66.42 |
| R3 diagnosis | 37,091 | 8,708 | 7,599 | 46.18 |
| R3 fusion | 84,290 | 12,640 | 11,930 | 70.07 |

新增输入 **1,218,565**、输出 **1,508,572**、总计 **2,727,137 Token**，其中推理 **1,408,835**。连同原运行累计输入 **1,380,702**、输出 **1,925,699**、总计 **3,306,401 Token**，其中推理 **1,806,508**（输出子集，不重复加总）。计数已排除复制／复用的旧记录重复收费。

共2次程序输出失败：首次R1 Editor摘录契约失败和本次R3 Fusion非法JSON；两次成本均保留。没有额外重试、HTTP传输失败或未知usage条目。失败R3 Fusion输入84290、输出12640，其中推理11930，HTTP70.07秒，均已计入上表及累计；原失败Editor输入24073、输出5710的成本计入原运行。未查询账户账单，金额仍未知，不能当作免费。

## 完整性核验与证据入口

`recovery_01_control/completion.json`和独立 `verification.json`确认：artifact_valid=true、campaign_complete=false、published_rounds=2、incomplete_rounds=1；恢复目录含13个语义调用记录，其中3个是明确复用，累计真实请求14次另含原失败Editor。原正式目录所有文件清单及哈希再次核对通过，`original_archive_unchanged=true`。档案有效不表示失败Fusion满足JSON契约，也不表示Memory语义完全正确。

- 归档与授权：`recovery_01_control/{authority,original_archive_manifest}.json`、`RECOVERY_PROTOCOL.md`、`archive/editor_attempt_01/`。
- 新工作与复用分离：`dispatch_ledger.json`；只读成本结算：`completion.json`；控制器及专项测试：`recover.py`、`test_recovery.py`、`offline_tests.log`。
- 原配置、全部任务、源码／Prompt／Schema：原实验23目录及恢复 `runtime_freeze.json`，参数和源码与原冻结逐项一致。
- 各轮证据：`recovery_01/rounds/r1`、`r2`、`r3`的原始轨迹、messages、calls、raw_outputs、Gate、实际diff、Editor映射、Findings、basis、Watch、Memory与状态；不存在的阶段未伪造产物。
- R3准确停点：`rounds/r3/calls/fusion.json`、响应body、`raw_outputs/fusion.txt`；严格JSON错误位置及原文哈希见 `analysis/recovery_01_final_results.json`。

## 结论边界

契约通过不等于行为解释正确；同请求恢复成功不能抹去首次失败，也不能据此宣称稳定遵从性。只有实际配对执行、有效编辑和对应Update才可进入Memory。连续实验不提供相对于无Memory方法的独立因果证据。

后续消融和独立Test应重点区分：历史Effect消费对局部搜索规则的作用、相同事实共享编码对模型执行身份解释的影响、长搜索与有限两对历史的交互、联合编辑中搜索和处理／放置的行为机会，以及原生成功数Gate与效率改善之间的差异。当前Selection已作为开发池参与优化，不能再作为独立选择集。此报告不授权新的调用、Probe或重试。

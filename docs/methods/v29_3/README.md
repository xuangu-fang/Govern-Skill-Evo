# v29.3：Diagnosis / Preconditioner 局部提示词修订

基于已完成训练和 Test 的 v29.2 实现。初次实现及两处措辞修订仅进行了离线验证。用户随后授权将 Editor 输出上限提高至 32,768 并启动独立训练；本次训练不自动启动 Test。离线手写响应只能验证接线、合同和恢复行为，不能证明提示词改善了模型判断或最终分数。

## 提示词设计

实际运行资源只有一份，位于源码目录：

- [Diagnosis](../../../src/skill_evolution/v29_3/prompts/diagnosis.md)：根据当前任务分析中的共同问题和修正方向组织 Update，保持同一修正的动作、条件、例外、优先级、保护边界和必要依赖完整；允许共享证据及必要配合，不按预期成败或去留拆分。限制附带的无依据行为改变，区分样本允许的形式与支持通用偏好的证据。保留简洁的迁移依据说明。
- [Preconditioner](../../../src/skill_evolution/v29_3/prompts/preconditioner.md)：区分整轮无 Knowledge、缺少具体 Update 关联和 Gate 决定；未归因不等于无关，也不构成某条 Update 获益或受损的归因证据。检查适用范围和规则协调，审查整条 Update 的附带改变；区分形式可接受、有限保持能力证据与偏好改善证据。
- [Diagnosis 差异](diagnosis.diff)、[Preconditioner 差异](preconditioner.diff)：相对于本次开始时的 v29.2 提示词。

初次实现对应四处主体修订和两处一致性调整：Diagnosis 的粒度、迁移依据与逐行书写说明；Preconditioner 的历史关联、Scope 与“未改善”比较前提。保留合理探索、必要联合动作和因果不确定性，不预设更多 WITHDRAW，不要求每种适用情形都有成功样本，不添加输出字段或强制检查清单。

随后按用户确认进一步精确化两处措辞：Diagnosis 允许各自有依据的多条 Update 同轮提出、在同一 Candidate 中评估，不再要求共同测试理由，也不因共同测试而合并目标；Preconditioner 将非空 `update_id` 理解为 Replay 已记录的归因判断，其证据强度仍须结合正文中的行为依据和限制评估。Replay 的关联要求、Gate 计数和 Memory 记录保持不变，沿用现有 v29.3 版本标识。

Diagnosis 的 reason 仍不会传给 Preconditioner。实施条件写入 Update text，相关直接执行证据仍通过 basis 传递。具体 Test 实体、答案及指定 Gate 结论不写入运行提示词。

2026-11-04 按确认方案完成五处原位替换：Diagnosis 的当前证据、行为增量、Update 组织标准三处，以及 Preconditioner 的当前提案理解、整条 KEEP 判断两处。修正不得顺带引入无依据的编码、范围或单位要求，但允许实现修正、解决冲突和保持有效行为所需的配合；通用 Skill 规则不得覆盖问题明确指定的输出要求。多种参考形式可接受不代表某种形式更优；实际执行保留原有成功结果可提供该任务上的有限保持能力证据，不作为另一份偏好改善证据。现有迁移、语义判断和历史 Memory 指导保持原样。

本次沿用 v29.3 方法及 Prompt 版本标识，仅更新两份运行提示词、对应设计说明、相对 v29.2 的差异文件及已有离线断言；其他模块、接口、配置和预算不变。既有训练/Test 产物仍对应修订前提示词，不改写其请求、哈希或结果，也不代表本次修订的验证结果。本次不启动真实训练或 Test。

本次验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python -m unittest discover -s tests/skill_evolution/v29_3 -t . -q`，36 项离线测试全部通过。修改前后对 89 个相关源码、配置、入口、文档和测试文件进行哈希比较，仅两份提示词、三份设计文档/差异文件及一份已有测试文件发生变化；其余 83 个文件一致。离线结果验证接线和合同，不证明模型判断或 Test 分数提高。

## 版本与运行接线

| 项目 | v29.3 |
| --- | --- |
| 方法版本 | `v29_3_campaign_v1` |
| Diagnosis Prompt | `v29_3_docvqa_diagnosis_v1` |
| Preconditioner Prompt | `v29_3_docvqa_preconditioner_v1` |
| 配置 | [v29_3_docvqa_optimization160.json](../../../experiments/configs/v29_3_docvqa_optimization160.json) |
| 独立入口 | [run_v29_3_campaign.py](../../../scripts/runs/run_v29_3_campaign.py) |

配置基线为 `v29_2_docvqa_optimization160_references_v4.json`。当前配置改变 `method.version`、`method.prompts.diagnosis`、`method.prompts.preconditioner`，以及用户后续授权的 `module_calls.editor.max_tokens`（16,384 → 32,768）。合同版本、阶段合同、执行输入视图、初始 Skill、空 Memory、160 题顺序与批次、Actor、评分、其他请求预算、超时、重试策略均不变。训练/Test 并发沿用 15/60。此次比较同时包含提示词修订与 Editor 预算提升，不属于严格的仅 Prompt 变化对照。

已核对完成训练的迁移 campaign：其配置与上述基线相同，五份当前 v29.2 提示词均与 R11 的实际请求原文一致。证据见 [completed_v29_2_baseline.json](../../../artifacts/verification/v29_3_runtime_20261103/completed_v29_2_baseline.json)。

Diagnosis 和 Preconditioner 包装原有调用，仅替换系统提示词及 Prompt 版本；用户消息、输入投影、校验和完成回调全部复用 v29.2。Grouping、Editor、Replay、Gate、Actor I/O 直接导入原实现。Memory 的决策生成和持久化格式沿用 v29.2；后续运行器修订改为直接读取已提交的 Knowledge，见下文。Preconditioner 不获得拆分或合并 Update ID 的权限。

v29.2 的阶段、训练和 Test 运行器采用模块级静态绑定。为不修改 v29.2，也不使用全局 monkeypatch，初始 v29.3 保留 `stages.py`、`evolution.py`、`evaluation.py` 的独立接线副本，仅调整 imports。后续获授权的轻量运行器修订修改了训练与 Test 的校验路径；`stages.py` 仍保持仅 imports 不同。副本原有 v29.2 文档字符串及 Test 格式标识作为沿用来源/合同保留，实际 method 和两个 Prompt 使用 v29.3 标识。

独立配置验证拒绝旧方法版本、混合 Prompt 和合同。阶段日志保存实际新提示词、Prompt 版本及源码哈希；恢复时验证冻结记录，不能将旧响应静默复用为 v29.3。实现清单覆盖 v29.3 文件和复用的 v29.2 源码与提示词。

## 离线验证

在仓库根目录运行，使用 DocVQA Python 环境：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_3_campaign.py --output artifacts/verification/v29_3_runtime_20261103 --baseline artifacts/verification/v29_3_runtime_20261103/v29_2_before.json
```

验证器禁止 socket 连接和子进程，执行 v29、v29.1、v29.2、v29.3 离线测试，并对完整冻结数据集执行 CLI `--validate-only`。该预检查不读取凭据、不创建 campaign，也不调用训练或 Test。所有合成训练/Test 流程仅使用临时目录、小型合成数据与手写响应。

v29.3 专项覆盖：仅两份系统提示词变化；输入与完成结果同构；KEEP/REPLACE/WITHDRAW 编译不变；未归因历史完整传递；独立 Update 的选择；实际请求及日志版本；双向跨版本恢复拒绝；Memory 提交后无传输恢复；Selected Skill 导出与合成 Test 文件一致；来源清单完整；运行器仅 imports 不同。

保护清单保存本次修改前 64 个 v29.2 文件的 SHA-256，覆盖源代码、提示词、测试、配置、入口、方法文档和完成训练/Test 的顶层文件。验证器报告任何哈希变化；不把未纳入清单的文件声称为已完成全量审计。

初次实现的结果见 [validation.json](../../../artifacts/verification/v29_3_runtime_20261103/validation.json) 和 [unittest.log](../../../artifacts/verification/v29_3_runtime_20261103/unittest.log)。该离线验收不创建正式 v29.3 campaign；后续授权的训练使用独立目录，不继承或改写 v29.2 的训练历史、最终 Skill 或 Test 结果。

2026-11-03 初次实现离线验收（上述两处后续措辞调整前）：473 项全部通过（v29 108、v29.1 27、v29.2 324、v29.3 14），无失败、错误或跳过；完整数据集的 CLI 只读预检查通过。64 个 v29.2 保护文件哈希一致，网络/子进程尝试及真实模型请求均为 0。

两处措辞调整后的专项验证及当前提示词哈希另存于 [最新验证报告](../../../artifacts/verification/v29_3_prompt_wording_20261103/validation.json)，不覆盖首次验收结果。

## Editor 预算调整与正式训练

用户授权将 Editor 的 `max_tokens` 提高至 32,768；其余调用参数不变。调整后的 14 项专项离线测试及完整数据集只读预检查均通过，见 [启动前验证](../../../artifacts/verification/v29_3_editor32768_20261103/validation.json)。

2026-11-03 22:35:03（Asia/Shanghai）已启动独立训练 [v29_3_docvqa160_epoch1_20261103_223457](../../../experiments/campaigns/v29_3_docvqa160_epoch1_20261103_223457/)，从初始 Skill 和空 Memory 开始，160 题、11 轮，Actor 并发 15。沿用 v29.2 的 `MallocMediumZone=0` 本机运行环境设置，既有请求重试预算不变，不自动重新启动进程、不自动运行 Test。动态状态及退出码见 [status.json](../../../experiments/automations/v29_3_docvqa160_epoch1_20261103_223457/status.json)，输出见 [training.log](../../../experiments/automations/v29_3_docvqa160_epoch1_20261103_223457/training.log)。


## 轻量运行器修订：v29_3_light_runtime_v1

用户授权直接删除 v29.3 的深度审计，而非保留为独立入口。本修订只涉及本版本的运行和持久化读取路径，不改变五个模块提示词、模型请求、逐 Update Gate 规则、Knowledge 字段、Memory 提交格式、Actor 或评分器。

删除的检查：

- 启动、恢复、最终导出与 Test 前后不再重放已发布训练轮次；不再提供 `_audit_published` 路径。
- Memory 加载直接校验内容寻址的提交链并构造已提交 Knowledge，不读取历史 `sources` 的完整模型证据、不重新运行历史 Gate。
- 每轮只缓存当前已完成批次；不保留文件或图片字节快照，不执行结束时的全文件重读比较。进入下一轮释放上一轮注册的执行记录。
- CLI 不再在 `run_test()` 前额外调用一次 `prepare_test()`。Test 前后仍做轻量身份检查。

保留的检查：

- 配置、方法版本与提示词身份；当前轮任务、实际 Skill、Parent/Candidate 配对；结构化输出与引用约束；补丁应用和逐 Update G/L 计算。
- Memory 提交的规范 JSON、内容摘要、序号与前驱关系；当前提议的 Gate 验证；写锁、原子 HEAD 发布、陈旧 HEAD 拒绝和幂等提交。
- 游标与最后已发布结果、Selected 文本和已提交 Memory 一致；Memory 先提交而游标尚未发布的单轮恢复。
- Test 集隔离、任务顺序、Actor 配置与导出 Skill 一致；原请求日志和六次预算、中断恢复、不重复已完成请求；完整覆盖后才发布汇总。

已完成训练的 `implementation.json` 继续作为当时运行来源记录保留，不改写成新运行器的源码哈希，也不再要求完成后的 Test 使用字节完全相同的运行器源码。原方法提示词仍须一致；新训练仍记录当前源码来源，未完成阶段仍须匹配其请求身份，不能借运行器升级重置重试额度。Test 的 `evaluation.json` 和 `summary.json` 增加运行器版本元数据 `runtime_version`；模型接口及训练配置没有新字段。

边界：普通 Test/恢复不再检出所有历史 HTTP 或源文件的事后修改；它信任已经提交的 Knowledge 和检查点，保留当前执行与提交完整性检查。这是明确的保障范围调整，不是捕获完整审计异常后忽略错误。旧 v29/v29.1/v29.2 实现不变。

离线验证与真实产物启动检查保存于 `artifacts/verification/v29_3_light_runtime_20261103/`。原 Test 启动失败记录保留；恢复使用同一 R11 Selected、同一 374 题及 Actor 配置，不重新训练。

本次验收：v29.3 36 项、未修改的 v29.2 324 项，共 360 项离线测试通过。真实训练产物的轻量 Test 准备检查约 0.02 秒；最终 Skill SHA-256 仍为 `caa202d587c72aa7205fc511c74de9a139f742c863236f1e7f668ccb5fe30182`。2026-11-03 23:52:26（Asia/Shanghai）恢复 Test，已进入真实逐题执行；动态状态见 `experiments/automations/v29_3_docvqa_test374_20261103_light_runtime/status.json`，原失败记录未覆盖。

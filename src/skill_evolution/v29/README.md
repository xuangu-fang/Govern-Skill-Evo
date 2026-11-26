# v29 DocVQA 第一至第三阶段实现

2026-11-02 试跑后确认：后续运行采用 Actor 32768、Grouping/Editor 16384、Diagnosis/Preconditioner/Replay 32768；超时沿用 300 秒。正式配置为 `experiments/configs/v29_docvqa_optimization160.json`。首批试跑已完成；按用户要求，其临时配置、执行归档及专用验收输出已删除。


已实现本地数据读取、Actor 图文请求与持久化执行、答案抽取、hard/ANLS、同批 Gate 比较及完整文本证据投影；第二阶段接入五模块输入构造与输出验收、Plan/补丁处理、Replay 和 Memory；第三阶段接入训练主循环、方法调用调度、恢复及 Parent/Memory 联合发布。六项输出额度和超时已确认；正式训练及最终 Test 入口已接入，均复用现有执行与恢复逻辑。历史离线验收记录与真实运行状态分开保存。

设计依据：[Actor 执行与评分协议](../../../docs/methods/v29/actor_execution_scoring_draft_20261102/DESIGN.md)、[五模块设计](../../../docs/methods/v29/five_module_draft_20261102/DESIGN.md)。当前实现状态以本文件及离线验收结果为准，原设计稿保留其设计阶段说明。

## 已实现的接口

| 文件 | 职责 |
|---|---|
| [protocol.py](benchmarks/docvqa/protocol.py) | 已确认 Actor 参数、System/User 模板、初始 Skill、原图 data URI 和文本投影 |
| [dataset.py](benchmarks/docvqa/dataset.py) | 读取已有固定 release；保留 107/53/374 划分和原 Train 后接 Validation 的顺序；生成 10×15＋1×10 调度列表 |
| [scoring.py](benchmarks/docvqa/scoring.py) | 直接使用本地 SkillAdam 的抽取和 ANLS；hard=ANLS≥0.999；完整同批 hard 成功数严格增加才接受 |
| [actor.py](benchmarks/docvqa/actor.py) | 显式传入 transport；记录请求与响应、六次总尝试、失败分类、完成结果恢复 |
| [adapter.py](benchmarks/docvqa/adapter.py) | 单批并发执行、按输入顺序返回、批次记录恢复、只读批次检查与 Gate；不会自行启动后续批次 |
| [facts.py](benchmarks/docvqa/facts.py) | 从完成的训练记录产生 P/Q 文本执行事实，拒绝 Test 进入优化证据 |
| [method.py](method.py) | 将纯合同绑定到显式完成批次；注册/重读执行来源；Memory 提交与只读恢复 |
| [memory_operation.py](memory_operation.py) | 单次 Memory 操作内复用已校验的历史、批次和文本投影；退出即丢弃 |
| [modules.py](modules.py) | 五模块 Call：构造模型消息、验收外部提供的 JSON 输出、传递阶段状态；自身不生成响应 |
| [evidence.py](benchmarks/docvqa/evidence.py) | 输入边界、直接引用选择、实际 Candidate 与同题 P/Q 核对、Replay 审计束 |
| [prompting.py](benchmarks/docvqa/prompting.py) | 原样安装已确认的五份英文 Prompt，核对共同 Actor 协议 |
| [replay_input_view.py](benchmarks/docvqa/replay_input_view.py) | 无损共享完整 initial 消息、去掉同一请求的重复展示 |
| [replay.py](replay.py) | 多 Knowledge 输出合同与 Knowledge Only 历史引用范围 |
| [config.py](config.py) | 固定 160 题单轮遍历、原始初始 Skill、六次方法尝试；五模块预算/超时默认 null |
| [campaign.py](campaign.py) | 绑定数据、Actor 和 campaign 接口；支持不发送请求的完整 Actor 批次摘要恢复 |
| [stages.py](stages.py)、[output_feedback.py](output_feedback.py) | 方法请求持久化、技术/length/输出合同错误的六次共享尝试、最近一次输出错误反馈和恢复 |
| [evolution.py](evolution.py) | 串行主循环、no-change/语义停止、Replay 后发布、断点续跑及只读最终 Parent 检查 |

`DocVQADataset()` 默认读取 `data/docvqa/releases/539088ef8a8ada01ac8e2e6d4e372586748a265e/`，不下载、不写入、不重新划分或排序。`case(task_id)` 的 payload 只包含 question/image_path，reference 单独保存；图片路径相对 release 根目录解析。离线验收使用相同批次形状的合成题目；真实运行结果位于独立 campaign/evaluation 目录。

`protocol.initial_skill()` 返回安装的 SkillOpt 原始初始 Skill。模板文件见 [context](benchmarks/docvqa/context/)；System 保留末尾换行，Skill 按上游规则 strip 后插入，问题不 strip，image_detail=auto 时省略 detail 字段。图片编码使用原文件字节。

评分直接导入 `external/SkillAdam` 的 DocVQA evaluation 函数；有效 stop 只评分一次，不因答错、空串或缺少标签重试。length 响应即使含答案也不评分。原始响应及隐藏字段留在执行记录中，优化事实只保留普通 content。

## 执行与恢复边界

`actor.execute(case, skill, directory, transport)` 显式执行单题；`actor.read_completed(...)` 只读恢复；`actor.validate_pending(...)` 检查未完成记录，不发送请求。真实 `ChatTransport(api_key)` 只接受显式凭据，不自动读取环境变量，HTTP 层不做隐式重试。

每题目录保存 `signature.json`、`attempts/001..006/` 和最终 `result.json`。请求开始前写入开始记录；已开始但结果未知的尝试占用原次数。已保存有效响应可恢复评分，不再请求；尚未开始的准备槽位可继续使用。恢复不重置六次额度。拒绝/工具调用等终止错误不会通过恢复重新采样，执行未完成时不补零分。

单批接口为 `DocVQAActorAdapter.actor_batch(tasks, skill_file, directory, config, final=False)`。config 包含 split/role：训练使用 train 与 parent/candidate，评估使用 test 与 evaluation 且 final=True。训练/Test workers 上限为 60，实际单批并发不超过题数，返回结果保持 tasks 顺序。该接口只有显式调用才执行；正式入口为 `scripts/runs/run_v29_campaign.py`，训练 workers=15、Test workers=60。

批次目录保存 `batch.json`、按任务顺序编号的 Actor 子目录、每题 `trajectory.json` 和 `records.json`。恢复先检查所有已有任务再创建线程；已有 result 可补齐 trajectory 和批次汇总，不重复模型请求。已完成标记所需的响应丢失时停止，不把损坏记录当作新题重跑。恢复检查直接比较已保存的任务、Skill、请求及响应。

`adapter.read_batch(directory)` 只读核对完成记录。`adapter.build_gate(parent_directory, candidate_directory)` 从两个完整批次检查角色、相同任务及相同 question/image，再比较 hard；发布由第三阶段 campaign 统一处理。

`facts.build_facts(records, adapter=..., directory=...)` 要求记录与显式批次目录一致；Parent 批产生 P 引用，Candidate 批产生 Q 引用。返回束中的 facts.parent 表示这一批实际执行的 Skill；Candidate 束用于后续配对，不能当作 Grouping/Diagnosis 的 Parent 输入。每条执行的 system 均保留自己的实际 Skill。`project_execution(...)` 提供单条纯投影检查，不替代批次来源检查。

图片块只在投影副本中换成占位文字，原始 Actor 请求不变。问题、普通响应、多参考答案和实际 Skill 不摘要、不截断。重试只形成一个最终有效模型回合，api_requests 保留请求次数；隐藏推理、usage、失败响应和图片编码不进入优化事实。

## 五模块、Plan 和补丁

`DocVQAMethod(actor_adapter, archives=[...])` 显式绑定已完成训练批次目录。所有合同操作在 `with method.using():` 内执行；后续 Candidate 批次完成后，先 `method.register_archive(directory)` 再用于 Replay。历史 Memory 所引用的批次也必须注册；未注册来源和 Test 记录不能成为优化证据。来源检查只读重建完成记录，不调用 transport。

调用顺序为 `grouping_call(records, round_id)` → `diagnosis_call(grouped)` → `preconditioner_call(diagnosed, active_memory)` → `editor_call(prepared)`。返回的 Call 包含 `name/input/messages/complete`。**只有 `messages` 是模型输入；`input` 保存完整审计状态，不应直接发送给模型。** `complete(parsed_json)` 或 `complete_text(ordinary_content)` 验收调用方提供的输出；没有隐式模型请求、输出修复或新增模块。有效输入和结果均复制后传递。

| 模块 | 实际 user 输入 |
|---|---|
| Grouping | Parent Skill、完整 Parent 批执行文本 |
| Diagnosis | Parent Skill、完整 Parent 批执行文本、Grouping |
| Preconditioner | 独立完整 Parent Skill、Original Plan、Plan 直接引用的整条 Parent 执行、Knowledge Only Memory |
| Editor | Parent Skill、Effective Plan |
| Replay | Parent Skill、实际 diff、去掉 basis 的 Effective Plan、所有成对 P/Q 文本、Knowledge Only Memory |

Preconditioner 的直接引用检查覆盖 Plan 的 basis、goal、Update text 和 Check question；Grouping ID 不展开成额外执行。内部保留 Grouping 只用于既有合同核对，不发送给 Preconditioner。Original Plan 沿用既有直接执行依据要求。History 只允许引用输入 Knowledge 已列出的精确证据，不因完整源执行存在而扩展到相邻回合。

Plan 编译、D/S/C、显式命名空间引用及无编号 `@@` 补丁直接复用 v27 的既有合同，与 v28 保持一致。KEEP、局部替换、撤回、Checks 继承/替换均保持原规则，没有新增 Update 数量限制。Diagnosis `no_change` 停止后续修改；全部撤回必须明确清空 Checks。Editor `patch=null` 表示 needs_revision，空串表示 no_change；两者均无 Candidate，不进入 Replay。非法 JSON、引用或补丁报错，不伪装成正常 no_change。Editor 精确应用补丁后生成实际 diff，Replay 以该实际结果为准。

## Replay 与 Memory

Grouping 请求构造与完整 Replay bundle 构造也分别进入现有 MemoryOperation：`grouping_call()` 将事实构造和消息生成放在同一局部作用域；`build_replay_from_editor()` 在公开入口覆盖 Parent/Candidate 事实、配对及 payload 校验。两批各两题、无历史的合成例中，Grouping 的完整批次验证由 8 次降为 1 次，完整 bundle 构造由 16 次降为 2 次，仍分别验证两条和四条 Actor 原始归档。这是验证次数的减少，不代表同倍率的实际加速。

完整 bundle 构造、`replay_call()` 消息生成、`complete()` 输出校验仍是独立的本地步骤；独立调用结束即释放作用域，嵌套调用复用外层作用域，不跨模型等待或跨轮保存结果。当前批次归档和传入记录校验保留；作用域退出时只释放缓存，不再扫描历史文件或图片；Prompt、评分、Plan/补丁及 Memory 合同不变。补充验收见 [validation.json](../../../artifacts/verification/v29_evidence_entry_reuse_20261102/validation.json)。

Candidate 完成并注册后，调用 `evidence.build_replay_from_editor(edited, editor_directory, parent_records, candidate_records, memory=active_memory)` 构造审计束，再 `modules.replay_call(bundle)`。核对 Parent/Candidate 的实际 Skill、相同题目/图片/Actor 条件、完整批次和不同执行记录；普通响应和评分均来自保存的 Actor 结果。编辑目录是审计定位信息，实际证据来自传入的已验收 Editor 状态和完成批次。

模型视图无损共享重复 initial 消息，并移除与 initial 完全一致的 request_messages。`outcome.answer.raw_content` 也仅在与同 run 的普通 `assistant.content` 完全相同后省略；完整响应在该轮保留一次，预测答案、参考答案和评分不变。`restore_model_input()` 供离线检查两处省略均可精确还原；实际发送不增加解码步骤。`Call.input` 和 Memory 审计束仍是完整原文。Replay Prompt 为 `v29_docvqa_replay_v2`，输入视图为 `v29_docvqa_pairs_shared_initial_v2`。Gate 决策不进入 Replay 输入，也不是规则有效性的证据。Prompt 保留图片不可见、Actor 转述归因和因果解释边界；程序核对结构、引用及执行结果，不声称自动验证自然语言因果判断。

普通 `replay_call()` 构造消息及其 `complete()` 校验输出，现在分别自动进入现有 MemoryOperation，仅复用各自本地步骤中的批次验证结果。作用域不会保存在 Call 中，也不跨越模型请求等待；每次独立 complete 都重新读取归档。外层已有同一适配器的作用域时继续复用，内层不关闭外层。退出时只释放缓存，异常或中断也释放自建作用域。两批各两题、无历史来源的合成例中，两步各从 16 次完整批次验证降为 2 次；已提交历史只读取保存的 Knowledge 与引用结构，不重新打开历史 Actor 批次。Prompt、请求正文、输出合同和归档格式不变。

`method.commit_memory(directory, context_id=..., context=bundle, result=replay_result)` 使用既有不可变 archive + 原子 Active 索引合同；其中 `replay_result` 取自 `replay_call.complete(parsed)['replay']`。每条 Knowledge 自带 text/evidence；每个 MemoryEntry 的证据并集必须同时覆盖实际编辑和执行。修订替换整个 Entry，保留内容需在新 Entry 中明确带回；旧档案保留。ACCEPT、RETAIN 都能提交 Knowledge；空 entries 也可记录已完成回放。

`method.load_memory(directory)` 只读核验已提交条目的身份、Active 链、修订关系和引用结构，不重跑历史 Replay，也不重新验证历史 Actor 来源。相同 context/result 的重复提交幂等；未完成的 archive 不进入 Active；中断恢复要求同一提交完成后再继续。第三阶段通过官方 `state.json` 联合选择 Parent 与已准备完整的 Memory。

一次 Memory 提交在同一锁内加载已提交状态并验证当前提案；仅校验本轮实际 Parent/Candidate、Replay 输出与引用权限。当前批次和投影可在局部作用域内复用，退出即释放。提交仍保留幂等检查、未提交记录恢复、Active 指针检查和原子发布，不再保存或比较历史文件、目录与图片字节快照。已有 Memory 存储格式和整条 Entry 修订语义不变。

当前六项输出额度已确认，见本文顶部及[后续运行配置](../../../experiments/configs/v29_docvqa_optimization160.json)。`pending_calls()` 继续提供未填写模板；实际执行应显式传入已确认配置。

## 训练主循环与发布

`CampaignAdapter(DocVQAActorAdapter(dataset, transport))` 绑定显式依赖，所有编排在 `with adapter.using():` 内进行。`campaign_config(adapter)` 生成待配置版本：五模块 `max_tokens` 和 `timeout_seconds` 均为 `None`；输入字符/字节限额沿用既有 4,000,000/6,000,000，属于完整输入保护。导入、构造配置和 `initialize()` 不请求模型。任何未确定的五模块预算都会在新一轮 Actor 执行之前阻止启动，不自动采用测试值。

`evolution.run_campaign(..., generate=...)` 按冻结批次顺序串行推进；`run_round()` 限制为一轮，`resume_round()` 明确恢复，`final_parent()` 只读重建已发布链并要求完整结束。没有隐式 transport、凭据读取或自动 Test。独立 Test 调度不属于本阶段。

每批顺序为 Parent → Grouping → Diagnosis → Preconditioner → Editor → Candidate → 配对/Gate → Replay → Memory → 官方状态发布。三种合法无更新保留 Parent/Memory 并继续；Editor null 停止且不允许通过重新采样绕过。ACCEPT/RETAIN 都先完成 Replay 与 Memory；ACCEPT 选择 Candidate，RETAIN 保留 Parent。Replay/Memory 失败不会提前切换官方 Parent、Memory 或轮次游标。

正常 Replay 后发布保留目标 Memory 目录准备、当前提交、view 写入和官方 state 更新。准备目标仍保存独立归档副本，以兼容原存储格式；最后原子替换 state.json，记录 next_round、parent、active_memory。恢复仅检查当前游标、最近发布结果、当前 Skill 和 Active 状态，随后续跑未完成轮次；已发布轮次不重新执行。已有 final_skill.md 时还需与当前 Selected Skill 一致。

完整接口、恢复边界及离线配置说明见[第三阶段实现说明](../../../docs/methods/v29/CAMPAIGN_IMPLEMENTATION.md)。

## 正式训练与最终 Test 入口

入口为 [run_v29_campaign.py](../../../scripts/runs/run_v29_campaign.py)。`train` 使用已确认的 [正式配置](../../../experiments/configs/v29_docvqa_optimization160.json)，执行 160 题单遍 11 批；结束后用 `final_parent()` 只读核验全部发布，导出 `final_skill.md` 和 `training_summary.json`，不会自动启动 Test。`test` 必须读取已完成训练的最终 Parent，使用固定 374 题保留集和 evaluation 角色，输出完整 `summary.json`。未完成评估不写汇总、不补零分；Test 不更新 Skill 或 Memory。

两个入口均支持 `--resume`，复用已完成响应且不重置六次尝试。`--validate-only` 只检查配置，不读取凭据、不建立 transport、不初始化运行目录。`test --validate-only` 不是最终 Parent 审计，实际 Test 执行仍要求训练完整结束。

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/runs/run_v29_campaign.py train experiments/campaigns/RUN_NAME --validate-only
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python -u scripts/runs/run_v29_campaign.py train experiments/campaigns/RUN_NAME
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python -u scripts/runs/run_v29_campaign.py test experiments/campaigns/RUN_NAME --output experiments/evaluations/RUN_NAME
```

统一离线验收已纳入 `test_module_validation_reuse` 与正式入口检查，报告从正式配置读取额度和超时，不再硬编码“预算待定/尚待试跑”。本次验收见 [validation.json](../../../artifacts/verification/v29_formal_entrypoints_20261102/validation.json)。

## 离线验收

使用现有 DocVQA conda 环境，从项目根目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_actor.py --output artifacts/verification/v29_actor_phase1_20261102
```

验收入口将项目及本地 `external/SkillAdam` 加入导入路径，并阻断网络连接和子进程。直接导入组件时应设置 `PYTHONPATH=.:external/SkillAdam`。不需要 API key。

模拟请求覆盖 length/技术失败共用六次额度、终止错误、请求中断、HTTP 原响应恢复、空串与格式回退、单批恢复、同批 Gate 和 Test 隔离；评分使用已审阅的 15 组案例与 3 组 Gate 案例。长普通响应和全部参考答案的完整投影另有检查。

真实数据只做静态读取、消息构造和图片解码检查：534 题、160/374 划分、11 批及 439 张不同图片。没有对真实题目生成响应或计算模型成绩。

2026-11-02 离线验收通过：25 项测试无失败，534 题静态消息构造和 439 张图片解码通过，网络/模型请求数均为 0。结果见 [validation.json](../../../artifacts/verification/v29_actor_phase1_20261102/validation.json)和 [unittest.log](../../../artifacts/verification/v29_actor_phase1_20261102/unittest.log)。通过离线验收不代表已验证服务端图像能力、实际吞吐或模型效果。

第二阶段验收（包含第一阶段全部回归）使用：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_method.py --output artifacts/verification/v29_method_phase2_20261102
```

新增验收覆盖六组合成示例、五份 Prompt 原文一致性、模块输入边界、Plan 与精确补丁、语义停止、历史引用范围、Replay 配对、整条 Memory 修订、ACCEPT/RETAIN 积累、空提交、重复提交、中断恢复及冷启动读取。全部响应由本地合成 fixture 提供，真实 534 题仍只做静态读取；合成 Test 标记用于隔离检查，不执行真实 Test。

2026-11-02 第二阶段验收通过：45 项测试（第一阶段 25 项回归＋第二阶段 20 项），0 失败、0 错误；534 题、439 张图片静态检查通过，网络/模型请求为 0。历史结果见 [validation.json](../../../artifacts/verification/v29_method_phase2_20261102/validation.json)及 [unittest.log](../../../artifacts/verification/v29_method_phase2_20261102/unittest.log)。之后继续接入第三阶段，旧版本源码保持不变。

同日完成 Replay 响应去重与 Memory 提交复用修复：当时验收 **55 项测试通过**，含上述 45 项回归及 10 项新增检查。相同的“已有一轮历史、每批两题”合成提交中，底层历史链遍历由此前观察的 3 次降为 1 次，完整批次校验由 80 次降为 4 次；四个涉及批次各校验一次，共八条 Actor 完成记录。归档结果与继承提交器逐字节一致；响应视图可以无损还原。详见[修复说明](../../../docs/methods/v29/MEMORY_REPLAY_FIX_20261102.md)和[修复验收报告](../../../artifacts/verification/v29_memory_replay_fix_20261102/validation.json)。

第三阶段验收 **84 项全部通过**：前述 55 项回归＋29 项方法阶段/完整合成 campaign 检查，0 失败、0 错误，网络及模型请求数为 0。正常完整发布中的历史链遍历仍为 1 次。报告见 [validation.json](../../../artifacts/verification/v29_campaign_phase3_20261102/validation.json)和 [unittest.log](../../../artifacts/verification/v29_campaign_phase3_20261102/unittest.log)。复现命令：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_campaign.py --output artifacts/verification/v29_campaign_phase3_20261102
```

普通 Replay 验证复用补充验收：**90 项全部通过**（此前 84 项＋6 项新增检查），网络及模型请求数为 0。两批无历史场景的请求构造、输出校验均为 2 次完整批次验证；有历史、异常退出、两步之间归档变化和嵌套复用均已覆盖。最新结果见 [validation.json](../../../artifacts/verification/v29_replay_validation_reuse_20261102/validation.json)及 [unittest.log](../../../artifacts/verification/v29_replay_validation_reuse_20261102/unittest.log)。复现使用第三阶段验收命令，并将输出目录改为 `artifacts/verification/v29_replay_validation_reuse_20261102`。

## 上游来源

System 模板与初始 Skill 来自 SkillOpt DocVQA；SkillAdam 提供同源模板及评分函数。许可证随本目录保留，见 [SkillOpt](benchmarks/docvqa/LICENSE.SkillOpt)和 [SkillAdam](benchmarks/docvqa/LICENSE.SkillAdam)。响应解析、usage 提取和 HTTP 错误分类直接复用项目已有 v27 实现。

## 2026-11-04 运行检查简化

v29 和 v29.1 共用上述轻量执行方式，v29.2 的独立引擎同步采用相同边界。全历史逐轮重放和文件/图片字节快照审计已删除，不提供独立深度审计入口。历史记录继续保留，但正常运行不承诺发现任意历史源文件的事后改动。

Prompt、Actor 配置、Gate 规则、Knowledge 内容与引用权限、Memory 格式、重试预算均未修改；已完成训练与 Test 不重跑、不改写。v29.2 额外取消 CLI 与 run_test 重复的启动准备，以及准备阶段提前构造所有图片请求；读取当前配置、完成状态、最终 Skill 和测试集边界的检查仍保留。其 implementation.json 中的旧源码哈希作为历史来源记录保留，当前运行仍匹配冻结配置和 Prompt。

离线回归及三个真实完成归档的只读预检查记录见 [verification](../../../artifacts/verification/v29_family_light_runtime_20261103/validation.json)。未调用真实模型。

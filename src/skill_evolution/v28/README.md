# v28 SearchQA：Actor、五模块与执行证据

状态：2026-11-01 已完成 Actor Prompt、评分、六次共享尝试、归档恢复和完整 Gate 身份校验，并通过合成场景离线验证。五模块 Prompt、输入投影、输出合同、Replay 与 Memory 已接入；现已接入完整 campaign 调度、方法阶段重试恢复和独立 Test 入口。未启动训练、Test 或真实模型调用。

## 已实现的接口

- `benchmarks/searchqa/protocol.py`：`build_messages(question=..., context=..., skill=...)` 构造单轮消息；`messages_for_row(row, skill)` 先检查任务和参考答案字段，再仅投影 question/context/skill。任务文本不 strip、不截断；Skill 按 SkillAdam 规则 strip 后注入 Task Format 与 Answer Format 之间。
- `context/actor_system.md`、`actor_user.md`：落实此前 Actor 草案，使用文字描述名为 `answer` 的 XML-style element；不引入 LMB 的选项标签或元素外禁止文字的约束。此写法尚无真实模型收益验证。
- `scoring.py:score`：直接调用冻结来源的 SkillAdam SearchQA 原生抽取、EM 和 F1 函数，输出答案审计字段及 `em/f1`。先移除冠词、再按 Unicode 正则移除标点；多参考答案分别取最佳 EM/F1；F1 可为连续值。
- `scoring.py:score_response`：直接复用 v27 的 API 响应校验，只读取正常 stop 的普通 `content`；不采用 `answer` 覆盖字段或隐藏推理。length、结构错误、拒绝和工具调用继续抛出 v27 的 `RequestFailure`，不补零分。
- `scoring.py:compare_scores`：对完整、唯一、同 ID 集合的逐题评分投影做纯比较。仅 Candidate 的 EM=1 成功数严格更多时 ACCEPT。F1 只做记录有效性检查，不进入决策公式。
- `scoring.py:summarize_scores`：在预期题目全部完成后，返回成功数、平均 EM、平均逐题最佳 F1；缺题、重复题或非法评分直接报错。

`compare_scores` 是低层纯函数。正式调用路径为下面的 `build_gate`，必须提供原始批次目录，由它完成身份与归档校验后再比较成功数。campaign 在 Replay 和 Memory 校验完成后原子发布决策。

## Actor 与归档接口

- `dataset.py:SearchQADataset`：只读取 `data/searchqa/` 的固定锁与优化视图，验证所有锁定文件；原 Train/Val 合并为有效 train，Test 保持隔离。对外返回的 case 将参考答案与 Actor payload 分开。
- `actor.py:ChatTransport`：继承 v27 的 HTTP 参数及错误分类；SDK 重试为 0，显式传入凭据，无环境变量自动读取。
- `actor.py:execute/read_completed/validate_pending`：沿用 v27 的有序尝试目录、请求开始标记、失败收据、HTTP 原文与解码响应交叉验证。SearchQA 的评分调用与执行签名已适配；新增任务目录锁，避免同一任务重复并发执行。
- `adapter.py:SearchQAActorAdapter.actor_batch`：训练/Test 的 Actor 并发固定为 15/15；先检查整个批次的已完成和待恢复归档，再创建任何工作线程。按冻结任务顺序收集结果。
- `adapter.py:SearchQAActorAdapter.build_gate`：要求 Parent/Candidate 原始批次目录、完整记录、冻结任务列表和各自 Skill。校验下表所有身份及原始响应后，仅用 EM 成功数作决策。不发送请求，不执行恢复，也不修改归档。

| 检查对象 | 必须匹配的内容 |
|---|---|
| 数据与任务 | 本地数据锁、优化视图、全部文件哈希、题目正文、参考答案、来源及有效 split |
| 实现与 Prompt | 固定来源哈希、实际加载的 SkillAdam scorer/parser 文件、v28 代码、Prompt 模板及 profile |
| 模型与 Skill | 固定 DeepSeek 参数、完整消息、每一侧的实际 Skill 原文 |
| 执行身份 | 批次 ID、任务 ID、唯一 run ID、Parent/Candidate 角色、完整且不重复的批次顺序 |
| 原始归档 | 请求、开始标记、全部失败收据、响应原文、终止原因、尝试计数及 usage |
| 评分 | 从普通 content 重新抽取答案并评分，与 result、trajectory 和批次 records 一致 |

首次、length、可重试技术错误共用六次总额度；每次重试沿用原请求，等待秒数为 1×尝试序号。正常 stop 不因答错、空串或格式问题重试。耗尽后无完成结果、不补零分，恢复不重置额度。已开始但结果未知的请求占用原尝试；只准备请求、尚未写开始标记的目录可继续使用同一槽位。

已保存的正常响应可恢复评分而不重发。完成记录缺少必要证据、原文和解码副本矛盾，或任何身份不匹配，均停止。沿用 v27 的冗余归档边界：解码 JSON 缺失但 HTTP 原文与状态完整时，可从原文验证；result 完整且 trajectory/批次汇总尚未写入时，可本地补全这些下游记录。

失败尝试与隐藏推理只在原始响应审计目录保留；完成执行记录仅含最终普通 content、其派生答案和评分，以及尝试数/usage。参考答案保存在隔离的签名中，不进入 Actor 消息。

## 来源与运行方式

Prompt 改写自 SkillAdam（MIT）；许可证见 `benchmarks/searchqa/LICENSE.SkillAdam`。`source_provenance.json` 与 `v27_contract_sources.json` 仅保留历史来源记录，不参与运行校验。源码与 Prompt 不做哈希冻结；执行签名保留行为版本、数据、模型及实际请求身份，数据与归档一致性检查继续生效。

代码依赖本地 `external/SkillAdam` 的评分函数，数据仅从 `data/searchqa/` 读取。环境验收使用的 `benchmarks/searchqa/reference/evaluator.py` 是另一个 SkillOpt 参考实现，未被覆盖，也不作为本组件 scorer。

在项目根目录执行：

```sh
conda run -n SearchQA python scripts/verification/verify_v28_actor_runtime.py --output artifacts/verification/v28_actor_runtime_20261101
```

该命令阻断网络连接和子进程，运行 Prompt/评分、重试、恢复、故障注入及完整 Gate 测试；核对全部 2000 条数据的输入投影、13 个冻结文件哈希、600/1400 划分和 40×15 批次顺序，并检查 v27 源码未改变。真实 Test 数据只检查输入结构；执行器测试使用合成题目和合成响应，不产生模型测试成绩。结果见输出目录的 `validation.json` 与 `unittest.log`。此前仅评分组件的验收报告保留在 `v28_actor_scoring_20261101`。

## 当前配置状态

初始 Skill 已选定并冻结为 `experiments/configs/v28_searchqa_initial_skill.md`，原文来自 SkillOpt SearchQA。正式配置见 `experiments/configs/v28_searchqa_train600_epoch1_deepseek_flash.json`，不执行 Stage0。

按用户确认，v28 与 v27 一致，不设置 `context_window_tokens`。保留 4,000,000 字符和 6,000,000 UTF-8 字节保护上限，以及输出预留记账；不执行可选的 token 窗口比较，不截断输入。服务商 token 容量未实测，也不再作为配置完成的前置条件。当前既定实验配置已全部完成，尚未启动真实训练或 Test。

正式 Gate 已确认 EM-only；F1 仅记录和报告，不作为拒绝条件或持平时的补充接受条件。

## 五模块与执行证据（已接入）

`modules.py` 提供 Grouping、Diagnosis、Preconditioner、Editor、Replay 的 `Call`：`messages` 是实际模型输入，`input` 是内部审计输入，`complete(parsed)` 对调用方提供的输出做确定性校验。该层不发送模型请求。Prompt 原样安装自已确认的五模块设计稿，以 v27 为基线；没有 Update 数量上限，也没有加入 v25.2 的精简修订附加段落，不安排相关消融。

| 模块 | 模型用户消息的顶层字段 |
|---|---|
| Grouping | parent、runs |
| Diagnosis | parent、runs、grouping |
| Preconditioner | parent、plan、runs、memory |
| Editor | parent、plan |
| Replay | parent、diff、plan、runs、pairs、memory |

`method.py:SearchQAMethod(actor_adapter, archives=[...])` 显式绑定当前和历史训练批次目录。在 `with method.using():` 中调用上述模块、证据函数及 Memory 接口。可使用无 transport 的 `SearchQAActorAdapter(dataset)` 做只读恢复。所有引用必须能返回已注册的完整原始归档；不自动寻找目录，不允许 Test 归档进入优化。归档验证复用已有 Actor 身份、六次尝试日志与重新评分检查。模块 callbacks 也必须在同一绑定上下文中执行。

`benchmarks/searchqa/facts.py` 投影 `v28_searchqa_facts_v1`：完整 question/context、初始消息、单个最终 stop 回合和 outcome。参考答案只在 outcome 的 `reference_answers` 中提供；EM/F1 沿用已验证执行评分。请求重试最多六次仍只形成一个可见回合；失败内容、隐藏推理、usage 和原始响应不进入五模块输入。每个 P/Q run 有四种引用：run、`:0`、`:1`、`:outcome`。所有投影与已验证原记录逐字段比对，额外字段、截断和伪造答案均拒绝。

`evidence.py` 沿用 v27 的逐模块投影。Preconditioner 只接收 Original Plan 直接引用的 runs，Group ID 不扩展全部成员；Grouping 仅留作内部引用校验。Editor 只接收 Parent 和编译后的有效 Plan。Replay 接收配对原始执行投影、实际编号 Diff 和有效 Plan 摘要，不接收 Gate 决策；Gate RETAIN 后仍可生成 Memory。历史 Memory 的模型视图只有 Active Knowledge 和精确 evidence 字符串，原始 sources 留在审计侧。

Plan、无编号 patch、有效 Plan 编译及 Memory 原子提交直接复用 v27 通用实现，不再校验 v27 源码哈希；v27 的配置或代码编辑不会仅因源码变化阻断 v28。启动时的 `contract.json` 只记录源码供查阅，恢复时不与当前源码比较。v28 补充拒绝 Grouping/Diagnosis 正文中不可用的 Candidate 或历史引用，因为 v27 的 Parent-only 扫描器不会识别这些引用。Replay 继续按整条 MemoryEntry 修订，历史引用不扩展相邻回合或同一 run 的其他字段。`SearchQAMethod.commit_memory/load_memory` 还会重查完整 Replay 审计包。Verifier/Repair 保持禁用。

五模块组件离线验收：

```sh
conda run -n SearchQA python scripts/verification/verify_v28_method.py --output artifacts/verification/v28_method_20261101
```

验收阻断网络和子进程，使用合成 Actor 响应及手工模块输出，不测量模型质量。检查覆盖五模块输入隔离、三条 Update、KEEP/精确修改/撤回、Check 引用、Editor 空串/null、实际 Diff、配对身份、Memory 提交/恢复/整条修订、历史越权、归档篡改及 Test 隔离；同时回归已有 Actor/评分/Gate 测试。历史设计稿及旧验收报告保留为当时快照；其“未安装”状态和保护哈希不更新为当前状态。当前状态以本文件、实验计划和新验收报告为准。


## 完整 campaign 与方法阶段恢复（已接入）

- `campaign.py:CampaignAdapter` 把 Actor 适配器与五模块证据层绑定；每个完成批次先核对原始归档，再登记可引用身份。恢复会按发布顺序重新绑定历史批次。传入无 transport 的 Actor 适配器可只读审计，也可从已完成 Actor 结果补齐批次汇总，不发送新请求。
- `config.py:campaign_config/validate_config` 固定完整 600 题的 40×15 顺序、单 epoch、15/15 并发、五模块模型参数、六次尝试及 2×序号秒等待。初始 Skill 已选定为 SkillOpt SearchQA 原始 initial.md；配置显式提供其逐字原文，不创建 campaign。
- `stages.py:run_stage` 沿用 v27 的持久化请求槽位、正常响应恢复、最近一次输出校验反馈及共享六次预算。未知请求消耗原槽位，未开始的准备槽位可复用；重试不会扩大预算。补充核对旧失败槽位及已保存 HTTP 原文／解码响应的一致性。输入／归档错误不会变成输出纠错反馈。
- `evolution.py:initialize/run_campaign/run_round/resume_round/final_parent` 接通 Parent→Grouping→Diagnosis→Preconditioner→Editor→Candidate→配对→Gate→Replay→Memory→原子发布。有效 no-change 继续下一批；Editor null 停止且不能 resume 重采样；RETAIN 仍提交有效 Replay Memory。发布恢复重查所有已发布依赖，使用单写锁，禁止源码和预算动态修改。
- `evaluation.py:run_evaluation/report_evaluation` 单独调度全部 1400 个 Test ID，支持冻结 Skill 和恢复、整体 EM/F1 报告，不自动在 campaign 后触发，不进入优化 Memory。
- `cli.py` 提供 configure、validate、run、audit、evaluate、report。configure／validate／audit／report 不读取凭据；run／evaluate 只有显式调用时才读取指定环境变量并构造 transport。archive-only 恢复不构造真实 transport。

模型输入均保持完整，容量检查失败即停止，不截断。沿用 v27 的字节估算只是一项保守检查，不代表服务商 tokenizer 已验证。

本轮完整验收命令（只运行合成测试）：

```sh
conda run -n SearchQA python scripts/verification/verify_v28_campaign.py --output artifacts/verification/v28_campaign_20261101
```

详细行为与范围见 `docs/methods/v28/CAMPAIGN_IMPLEMENTATION.md`。验收包括 600 道合成题的完整 40 批调度、多轮 ACCEPT/RETAIN、三个 no-change 分支、Replay 六次耗尽、13 个阶段／发布中断点、只读恢复、方法反馈和独立 Test 隔离，以及全部既有组件回归。真实题目仅做数据和配置静态检查，不调用模型、不创建正式训练目录；不将合成结果作为模型成绩。

# 记忆与问题边界

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v21 第 3 步：从修改后证据更新 Memory](#v21-memory-update)
- [v21 第 4 步：让双维认识参与下一轮修改](#v21-memory-consumption)
- [v21 补强第 3 步：简明当前认识与历史消费](#v21-current-understanding)
- [v21 补强第 2 步：issue 写回与复查边界](#v21-issue-boundaries)

<a id="v21-memory-update"></a>

## v21 第 3 步：从修改后证据更新 Memory

日期：2026-10-09。状态：已实现单次语义更新请求、来源校验、增量合并、派生证据保存及显式恢复；完成构造测试和真实产物的请求装配预检。未调用真实模型，尚未验证归因语义质量；未接入完整 v21 campaign 或改写活动 Memory head。

后续已完成[输入无损优化](FUSION_AND_INPUT.md#v21-input-optimization)：相同 539 个事件的请求由 238,240 降到 84,051 个代理 token。再完成[新增退化覆盖](REGRESSION.md#v21-regression-coverage)后，当前默认请求为 9 组配对、675 个事件、99,405 个代理 token；新增三组此前遗漏的退化配对。下文原预检数字保留为历史记录。

方法定位见 [v21 契约](METHOD.md#v21-method-contract)，输入证据来自[第 2 步](EVIDENCE.md#v21-post-modification-evidence)。

后续 [issue 边界](MEMORY.md#v21-issue-boundaries)已固定既有 problem 原文，并区分显式来源与共享 edit 上下文；自动反证继承仅来自本问题的显式来源链，共享证据仍可审阅。当前输入 99,761 个代理 token，Prompt 为 `memory_update_v21.4`。

再完成 [当前认识](MEMORY.md#v21-current-understanding)：同一次响应为每个被更新 issue 增加 `current_understanding`，最多 2,000 字符，必须引用含本轮 Replay 的原始事件；保存为现有来源记录，完整 attempts 不删。该步 Prompt 为 v21.5，真实旧材料预检为 100,026 个代理 token。本页以下保留此前实现记录；新响应字段及消费规则以当前认识说明为准。

2026-10-10 完成 [退化证据跨轮保留](REGRESSION.md#v21-regression-retention)：当前 Prompt 为 v21.6，强化相关双维退化的有界认识与双侧来源，并保存独立的 `regression-retention.json` 核查。响应/Memory schema 与 2,000 字符限制不变；报告检查来源和回查，不替代语义判断或自动分配 issue。

### 1. 这一步改变什么

更新不再只组合整批统计与修改前 Review。一次模型调用读取真实回放事件及双维反馈，形成或修订自然语言 assessment，再由程序验证来源、分配身份、合并增量并保存可回查的认识。

持久化 Memory 继续使用现有 `problem`、`approach`、`assessment`、`edit_refs`、`source_refs`。不新增效果类别、分数、生命周期状态、独立归因 Agent、第二轮 Review 或强制逐 edit 分析。

实现：

- [memory_update_v21.py](../../../src/skill_evolution/v21/memory_update_v21.py)：输入装配、来源/身份检查、增量合并、保存与恢复。
- [memory_update_prompt_v21.py](../../../src/skill_evolution/v21/memory_update_prompt_v21.py)：一次语义更新的说明与最小响应结构。
- [update_v21_memory.py](../../../scripts/runs/v21/update_v21_memory.py)：默认零模型预检，显式 `--run` 才调用配置模型。
- [test_memory_update_v21.py](../../../tests/skill_evolution/v21/test_memory_update_v21.py)：构造证据与模拟 transport 的专项测试。

### 2. 一次更新的输入范围

`build_memory_update_input` 默认加载本轮提案及其相关问题、原始证据、反证和配对轨迹，复用第 2 步的局部读取。同时扫描完整当前回放，自动补入任一维度从 `true` 降为 `false` 的配对及双侧原文，不依赖修改前引用。它不自动读取全部历史，也不为每条 edit 单独调用模型。

可通过 `issue_refs` 显式加入没有被 Fusion 选中的历史问题，通过 `pair_refs` 加入其他相关新配对。加入旧问题不要求本轮再次执行其旧 edit；只要有相关新证据，就可以修订其认识。

其余旧问题只以简短目录出现，帮助避免重复建问题，不能冒充已读原始证据。未加载的旧问题不能在本次响应中被改写；调用方需要依据已有分析或明确关联将其纳入范围。本步不增加自动语义检索 Agent，也不宣称自动找全所有潜在关联问题。

每次更新必须有已加载的本轮 Replay。输入在调用前和响应验证时重新对照来源重建，防止证据对象、局部视图或版本绑定漂移。使用已有无损文本/事件引用表示和调用预算检查；超限时停止，不自动删反证、压缩成摘要或扩展多轮流程。

### 3. 语义规则与引用规则

Prompt 要求：

- 根据实际行为及两维标签区分观察、解释和未知，修改前的合理性不充当修改后的效果证据。
- 一个维度的支持不能抹去另一维问题，失败也不能自动否定必要程序。
- 新证据可以修订旧解释，但不能改写历史事实，不能跨运行或版本拼成联合成功。
- 多条修改可以共同对应一个尝试；只有整包观察时明确保留局部影响未知。
- 在 assessment 中保留仍成立的限制和反证，说明新证据为何改变旧判断，不追加逐轮流水账。
- 同一问题/行为方案使用既有身份；行为路径或适用范围实质改变时建立新尝试。

模型只返回有必要更新的问题与尝试。响应沿用现有字段名；新对象暂用 `NEW/<local-name>`，由程序按输入身份生成稳定 issue/attempt ID，不能由模型伪造正式 ID。

响应中的 `source_refs` 是已加载的原始事件引用，不接受标签、pair ID、policy ID、Memory 摘要或未知引用替代。每份被改写的尝试必须引用本轮 Replay；承载本轮新 edits 的尝试必须包含 Candidate 事件。行为变化的解释应引用两侧证据，不能只从标签反推原因。

每个实际 edit 都要被至少一份尝试记录，属于修改账本完整性要求，不是逐 edit 效果归因：多条 edits 可以放进同一尝试，也允许明确写“效果未确定”。旧尝试只能追加它原有 edits 和本轮实际 edits，新尝试不能借用其他历史方案的 edit 身份。

### 4. 如何更新、如何回查

程序将每份新认识保存为有原始事件引用的 `ASSESSMENT_V21/...` 档案记录，Memory 的 `source_refs` 指向它。记录保留相关旧来源和已知反证依赖；这些旧判断可以被修订，但不从档案消失。

然后复用 v20 的确定性增量合并：

- 未提交更新的问题与尝试保持原样。
- 已有尝试更新 assessment，来源与 edits 按集合追加。
- 新尝试由程序分配身份，不覆盖旧方案结果。
- 同一增量重复应用不重复创建对象。

持久化 schema 仍真实标记 `issue_memory_v20.1` / `issue_memory_update_v20.1`，这是复用数据格式，不是宣称语义更新仍由 v20 默认函数执行。

输出同时包含更新后的 Memory 和派生 `ModificationEvidence`。派生证据保留 `prior_evidence_ref`、本次输入引用及响应摘要，原始证据文件保持不变。所有新来源都会经过同一局部读取接口复验，下一步可以重新打开实际事件，而不是只能读取总结文字。

结构验证不能证明自然语言因果判断正确，也不能自动识别语义重复方案或保证 assessment 已正确解释全部反证。这些属于后续真实模型核查与效果实验的范围。

### 5. 接口与发布边界

```python
from src.skill_evolution.v21.memory_update_v21 import (
    build_memory_update_input, run_memory_update,
)

request = build_memory_update_input(
    evidence,
    issue_refs=additional_historical_issue_refs,
    pair_refs=additional_pair_refs,
)
result = run_memory_update(request, output=independent_update_directory)
delta = result.payload['memory_update']
updated_memory = result.payload['memory']
updated_evidence = result.updated_evidence
```

`run_memory_update` 实际执行一次模型调用；测试可以注入 `transport`。输出目录包括：

- `input.json`、`request.json`、`response.json` 和响应完整性标记；
- `memory-update.json`：可供现有存储/调度器消费的增量；
- `memory.json`：合并后的完整新版本；
- `updated-evidence.json`：含新认识来源的派生档案；
- `result.json`、`complete.json`：验证结果和最终完整性标记。

本阶段生成并保存新 Memory 版本，但不独立发布活动 head 或 retained Skill。两者的原子发布仍归后续 v21 调度器负责，不能因为一次 Memory 模型响应成功就独立推进线上版本。v20 入口与行为不变。

网络失败、拒绝、截断、非法引用或覆盖不全均停止，不返回伪造的成功更新，不启动自动重试或修复 Review。显式 `resume=True` 复用已完成响应；调用结果不确定时要求新的显式尝试目录，不重新发送旧调用。输入、模型请求或已保存产物漂移时拒绝恢复。最终标记在所有派生文件保存后发布。

### 6. 命令与本次验证

零模型预检：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/runs/v21/update_v21_memory.py \
  --evidence artifacts/methods/v21/v21_evidence_step2/round-04.json \
  --expected-ref MODIFICATION_EVIDENCE_V21/21dd54b436057663c8afe5e44d56d527748a18f0c1f9634168e16fe11d8f7a4e
```

后续确需真实调用时，增加 `--run --output <独立目录>`；恢复增加 `--resume`。`--issue` 与 `--pair` 可重复，用于补充明确相关的旧问题/配对。本次没有执行 `--run`。

测试命令：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q \
  tests/skill_evolution/v21/test_memory_update_v21.py \
  tests/skill_evolution/v21/test_modification_evidence_v21.py \
  tests/skill_evolution/v20/test_issue_memory_v20.py \
  tests/skill_evolution/v20/test_runtime_v20.py \
  tests/skill_evolution/v20/test_local_generation_v20.py \
  tests/skill_evolution/v19/test_evolution_replay_v19.py
```

结果：**114 项通过**，其中本步专项 **24 项**。覆盖新尝试、旧认识修订、未涉及记录保留、显式加载未选中的历史问题、来源限制、两维不一致的构造反馈、稳定身份、联合修改记录、无损请求、预算前置检查、单次调用/恢复、失败不发布及篡改拒绝。模拟模型测试验证通路，不代表真实模型已经正确归因。

真实 v20 第 4 轮证据预检默认加载 **3 个历史问题、6 组配对、539 个事件**。输入为 **238,240 个 cl100k_base 代理 token**，含安全余量与输出预留为 **325,896**；这不是网关 tokenizer 的实测用量。请求仍较大，尚未验证实际调用成本、延迟或语义效果，不宣称 token 成本下降。没有截断原始证据。

预检报告：`artifacts/methods/v21/v21_memory_step3_preflight.json`。本次零真实模型调用、零 rollout、未发布活动 Memory head。后续[第 4 步消费适配](MEMORY.md#v21-memory-consumption)已接通已有 Fusion/Evidence Review，并完成跨轮候选生成的离线验证；真实语义效果仍待 Pilot 检验。

<a id="v21-memory-consumption"></a>

## v21 第 4 步：让双维认识参与下一轮修改

日期：2026-10-09。状态：已接通更新后的 Memory → Fusion → 现有局部 Review → Compiler/Editor，并验证候选及认识来源能进入下一轮修改后证据档案。完成离线测试与历史真实产物预检；未运行真实模型、重新 rollout 或发布活动 head。完整 campaign 的恢复、原子发布和两轮真实 Pilot 留在第 5 步。

后续已完成[输入无损优化](FUSION_AND_INPUT.md#v21-input-optimization)：相同六个历史 Review 由 38,899–107,958 降到 20,625–61,025 个代理 token；Prompt 升为 v21.2，原始证据范围不变。下文第 5 节数字是优化前记录。

后续 [issue 边界](MEMORY.md#v21-issue-boundaries)已进一步要求按原 problem 复查，并提供已有来源链与共享上下文的区分；Fusion/Review Prompt 当前为 v21.2/v21.3。保持完整相关证据，六个历史 Review 当前为 20,872–61,287 个代理 token。

再完成 [当前认识与历史消费](MEMORY.md#v21-current-understanding)：已有综合认识的 issue 在 Fusion 中只展示认识和尝试目录，Review 根据 `memory_attempt_refs` 按需打开尝试，保留已知反例及历史配对退化；无认识的旧记录继续完整读取。Fusion/Review Prompt 当前为 v21.6/v21.9；[语义定向修订](VALIDATION_CASES.md#v21-semantic-followup)引入任务/操作原文对照，[缺陷依据与修改授权调整](EVIDENCE.md#v21-defect-grounding)进一步要求原文可推翻上游缺陷假设，新增程序义务须有依据。此前的[提案依据要求](FUSION_AND_INPUT.md#v21-fusion-proposal-basis)和[证据比较要求](EVIDENCE.md#v21-evidence-comparison)继续保留。本页以下的“全部尝试”描述保留为旧实现记录，新规则以当前认识说明为准。

### 1. 相比 v20 的实际变化

| 环节 | v20 已有能力 | 本步改动 |
|---|---|---|
| Fusion | 读取问题、尝试及 assessment，选择 PROPOSE/NO_EDIT | 直接读取第 3 步更新后的完整 assessment；提示明确同时考虑另一维问题、反证和未知，在原有 reason 中说明修改方向如何回应限制 |
| 局部 Review | 回查选中问题的全部尝试和原始证据，授权有界 gap | 解析 ASSESSMENT_V21 的来源链、配对 Replay 和版本身份；结合当前 Parent 重新判断支持、问题和未知怎样影响修改 |
| Compiler/Editor | VERIFIED 才可生成有界修改 | 复用现有实现；更新后的认识、已核验理由和反证进入原有编辑输入，不另增编辑授权 |
| 后续档案 | 保存当前诊断、历史来源和实际 edits | 接受明确标记的 v21 generation source，把上一轮更新档案连同新轮证据继续保存，避免来源在下一轮断开 |

Memory 的问题/尝试字段、Fusion 响应字段、Review verdict/gap、编辑计划与 Gate 规则没有新增分类或状态。双维使用要求写入现有提示和 reason，不另设处置表、独立 Agent、额外 Review 或逐 edit 因果分析。

### 2. 具体消费规则

Fusion 只看简明认识，不声称自己已读取历史原文。引用有利尝试时，也要考虑同一问题其他尝试中的限制，不能把任务成功视为程序正确，或因为任务失败否定已观察到的合规行为。不同运行/版本的成功与合规不能拼成联合成功。当前 edit 绑定缺少完整已提交账本时仍为 `UNRESOLVED`。

Review 按选中问题加载全部尝试，沿显式 source/edit 关系保留联合依据和反证，再打开相关完整轨迹及已知配对两侧。不会自动扩成全轮、全历史，也不会只因 Fusion 选了某个有利 attempt 而隐藏同一问题的其他尝试。无关联的来源不加载；历史缺少配对信息时不制造配对或局部效果。

历史 PARENT/CANDIDATE 角色属于当时的 Replay；可编辑目标只能来自本轮实际 Parent。Memory 更新成功不意味着该 Candidate 已被部署，适配器不自行猜测 Gate 结果。调用方必须从可信提交或显式导入选择 bundle，并提供当前 Parent 和完整 Current Diagnosis batch。

Review 在原有 reason 和 gap 中说明参考了什么支持、回应了什么限制、哪些效果待验证。可以探索假设、重写整体方案，也允许 NO_EDIT；不要求每次 Memory 变化都机械改变候选。新的解释可以修订旧解释，但历史事实及已知反证仍保留。必要程序由可见 policy 约束，未知本身不构成新增禁止、确认或转人工义务。

这些语义要求由模型执行，程序只验证结构、身份、来源闭包、已知反证及编辑权限，不能据此宣称模型归因正确。

### 3. 实现与兼容边界

- [memory_consumption_v21.py](../../../src/skill_evolution/v21/memory_consumption_v21.py)：独立 Fusion 提示、配对证据审阅适配、v21 generation source，以及单次本地消费入口。
- [consume_v21_memory.py](../../../scripts/runs/v21/consume_v21_memory.py)：默认只预检，显式 `--run` 才执行 Fusion/Review/Editor。
- [modification_evidence_v21.py](../../../src/skill_evolution/v21/modification_evidence_v21.py)：显式识别 v21 generation source，复验后继承其证据档案，不把 v21 Replay 伪装成旧档案格式。
- [test_memory_consumption_v21.py](../../../tests/skill_evolution/v21/test_memory_consumption_v21.py)：来源、跨轮生成和受控反馈响应测试。

为避免复制整套 Compiler/Editor，在 `evidence_review_v20.py` 和 `local_generation_v20.py` 中只增加输入对象的装配/提示适配入口及显式 `source_type` 恢复参数。v20 默认输入仍使用原装配和原提示，未切换 v20 campaign；相关回归通过。

Fusion/review 响应、编辑计划、结果和 audit 外层继续复用 v20 结构契约，故部分 `schema_version` 和 ID 前缀仍含 V20；这表示协议复用。v21 的 generation source 明确为 `generation_input_v21.1`，来源 ID 为 `GENERATION_INPUT_V21/...`，审阅输入 ID 为 `EVIDENCE_REVIEW_INPUT_V21/...`，Prompt 有独立 v21 版本。恢复 v21 audit 应调用本模块 `restore_generation`，不能当作普通 v20 source 恢复。

Current Diagnosis 仍独立于 Memory。本步不重新诊断，不消费私有 Monitor，也不新增语义更新调用。Fusion 一次，每个 PROPOSE 一个原有 Review；Compiler 决定是否需要一次 Editor。NO_EDIT 不触发 Review，NO_UPDATE 不伪造候选或回放。失败保存已发生的调用和阶段产物，拒绝隐式重试或覆盖既有输出目录。

### 4. 使用入口

`--current-source` 读取 JSON 的 `parent_skill`、`current_requests`、`current_findings` 三项，可以使用既有 `generation/source.json` 中的当前批次。Memory 必须来自另一个已完成轮次的可信/显式导入档案；`--expected-ref` 应来自可信调用方，而非临时相信文件自报的 hash。

默认预检不调用模型：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/runs/v21/consume_v21_memory.py \
  --evidence <上一轮更新输出/updated-evidence.json> \
  --expected-ref <可信MODIFICATION_EVIDENCE_V21引用> \
  --current-source <下一轮当前诊断批次.json>
```

只有明确需要运行本地生成时，添加 `--run --output <新的独立目录>`。输出包含 Fusion 请求/响应、`generation/generation-audit.json` 和阶段状态；不执行新的 Agent rollout、Gate 或活动 Memory 发布。默认预检仅检查 Fusion；选择提案后，生成装配会验证相关来源闭包，Review 提示会作保守 token 预算检查，超预算不截断证据继续发送。

Python 调用方可直接使用 `build_issue_fusion_input`、`build_issue_fusion_request`、已有 `validate_issue_fusion`、`build_generation_input`，或用 `run_memory_consumption` 执行这一局部阶段。第 5 步调度可复用这些接口，并负责可信提交选择、完整恢复和原子发布。

### 5. 验证事实与结论边界

本步专项 **15 项通过**；连同第 2/3 步、v20 Fusion/Memory/生成/运行/campaign 和 Replay 回归，共 **141 项通过**。

覆盖：更新后的 assessment 进入 Fusion；选中问题的全部尝试、反证、配对双侧和版本保留；当前问题/纯历史方向；当前 Parent 编辑权限；摘要冒充事件、遗漏反证、篡改/陈旧来源拒绝；NO_EDIT 和失败不调用下游；完整 generation audit 复验；新一轮 Replay 档案保留旧认识来源。

受控 transport 测试使用 fixture 中真实存在的两种联合标签——T002 Candidate 失败但合规、T003 Candidate 成功但违规——经过 Memory 更新、Fusion、Review 和 Editor 得到不同理由与候选。响应逻辑是测试中编写的，不是真实模型推理；这验证证据与认识可以影响修改，不证明归因正确或方法收益。

历史真实产物预检只读导入 v20 第 3 轮证据，结合第 4 轮当前批次。Fusion 读取 6 个历史问题，代理输入 13,020 tokens。逐个历史问题的构造选择读取 240、63、272、68、266、96 个事件，保留各自已知反证；Review 代理输入范围 38,899–107,958 tokens。另一个合并当前 Findings 的装配 fixture 为 735 个事件、259,416 tokens，并非建议正式运行时把所有当前问题合成一个提案。

这些旧 Memory 的选中来源没有可解析的 v21 配对，因此相关历史视图的 pairs 为 0；没有为展示双维效果而补造关联。v21 新认识到配对原文的通路由上述跨轮 fixture 单独验证。真实预检也没有执行第 3 步语义更新，不能称为 v21 Pilot。报告见 `artifacts/methods/v21/v21_memory_step4_preflight/check.json`。

所有 token 为 cl100k_base 代理估计，不是网关实测。尚未验证新增机制的真实成本、学习收益或语义稳定性。下一步应在完整调度和原子提交接通后，运行两轮真实 Pilot，检查“修改后形成认识 → 下一轮复用/修订”的实际证据链，再开展匹配对照。

<a id="v21-current-understanding"></a>

## v21 补强第 3 步：简明当前认识与历史消费

日期：2026-10-09。已实现同次更新维护 issue 当前认识，以及 Fusion/Review 的分层读取；未调用真实模型、新建真实 rollout 或发布活动 head。

### 1. 当前认识怎样维护

现有一次 Memory 更新响应中，每个被更新 issue 增加一个 `current_understanding` 段落；继续保留 `problem` 固定锚点和各 attempt 的 `assessment`。不增加摘要 Agent、第二次更新调用、状态分类或逐 edit 分析。

Prompt 要求综合本问题的相关尝试，写清：哪些方向有证据支持及其适用条件，任务成功/程序合规各自暴露过什么问题和反例，最新尝试相对以前改变了什么，以及仍然未知的部分。压缩时不能只保留修改建议主体。Skill 中出现了文字与运行验证了效果必须区分。

当前认识限制为不超过 **2,000 个字符**，这是输入规模约束，不是完整性证明。超过上限或只有空白时拒绝更新，不自动截断，也不启动隐式修复调用。issue 级 `source_refs` 必须引用已加载原始事件，并包含本轮 Replay；程序还合并本次被修改 attempts 的事件引用，并保留该 issue 已有的显式反证。

一段新认识覆盖“当前读取位置”，不覆盖历史事实。未返回的 issue 保持原样。新发现的问题可以没有实际 attempt，但仍须有认识和原始事件依据。

### 2. 保存方式

完整 Memory 仍使用 `issue_memory_v20.1` 的原有字段。程序把当前认识保存成已有档案结构中的 `UNDERSTANDING_V21/...` 来源记录，再将引用追加到该 issue 的 `source_refs`；最新的一条是当前认识。

该记录复用 `statement`、`evidence_refs`、`counterevidence_refs`、`source_refs`，直接关联观察及配对，不虚构一个“汇总 attempt”，也不把所有旧摘要逐层链接到新摘要。完整 attempts、旧认识、原始事件和旧来源仍留在 Memory/档案中，原有完整回查接口继续可用。

因此只新增一个模型响应文本字段，没有增加持久化效果状态或另建记忆系统。消费方通过可信 evidence bundle 读取当前认识；单独的旧 Memory JSON 不能冒充已经包含新综合认识。

### 3. 下一轮怎样读取

| 场景 | 默认读取 | 需要历史细节时 |
|---|---|---|
| Fusion：已有当前认识 | 原 problem、一段当前认识、attempt ID/approach 目录及原有绑定信息 | 在已有 `memory_attempt_refs` 中选择需要比较、重试或核查的尝试 |
| Review：已有当前认识 | 当前认识及其原始依据、当前选中 Findings、已知反证、此前关联的双维标签退化配对 | 加载 Fusion 显式选择的完整 attempts、原始依据及联合依赖 |
| 旧 issue 尚无当前认识 | 保持原完整历史路径 | 不用截断或拼接旧 assessment 冒充新认识 |
| 修改后的 Memory 更新 | 保留相关问题完整历史及修改后证据，同时显示上一段当前认识 | 在同一次调用中综合修订，避免仅凭摘要再摘要 |

Review 使用现有 `memory_attempt_refs`，不增加检索 Agent 或额外 Review。选中有利尝试不能隐藏已知反例：程序在本地对原完整来源范围做索引，强制保留所有已知 `counterevidence_refs` 对应完整轨迹；过去关联配对中任一维度 `true → false` 的双方原文也保留，即使旧更新把它们记为普通证据而非反证。

当前认识引用、已知反例或显式选择可能仍然打开较大的相关范围；这是保留限制和反证的代价，不通过固定最近 N 条或机械截断降低成本。未加载的历史仍在本地，不等于已经无效。如果现有材料不足以证明修改必要性，Review 应使用既有 `NO_EDIT` 并说明限制，不能猜测未读历史。

前一步的 issue 边界继续生效：共享证据不自动拥有同一个归因结论；普通更新不能改写原 problem。当前认识可以改写解释和条件，但不能换成另一个问题。

### 4. 验证与成本边界

专项构造测试覆盖：同次调用写入认识、完整历史保存、更新后只读取最新综合认识、长度/引用约束、Fusion 目录化、选择性历史回查、已知反例和历史退化不可隐藏、旧数据回退、错误来源拒绝，以及未涉及 issue 保持不变。构造了 12 条重复旧 attempt 的场景，验证完整 attempts 仍在本地，而 Fusion 不再重复携带其 assessment，代理输入确实减少。

这是工程通路测试，摘要文本由测试提供；不能证明真实模型已经保留全部语义限制，也不是研究效果或实际成本实验。

新增专项 **16 项**，连同既有 v21 更新/消费/来源/表示及 v20/Replay 回归，共 **205 项通过**。

真实历史材料预检报告：[report.json](../../../artifacts/methods/v21/v21_current_understanding/report.json)。使用此前 v20 历史产物，**6 个历史 issue 都尚无新格式当前认识**，因此全部回退完整历史。默认更新仍覆盖 **9 组配对、675 个事件**，包括此前补齐的三个退化案例。当前代理输入为 Memory **100,026**、Fusion **13,240**、六个历史 Review **20,986–61,401**；不能把这些尚未生成真实摘要的数据宣称为摘要压缩效果。Memory 更新保留完整相关历史，其长期增长也未被本步宣称解决。

所有数字是 cl100k_base 代理估计。旧预检报告保留；当前复现命令为：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/runs/v21/preflight_v21_input_budget.py
```

### 5. 实现与兼容

- [current_understanding_v21.py](../../../src/skill_evolution/v21/current_understanding_v21.py)：当前认识读取、按需历史展开及反证/退化保留。
- [memory_update_v21.py](../../../src/skill_evolution/v21/memory_update_v21.py) 与 Prompt：同次生成并保存综合认识，保留完整历史和显式恢复。
- [memory_consumption_v21.py](../../../src/skill_evolution/v21/memory_consumption_v21.py)：Fusion 目录视图、原有选择字段和 Review 适配。
- [test_current_understanding_v21.py](../../../tests/skill_evolution/v21/test_current_understanding_v21.py)：专项测试。

Memory 输入为 `memory_update_input_v21.4`；该步 Prompt 为 `memory_update_v21.5`，后续[退化证据跨轮保留](REGRESSION.md#v21-regression-retention)更新至 v21.6，2,000 字符限制不变。Fusion 输入明确为 `issue_fusion_input_v21.1`，Fusion/Review Prompt 当前为 v21.6/v21.9；[语义定向修订](VALIDATION_CASES.md#v21-semantic-followup)引入任务/操作原文对照，[缺陷依据与修改授权调整](EVIDENCE.md#v21-defect-grounding)进一步要求原文可推翻上游缺陷假设，新增程序义务须有依据。此前的[提案依据要求](FUSION_AND_INPUT.md#v21-fusion-proposal-basis)和[证据比较要求](EVIDENCE.md#v21-evidence-comparison)继续保留。为复用原 Fusion 身份/归属校验，v20 输入类型只增加默认恒等的校验视图入口；v21 适配目录字段，内部占位文本不进入模型。v20 默认行为、Memory 格式、Fusion/Review 响应和 Gate 不变。

旧可信证据档案可读。旧模型响应缺少新认识字段，或旧请求与新输入/Prompt 不一致时，不能假装恢复为新版运行；需新的独立调用目录。没有自动历史回填或额外模型调用。

按后续讨论，完整 v21 运行与恢复、Skill/Memory 原子发布之前，先做小规模真实模型验证：检查摘要中的条件/反例是否保留，以及 Fusion/Review 是否据此形成合理修改决策。本次已完成[案例与判定依据准备](VALIDATION_CASES.md#v21-small-validation-cases)，保留 2,000 字符硬限制，尚未调用真实模型。只在验证暴露具体不足时做最小强化，之后再接通完整调度并进行两轮 Pilot。

<a id="v21-issue-boundaries"></a>

## v21 补强第 2 步：issue 写回与复查边界

日期：2026-10-09。已完成写回约束、来源区分和 Fusion/Review 提示调整；未调用真实模型、重新 rollout 或发布活动 head。

后续 [当前认识与历史消费](MEMORY.md#v21-current-understanding)已实现同次更新维护 issue 综合认识，以及按需历史读取；原问题和归属边界继续保留。下文数字与版本是本步当时记录，当前预检默认路径为 `artifacts/methods/v21/v21_current_understanding/report.json`。

### 1. 本步约定

**一个 issue 围绕原来的问题积累认识。联合提案、共同 edit 或共同轨迹允许共享证据，不自动合并问题范围，也不让每个 issue 继承整段联合修改建议。**

现有 issue 的 `problem` 原文作为固定范围锚点。普通 Memory 更新不能改写它；修订对方法、条件及双维结果的认识，写入相关 attempt 的 `assessment`。发现不同问题时，使用已有 NEW issue 机制及原始事件引用；没有实际修改时可以没有 attempt。不得因此重复建立已有问题。

这是当前写回接口的明确限制：即使提供了合法新事件，改写旧 `problem` 也会被拒绝。它防止在原 ID 下替换复查对象，不等于程序能够识别所有文字中的语义偏移，也不自动清洗过去已经混杂的记录。

### 2. 实际改动

#### 来源区分

`open_memory_evidence` 增加一个输入派生映射 `issue_source_refs`：每个已加载 issue 对应自己的来源、各 attempt 来源及沿 `source_refs` 正向可达的历史记录。它不沿共享 edit 的反向关系认领其他记录。

原有完整读取范围保持：通过共享 edit 展开的其他记录、配对双侧、上下文和已知反证仍在 `source_records`/`events` 中。映射只区分已有来源链与其他上下文，不裁剪证据，也不表示来源内的每句话都属于该 issue 或已经正确归因。旧的显式来源本身可能混杂，模型仍须回到原问题判断。

映射不新增 Memory 持久化字段、效果状态或第二套目录。短引用表示能够完整还原它；Memory 调用前重建输入，篡改 issue 与来源的绑定会被拒绝。

#### Memory 写回

- 既有 `problem` 必须原文保留；已有 attempt 身份仍只能在所属 issue 下更新。
- 新评价自动保留本 issue 显式历史来源中的反证，不再把通过共享 edit 连带加载的其他 issue 的全部反证自动复制成自己的评价附件。
- 共享反证仍在完整档案和后续 Review 中。若新观察确实与本问题相关，模型可引用其原始事件并说明关联；不禁止跨问题的真实影响。
- Prompt 要求 `approach`/`assessment` 只写与本 issue 相关的行为、修改后观察及限制。联合提案/Review gap 的整段文字不能机械复制到每个关联 issue。
- edit 的账本覆盖要求仍对本次更新整体生效，不要求每个关联 issue 都记一份。确有依据时，同一实际 edit 可对应多个 issue 下分别表述的尝试，不宣称隔离效果。

#### Fusion 与 Review

Fusion 以原 `problem` 为范围锚点。仅共同任务、规则或 edit 不足以合并独立问题；相关问题可以联合提出，但须在原有 `reason` 中交代关联。

Review 接收原 `memory_issues`、来源映射及完整相关证据。Prompt 明确：Fusion 的 `issue_statement` 是修改方向，不能替换历史问题；旧 attempt 中混入的其他议题或共享轨迹里的偶发问题，不能成为扩大 gap 的理由。无法为选中问题证明修改必要性时，使用既有 `NO_EDIT`。联合 Review 仍是一个调用，不增加逐 issue/逐 edit 的重复审阅表。

当前规则中已有相关文字只能证明文字覆盖，不能证明运行成功或程序合规；Review 需在原有 `reason` 中区分这些结论。

### 3. 验证与限制

新增 [10 项边界测试](../../../tests/skill_evolution/v21/test_issue_boundaries_v21.py)，包括：

- 两个问题共享 edit 时，来源链保持各自边界，共享原文仍可读取；
- 只更新 A 时，B 不变，B 的反证不被自动写成 A 的新评价附件；
- 同一实际修改可形成两个分别表述的 issue assessment；
- 即使有合法事件，也拒绝替换既有 problem 或跨 issue 搬用 attempt 身份；
- 原范围、来源映射、共享反证能够进入下一轮 Review；联合问题仍只装配一个 Review；
- 旧显式混杂链接保留为历史，不按未经验证的语义判断删除。

这些测试使用构造的模型响应验证通路。程序能强制固定锚点、身份归属、来源绑定及自动继承规则；能否正确划分相关行为、避免自然语言跑题，仍需真实模型实验，不能由测试通过宣称解决。

新增专项连同既有 v21 更新/消费/证据/表示及 v20/Replay 回归，共 **189 项通过**。

历史真实产物只读预检仍保留 **9 组配对、675 个事件**，包括上一步补入的 T005/T022/T036。Memory 代理输入从 99,405 变为 **99,761**，新增 356 tokens；Fusion 为 13,127，六个历史 Review 为 20,872–61,287。所有原始事件、配对与已知反证计数和上一步一致，并通过无损还原校验。

报告：[report.json](../../../artifacts/methods/v21/v21_issue_boundaries/report.json)。它由下列命令生成；此前退化覆盖与输入优化报告保留，当前目录的 `check.json` 是本步中间报告。

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/runs/v21/preflight_v21_input_budget.py
```

数字是 cl100k_base 代理估计，不是网关实测。各阶段使用历史构造请求，不构成一轮真实 v21 campaign。

### 4. 版本与后续

当前局部证据视图为 `memory_evidence_view_v21.2`，Memory 输入为 `memory_update_input_v21.3`；Memory/Fusion/Review Prompt 分别为 `memory_update_v21.4`、`issue-fusion-v21.2`、`evidence-review-v21.3`。Memory 持久化和三个模型响应格式不变。v20 默认路径不变。

已保存规范证据和 Memory 仍可读取。新输入/Prompt 不能冒充旧请求恢复；旧调用或生成审计若与重建输入不符会被拒绝，应使用新独立运行目录。

下一步是整理每个 issue 的简明当前认识及历史消费，避免跨轮重复增长。本步没有实现历史语义清洗、摘要压缩、完整 campaign 或真实 Pilot。

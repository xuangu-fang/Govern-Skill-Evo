# v21 第 3 步：从修改后证据更新 Memory

日期：2026-10-09。状态：已实现单次语义更新请求、来源校验、增量合并、派生证据保存及显式恢复；完成构造测试和真实产物的请求装配预检。未调用真实模型，尚未验证归因语义质量；未接入完整 v21 campaign 或改写活动 Memory head。

后续已完成[输入无损优化](V21_INPUT_OPTIMIZATION.md)：相同 539 个事件的请求由 238,240 降到 84,051 个代理 token。再完成[新增退化覆盖](V21_REGRESSION_COVERAGE.md)后，当前默认请求为 9 组配对、675 个事件、99,405 个代理 token；新增三组此前遗漏的退化配对。下文原预检数字保留为历史记录。

方法定位见 [v21 契约](V21_METHOD_CONTRACT.md)，输入证据来自[第 2 步](V21_POST_MODIFICATION_EVIDENCE.md)。

后续 [issue 边界](V21_ISSUE_BOUNDARIES.md)已固定既有 problem 原文，并区分显式来源与共享 edit 上下文；自动反证继承仅来自本问题的显式来源链，共享证据仍可审阅。当前输入 99,761 个代理 token，Prompt 为 `memory_update_v21.4`。

再完成 [当前认识](V21_CURRENT_UNDERSTANDING.md)：同一次响应为每个被更新 issue 增加 `current_understanding`，最多 2,000 字符，必须引用含本轮 Replay 的原始事件；保存为现有来源记录，完整 attempts 不删。该步 Prompt 为 v21.5，真实旧材料预检为 100,026 个代理 token。本页以下保留此前实现记录；新响应字段及消费规则以当前认识说明为准。

2026-10-10 完成 [退化证据跨轮保留](V21_REGRESSION_RETENTION.md)：当前 Prompt 为 v21.6，强化相关双维退化的有界认识与双侧来源，并保存独立的 `regression-retention.json` 核查。响应/Memory schema 与 2,000 字符限制不变；报告检查来源和回查，不替代语义判断或自动分配 issue。

## 1. 这一步改变什么

更新不再只组合整批统计与修改前 Review。一次模型调用读取真实回放事件及双维反馈，形成或修订自然语言 assessment，再由程序验证来源、分配身份、合并增量并保存可回查的认识。

持久化 Memory 继续使用现有 `problem`、`approach`、`assessment`、`edit_refs`、`source_refs`。不新增效果类别、分数、生命周期状态、独立归因 Agent、第二轮 Review 或强制逐 edit 分析。

实现：

- [memory_update_v21.py](../src/skill_evolution/memory_update_v21.py)：输入装配、来源/身份检查、增量合并、保存与恢复。
- [memory_update_prompt_v21.py](../src/skill_evolution/memory_update_prompt_v21.py)：一次语义更新的说明与最小响应结构。
- [update_v21_memory.py](../scripts/update_v21_memory.py)：默认零模型预检，显式 `--run` 才调用配置模型。
- [test_memory_update_v21.py](../tests/skill_evolution/test_memory_update_v21.py)：构造证据与模拟 transport 的专项测试。

## 2. 一次更新的输入范围

`build_memory_update_input` 默认加载本轮提案及其相关问题、原始证据、反证和配对轨迹，复用第 2 步的局部读取。同时扫描完整当前回放，自动补入任一维度从 `true` 降为 `false` 的配对及双侧原文，不依赖修改前引用。它不自动读取全部历史，也不为每条 edit 单独调用模型。

可通过 `issue_refs` 显式加入没有被 Fusion 选中的历史问题，通过 `pair_refs` 加入其他相关新配对。加入旧问题不要求本轮再次执行其旧 edit；只要有相关新证据，就可以修订其认识。

其余旧问题只以简短目录出现，帮助避免重复建问题，不能冒充已读原始证据。未加载的旧问题不能在本次响应中被改写；调用方需要依据已有分析或明确关联将其纳入范围。本步不增加自动语义检索 Agent，也不宣称自动找全所有潜在关联问题。

每次更新必须有已加载的本轮 Replay。输入在调用前和响应验证时重新对照来源重建，防止证据对象、局部视图或版本绑定漂移。使用已有无损文本/事件引用表示和调用预算检查；超限时停止，不自动删反证、压缩成摘要或扩展多轮流程。

## 3. 语义规则与引用规则

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

## 4. 如何更新、如何回查

程序将每份新认识保存为有原始事件引用的 `ASSESSMENT_V21/...` 档案记录，Memory 的 `source_refs` 指向它。记录保留相关旧来源和已知反证依赖；这些旧判断可以被修订，但不从档案消失。

然后复用 v20 的确定性增量合并：

- 未提交更新的问题与尝试保持原样。
- 已有尝试更新 assessment，来源与 edits 按集合追加。
- 新尝试由程序分配身份，不覆盖旧方案结果。
- 同一增量重复应用不重复创建对象。

持久化 schema 仍真实标记 `issue_memory_v20.1` / `issue_memory_update_v20.1`，这是复用数据格式，不是宣称语义更新仍由 v20 默认函数执行。

输出同时包含更新后的 Memory 和派生 `ModificationEvidence`。派生证据保留 `prior_evidence_ref`、本次输入引用及响应摘要，原始证据文件保持不变。所有新来源都会经过同一局部读取接口复验，下一步可以重新打开实际事件，而不是只能读取总结文字。

结构验证不能证明自然语言因果判断正确，也不能自动识别语义重复方案或保证 assessment 已正确解释全部反证。这些属于后续真实模型核查与效果实验的范围。

## 5. 接口与发布边界

```python
from src.skill_evolution.memory_update_v21 import (
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

## 6. 命令与本次验证

零模型预检：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/update_v21_memory.py \
  --evidence artifacts/v21_evidence_step2/round-04.json \
  --expected-ref MODIFICATION_EVIDENCE_V21/21dd54b436057663c8afe5e44d56d527748a18f0c1f9634168e16fe11d8f7a4e
```

后续确需真实调用时，增加 `--run --output <独立目录>`；恢复增加 `--resume`。`--issue` 与 `--pair` 可重复，用于补充明确相关的旧问题/配对。本次没有执行 `--run`。

测试命令：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q \
  tests/skill_evolution/test_memory_update_v21.py \
  tests/skill_evolution/test_modification_evidence_v21.py \
  tests/skill_evolution/test_issue_memory_v20.py \
  tests/skill_evolution/test_runtime_v20.py \
  tests/skill_evolution/test_local_generation_v20.py \
  tests/skill_evolution/test_evolution_replay_v19.py
```

结果：**114 项通过**，其中本步专项 **24 项**。覆盖新尝试、旧认识修订、未涉及记录保留、显式加载未选中的历史问题、来源限制、两维不一致的构造反馈、稳定身份、联合修改记录、无损请求、预算前置检查、单次调用/恢复、失败不发布及篡改拒绝。模拟模型测试验证通路，不代表真实模型已经正确归因。

真实 v20 第 4 轮证据预检默认加载 **3 个历史问题、6 组配对、539 个事件**。输入为 **238,240 个 cl100k_base 代理 token**，含安全余量与输出预留为 **325,896**；这不是网关 tokenizer 的实测用量。请求仍较大，尚未验证实际调用成本、延迟或语义效果，不宣称 token 成本下降。没有截断原始证据。

预检报告：`artifacts/v21_memory_step3_preflight.json`。本次零真实模型调用、零 rollout、未发布活动 Memory head。后续[第 4 步消费适配](V21_MEMORY_CONSUMPTION.md)已接通已有 Fusion/Evidence Review，并完成跨轮候选生成的离线验证；真实语义效果仍待 Pilot 检验。

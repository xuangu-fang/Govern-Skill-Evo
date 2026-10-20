# V23 模块串联与轮次调度设计方案

- **研究主题：** 基于诊断预条件化的持续 Skill 自进化。
- **状态：** 调度已实现并通过离线回归；实现细节见 [EVOLUTION_DESIGN.md](EVOLUTION_DESIGN.md)。
- **范围：** 串联现有模块，管理轮次冻结、有限重试、断点恢复及统一发布。
- **实现入口建议：** `src/skill_evolution/v23/evolution.py`。

## 1. 职责与边界

Orchestrator 复用现有 Grouping、Diagnosis、Preconditioner、Editor、Replay、Memory、Gate 以及 ALFWorld Actor 入口。不增加 LLM 模块、模块 Prompt、自然语言审核器或新的学习算法。

调度层只解决三件事：

1. **串联：** 各阶段消费同一轮真实执行和已有产物，不重复运行已完成的任务。
2. **恢复：** 保存失败，执行有上限的技术重试，复用经过校验的有效阶段。
3. **推进：** 本轮所需产物完成后，统一发布下一轮 Parent Skill 和 Active Memory。

以一个 `evolution.py` 为主要调度入口，允许对现有模块的保存、读取和重试参数做最小必要适配，尤其是 Memory 待发布快照。不能为了“只新增一个文件”而复制模块内部逻辑，也不重构整个系统。

## 2. 每轮流程与数据划分

第 t 轮读取 Parent Skill Sₜ、Active Memory Mₜ，以及预先确定的 Train 任务批次：

```text
冻结 Sₜ、Mₜ、任务和配置
  → Parent 执行
  → Grouping → Diagnosis
  → Preconditioner → Editor
  → Candidate 执行
  → Parent/Candidate 配对核验
  → Gate
  → Replay → Memory 待发布快照
  → 统一发布 Sₜ₊₁、Mₜ₊₁
```

Gate 和 Replay 使用同一批经过核验的 Train 配对，不设置独立 Validation。可以先 Gate、后 Replay，顺序执行即可。Gate 不依赖 Replay 的模型判断，Replay 不读取 Gate 决定。

这是对此前 Gate 文档中建议采用独立 Validation 的**明确调整**。Gate 仍仅判断 Candidate 是否在当前训练批次增加成功数量，规则不变。各轮 ACCEPT 不表示取得独立验证收益。

独立 Test 用于最终效果评价，不进入轮次调度、Diagnosis、Replay、Memory 或 Gate，不根据 Test 结果调整演化过程。将来若另行采用独立 Validation，需重新冻结实验配置和数据边界；不能静默混入本方案。

## 3. Campaign 状态与轮次冻结

Campaign 只维护一个正式状态入口，示意如下：

```json
{
  "next_round": 2,
  "parent": "rounds/R01/editor/attempts/001/candidate.md",
  "active_memory": "rounds/R01/memory/active_memory.json"
}
```

`parent: null` 表示 No Skill。路径相对 Campaign 根目录解析，指向已保存且不可变的材料。Memory 状态引用必须能还原 Active 身份、已提交历史及所需 Archive 来源，不能只有脱离来源的知识文本。

轮次开始时冻结：

- 实际 Parent 全文或 null，以及原始来源。
- 当时的 Active Memory 身份、完整 `entries + sources` 读取视图及 Archive 来源。
- 有序任务清单、任务身份和必要环境初始配置。
- Actor 能力、基础协议、模型参数、步数上限。
- 各模块模型参数、输入容量、输出预算、超时和重试预算。
- 当前实际 Prompt、阶段来源，以及正常无更新后是否推进下一批的策略。

**冻结的是实际内容，不只是可变文件的路径。** `input.json` 应保存内容或引用不可变快照；仅指向以后可能修改的全局 `config.json` 不足以冻结配置。

调度层不新增 SHA256、input_hash、output_hash 等字段体系。恢复时核对实际输入、Prompt、参数和上游来源。既有模块的 Skill 身份、环境哈希和来源核验继续保留，不因调度层简化而删除。

本轮 Preconditioner 和 Replay 都读取 Mₜ。Replay 生成的新 Memory 不回流到本轮 Preconditioner，只有下一轮读取 Mₜ₊₁。轮次 ID 与 Campaign 身份共同构成唯一上下文，避免不同 Campaign 的 R01 混淆。

## 4. 模块交接

| 阶段 | 主要输入 | 交接产物 |
|---|---|---|
| Parent 执行 | 冻结 Parent、当前任务、Actor 配置 | 完整 Parent 原始执行 |
| Grouping | Parent 共享事实与背景 | Groups |
| Diagnosis | Parent 共享事实、Groups | Original Plan |
| Preconditioner | Original Plan、引用的当前证据、Mₜ | Effective Plan |
| Editor | Parent、Effective Plan、共享背景 | Patch、程序构造的 Candidate |
| Candidate 执行 | 实际 Candidate、相同任务与可比较配置 | 完整 Candidate 原始执行 |
| 配对核验 | 两侧实际执行及冻结任务清单 | 真实配对身份与核验材料 |
| Gate | 全部已核验配对的环境成功结果 | ACCEPT 或 RETAIN |
| Replay | 实际编辑、Effective Plan、配对事实、Mₜ | entries 提案 |
| Memory 程序 | 合法提案、Mₜ 与实际来源 | 不可变提交及待发布 Active 快照 |

Parent 的一条完整合法执行只运行一次，各模块复用它。技术中断后重新开始的任务是另一个独立 Attempt，不与前一条拼接。Candidate 必须是 Editor 实际严格应用 Patch 生成的 Skill，不能用 Plan 文本代替。

复用既有 `facts.py`、模块 `run_* / load_*` 与配对核验。保留 P/Q、步骤、Group、Update、Memory 和上下文引用，不另建执行编号或轨迹摘要。

Gate 和 Replay 使用同一份核验后的配对身份，但消费不同视图。Gate 只读取环境成功结果；Replay 保持七字段：`parent / diff / plan / command_sets / runs / pairs / memory`。Gate 决定不加入 Replay 输入或 MemoryEntry。

当前 Gate 的已有 Replay 档案适配器不是新轮次的运行依赖。调度应先形成公共配对材料，再调用通用 Gate 配对/判定接口；不能要求 Replay 模型已经执行才运行 Gate。

## 5. 技术失败、有限重试与 Attempt 归档

模块模型调用采用**首次调用加最多两次自动重试**。三次仍失败，停止整个 Campaign，不跳过轮次、不进入下一任务批次。

技术重试保持相同输入、Prompt 和生成参数，不加入上次错误反馈，不自动修补 Patch 或其他输出。JSON/契约错误、空响应、截断、Patch 严格应用失败和可恢复网络错误可按冻结预算重试。

认证错误、来源缺失、配置冲突、输入超过冻结容量等重复请求不能解决的问题直接停止。输入过大不静默截断，也不临时扩大预算后混入原请求。正常任务失败及合法语义决定不属于技术重试对象。

每次模型请求使用独立目录：

```text
editor/
  attempts/
    001/   # 原始请求、响应、错误、消耗
    002/
    003/
  result.json   # 记录所选合法 Attempt 的来源
```

请求发出前保存消息和配置；收到响应后先保存原文，再解析、校验。保留 finish_reason、实际 Token、推理 Token、耗时及错误。服务端用量不可获知时记录未知，不能计为零。失败后已经产生的费用也计入实验消耗。

按顺序采用首个合法结果，不继续采样择优。合法 `no_change`、`need_evidence`、空 Patch、null Patch、`entries=[]` 或 Keep 不重试。

Actor 需要区分两个层级：

- **单步传输请求：** 冻结实际 HTTP 请求及重试上限，记录每次真实请求。
- **整任务恢复：** 环境无法可靠恢复时，从初始状态重新执行该任务，冻结独立的任务尝试上限。

当前 Actor 对部分 HTTP 错误已有最多六次请求的逻辑。实现时必须显式处理这一既有预算，不能在外层再套三次而不报告实际放大的请求数。具体 Actor 上限在实现与实验配置中明确，本文不将模块三次请求预算误写为已经覆盖所有底层请求。

HTTP 中断前的部分轨迹原样保留，不能拼接到新尝试。完成的其他任务复用。正常步数耗尽是合法任务失败，不因任务未成功重新执行。每个任务最终使用首个完整、合法、可核验的执行，不能按成功与否挑选尝试。

## 6. resume 与有效结果复用

建议提供：

```text
run_round(...)
resume_round(...)
run_campaign(...)

python -m src.skill_evolution.v23.evolution resume --campaign <campaign_directory>
```

这些为待实现接口，不表示当前已有 CLI。

例如 Parent、Grouping、Diagnosis、Preconditioner 已完成，而 Editor 三次技术失败：用户明确启动 resume 后，复用已校验的上游，从 Editor 开始一组新的有限恢复尝试。Attempt 编号继续递增，原失败不覆盖。resume 不是后台无限重试。

恢复时区分：

- 有效产物：调用现有读取器核验输入、Prompt、配置及来源后复用。
- 有原始响应但归档未完成：优先从已保存响应完成确定性解析/校验，不另发相同模型请求。
- 没有可恢复响应：记录未知结果及未知消耗，按明确的剩余预算或新恢复操作处理。
- 已发布轮次：识别正式状态，不能再次创建 MemoryEntry 或重复推进 next_round。

修改了上游实际输入或方法契约时，受影响的下游结果不能复用；需要明确记录配置变化。实质性算法修改应建立新的实验配置。不能只因路径相同便接受旧结果。

`need_evidence` 或 `patch=null` 属于语义阻碍。同样输入下执行 resume 不自动重采样；应先解决上游事实或更新要求，再按变化范围确定重新运行的阶段。

## 7. 合法没有 Candidate 的处理

| 合法结果 | 本轮处理 |
|---|---|
| Diagnosis `no_change` | 正常无更新结束，保持 Skill/Memory，不调用后续模型或 Candidate 阶段 |
| Preconditioner `no_change` | 正常无更新结束，不调用 Editor、Candidate、Gate、Replay |
| Editor `patch=""` | 正常无更新结束，不创建 Candidate，不调用 Gate 或 Replay |
| Diagnosis/Preconditioner `need_evidence` | 保存语义阻碍，停止自动推进，不技术重试 |
| Editor `patch=null` | 保存实施阻碍，停止自动推进，不技术重试 |
| Replay `entries=[]` | 正常完成，Memory 认识不变，仍按 Gate 选择下一轮 Skill |

前三种情况统一保持 Sₜ 和 Mₜ。只有预先冻结了继续下一任务批次的策略，才发布轮次完成并递增 next_round；否则停在本轮正常完成位置。不能自动在同一批任务上反复请求更新。

## 8. Skill 与 Memory 的统一发布

正式状态只在本轮所有必要阶段完成后发布一次：

| Gate | 下一轮 Skill | 下一轮 Memory |
|---|---|---|
| ACCEPT | 实际 Candidate | Replay 更新后的 Active |
| RETAIN | 当前 Parent | Replay 更新后的 Active |

若 Gate 已 ACCEPT，但 Replay 连续技术失败，保存 Gate 结果并停止，正式状态仍指向旧 Skill 和旧 Memory。resume 完成剩余阶段后才统一发布。

建议按以下顺序实现：

1. 验证全部 Replay 提案，准备不可变 Archive 提交和本轮待发布 Active 快照。
2. 核验下一轮 Parent、Memory、轮次结果均已落盘且可读取。
3. 原子替换唯一正式 `state.json`，同时更新 Parent、Active Memory 引用和 next_round。

state.json 是唯一正式发布入口。发布前写入的 Archive 或快照不自动成为下一轮采用的正式 Memory。发布中断时，要么仍读取旧状态，要么读取完整新状态，不能得到新 Skill 加旧 Memory 的混合状态。

当前 `commit_memory()` 会立即切换目标目录的 active.json，实现时需要最小适配，使本轮更新先准备在待发布范围，正式读取以 Campaign 状态指定的快照为准。继续保留现有 Memory ID、Archive、证据展开、修订检查与同轮幂等规则，不重新实现学习或版本算法。

不可变 Archive 可以先保存；重复准备或重复恢复同一轮必须识别相同提交，不重新分配 M ID。未发布快照及失败产物保留以供审计，不作为后续轮次输入。初版按单个 Campaign 单写入者执行，不实现复杂并发调度或数据库事务。

## 9. 建议目录

```text
artifacts/methods/v23/campaign_001/
  config.json
  state.json
  rounds/
    R01/
      input.json
      parent_runs/
      grouping/
      diagnosis/
      preconditioner/
      editor/
      candidate_runs/
      pairs/
      gate/
      replay/
      memory/
      result.json
    R02/
```

模型阶段下建立 attempts，模块自身格式继续由现有运行器保存。阶段 result 指向明确的合法 Attempt，避免复制多份结果形成歧义。Memory 快照保持到共享不可变 Archive 的可解析来源，不因每轮目录不同而重置 M ID。

执行归档通过已有来源引用复用，不为每个模块重复复制整套轨迹。轮次 result 记录实际阶段产物、正常结束/技术停止/语义阻碍、任务尝试、总消耗及发布信息；这些程序信息不扩展模型输出契约。

## 10. 验证方案与后续实施边界

先完成无模型的串联测试，覆盖：

- ACCEPT、RETAIN、正常无更新、语义阻碍。
- 冻结任务完整覆盖、真实配对、技术失败不能计为普通失败。
- Memory 新增、修订、合并、空提案及来源读取。
- 模块三次技术失败停止、用户 resume、Attempt 编号和成本累积。
- Actor 单步与整任务预算分开、部分轨迹不拼接、已完成任务不重跑。
- Gate 已完成但 Replay 失败时，不提前发布 Skill。
- Memory 准备后、状态发布前及发布后的中断恢复，不重复提交。
- 下一轮准确读取上一轮所选 Skill 和 Memory；当轮新 Memory 不反向流入当轮 Preconditioner。
- 来源变化拒绝错误复用，全部现有模块回归通过，旧实验档案不变。

再单独冻结并开展 2～3 轮小规模真实验证：不同 Train 批次、parent=null、空 Memory 起步，固定任务数、步数、模型参数、所有重试与调用预算。

真实运行只核查实际发生的路径。不强制出现 ACCEPT、Memory 修订、非恒等 Adjustment 或失败恢复；相关分支通过离线故障注入覆盖。不得为展示某一结果而额外采样、挑选轨迹或临时修改 Prompt。

小规模验证首先证明持续运行和数据交接可靠性。是否积累了有效历史认识、是否合理影响后续更新，应按真实证据报告；训练批次成功数与工程通过不能直接证明泛化收益，最终仍需独立 Test。

本文保留已确认的机制设计。正式实现及至多两轮真实验证已单独获得授权，实际结果以[实现说明](EVOLUTION_DESIGN.md)及验证报告为准。

# 回归覆盖与保留

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v21 补强第 1 步：修改后新增退化的证据覆盖](#v21-regression-coverage)
- [v21 退化证据的跨轮保留](#v21-regression-retention)

<a id="v21-regression-coverage"></a>

## v21 补强第 1 步：修改后新增退化的证据覆盖

日期：2026-10-09。已实现自动覆盖、输入复验和后续引用通路；只读使用历史真实产物，没有调用真实模型、重新 rollout 或发布活动 head。

后续已完成 [issue 写回与复查边界](MEMORY.md#v21-issue-boundaries)，当前预检默认产物改为 `artifacts/methods/v21/v21_issue_boundaries/report.json`，Memory 输入为 99,761 个代理 token。本文保留本步当时的版本与测量数字。

### 1. 覆盖规则

原来的默认更新输入依赖修改前提案引用的案例，可能遗漏修改后才出现的问题。现在 `build_memory_update_input` 先检查本轮完整 Replay 的所有 Parent/Candidate 配对，再将以下配对与原选择范围取并集：

- 任务成功：Parent `true` → Candidate `false`；
- 程序合规：Parent `true` → Candidate `false`。

两维独立检查，一维改善不能抵消另一维退化。已有支持、历史来源和反证继续保留。程序扫描完整配对索引与标签，但只额外展开退化配对的双侧完整原始轨迹、事件和公共上下文，不默认把全轮所有轨迹送给模型。

这是一条确定性的输入选择规则，不是新的归因 Agent、效果分类或逐 edit Review。持久化 Memory、响应格式及 Gate 不变；仅增加输入清单 `regression_pair_refs`，用于让模型识别这些不能因修改前引用缺失而忽略的案例。

### 2. 校验与学习边界

- 检查本轮配对索引完整性、双方角色/版本绑定和 Level-0 布尔标签；材料不合法时停止，不将未知标签当成没有退化。
- 调用方即使传入空的显式选择，也不能关闭自动退化覆盖。调用前重建规范输入，删除退化标记、配对或事件会被拒绝。
- 继续使用无损输入表示。超预算在模型调用前停止，不通过删除必需配对或反证降低输入。
- Prompt 要求结合双侧原文检查退化。标签下降是运行观察，不足以证明某条修改导致退化；标签不变也不能证明行为没有变差。
- 有依据时将新观察关联到相关问题/尝试；没有关联依据时保留不确定性。允许引用原始事件建立尚无尝试的新问题，不伪造 edit 归属，不把每组退化复制到所有 issue。
- 新认识引用的退化事件通过已有派生档案进入下一轮局部 Review。未被引用的原始配对仍保存在完整档案中；本步不承诺每组退化都会被模型正确解释或在下一轮自动选中。

本步保证的是**两维标签新增退化的输入覆盖**，不保证因果归因正确，也不能自动发现两维布尔标签均未变化时的新增错误。没有新增逐配对处置表、强制逐 edit 分析或额外模型调用。

### 3. 真实历史材料的离线验收

材料来自 `v20_pilot_001_continuation_grouping24k/round-04`，经既有 v21 证据接口只读转换。它是历史证据预检，不是新的 v21 Pilot。

| 检查项 | 补齐前 | 补齐后 |
|---|---:|---:|
| 本轮完整回放配对 | 36 | 36 |
| 默认更新输入中的配对 | 6 | 9 |
| 默认输入覆盖的标签退化配对 | 0 | 3 |
| 原始事件数 | 539 | 675 |
| 已加载历史问题数 | 3 | 3 |
| 代理输入 token | 84,051 | 99,405 |

新覆盖 **T005、T022、T036**，均为任务成功 `true → false`，合规保持 `true`。双侧事件分别为 20/16、26/37、21/16，均逐项对照档案原文验证。这里不能据标签认定三组退化由本轮修改导致。

新增约 15,354 个代理 token 来自扩大证据范围及提示调整，不是相同范围的压缩效率比较。统计使用 cl100k_base 代理估计，不是网关实测用量；包含安全余量与输出预留为 152,353。此前无损优化报告保持不变。

当前报告：[report.json](../../../artifacts/methods/v21/v21_regression_coverage/report.json)。复现命令：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/runs/v21/preflight_v21_input_budget.py
```

本步当时脚本默认写入上述位置；后续默认路径见本文开头。同内容可重跑，不同内容拒绝覆盖。它校验旧选择范围、自动新增覆盖和双侧事件完整性，并检验模型输入可精确还原。`scripts/runs/v21/update_v21_memory.py` 的默认零模型预检也输出扫描配对数和退化配对数。

### 4. 实现与版本

- [memory_update_v21.py](../../../src/skill_evolution/v21/memory_update_v21.py)：完整当前标签扫描、自动并集和规范输入复验。
- [memory_update_prompt_v21.py](../../../src/skill_evolution/v21/memory_update_prompt_v21.py)：退化证据使用及不确定性约束。
- [test_regression_coverage_v21.py](../../../tests/skill_evolution/v21/test_regression_coverage_v21.py)：22 项专项测试，包括两维分别退化、相反方向变化、旧轮隔离、不可漏选、预算失败，以及新问题到下一轮 Review 的引用通路。

输入版本为 `memory_update_input_v21.2`，Prompt 为 `memory_update_v21.3`。旧规范证据档案可继续读取；旧 Prompt 的调用检查点不能以新版请求恢复，应使用新独立目录。Memory 持久化 schema 保持原样。

专项测试连同既有 v21 更新/消费/表示/证据通路，以及 v20 生成/运行/Fusion/Memory/campaign 和 Replay 回归，共 **179 项通过**。模拟响应验证工程通路，不代表真实模型已学会正确归因。

下一步仍是收紧 issue 的写回与复查边界。本步没有宣称解决历史内容混杂、认识压缩或完整 campaign 发布。

<a id="v21-regression-retention"></a>

## v21 退化证据的跨轮保留

日期：2026-10-10。对应真实模型局部对照之后的优化第 1 步。

本步针对 [局部对照](VALIDATION_CASES.md#v21-local-comparison-report) 中的具体断点：T009 的退化配对进入了 Memory 更新输入，却没有被新认识引用，下一轮行李 Review 未加载该显式配对。原始证据并未从档案删除；缺口是认识与来源的关联没有形成。Review 对另一条已经加载的正面历史回应不足，是后续第 2 步的问题，本步不宣称一并解决。

### 改动范围

1. **强化同一次 Memory 更新的要求。** Prompt 升至 `memory_update_v21.6`，要求返回前核对现有 `regression_pair_refs`：将相关两维变化、可见行为和条件、反例与未知写入合适的认识，并引用实际 Parent/Candidate 原始事件。无法确定原因时保留观察，不强归因到 edit；没有可归属的真实修改时，可以沿用 `NEW/...` issue、`attempts=[]` 保存独立问题。不得篡改原 problem、复制所有退化给所有 issue 或用无关引用凑覆盖。
2. **增加独立的来源保留核查。** `regression_retention_report` 重新验证模型结果，检查每个当前退化配对是否被最新 issue 认识直接引用，引用来自哪一侧，以及通过现有 issue 局部读取能否取回双侧完整原文。记录两维原始标签、issue/认识引用和原始事件位置，供离线复查。
3. **保存与显式展示。** 新的成功更新额外保存 `regression-retention.json`，纳入 `complete.json` 文件哈希；CLI 显示报告路径、未引用数量和仅单侧引用数量。恢复时复验报告，发生变化拒绝覆盖，不额外调用模型。已有历史结果可用独立只读脚本核查，报告写到历史目录以外。

保持原有 Memory schema、响应字段、input v21.4 和 result v21.1，不新增运行时状态、分类、Agent、Review 或每条 edit 的归因流程。Fusion/Review Prompt 不变。**2,000 字符硬上限保持不变。** 本次没有把任何行李规则或预期案例答案写入 Prompt。

### 如何理解核查报告

| 报告项 | 含义 | 不代表什么 |
|---|---|---|
| `uncited_pair_refs` | 没有最新 issue 认识直接引用该配对的原始事件 | 不代表原始档案已丢失，也不代表必须强行关联到已有 issue |
| `one_sided_pair_refs` | 存在直接引用，但没有同一个 issue 同时引用该配对双侧事件 | 不代表另一侧原文一定不可读取，也不把不同 issue 的单侧引用拼成一份完整认识 |
| `review_has_complete_pair` | 选择该 issue 后，现有读取接口能取回此配对及双侧全部原文 | 不证明 Fusion 实际选择了该 issue，也不证明 Review 理解或使用了证据 |
| `unreadable_pair_refs` | 已有关联，但至少一个相关 issue 的局部读取未恢复完整配对 | 用于发现来源通路问题，不是新效果类别 |

最新认识的直接证据及其保留反例参与核查；同一 Parent 的显式别名按 `parent_pairs` 还原，不视作独立样本。共享 edit 展开的其他上下文不能自动算成该 issue 的认识。完整尝试、旧认识和原始档案继续保留，既有“已关联退化在摘要更新后仍可回查”逻辑不变。

**这是来源与可读取性核查，不是语义通过判定，也不是新的采用 Gate。** 报告不会自动创建 issue、添加引用、修改认识、生成 Skill 或触发重试。即使引用齐全，也可能存在错误归因；即使有关联缺口，也不能为了清空报告而虚构行为缺陷。结构校验通过而仍有未引用退化的结果会连同明确报告保存，不伪装为语义验收通过。

模型应优先保留证据支持的观察及限制。只有标签变化、缺乏可定位的行为缺陷时，不据此编造修复建议；能够描述有界问题但原因未知时可以记录未知。后续 Skill 决策仍允许 NO_EDIT，不以修复单个案例为修改合理性的唯一依据。

### 历史真实材料核查

对上一轮真实实验中通过校验的 `update-48k` 原始响应重新验证，并生成 [historical-audit.json](../../../artifacts/methods/v21/v21_regression_retention/historical-audit.json)：

| 第 3 轮配对 | Parent → Candidate（成功，合规） | 核查结果 |
|---|---|---|
| T009 | (true, true) → (true, false) | 最新认识未引用，准确复现遗漏 |
| T013 | (true, false) → (false, true) | 同一认识引用双侧，相关 issue 可读取完整配对 |
| T034 | (true, true) → (false, true) | 最新认识仅直接引用 Candidate，但相关 issue 仍可读取完整双侧 |

这份报告使用**原实验的模型答案**，未手工补写 T009、未伪造更新后的 Memory，也未修改原实验目录。它证明遗漏能够被定位，不证明新 Prompt 已使真实模型补齐遗漏。新 Prompt 的语义效果保留到分阶段真实复验中检查。

同一真实输入的 [Prompt 预检](../../../artifacts/methods/v21/v21_regression_retention/prompt-preflight.json) 确认：user payload 和响应 schema 不变，无损展开仍与规范输入完全一致；代理输入由 170,463 增至 170,793 token，仅增加 330。没有借本步截断原始证据或改变模型输出预算。

复现命令（项目根目录）：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/analysis/v21/audit_v21_regression_retention.py \
  --evidence artifacts/methods/v21/v21_memory_step4_preflight/round-03-import.json \
  --expected-ref MODIFICATION_EVIDENCE_V21/3c1e2820f9a215ed9c496fba10565a83c09c5011eaf898e60ac923f07484ff7a \
  --update artifacts/methods/v21/v21_local_comparison_001/update-48k \
  --output artifacts/methods/v21/v21_regression_retention/historical-audit.json
```

旧 Prompt 调用不能冒充新 Prompt 恢复。离线核查允许读取兼容的旧输入和原始完整响应，并按其原请求复验响应检查点；这与用新版 Prompt 恢复旧运行不同。报告内容相同可以重跑，内容不同拒绝覆盖。

### 验收范围

专项测试覆盖：遗漏不自动分配 issue；单侧引用与完整回查的区别；不同 issue 的双侧不能拼接；Parent 别名；无实际 edit 的新观察进入 Fusion 和所选 Review；双侧原文完整；核查文件保存/恢复及篡改拒绝；结果与原响应一致性；无退化不增加保留义务；共享 edit 上下文不算认识归属。

专项新增 11 项测试，与相关 v21/v20/Replay 回归合计 **210 项通过**。这些是受控工程测试，构造响应不冒充真实模型认识。相关回归继续检查旧记录兼容、过去退化/反例保留、固定 problem 边界、2,000 字符拒绝、预算与无损引用。没有新增真实模型调用、Replay 或活动 Skill/Memory 发布。

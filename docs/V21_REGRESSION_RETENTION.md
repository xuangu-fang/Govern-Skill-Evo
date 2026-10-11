# v21 退化证据的跨轮保留

日期：2026-10-10。对应真实模型局部对照之后的优化第 1 步。

本步针对 [局部对照](V21_LOCAL_COMPARISON_REPORT.md) 中的具体断点：T009 的退化配对进入了 Memory 更新输入，却没有被新认识引用，下一轮行李 Review 未加载该显式配对。原始证据并未从档案删除；缺口是认识与来源的关联没有形成。Review 对另一条已经加载的正面历史回应不足，是后续第 2 步的问题，本步不宣称一并解决。

## 改动范围

1. **强化同一次 Memory 更新的要求。** Prompt 升至 `memory_update_v21.6`，要求返回前核对现有 `regression_pair_refs`：将相关两维变化、可见行为和条件、反例与未知写入合适的认识，并引用实际 Parent/Candidate 原始事件。无法确定原因时保留观察，不强归因到 edit；没有可归属的真实修改时，可以沿用 `NEW/...` issue、`attempts=[]` 保存独立问题。不得篡改原 problem、复制所有退化给所有 issue 或用无关引用凑覆盖。
2. **增加独立的来源保留核查。** `regression_retention_report` 重新验证模型结果，检查每个当前退化配对是否被最新 issue 认识直接引用，引用来自哪一侧，以及通过现有 issue 局部读取能否取回双侧完整原文。记录两维原始标签、issue/认识引用和原始事件位置，供离线复查。
3. **保存与显式展示。** 新的成功更新额外保存 `regression-retention.json`，纳入 `complete.json` 文件哈希；CLI 显示报告路径、未引用数量和仅单侧引用数量。恢复时复验报告，发生变化拒绝覆盖，不额外调用模型。已有历史结果可用独立只读脚本核查，报告写到历史目录以外。

保持原有 Memory schema、响应字段、input v21.4 和 result v21.1，不新增运行时状态、分类、Agent、Review 或每条 edit 的归因流程。Fusion/Review Prompt 不变。**2,000 字符硬上限保持不变。** 本次没有把任何行李规则或预期案例答案写入 Prompt。

## 如何理解核查报告

| 报告项 | 含义 | 不代表什么 |
|---|---|---|
| `uncited_pair_refs` | 没有最新 issue 认识直接引用该配对的原始事件 | 不代表原始档案已丢失，也不代表必须强行关联到已有 issue |
| `one_sided_pair_refs` | 存在直接引用，但没有同一个 issue 同时引用该配对双侧事件 | 不代表另一侧原文一定不可读取，也不把不同 issue 的单侧引用拼成一份完整认识 |
| `review_has_complete_pair` | 选择该 issue 后，现有读取接口能取回此配对及双侧全部原文 | 不证明 Fusion 实际选择了该 issue，也不证明 Review 理解或使用了证据 |
| `unreadable_pair_refs` | 已有关联，但至少一个相关 issue 的局部读取未恢复完整配对 | 用于发现来源通路问题，不是新效果类别 |

最新认识的直接证据及其保留反例参与核查；同一 Parent 的显式别名按 `parent_pairs` 还原，不视作独立样本。共享 edit 展开的其他上下文不能自动算成该 issue 的认识。完整尝试、旧认识和原始档案继续保留，既有“已关联退化在摘要更新后仍可回查”逻辑不变。

**这是来源与可读取性核查，不是语义通过判定，也不是新的采用 Gate。** 报告不会自动创建 issue、添加引用、修改认识、生成 Skill 或触发重试。即使引用齐全，也可能存在错误归因；即使有关联缺口，也不能为了清空报告而虚构行为缺陷。结构校验通过而仍有未引用退化的结果会连同明确报告保存，不伪装为语义验收通过。

模型应优先保留证据支持的观察及限制。只有标签变化、缺乏可定位的行为缺陷时，不据此编造修复建议；能够描述有界问题但原因未知时可以记录未知。后续 Skill 决策仍允许 NO_EDIT，不以修复单个案例为修改合理性的唯一依据。

## 历史真实材料核查

对上一轮真实实验中通过校验的 `update-48k` 原始响应重新验证，并生成 [historical-audit.json](../artifacts/v21_regression_retention/historical-audit.json)：

| 第 3 轮配对 | Parent → Candidate（成功，合规） | 核查结果 |
|---|---|---|
| T009 | (true, true) → (true, false) | 最新认识未引用，准确复现遗漏 |
| T013 | (true, false) → (false, true) | 同一认识引用双侧，相关 issue 可读取完整配对 |
| T034 | (true, true) → (false, true) | 最新认识仅直接引用 Candidate，但相关 issue 仍可读取完整双侧 |

这份报告使用**原实验的模型答案**，未手工补写 T009、未伪造更新后的 Memory，也未修改原实验目录。它证明遗漏能够被定位，不证明新 Prompt 已使真实模型补齐遗漏。新 Prompt 的语义效果保留到分阶段真实复验中检查。

同一真实输入的 [Prompt 预检](../artifacts/v21_regression_retention/prompt-preflight.json) 确认：user payload 和响应 schema 不变，无损展开仍与规范输入完全一致；代理输入由 170,463 增至 170,793 token，仅增加 330。没有借本步截断原始证据或改变模型输出预算。

复现命令（项目根目录）：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/audit_v21_regression_retention.py \
  --evidence artifacts/v21_memory_step4_preflight/round-03-import.json \
  --expected-ref MODIFICATION_EVIDENCE_V21/3c1e2820f9a215ed9c496fba10565a83c09c5011eaf898e60ac923f07484ff7a \
  --update artifacts/v21_local_comparison_001/update-48k \
  --output artifacts/v21_regression_retention/historical-audit.json
```

旧 Prompt 调用不能冒充新 Prompt 恢复。离线核查允许读取兼容的旧输入和原始完整响应，并按其原请求复验响应检查点；这与用新版 Prompt 恢复旧运行不同。报告内容相同可以重跑，内容不同拒绝覆盖。

## 验收范围

专项测试覆盖：遗漏不自动分配 issue；单侧引用与完整回查的区别；不同 issue 的双侧不能拼接；Parent 别名；无实际 edit 的新观察进入 Fusion 和所选 Review；双侧原文完整；核查文件保存/恢复及篡改拒绝；结果与原响应一致性；无退化不增加保留义务；共享 edit 上下文不算认识归属。

专项新增 11 项测试，与相关 v21/v20/Replay 回归合计 **210 项通过**。这些是受控工程测试，构造响应不冒充真实模型认识。相关回归继续检查旧记录兼容、过去退化/反例保留、固定 problem 边界、2,000 字符拒绝、预算与无损引用。没有新增真实模型调用、Replay 或活动 Skill/Memory 发布。

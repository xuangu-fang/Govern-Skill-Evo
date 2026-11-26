# SearchQA v28.2 — Diagnosis / Preconditioner Prompt v2

2026-11-04。按用户确认的五组调整及 Parent 指导微调实施。保留 SearchQA 已有适配，正式训练与 Test 未启动。

## 当前身份与范围

| 项目 | 修订前 | 修订后 |
|---|---|---|
| Diagnosis Prompt | `v28_2_searchqa_diagnosis_v1` | `v28_2_searchqa_diagnosis_v2` |
| Preconditioner Prompt | `v28_2_searchqa_preconditioner_v1` | `v28_2_searchqa_preconditioner_v2` |
| 方法 / stage | `v28_2_campaign_v1` / `v28_2_stages_v1` | 不变 |
| 五模块输出合同、输入视图、Gate / Memory | 原 v1 合同 | 不变 |
| Grouping / Editor / Replay Prompt | 原 v1 | 原文与版本不变 |
| Actor / 评分 / 调度 / 预算 / 重试 | 原 v28.2 参数 | 不变 |

运行器仍直接读取 [Diagnosis](../../prompts/diagnosis.md) 与 [Preconditioner](../../prompts/preconditioner.md)。仅两个 Python 模块的 `PROMPT_VERSION` 常量和配置内对应两个 `method.prompts` 值改变；未调整运行逻辑。方法版本保留是因为算法和结构合同未变，Prompt 身份与冻结原文已足以区分请求、配置和恢复边界。

## 五组调整的落点

1. **完整决策修正**：不同任务可支持同一修正，任务/Group 不是 Update 单元；同错误标签不自动合并不同修正。取消按预期成功、失败、保留或撤回来拆分；保留动作、条件、例外和必要配合，不预设数量。
2. **Parent 与行为增量**：不把执行错误解释为 Parent 必有缺口。评估缺失、误导、冲突或难以落实，也保留未正确应用、被其他要求压过、遵循不可观测、能力限制或证据不足的可能；不虚构内部过程。解释可用判断增量，允许删改/协调指导，没有合理修正时允许 no_change。
3. **成功与反例**：使用已有相关对照确定哪些可见差异影响动作、范围、优先级；不强制正反配对或每种情形的成功验证。单案例可支持合理试验；条件偏好也需要范围依据，不用改弱措辞掩盖不合理范围。
4. **附带改变与必要协调**：名称、编码、单位、答案范围等附加变化需要相关依据或必要性；尊重问题具体要求和固定协议。KEEP 审查整条，REPLACE 保留合理方向、修正附加要求；不为让修改小而删除必要配合。
5. **证据解释**：多种参考可接受不建立形式偏好；明确提供的成功保持只提供有限任务级证据，不能算作另一项新增改善。缺少 Knowledge/关联不证明保持成功，尚未执行的提案不能声称已有成效。

原位融合，不增加输出字段、必填审查清单、模型调用或额外评估阶段。保留实体/关系/答案边界/参考形式区分、完整 question/context 可见性、实际使用不可观测性、原生 EM/F1 归一化和历史解释边界。Diagnosis 与 Preconditioner 分别约增加 281 / 257 个空白分词，仅表示文本规模变化，不作为效果指标。

## 基线与差异

- [修订前五份 Prompt](baseline/prompts/) 与 [修订前配置](baseline/campaign_config.json) 为本轮开始时的原文快照，不是可运行的第二条链路。
- [Diagnosis v1 → v2](diffs/diagnosis_v1_to_v2.diff)、[Preconditioner v1 → v2](diffs/preconditioner_v1_to_v2.diff)。
- [原来源索引](baseline/source_map.json)、[原审阅记录](baseline/PROMPT_REVIEW.md) 保留历史；当前规范见 [当前审阅](../../PROMPT_REVIEW.md)。
- [范围与绑定核对](scope_validation.json) 使用直接字节/结构比较，不使用哈希清单。

当前配置是 [v28_2_searchqa_train600_batch30.json](../../../../../experiments/configs/v28_2_searchqa_train600_batch30.json)。旧 Prompt v1 的配置和请求归档不能在当前 v2 绑定下继续执行，现有检查会在方法请求前拒绝版本或文本不匹配；不覆盖旧归档，不重置请求额度，也不自动迁移旧运行。

## 离线验收

本轮离线验收 **274 / 274 全部通过**：v28.2 118 项（含新增 4 项修订测试），SearchQA v28/v28.1 回归 156 项；失败、错误、跳过均为 0。另有 16 项原文/结构范围核对全部通过。网络/子进程访问触发 0，真实模型请求 0，新增正式 v28.2 实验目录 0。

从仓库根目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam \
  /Users/didi/miniforge3/envs/SearchQA/bin/python \
  scripts/verification/verify_v28_2_offline.py --with-regressions \
  --output docs/methods/v28_2/revisions/prompt_v2
```

结果见 [offline_acceptance.json](offline_acceptance.json) 和 [完整日志](offline_acceptance.log)。本轮运行全部 v28.2 测试及 SearchQA v28/v28.1 回归；没有重跑未改动的 DocVQA 链路，不将初始实现的 777 项历史结果计作本轮结果。

新增四项测试覆盖：

- 配置只改变两个 Prompt 身份；实际加载当前文本；保留 SearchQA 证据/评分/Actor 协议、历史视图及输出合同原文。
- 旧配置与初始化的 v1 campaign 在 v2 下恢复被拒绝，且无模型请求或归档改写。
- 旧 Prompt 身份，或带新版身份但使用旧文本的调用，在方法请求前被拒绝。
- 多个当前执行依据可支持同一完整修正；REPLACE 删除无依据附加要求，保留 goal、ID、basis 和完整必要行为，并正确投影至 Editor。

既有测试继续覆盖 no_change/全撤回/空或 null patch、EM 翻转与 F1-only、归因和 Gate、Memory 追加与原子发布、请求恢复，以及临时合成 600 / 1,400 调度。合成响应不能证明真实模型的判断合理或测试成功率提升。

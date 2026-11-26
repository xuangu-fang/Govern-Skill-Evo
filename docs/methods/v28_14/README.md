# SearchQA v28.14

基于 v28.13 的独立版本。只调整 Diagnosis、Preconditioner、Editor 的 Prompt 及版本绑定，目标是让同一个判断在 Skill 中有明确位置，完整替换旧的重复表达，并统一规则、条件、例外和例子的组织。未启动真实训练或 Test。

## 调整范围

| 模块 | 新要求 |
| --- | --- |
| Diagnosis | 在分配 Update ID 前，将同一判断的通常做法、适用条件和必要例外归为一个 Original，即使不同条件要求不同动作；不拆开默认行为和必要例外，不因题材、实体或措辞不同重复提案。独立判断仍分别处理。写默认答案类别前，区分提示候选解释的题面线索与能区分合理替代解释的证据。证据不足时，只提出具体可执行的检查、缩小范围或 no_change。 |
| Preconditioner | 在现有 Update text 中明确负责该决策的 Parent 位置、本次贡献，以及要替换／删除的旧句子、条目和例子。多处共同规定同一判断时，指定一个保留位置、迁入必要条件和例外，并明确删除被完整覆盖的旧表达。保留独立判断，不合并 ID 或篡改 basis。 |
| Editor | 通读 Parent 和 Plan 后，在授权范围内落实完整替换；一个 Update 可以有多个修改位置。Workflow 按支持的判断先后组织，特殊题型保留为条件或避错指导，不充当普适开头。两个章节均在正文写可迁移判断，例外紧随所属步骤或规则，具体例子统一作为缩进子项下挂；允许只有正例，不强制补例子或编造反例。提交前检查判断是否仍分散、指令是否过强、例子与例外是否位置混乱。 |

Preconditioner 的归属、贡献和替换范围是文字要求，不增加 JSON 字段。Editor 没有原始执行证据，不自行发明缺失条件或扩大整理范围；需要实质性未决选择时沿用既有 blocker 机制。新例子仍只取直接引用的当前训练 reference_answers 和 extracted_answer；不从 Test 或 Memory 收集答案对。

篇幅 3,000–4,000 字符软预算、最多五条独立 safeguards、默认 1–2 个代表例子、每轮最多四条有效 Update 均沿用 v28.13。新增例子优先替换解释同一区别的较弱例子，必要边界不因数量或长度而删除。格式遵从性仍由模型生成决定，没有增加硬格式校验或自动美化。

2026-11-12 复审修正仅涉及上述 Diagnosis 归并边界和 Editor 跨章节例子格式。Diagnosis Prompt 绑定升级为 `v28_14_searchqa_diagnosis_decision_grouping_v2`，Editor 升级为 `v28_14_searchqa_editor_integrated_rules_v2`，同步到运行配置和离线验证器。Preconditioner Prompt 及其 v1 绑定保持不变，原有五条独立 safeguards 上限不作调整。原 v28.14 的 Diagnosis／Editor v1 绑定不能作为修订后配置继续运行。

## 保持不变的机制

- Gate 源文件与 v28.13 **逐字节相同**，继续使用 `v28_13_gate_net_em_min2_v1` 合同。对每条非空 Update：归因净改善 N ≥ 2 为 Retain，N = 0/1 为 Defer，N < 0 为 Reject；空补丁不参与决策。没有精简例外，也没有 OR Gate。
- 沿用同批 Parent/Candidate、逐 Update 补丁、Replay 关联、选中补丁重组、追加式 Memory、模型调用预算、重试与恢复流程。Replay Prompt 逐字节不变。
- 600 道优化题，10 批 × 60；独立 Test 1,400 题；Train/Test 并发 60/15；Actor、模型、评分、任务顺序和预算不变。
- 初始 Skill 内容与 v28.13 相同，只有主标题、Workflow 和 Error Avoidance 两个空章节；在 v28.14 单独保存文件与路径绑定。
- 不增加独立精简轮次、历史边界复验或 Gate 后整理。没有净改善的纯排版修改仍可能 Defer。

G/L 仍来自联合 Candidate 和 Replay 关联，不是单个补丁的独立因果效果。若选中组合没有精确对应的执行，继续使用 selected_execution_source=null，不借用完整 Candidate 分数。

## 独立文件

- 源码：`src/skill_evolution/v28_14/`
- Prompt：[Diagnosis](prompts/diagnosis.md)、[Preconditioner](prompts/preconditioner.md)、[Editor](prompts/editor.md)
- 配置：`experiments/configs/v28_14_searchqa_train600_batch60.json`
- 初始模板：`experiments/configs/v28_14_searchqa_initial_skill.md`
- 入口：`scripts/runs/run_v28_14_campaign.py`

v28.13 的源码、Prompt、配置、入口、初始模板、测试及验证器均保留。v28.14 不导入 v28.13 的方法模块，也不接受 v28.13 的 campaign 配置恢复；共享基础组件继续复用。相同 schema 的合同身份沿用旧值，不表示执行时调用旧版本模块。

## 离线验证

2026-11-12 修正后验证通过：157 项测试（共享基础 v28.5：131；v28.13：12；v28.14：14），0 失败、0 错误、0 跳过。真实数据配置预检通过，新 Prompt 绑定生效，已被替代的 v28.14 Diagnosis／Editor v1 绑定被拒绝。Gate 源码和 Replay Prompt 与 v28.13 逐字节一致；34 个受保护的 v28.13 文件未变。网络／子进程调用尝试为 0，真实模型调用为 0，未启动真实训练或 Test。

```sh
/Users/didi/miniforge3/envs/SearchQA/bin/python scripts/verification/verify_v28_14_offline.py \
  --output artifacts/verification/v28_14_prompt_review_20261112 \
  --baseline artifacts/verification/v28_14_prompt_review_20261112/v28_13_before.json
```

验证期间阻断网络、DNS 和子进程；只使用人工编写的模拟输出和只读真实数据预检。检查内容：

- Gate 与 Replay Prompt 逐字节相同；其他运行源码仅有版本与资源路径绑定变化。
- 三个新 Prompt 确实通过正常调用路径发送，Actor 协议原文仍一致。
- 配置除版本身份和同内容模板路径外不变；旧配置和旧模板路径绑定不被新版本接受。
- 继承的 Gate 边界、无变化、空补丁、选择组合、Memory、恢复、模板八种子集等测试。
- 人工编写的规则整合场景：保留 Update ID 与 basis、撤回重复提案、一个补丁完整替换多处规则、保留必要例外与无关指导、独立 Update 的选择子集，以及真实流程中的模拟执行、筛选与恢复。
- 对实施前 34 个 v28.13 文件进行哈希核对。

[本次验证报告](../../../artifacts/verification/v28_14_prompt_review_20261112/validation.json) · [测试日志](../../../artifacts/verification/v28_14_prompt_review_20261112/unittest.log) · [v28.13 基线](../../../artifacts/verification/v28_14_prompt_review_20261112/v28_13_before.json) · [修正范围核对](../../../artifacts/verification/v28_14_prompt_review_20261112/revision_scope.json)

保留 [2026-11-11 初版验证报告](../../../artifacts/verification/v28_14_offline_20261111/validation.json)，本次输出存入独立目录。

这些检查证明软件流程与内容交接可用，不证明真实模型一定合并规则或提高效果。模拟整合材料不取自已完成实验的 Test 结果，也没有将历史最终 Skill 中的具体答案写入正式初始模板或 Prompt。

只读入口预检：

```sh
/Users/didi/miniforge3/envs/SearchQA/bin/python scripts/runs/run_v28_14_campaign.py train \
  /tmp/v28_14_validate_only \
  --config experiments/configs/v28_14_searchqa_train600_batch60.json --validate-only
```

该命令不读取凭据、不创建训练目录、不调用模型。

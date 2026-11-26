# SearchQA v28.13

基于 v28.12 的独立版本：调整 Diagnosis、Preconditioner、Editor 的写作提示词，使 Skill 按作答流程、避错规则及具体正反例组织；Gate 统一要求净改善至少两题，取消篇幅条件。未启动真实训练或 Test。

## 流程与版本隔离

沿用 Parent → Diagnosis → Preconditioner → Editor → Candidate → Replay → 分项 Gate → Selected Skill / Memory 的流程。保持逐 Update 补丁、联合 Candidate 执行、Replay 关联、选中补丁重组、追加式 Memory 和恢复校验。

独立源码在 `src/skill_evolution/v28_13/`，入口为 `scripts/runs/run_v28_13_campaign.py`，配置为 `experiments/configs/v28_13_searchqa_train600_batch60.json`。v28.12 文件不修改，不将其历史运行或 checkpoint 当成 v28.13 恢复。共享 SearchQA 执行环境和底层基础组件继续复用。

数据与执行条件沿用 v28.12：600 道优化任务、10 批 × 60，独立 Test 1,400 题；初始 Skill 改用独立的 `experiments/configs/v28_13_searchqa_initial_skill.md`，只包含主标题和两个空章节 `Workflow`、`Error Avoidance`，不含学习规则；Actor 与四个模块的模型参数、输出预算、重试及并发不变。Replay Prompt 保持逐字一致。

## 初始模板与 Prompt 复查修订

2026-11-11 复查后，按用户选择为 v28.13 单独建立空章节模板，保留 v28.12 及共享旧模板不变。三个 Prompt 身份升级为 v2，配置绑定新的文本与模板；Gate 和执行流程不变。

```markdown
# Question Answering Skill

## Workflow

## Error Avoidance
```

首轮补丁只向现有章节添加内容，不创建、移动或删除公共标题。离线测试覆盖三条独立 Update（其中两条位于同一章节）的全部八种选择子集，以及实际模拟 Gate 筛选后下一轮 Parent 的标题保留。

其余修订：Preconditioner 的重复过滤不再因一般规则已存在而自动撤回有当前证据支持的新例子；Editor 的空补丁判断检查完整授权修订，包括例子和表达支持。默认每条规则 1–2 个例子，更多例子以非重复说明价值判断，不强制新增行为边界；无需例子时仍可 KEEP。新答案对明确取当前样本的 `outcome.reference_answers` 中一项和评分所用 `outcome.answer.extracted_answer`，不复制完整回复、推理或答案包装标签，提取失败时不强凑对照。

## 三个 Prompt

- [Diagnosis](prompts/diagnosis.md)：先表达可迁移规则，再分开描述必要边界。允许每条提案附 1–2 组当前直接引用证据中的参考答案／实际错误回答。保留原文，需要时带短题干条件；不编造、不采集 Test 或 Memory 答案对。规则和例子放在 `text`，来源用 `basis`，分析用 `reason`，不增加字段。
- [Preconditioner](prompts/preconditioner.md)：为决策确定主要位置，Workflow 放作答动作，Error Avoidance 放独立避错指导。明确保留的总结、边界、例子及局部整理授权。同类例子优先替换、合并，必要边界优先保留。例子可以说明已有区别，不必引入新行为分支。每轮最多四条有效 Update、最多五条独立 safeguards 和 3,000–4,000 字符软预算继续保留。
- [Editor](prompts/editor.md)：明确两节结构；Workflow 使用有序步骤；Error Avoidance 使用短总结、单列的必要边界和下挂 `'Expected' not 'Incorrect'` 子列表。提供完整占位格式示例。只实现 Effective Plan 授权内容，重新整理受影响条目而不是不断追加句子。结构修改仍需明确归属和满足补丁重组约束。

章节与例子属于写作要求，不新增格式 Gate、自动格式修复或 Gate 后美化。空章节不应靠虚构规则填充。Prompt 无法硬性保证模型在所有选择组合下都输出理想结构；格式遵从性须在未来真实执行中观察。

## Gate

对每条非空 Update 补丁，G 是 Replay 关联的错转对题数，L 是对转错题数，N = G − L。

| 条件 | 决策 |
| --- | --- |
| 空补丁 | 不参与决策 |
| N ≥ 2 | Retain |
| N = 0 或 1 | Defer |
| N < 0 | Reject |

Defer 本轮不合入，不建立后续待验证队列。取消“净改善一题且不变长”和“无改善但纯精简且缩短”两条通道。

`delta_chars` 和兼容字段 `pure_simplification` 继续记录，以保持审计结构；`_decision` 仅接收补丁与 G/L，不读取这两个字段。新 Preconditioner 输出不要求精简标记，旧 schema 的布尔验证仍保留。篇幅只用于 Prompt 写作引导和日志观察。

G/L 来自联合 Candidate 的结果与 Replay 关联，不代表单条补丁被独立执行后证实的因果收益。选择组合无对应执行时继续记录 `selected_execution_source=null`，不冒用完整 Candidate 的分数。

## 离线验证

本次修订验证通过：148 项测试（共享基础 v28.5：131；v28.12：5；v28.13：12），0 失败、0 错误、0 跳过。真实数据配置预检通过；31 个受保护文件（v28.12 的 30 个文件及共享旧初始模板）未变；网络／子进程调用尝试为 0，真实模型调用为 0，未启动真实训练或 Test。

首次实现的历史离线报告见 [原始验证报告](../../../artifacts/verification/v28_13_offline_20261111/validation.json)。本次模板与 Prompt 修订使用下列独立目录保存最新验证结果，不覆盖原始报告。

```sh
/Users/didi/miniforge3/envs/SearchQA/bin/python scripts/verification/verify_v28_13_offline.py \
  --output artifacts/verification/v28_13_prompt_review_20261111 \
  --baseline artifacts/verification/v28_13_prompt_review_20261111/v28_12_before.json
```

验证器阻断网络连接、DNS 与子进程调用；使用人工编写的模拟响应运行流程，并对真实数据和配置做只读预检。覆盖净改善 1/2 题边界与长度/兼容标记无关、零改善精简 Defer、空补丁、无变化分支、未归因及相抵变化、选择重组、下一轮 Parent、Memory、恢复、例子传递及实际 Prompt 绑定。还运行 v28.12 与共享基础流程的回归测试。

基线清单记录实施前 v28.12 源码、Prompt、测试、配置和入口文件的 SHA-256；验证器核对其保持不变，并保护共享旧初始模板，比较 v28.13 除 Gate 外的运行代码仅有版本绑定与初始模板路径变化。

[最新验证报告](../../../artifacts/verification/v28_13_prompt_review_20261111/validation.json) · [测试日志](../../../artifacts/verification/v28_13_prompt_review_20261111/unittest.log) · [受保护文件基线](../../../artifacts/verification/v28_13_prompt_review_20261111/v28_12_before.json)

只读入口预检（不创建 campaign、不读取凭据）：

```sh
/Users/didi/miniforge3/envs/SearchQA/bin/python scripts/runs/run_v28_13_campaign.py train \
  /tmp/v28_13_validate_only \
  --config experiments/configs/v28_13_searchqa_train600_batch60.json --validate-only
```

这些检查验证软件流程和格式传递，不证明真实模型会遵守版式，也不提供 benchmark 效果结论。本版同时改变初始模板、Prompt 和 Gate，未来与 v28.12 的整体差异不能单独归因于阅读结构。

# v21 第 4 步：让双维认识参与下一轮修改

日期：2026-10-09。状态：已接通更新后的 Memory → Fusion → 现有局部 Review → Compiler/Editor，并验证候选及认识来源能进入下一轮修改后证据档案。完成离线测试与历史真实产物预检；未运行真实模型、重新 rollout 或发布活动 head。完整 campaign 的恢复、原子发布和两轮真实 Pilot 留在第 5 步。

后续已完成[输入无损优化](V21_INPUT_OPTIMIZATION.md)：相同六个历史 Review 由 38,899–107,958 降到 20,625–61,025 个代理 token；Prompt 升为 v21.2，原始证据范围不变。下文第 5 节数字是优化前记录。

后续 [issue 边界](V21_ISSUE_BOUNDARIES.md)已进一步要求按原 problem 复查，并提供已有来源链与共享上下文的区分；Fusion/Review Prompt 当前为 v21.2/v21.3。保持完整相关证据，六个历史 Review 当前为 20,872–61,287 个代理 token。

再完成 [当前认识与历史消费](V21_CURRENT_UNDERSTANDING.md)：已有综合认识的 issue 在 Fusion 中只展示认识和尝试目录，Review 根据 `memory_attempt_refs` 按需打开尝试，保留已知反例及历史配对退化；无认识的旧记录继续完整读取。Fusion/Review Prompt 当前为 v21.6/v21.9；[语义定向修订](V21_SEMANTIC_FOLLOWUP.md)引入任务/操作原文对照，[缺陷依据与修改授权调整](V21_DEFECT_GROUNDING.md)进一步要求原文可推翻上游缺陷假设，新增程序义务须有依据。此前的[提案依据要求](V21_FUSION_PROPOSAL_BASIS.md)和[证据比较要求](V21_EVIDENCE_COMPARISON.md)继续保留。本页以下的“全部尝试”描述保留为旧实现记录，新规则以当前认识说明为准。

## 1. 相比 v20 的实际变化

| 环节 | v20 已有能力 | 本步改动 |
|---|---|---|
| Fusion | 读取问题、尝试及 assessment，选择 PROPOSE/NO_EDIT | 直接读取第 3 步更新后的完整 assessment；提示明确同时考虑另一维问题、反证和未知，在原有 reason 中说明修改方向如何回应限制 |
| 局部 Review | 回查选中问题的全部尝试和原始证据，授权有界 gap | 解析 ASSESSMENT_V21 的来源链、配对 Replay 和版本身份；结合当前 Parent 重新判断支持、问题和未知怎样影响修改 |
| Compiler/Editor | VERIFIED 才可生成有界修改 | 复用现有实现；更新后的认识、已核验理由和反证进入原有编辑输入，不另增编辑授权 |
| 后续档案 | 保存当前诊断、历史来源和实际 edits | 接受明确标记的 v21 generation source，把上一轮更新档案连同新轮证据继续保存，避免来源在下一轮断开 |

Memory 的问题/尝试字段、Fusion 响应字段、Review verdict/gap、编辑计划与 Gate 规则没有新增分类或状态。双维使用要求写入现有提示和 reason，不另设处置表、独立 Agent、额外 Review 或逐 edit 因果分析。

## 2. 具体消费规则

Fusion 只看简明认识，不声称自己已读取历史原文。引用有利尝试时，也要考虑同一问题其他尝试中的限制，不能把任务成功视为程序正确，或因为任务失败否定已观察到的合规行为。不同运行/版本的成功与合规不能拼成联合成功。当前 edit 绑定缺少完整已提交账本时仍为 `UNRESOLVED`。

Review 按选中问题加载全部尝试，沿显式 source/edit 关系保留联合依据和反证，再打开相关完整轨迹及已知配对两侧。不会自动扩成全轮、全历史，也不会只因 Fusion 选了某个有利 attempt 而隐藏同一问题的其他尝试。无关联的来源不加载；历史缺少配对信息时不制造配对或局部效果。

历史 PARENT/CANDIDATE 角色属于当时的 Replay；可编辑目标只能来自本轮实际 Parent。Memory 更新成功不意味着该 Candidate 已被部署，适配器不自行猜测 Gate 结果。调用方必须从可信提交或显式导入选择 bundle，并提供当前 Parent 和完整 Current Diagnosis batch。

Review 在原有 reason 和 gap 中说明参考了什么支持、回应了什么限制、哪些效果待验证。可以探索假设、重写整体方案，也允许 NO_EDIT；不要求每次 Memory 变化都机械改变候选。新的解释可以修订旧解释，但历史事实及已知反证仍保留。必要程序由可见 policy 约束，未知本身不构成新增禁止、确认或转人工义务。

这些语义要求由模型执行，程序只验证结构、身份、来源闭包、已知反证及编辑权限，不能据此宣称模型归因正确。

## 3. 实现与兼容边界

- [memory_consumption_v21.py](../src/skill_evolution/memory_consumption_v21.py)：独立 Fusion 提示、配对证据审阅适配、v21 generation source，以及单次本地消费入口。
- [consume_v21_memory.py](../scripts/consume_v21_memory.py)：默认只预检，显式 `--run` 才执行 Fusion/Review/Editor。
- [modification_evidence_v21.py](../src/skill_evolution/modification_evidence_v21.py)：显式识别 v21 generation source，复验后继承其证据档案，不把 v21 Replay 伪装成旧档案格式。
- [test_memory_consumption_v21.py](../tests/skill_evolution/test_memory_consumption_v21.py)：来源、跨轮生成和受控反馈响应测试。

为避免复制整套 Compiler/Editor，在 `evidence_review_v20.py` 和 `local_generation_v20.py` 中只增加输入对象的装配/提示适配入口及显式 `source_type` 恢复参数。v20 默认输入仍使用原装配和原提示，未切换 v20 campaign；相关回归通过。

Fusion/review 响应、编辑计划、结果和 audit 外层继续复用 v20 结构契约，故部分 `schema_version` 和 ID 前缀仍含 V20；这表示协议复用。v21 的 generation source 明确为 `generation_input_v21.1`，来源 ID 为 `GENERATION_INPUT_V21/...`，审阅输入 ID 为 `EVIDENCE_REVIEW_INPUT_V21/...`，Prompt 有独立 v21 版本。恢复 v21 audit 应调用本模块 `restore_generation`，不能当作普通 v20 source 恢复。

Current Diagnosis 仍独立于 Memory。本步不重新诊断，不消费私有 Monitor，也不新增语义更新调用。Fusion 一次，每个 PROPOSE 一个原有 Review；Compiler 决定是否需要一次 Editor。NO_EDIT 不触发 Review，NO_UPDATE 不伪造候选或回放。失败保存已发生的调用和阶段产物，拒绝隐式重试或覆盖既有输出目录。

## 4. 使用入口

`--current-source` 读取 JSON 的 `parent_skill`、`current_requests`、`current_findings` 三项，可以使用既有 `generation/source.json` 中的当前批次。Memory 必须来自另一个已完成轮次的可信/显式导入档案；`--expected-ref` 应来自可信调用方，而非临时相信文件自报的 hash。

默认预检不调用模型：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/consume_v21_memory.py \
  --evidence <上一轮更新输出/updated-evidence.json> \
  --expected-ref <可信MODIFICATION_EVIDENCE_V21引用> \
  --current-source <下一轮当前诊断批次.json>
```

只有明确需要运行本地生成时，添加 `--run --output <新的独立目录>`。输出包含 Fusion 请求/响应、`generation/generation-audit.json` 和阶段状态；不执行新的 Agent rollout、Gate 或活动 Memory 发布。默认预检仅检查 Fusion；选择提案后，生成装配会验证相关来源闭包，Review 提示会作保守 token 预算检查，超预算不截断证据继续发送。

Python 调用方可直接使用 `build_issue_fusion_input`、`build_issue_fusion_request`、已有 `validate_issue_fusion`、`build_generation_input`，或用 `run_memory_consumption` 执行这一局部阶段。第 5 步调度可复用这些接口，并负责可信提交选择、完整恢复和原子发布。

## 5. 验证事实与结论边界

本步专项 **15 项通过**；连同第 2/3 步、v20 Fusion/Memory/生成/运行/campaign 和 Replay 回归，共 **141 项通过**。

覆盖：更新后的 assessment 进入 Fusion；选中问题的全部尝试、反证、配对双侧和版本保留；当前问题/纯历史方向；当前 Parent 编辑权限；摘要冒充事件、遗漏反证、篡改/陈旧来源拒绝；NO_EDIT 和失败不调用下游；完整 generation audit 复验；新一轮 Replay 档案保留旧认识来源。

受控 transport 测试使用 fixture 中真实存在的两种联合标签——T002 Candidate 失败但合规、T003 Candidate 成功但违规——经过 Memory 更新、Fusion、Review 和 Editor 得到不同理由与候选。响应逻辑是测试中编写的，不是真实模型推理；这验证证据与认识可以影响修改，不证明归因正确或方法收益。

历史真实产物预检只读导入 v20 第 3 轮证据，结合第 4 轮当前批次。Fusion 读取 6 个历史问题，代理输入 13,020 tokens。逐个历史问题的构造选择读取 240、63、272、68、266、96 个事件，保留各自已知反证；Review 代理输入范围 38,899–107,958 tokens。另一个合并当前 Findings 的装配 fixture 为 735 个事件、259,416 tokens，并非建议正式运行时把所有当前问题合成一个提案。

这些旧 Memory 的选中来源没有可解析的 v21 配对，因此相关历史视图的 pairs 为 0；没有为展示双维效果而补造关联。v21 新认识到配对原文的通路由上述跨轮 fixture 单独验证。真实预检也没有执行第 3 步语义更新，不能称为 v21 Pilot。报告见 `artifacts/v21_memory_step4_preflight/check.json`。

所有 token 为 cl100k_base 代理估计，不是网关实测。尚未验证新增机制的真实成本、学习收益或语义稳定性。下一步应在完整调度和原子提交接通后，运行两轮真实 Pilot，检查“修改后形成认识 → 下一轮复用/修订”的实际证据链，再开展匹配对照。

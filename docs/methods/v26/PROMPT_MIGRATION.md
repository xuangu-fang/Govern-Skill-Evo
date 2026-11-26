# V26 OfficeQA 七模块 Prompt 适配

完成日期：2026-10-29。基于[步骤 1 的冻结快照](INHERITANCE_SCOPE.md)和[步骤 2 的事实与证据视图](FACTS_EVIDENCE.md)，只改写领域说明并接通纯消息构造。没有调用模型或启动实验。

## 采用的版本与保留的语义

底稿直接读取 `inheritance_20261028_001/source_snapshot.tar.gz`，先核对快照及每份资源的 SHA-256。不是从其他 benchmark 重新编写方法，也没有采用 V25 的旧版 Prompt。特别核验：快照的 `preconditioner.md` 与 `preconditioner_legacy_v7.md` 字节相同，不是 v8。

| 模块 | 冻结底稿 | V26 标识 | 保留的主要语义 |
|---|---|---|---|
| Grouping | V25 `grouping.md`，以源哈希定版本 | `v26_officeqa_grouping_v1` | 按具体决策问题比较；每次执行只属于一个组；允许单例；不诊断、不建议修改 |
| Diagnosis | `v25_diagnosis_evidence_scoped_updates_v5` | `v26_officeqa_diagnosis_evidence_scoped_updates_v1` | 整批形成一个 Plan；可有多个有依据的 Update；不设固定数量；只输出 revise/no_change；合理假设不必先证明有效 |
| Preconditioner | `v25_preconditioner_evidence_decision_boundaries_v7` | `v26_officeqa_preconditioner_evidence_decision_boundaries_v1` | 联合判断 D/S/C；历史可促进发展，也可修正缺陷；无 Memory 也能纠正具体 Plan 问题；不重新 Diagnosis |
| Editor | `v25_editor_scope_fidelity_v2` | `v26_officeqa_editor_scope_fidelity_v1` | 忠实实施 Effective Plan；保留条件、强度与作用范围；不把例子或许可升级为默认或强制规则 |
| Replay | `v25_replay_decision_fidelity_v4` | `v26_officeqa_replay_decision_fidelity_v1` | 从实际 Diff 和已验证配对学习条件性的编辑—行为关系；保留不对称比较与归因边界；一次提出 Memory 更新 |
| Verifier | `obvious_fact_verifier_targeted_repair_v1` | `v26_officeqa_obvious_fact_verifier_v1` | 仅筛查明显且重要的事实错误；缺失证据本身不构成 CONFLICT；SUPPORTED 不代表全面证明 |
| Repair | 同上 | `v26_officeqa_targeted_repair_v1` | 一次定点修复授权 Knowledge；最小有效修改；保留未受影响内容；没有第二次独立语义审查 |

Preconditioner 的 Original Goal/ID/文本仍冻结；显式引用仍使用 `Memory:` / `Group:` / `Evidence:` / `Update:` / `Check:`。每个 Original Update 对应一个 Adjustment；全部 KEEP 仍交给 Editor，全部合法撤回则没有 Effective Plan。Editor 的无行号 `@@` 补丁、空字符串与 null 的不同含义没有改变。

Replay 仍使用多 Knowledge 的 MemoryEntry，逐项保存 evidence；替换整个 Entry 必须保留仍有效的历史理解。RETAIN 不阻止学习。原始更新、补丁、Memory、审查和合并契约均未修改。

## 各处修改及原因

| 位置 | 具体修改 | 原因 |
|---|---|---|
| Grouping §1、§2、§3 | 将代码尝试/执行文件改为正式模型轮次、工具调用及观察；解释 `P1:1_t1`；将表头、worksheet、变换顺序例子改为文档、时期、单位、操作数及工具报错 | OfficeQA 没有生成 Python 程序的执行阶段；分组依据必须来自实际可见决策，不能把 HTTP 重试或页码当成行为步骤 |
| Diagnosis §1、§2 | 用正式消息、工具观察、事后 EM/F1 解释事实；保留技能缺口、不遵守现有指导、技术问题和成功行为的区分；替换工作簿可读性、错误坐标等描述 | 文档可访问不等于模型已看到；低分不能直接证明某个检索或算术错误，不能凭评分推测原文数值 |
| Diagnosis §3 | 将触发条件限定于题目/正式历史/允许的文档工具可检查的信息；阶段改为检索、解释、计算、提交答案；替换公式/写回文件的 fallback 示例为时期和单位要求；增加轮内工具引用示例 | 保留“任务要求不能因失败或高分而削弱”的方法原则；避免要求 Python、shell、网页搜索或评分后重答；保留每条 Update 的证据和适用范围 |
| Diagnosis §4 | 自检和恢复示例改为可读片段、答案形式、Actor 自己的计算、工具使用与解释 | 这些现象都不是正确答案的充分证明；额外工具调用或轮次本身也不是改进 |
| Preconditioner §1、§2、§3 | 将程序分支/工作表范围比较换成实际调用与观察、文档/页/窗口/时期/单位；区分未读信息与不存在；无匹配结果不自动要求扩大检索 | D/S/C 的职责不变，只把比较单位和可观察条件改为 OfficeQA；不能从历史或片段缺失中编造事实 |
| Preconditioner §4、§6 | 完成状态从有效输出文件改为答案提交；自检不升级成正确性；可检查条件基于本地文档工具；引用示例加入工具 ID，普通代码示例改为 read/start/page/单位 | 保持对退出、fallback、优先级和预算影响的原有判断；模型轮次、工具调用与 HTTP 消费不能混淆；不改变引用语法或补丁契约 |
| Editor §2 | 用 `<answer>` 内外范围与“来源页码不是 read 起始行”替换 Python fenced block / INPUT_PATH / OUTPUT_PATH；编辑对象仍只是 Skill | 保留 v2 的作用范围忠实性，避免把格式要求扩大成禁止工具调用，或生成更改文档/执行器的补丁 |
| Replay §1、§2、§3、§6 | 将代码分支、单元格与程序执行计数改为检索/解释/计算决策、页与行身份、模型轮次/工具/API 计数；同分不等于同答案或同行为；仍保留条件、竞争解释和成对不对称结果 | 既有决策比较语义可以继承，但证据单位与评分测量不同；EM/F1 不能证明检索路径或孤立因果 |
| Replay “Current pairing view” | 对齐实际 `pairs` 的六个结果字段；按 task ID 配对，不能按完成顺序；将严格 EM 成功数 Gate 写成显式配置后的条件规则 | 不再引用不存在的 hard/per_cell 字段；F1 改善不冒充 EM 成功数改善；Prompt 不替正式实验选定 Gate。未完成请求不伪装为已完成失败 |
| Verifier Input / Prioritize / Output | 改为轮次或单工具来源、文档页/TXT 行身份及工具观察时序；取消执行 Python/单元格错误的特定描述 | 审查必须针对实际提供的来源。单工具来源不包含同轮兄弟调用的观察；不因缺少轨迹就判错，也不凭未读片段推断全局不存在 |
| Repair Input / Task | 保留授权目标、原始来源及 issues 的范围，使用 OfficeQA 的时间与身份解释；不得添加兄弟工具结果或虚构计算轨迹 | 修复应依赖原始记录，而非把 Verifier 的转述当成事实；仍只做最小定点修正与确定性合并 |

61 条显式文本替换均记录了前后原文、作用次数和原因，见 [migration.json](../../../artifacts/methods/v26/prompts_20261029_001/migration.json)。完整逐行差异见 [v25_to_v26.patch](../../../artifacts/methods/v26/prompts_20261029_001/v25_to_v26.patch)。测试将这些替换依次作用于冻结底稿，要求结果与最终资源完全一致。

## 共享说明与消息边界

新增 [execution_context.md](../../../src/skill_evolution/v26/benchmarks/officeqa/prompts/execution_context.md)，由记录中的 background 填入工具 schema、实际模型/输出额度和执行设置；没有把 16384 等固定输出额度写入 Prompt。补充以下必要解释：

- 初始请求页、实际渲染片段、TXT 行是不同概念；grep 是不区分大小写的字面子串检索；截断和无匹配不证明全局不存在。
- `attempts` 是接受的模型轮次，包含无工具的最终答案轮；同轮调用先于本轮全部工具观察。`api_requests` 包含已消费的请求尝试。
- 传输失败与临时格式纠错不进入方法事实；正式 `request_messages` 不冒充每次 HTTP 请求的原始上下文。
- 六次请求总尝试按模型轮次计费且恢复不补额度；无 8/96 工具调用限制；正常轮次耗尽与未完成执行分开。
- 原生答案标签解析和文本回退只是实际协议说明，不鼓励放弃 Actor 原有格式要求；评分和参考答案不会作为 Actor 纠错输入。

为了让 Editor 等模块能够判断是否重复基础指导，原生 `VENDOR_PROMPT` 去掉 Skill 后作为带明确数据边界的引用加入共享说明，内容直接来自公共 Actor 使用的上游资源，没有新编一套解题策略。Prompt 身份同时记录该文本的哈希。Verifier/Repair 也附上同一份协议解释；其任务与历史记录权限仍只来自已有 `context/targets/source_records`，不增加任务证据。

Knowledge Only 说明仅替换领域名词；版本与精确历史引用规则不变。`method_validation_feedback.md` 与冻结底稿字节一致。仅提供诊断消息渲染，不在本步骤选择或实现优化器重试政策。

| 模块消息构造函数 | 送入 user message 的内容 |
|---|---|
| `grouping_messages(saved)` | Parent、整批正式 runs |
| `diagnosis_messages(saved)` | Parent、runs、已验证 Grouping |
| `preconditioner_messages(saved)` | Parent、Original Plan、Plan 引用选出的完整 runs、Knowledge Only；不附 Grouping 内容或历史原始档案 |
| `editor_messages(saved, adjustments)` | Parent、确定性编译后的 Effective Plan；不附轨迹、Memory 或 Preconditioner 的理由 |
| `replay_messages(bundle)` | 已验证的 Parent、实际 Diff、Plan、pairs、runs、Knowledge Only；不附 audit |
| `verifier_messages(bundle, candidate, historical)` | 已筛选的新/变化目标及精确来源；历史档案必须显式提供并核验 |
| `repair_messages(verifier_input, verdicts, candidate)` | 仅 CONFLICT 目标，来源限于原 Knowledge 与 issues 的联合，来自冻结的 Verifier 输入 |

上述函数位于 [prompting.py](../../../src/skill_evolution/v26/benchmarks/officeqa/prompting.py)，在 `using_benchmark(adapter)` 下使用，只返回 `system/user` 消息。全部撤回、无 Verifier 目标或无 Repair 目标时，相应函数返回 `None`。Diagnosis no_change 不能继续进入 Preconditioner。

`adapter.resource()` 只允许已登记的十个 Markdown 资源，拒绝路径穿越或 V25 旧版本回退；`frozen_files()` 将 Prompt 加入源码冻结。`prompt_identity(module)` 返回版本、领域视图和共享资源/基础 Actor Prompt 哈希，供后续 Campaign 持久化及恢复校验。本步骤尚未实现 Campaign 自动存取身份。

## 离线验收

```sh
/Users/didi/miniforge3/envs/OfficeQA/bin/python -m pytest \
  tests/skill_evolution/v26 tests/adapters/officeqa -q \
  --junitxml=artifacts/methods/v26/prompts_20261029_001/pytest.xml
```

新增 19 项测试，连同已有证据层 58 项、公共 OfficeQA 81 项，共 158 项通过。新增用例覆盖七模块实际消息投影、历史权限、秘密/标准答案字段隔离、临时格式上下文隔离、无工作分支、真实契约与补丁编译、版本/资源冻结及完整源文本迁移。V26 测试阻断 socket、requests 与 OpenAI/Azure 客户端；Actor 桥仅使用合成语料和固定假响应。没有真实题目 rollout、模型推理或实验。

验收记录见 [report.json](../../../artifacts/methods/v26/prompts_20261029_001/report.json) 和 [JUnit](../../../artifacts/methods/v26/prompts_20261029_001/pytest.xml)。测试能证明消息与契约兼容、源改动受控，不能证明模型实际遵循 Prompt 或优化效果。

后续仍需接通模块调用/持久化与恢复、Campaign 主循环、最终评估入口和全局成本统计，并在确定模型、输出额度、初始 Skill、训练批次/预算、Validation 用法及 Gate 后验收输入容量。七份 Prompt 可离线构造消息，不等于完整 V26 实验已经可启动。
## 后续输入表示更新（2026-10-29）

本文记录的七模块学习 Prompt 原文及输出语义不变。实际发送消息现额外经过 [OfficeQA 无损输入视图](LOSSLESS_INPUT.md)，仅在采用编码时附加独立的表示解码说明；输入视图和说明哈希单独冻结。原始事实、Memory 和验证器输入契约不压缩，旧归档不自动迁移。


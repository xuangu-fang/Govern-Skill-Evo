# V26 OfficeQA 事实与证据适配层

完成日期：2026-10-29（Asia/Shanghai）。继承依据见 [步骤 1 的范围记录](INHERITANCE_SCOPE.md)。本步骤实现确定性事实、证据与执行桥接，不运行七个优化模块，不新增方法 Prompt，不启动训练。

## 实现边界

入口为 [OfficeQAEvidenceAdapter](../../../src/skill_evolution/v26/benchmarks/officeqa/adapter.py)。它连接既有 OfficeQA 公共 Actor，构造可复核的执行记录，并提供 Grouping、Diagnosis、Preconditioner、Editor、Replay、Verifier、Repair 所需的数据视图。

V26 的纯契约从步骤 1 保存的源码快照提取，而不是运行时导入持续变化的 V25。只迁入证据层所需的解析、引用、计划编译、补丁、Memory 和审查契约；没有复制 V25 的模型传输、训练主循环、CLI 或 SpreadsheetBench 执行器。来源记录见 [inherited_sources.json](../../../artifacts/methods/v26/evidence_20261029_001/inherited_sources.json)。

核心契约保持原语义标识，例如 `entries_sources_multi_knowledge_v1`、`v25_explicit_references_v2`；这表示继承了同一契约，不表示运行 V25 模块。OfficeQA 记录和输入视图使用新标识，未伪造 V26 Prompt 已经存在。

| 标识 | 作用 |
|---|---|
| `officeqa_skilladam_aligned_v2` | 原有公共 Actor 执行协议 |
| `v26_officeqa_execution_v1` | 带独立执行身份、任务及来源指纹的 V26 记录 |
| `v26_officeqa_formal_evidence_v1` | 正式执行事实 |
| `v26_officeqa_pairs_formal_v1` | Replay 的配对事实视图 |
| `officeqa_em_f1_no_reference_answers_v1` | 仅 EM/F1 的评分视图 |
| `formal_history_without_temporary_format_feedback_v1` | 模块看到的正式上下文，不冒充含临时纠错的完整 API 请求 |
| `officeqa_em_exact_v1` | 可显式选择的 Gate 映射；默认未选择 |

## 执行记录与身份

公共 Actor 的原始记录格式保持不变。V26 在外面增加一层：

```text
schema
run_id                  本批 UUID + task_id 的哈希；在首次执行前持久化
task_id
task                    公开题目字段、split、来源文件和独立 URL
provenance
  batch_id / role       parent、candidate 或 evaluation
  source_assets         每份 TXT 和实际解析 JSON 的内容哈希
  task_context_sha256   不带 Skill 的初始消息指纹
  record_sha256         公共 Actor 完成记录的内容哈希
execution               原始公共 Actor 记录，包括请求审计
```

记录中的题目字段采用白名单，不复制 `answers`、`ground_truth`、`reference` 或任意 metadata。允许文档本身包含解题数值；这与向优化器复制标准答案字段不同。

`check_record` 将记录与当前 canonical case、初始消息、Skill、Actor 配置及来源字节核对，并使用原生评分器离线重算 EM/F1。纯事实重载器检查记录内部一致性；哈希用于发现内容改变，不是来源真实性的数字签名，也不证明自然语言陈述成立。

记录的批次目录是固定任务列表、角色、Skill、Actor 配置及输入资源的一次执行。恢复沿用原 UUID；不同 Parent/Candidate 批次具有不同执行身份，不能仅因为输出文字相同就视为同一次执行。

## 正式事实结构与引用

`build_facts(records)` 返回 `facts/background/sources`。`facts` 含 `parent/runs`，每个 run 为：

`background` 同时记录实际工具 schema、工具返回上限、oracle 页面/总上下文上限以及 Actor 参数，避免只列工具名称而遗漏其真实能力和截断条件。

```text
ref / task_id / run_id
initial
  ref
  task
  declared_source_pages  请求指定的文档及页码，不表示全部内容实际进入上下文
  messages               实际保存的初始 system/user 消息
attempts[]               每项是一轮最终被接受的模型响应，不是一次 HTTP 尝试
  ref
  request_context
  request_messages       该轮生成前的正式历史
  assistant              该轮被接受的 assistant 消息，保留完整 tool_calls
  tools[]
    ref / call / observation
outcome
  ref / status / termination / answer
  model_rounds / tool_calls / api_requests
  score                  em、f1；只在任务结束后产生
```

保留 `attempts` 容器名以接入已有计划契约，但它在 OfficeQA 中明确表示接受的模型轮次。不得把它解释为程序执行、API 重试或单个工具调用。Diagnosis/Plan 的引用集合已改为由领域适配器提供，以允许引用轮内具体工具。

| 引用示例 | 精确含义 |
|---|---|
| `P1` | 当前 Parent 批次中的一次完整执行 |
| `P1:0` | 该执行的初始输入与声明的来源 |
| `P1:1` | 第一轮被接受的 assistant 响应及本轮全部已提交工具返回 |
| `P1:1_t2` | 第一轮第二个工具调用及其返回 |
| `P1:outcome` | 最终答案、结束原因、计数和事后评分 |
| `Q1:1_t2` | 与 P1 按题目 ID 配对的 Candidate 对应工具事件 |
| `diff` | Parent 到实际 Candidate 的精确 Skill Diff |
| `R01/P1:1_t2` | 指定历史上下文中、已由当前 Knowledge 明确授予的历史引用 |

P/Q 编号不是题目难度、排名或类别。父批次的完成顺序决定最初 P 编号，并在其后的诊断和配对中保持不变；Candidate 不能按返回位置与 Parent 配对。相同的 provider tool-call ID 可以在不同轮重复，证据编号仍然不同。

独立工具引用附带该轮生成前的正式请求历史，但不包含本轮其他工具的返回，不从本轮稍后的观察倒推生成前的可见信息。整轮引用包含该轮全部工具事件；完整执行引用保留完整正式历史。

## 页码、行号和可见性的区别

- `declared_source_pages[].source_page` 是现有 URL/解析 JSON 使用的页面标识，不解释为印刷页码或 TXT 行号。
- `read` 的 `start/limit` 及 `grep` 输出中的行号属于 transformed TXT。工具参数和返回按原文保留，不推导“这一文本行一定来自某页”。
- 初始消息保留真实 oracle 页面文本及截断标记。声明了页面不代表完整页面或全部声明页面进入了模型输入；缺失窗口不能解释为文档没有相关内容。
- 工具错误也是正式观察，例如非法窗口、路径不允许；不会变成格式重试证据。
- 原公共 Actor 已对路径脱敏。`<officeqa-docs>/...` 是显示形式，不能单凭该前缀断言路径获准；结合题目 allowlist 和实际工具返回判断。

## 格式重试与正式事实分离

[facts.py](../../../src/skill_evolution/v26/benchmarks/officeqa/facts.py) 在投影前校验全部请求审计：

1. 每轮请求编号连续，最多六次，最后一次为 accepted；不能存在未完成或 fatal 的轮次。
2. 技术重试保持原请求；格式重试使用最近一次失败响应和实际诊断；正常响应后临时纠错清空。
3. 重建的正式消息必须逐项等于公共 Actor 保存的最终 transcript。
4. 工具数量、调用身份、提交状态、原始返回和总计数必须对应。
5. 最终答案、原生提取结果、终止方式和 usage 审计必须一致。

格式错误、截断、超时及临时纠错消息留在 `execution.request_audit`，不进入 `facts.runs.attempts`，不会获得工具执行证据 ID。`request_messages` 是明确标识的正式历史，不宣称它等于包含临时纠错的实际 API 请求。原始实际请求仍可通过审计记录检查。

`api_requests` 记录所有已消费请求尝试，包括失败和未知结果；它是成本计数，不是新增执行事件。`facts.cost_summary` 对传入的完整记录累计请求及已知 token 数，单独报告未知用量。它不扫描未完成批次中的状态文件，不能作为未来完整训练的全局成本统计器。

六次生成失败耗尽后没有完整记录，不能交给 Grouping/Gate 伪装成零分。24 轮模型交互正常耗尽则依照现有 Actor 协议，是空答案、零分的完整执行。

## 各模块可见信息

| 模块/接口 | 提供的信息 | 不提供的信息 |
|---|---|---|
| Grouping：`build_facts` 的 facts | Parent Skill、当前全部 Parent 正式执行及终局评分 | Memory、Candidate、标准答案、请求失败正文 |
| Diagnosis：`diagnosis_input` | Parent、当前 runs、已校验 Grouping | 历史 Memory、Candidate |
| Preconditioner：`preconditioner_model_input` | Parent、原 Plan、Plan 引用的当前 runs、Knowledge Only 历史 | Grouping 正文、未引用的当前 runs、历史原始轨迹、标准答案 |
| Editor：`editor_model_input` | Parent 与按继承契约编译出的 Effective Plan | 原始执行、Memory；全部 KEEP 仍有有效计划，全部撤回返回 None |
| Replay：`model_input` | Parent、实际 Diff、有效 Plan、pairs、邻接排列的 P/Q runs、Knowledge Only | 原始审计包装、历史来源目录和未授予的历史轨迹 |
| Verifier：`build_input` | 新增或修改的 Knowledge 目标、精确引用的 source_records、相关配对与执行条件 | 未引用的邻近工具、任意历史轨迹目录；完全沿用的历史 Knowledge 不重复成为目标 |
| Repair：`build_repair_input` | 仅 CONFLICT 目标及其 Knowledge 引用与 issues 引用的并集 | 其他修改目标或任意新增证据；merge 检查目标与原候选完全一致 |

方法模块只能看到 EM/F1 数字以及 Actor 自己的最终答案。评分标准答案只由本地评分器使用；评分结果不写回 Actor。没有引入“根据标准答案再生成一次”的路径。

Replay 的 `audit` 保存构造时的原始执行和 Editor handoff，用于重新校验血缘；`model_input` 不投影该字段。由于本步骤尚无运行中的 Editor，handoff 由调用方显式传入；校验覆盖实际补丁应用、执行的 Candidate、Parent 原始事实和配对，不能据此声称已完成整个 Editor 模块接入。

目前不对正式输入做摘要、跨任务响应合并或代码去重。完整历史有重复表示，但每个引用能精确还原。后续如优化输入体积，需要独立的无损等价验收；此时也需按实际批次验证模型输入容量。

## 配对和评分 Gate

配对按 task ID 验证全覆盖和唯一性，检查任务、源文件/解析文件字节、无 Skill 的初始上下文和 Actor 参数相同，同时确认执行身份独立。Parent 轨迹由本轮直接复用，不新增一次 Parent 执行。

`gate_metric=None` 是默认值，调用 Gate 会明确报错。显式传入 `gate_metric='officeqa_em_exact_v1'` 后，EM=1 映射为成功，严格成功数增加才 ACCEPT，持平或下降为 RETAIN。F1 不参与决定。这实现了此前建议的可选映射，**没有替正式实验选择该映射**。

绑定真实 dataset/runtime 的 Adapter 在构建 Gate 时会再次核对记录、来源及原生分数；无 Actor 依赖的纯 Adapter 可用于离线归档契约检查，但不能证明归档分数与未提供的标准答案一致。

历史来源可解析不等于模型获准引用。Replay/Preconditioner 只获得 Knowledge 文本及其精确历史引用；`R01/P1:1_t2` 不授予 `R01/P1`、`R01/P1:1_t1` 或该 run 的 outcome。Verifier 从显式提供并核验的历史包取记录，不隐式扫描历史目录。

## 执行桥接与恢复

```text
<batch>/
  actor/
    run.json
    results.jsonl
    cases/<原公共 Actor task hash>/actor_state.json
  evidence/
    batch.json
    records/<V26 task hash>/trajectory.json
```

`actor_batch` 只调用一次公共 Actor 线程池，workers=4。沿用完成顺序日志、失败题停止而剩余及排队题继续、整批结束后报错。没有复制 V25 的失败后停止补充逻辑，没有增加第二层题目线程池。

在成功收尾后，证据包装按同一日志顺序保存。若批次失败，已经完成的原始结果仍在公共 journal，包装可在之后成功恢复收尾时生成；不把部分结果冒充完整训练批次。

恢复不重置请求预算。已持久化的第六次响应可解析而不发第七次请求；已提交工具不重放，started 但没有提交结果的工具阻止自动恢复。更换任务、角色、Skill、Actor 配置或来源字节需要独立目录，不改变旧批次身份。

Train、Validation、Test 使用显式 split。Test 只允许 `role='evaluation', final=True`；评估记录可以核验，但不能进入优化 facts。是否使用 Validation 优化仍由未来训练配置决定，没有自动并入 Train。

## 离线验收与复现

在独立 OfficeQA conda 环境运行：

```sh
/Users/didi/miniforge3/envs/OfficeQA/bin/python -m pytest \
  tests/skill_evolution/v26 tests/adapters/officeqa -q
```

新增测试使用临时合成语料、固定响应与真实本地工具/评分器，阻断网络和 OpenAI/Azure 客户端；没有模型推理。覆盖临时纠错隔离、源页面截断、工具值错误、非法归档、角色与 split、按 ID 配对、来源漂移、明确 Gate 映射、分数重算、历史权限、Memory 提交/重读、Verifier/Repair，以及批次和第六次响应恢复。

另对真实 246 道题只做公开任务结构、来源映射/指纹和初始消息构造检查，不运行 Actor、不生成答案、不评分。结果与每题输入指纹见 [输入预检](../../../artifacts/methods/v26/evidence_20261029_001/input_preflight.json)。测试结果见 [JUnit 报告](../../../artifacts/methods/v26/evidence_20261029_001/pytest.xml)，代码及继承差异核验见 [验收报告](../../../artifacts/methods/v26/evidence_20261029_001/report.json)。

本次交付的是可用的事实与证据层。七模块正式 Prompt、Campaign 主循环与最终评估 CLI、全局成本统计、批量输入容量检查和正式实验参数仍是后续工作；`resource()` 明确拒绝读取尚未实现的 Prompt，不会回退到 SpreadsheetBench 文本。
## 后续输入表示更新（2026-10-29）

上文的事实/轨迹存储契约保留不变。模型消息现已接入 [OfficeQA 专用无损输入视图](LOSSLESS_INPUT.md)：完整 run 不再逐轮重复 request_messages，相同初始消息按严格范围共享；v2 进一步编码同一执行内已提供的局部引用上下文的相同前缀，保留每个引用的精确边界，可完整还原。公共 Actor、原始审计和评分未修改，正式 token 预算仍未确定。


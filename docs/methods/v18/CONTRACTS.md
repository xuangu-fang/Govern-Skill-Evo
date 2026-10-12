# Diagnosis、Compiler 与 Editor 契约

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v18 Diagnosis 输入输出与验收契约](#v18-diagnosis-contract)
- [v18 Compiler：确定性 ADD / REPLACE / DELETE](#v18-compiler-contract)
- [v18 Editor 与确定性文本应用](#v18-editor-contract)

<a id="v18-diagnosis-contract"></a>

## v18 Diagnosis 输入输出与验收契约

状态：第 2 步契约与第 3 步 Prompt/transport 已实现；2026-09-19 第 4 步 [Compiler](CONTRACTS.md#v18-compiler-contract) 和第 5 步 [Editor/应用器](CONTRACTS.md#v18-editor-contract) 已接入，尚未进入完整 v18 campaign。Prompt 实施说明见文末。

### 1. 模块与版本

| 模块 | 职责 |
|---|---|
| `src/skill_evolution/v18/diagnosis_contract_v18.py` | strict JSON Schema、字段/类型/枚举及跨字段结构约束 |
| `src/skill_evolution/v18/diagnosis_references_v18.py` | 当前组证据、可见 policy、当前 Parent 规则的引用解析 |
| `src/skill_evolution/v18/diagnosis_validation_v18.py` | PARSE → STRUCTURE → REFERENCES → LINKAGE 验收与独立封装 |

三份模块从 v17 对应实现独立复制并修改；v17 文件、Schema、验收行为不变。未变化的输入装配仍复用 `group_diagnosis_input_v17.GroupDiagnosisInput`（payload 版本 v17.2、签名种类 `V17_GROUP_DIAGNOSIS_INPUT`），引用寻址规则完全兼容。暂不为未变化的 Grouping/经验输入另建协议。

模型 response format 名称为 `v18_group_diagnosis`，strict=true。成功输出的 Envelope kind 为 `V18_VALIDATED_DIAGNOSIS`，payload schema_version 为 `validated_diagnosis_v18.1`。不能用 v17 的 Envelope kind 解包，也不能直接送入 v17 Compiler；v18 Compiler 接入属于第 4 步。

### 2. 输出结构

四个顶层字段保持不变，均必填，所有层级拒绝额外字段：

```json
{
  "success_analysis": {
    "finding": "可观察条件、行为和结果的关系，区分观察与推断。",
    "evidence_refs": [],
    "supervision_refs": [],
    "unresolved": []
  },
  "compliance_analysis": {
    "finding": "对可见 policy、用户约束和工具契约的分析。",
    "evidence_refs": [],
    "supervision_refs": [],
    "unresolved": []
  },
  "skill_addressability": {
    "status": "NOT_ADDRESSABLE",
    "reason": "存在问题，但没有证据支持 Agent 能实际改变的决策。"
  },
  "parent_skill_gaps": []
}
```

finding、reason、gap 及各字符串数组元素必须非空白。数组必须为 list；引用与维度数组拒绝重复值，不修剪、不去重、不转换类型。Analysis 中引用和 unresolved 可为空。

| Status | 语义要求 | gaps |
|---|---|---|
| NO_ISSUE | 没有观测到需修复的问题；输入中全部 success/compliant 标签为 true | 空 |
| NOT_ADDRESSABLE | 有问题，但证据不支持通过 Skill 指导修改具体 Agent 决策或行为 | 空 |
| ADDRESSABLE | 至少一个问题支持修改具体 Parent 指导，并说明可改变的 Agent 决策或行为 | 至少一条 |

正标签不强制 NO_ISSUE，轨迹仍可能暴露其他异常。混合组只为可修复问题提供 gap。缺信息并不自动推出 NOT_ADDRESSABLE；若存在证据支持且可执行的合法澄清/查询路径，可以 ADDRESSABLE。机制未知也不自动产生新的核实或停止义务。

### 3. 三种 gap

每个 gap **恰好五个字段**：`kind`、`gap`、`evidence_refs`、`related_rule_refs`、`source_dimensions`。不新增 removal_justification、operation、gap_id 或最终 Skill 文本字段。

| kind | 含义 | related_rule_refs | 后续确定性映射 |
|---|---|---|---|
| MISSING | 缺少证据支持的指导 | 必须为空 | ADD |
| NEEDS_REVISION | 已有规则核心方向仍有价值，条件、范围或内容需要修改 | 必须非空 | REPLACE |
| SHOULD_REMOVE | 整个目标规则被证明不必要、错误或不应继续存在，删除优于修改 | 必须非空 | DELETE |

上述操作映射是未来 Compiler 的约定，不是本步输出字段或已实现的编辑操作。`kind="DELETE"` 非法。

所有 gap 的 evidence_refs 必须非空，解析后至少含一个本组轨迹事件；仅有 policy 引用不够。source_dimensions 必须为 SUCCESS、COMPLIANCE 或两者，无重复。NEEDS_REVISION/SHOULD_REMOVE 的目标均须解析到当前 Parent 的完整规则块；未知、过期或其他类型引用拒绝。

#### SHOULD_REMOVE 的更高证据门槛

Diagnosis 应在已有 finding/gap 文本及引用中明确说明：

1. 规则的核心指令被什么证据否定，或为何没有应继续保留的作用；
2. 结论为何涉及整个引用块，而非局部条件或措辞；
3. 为什么缩小范围、补齐条件、降低确定性或保留有效部分的修订不适合；
4. 删除将改变 Agent 的哪个具体决策，并且不绕过有效 policy、用户约束或工具契约。

规则范围过宽、条件缺失、表述过强，优先 NEEDS_REVISION。一个 Markdown 块仍有有效指导时，也应 REPLACE 保留有效部分。单次失败、规则本轮未触发、未观察到收益、尚不确定，不能单独构成删除依据；证据不足则不强制产生 gap。不以固定最小样本数代替证据质量。

这是语义契约，由第 3 步 Prompt 和后续离线语义评估落实。确定性验收不使用关键词、文本长度或引用数量来伪装验证删除理由；结构 VALID 不证明已经达到更高证据门槛。

### 4. 确定性验收

`build_diagnosis_response_format()` 每次返回独立 Schema 副本。
`validate_diagnosis_output(output)` 只校验结构，成功返回 None，失败抛出 `DiagnosisContractError`，不修改输入。

`resolve_diagnosis_references(output, request=...)` 接收已签名组输入，校验并解析全部结构化引用。TRAJECTORY、SUPERVISION、VISIBLE_POLICY、PARENT_SKILL_RULE 类型隔离；引用必须属于输入目录。policy/规则目录根据精确原文重新计算，Parent 即使只改空白也会使旧规则引用失效。可选 quote/context 检查沿用精确匹配，不证明语义蕴含。

`validate_diagnosis_response(raw, request=...)` 是完整验收入口：

1. **PARSE**：只接受一份 JSON 文本，拒绝重复 key、非有限常量、围栏和附加文字。
2. **STRUCTURE**：字段、枚举、非空约束、状态与 gaps、gap 类型与目标数量一致。
3. **REFERENCES**：签名输入、目录完整性、引用类型/归属、当前 Parent 与轨迹证据要求。
4. **LINKAGE**：NO_ISSUE 不得与任何负标签冲突；gap 全部 evidence_refs 必须包含于声明来源 Analysis 的证据并集，每个声明维度必须与 gap 共享至少一条轨迹引用。

任何错误抛出 `DiagnosisRejected(stage, reason)`，不修复 JSON、不补字段、不删除坏 gap、不返回部分有效响应。通过后原样保存 semantic、raw_response、resolved_references，以及原始响应和签名输入 payload 的 SHA-256，标记 `validation_status=VALID`、`semantic_origin=LEARNER_INFERRED`。

本层不能确定 findings 的真伪、引用的因果作用、policy 适用性、ADDRESSABLE 是否确有可执行决策，或删除是否优于修订。它不授予编辑权限，不等于 Gate ACCEPT。

### 5. 验证记录

测试：`test_diagnosis_contract_v18.py`、`test_diagnosis_references_v18.py`、`test_diagnosis_validation_v18.py`；测试输入复用未变化的 v17 经验/分组构造 fixture，不复用 v17 输出验收。

已运行 v18 三份测试与对应 v17 回归测试，共 **150 项通过**。覆盖三类 gap 目标基数、删除规则引用、跨组/过期/错误类型引用、Analysis 关联、结构拒绝、原始响应保留、独立封装版本和新旧 Schema 隔离。构造样本中的 SHOULD_REMOVE 通过只验证协议，不代表样本的删除理由在语义上成立。

### 6. 第 3 步：通用 Prompt 与请求接入

`diagnosis_prompt_v18.py` 当前定义 `v18-group-diagnosis-2`（2026-09-19），通过以下顺序约束一次模型调用内的推理：

1. 两维 Analysis 优先对比可观察条件、行为与结果，保留反例；不完整的机制解释不能抹掉已支持的候选关系，也不能补造精确映射。
2. Addressability 的 reason 指出修改 Skill 能改变的具体决策或行为，以及现有信息/工具/合法交互依据；不检查 runtime 回合可达性。
3. Gap 保留 Analysis 中条件、行为、适用范围和 epistemic status；候选规律在 gap 本身仍须为条件性、暂定指导，不能写成普适强规则后再加免责声明。未知不自动产生核实、前置、禁止、转人工或停止义务；新增限制必须已有来源 Analysis 支持其必要性，需要核实或满足的前提还须存在合法可行路径。不得额外安全化、保守化或扩展义务。真实用户和 policy 限制继续有效。
4. 三种 gap 按第 3 节区分。删除需要说明整块规则为何不应保留、为何修订不足、会改变什么决策；仍有有效内容时优先修订。

固定 Prompt 不包含任务编号、渠道/姓名/人数案例、隐藏 benchmark 标签或样本答案；没有新增输出字段。`build_diagnosis_prompts` 和 `build_diagnosis_request` 保留完整 learner payload，不发送运行时 provenance。默认 experiment_scope 为空，只有可信调用方显式指定时才附加，并记录实际 system prompt SHA-256；不隐含沿用历史 pilot 的目标排除条款。

独立 `diagnosis_v18.py` 复用 v17 的一次调用审计方式，接入 v18 Prompt/Schema/验收封装：deepseek-v4-pro、temperature=0、reasoning_effort=high、24,000 completion tokens、300 秒 timeout、SDK max_retries=0，无自动修补/重试/fallback。调用前保存 request/provenance，之后保留原始 response、完成状态、provider model/id、usage 和验收结果；不覆盖已有目录。版本化模型名称不保证远端后端固定。

新增固定输入 pilot：`scripts/runs/v18/run_v18_diagnosis_pilot.py`，输入清单在 `experiments/methods/v18/v18_diagnosis_pilot_001/config/sources.json`。清单固定 R2 g5、R2 g3、R3 g6 三组已保存的 Evolution 请求，绑定 request/provenance/response/validated 文件摘要并复验历史请求和响应，只将原始 learner payload 发给 v18。历史 Diagnosis 输出仅用于来源复验，不进入新模型输入；不读取 Monitor。该入口是对可信本地历史产物的显式回放，不是任意外部 JSON 的可信装载器。

```bash
# 仅复验固定输入，不调用模型；目录必须不存在。
python scripts/runs/v18/run_v18_diagnosis_pilot.py --output artifacts/v18_diagnosis_preflight_new
# 同样的三组输入，每组一次模型调用。
python scripts/runs/v18/run_v18_diagnosis_pilot.py --run --output artifacts/v18_diagnosis_pilot_new
```

Prompt、模型请求和 pilot 新增测试连同 v17/v18 契约相关回归，共 **184 项通过**。检查完整输入与 v17 相同、实际 SDK 消息/Schema 一致、Prompt 摘要绑定、源文件漂移拒绝、删除输出进入 v18 验收、拒绝与传输失败不重试。语义效果需单独看 pilot 分析，不能由这些测试推断。

上述三次真实调用使用 Prompt v1，均结构 VALID；新增执行门槛和经验规律强度仍有疑问。完整记录见 [首次固定输入试验报告](DIAGNOSIS_VALIDATION.md#v18-diagnosis-pilot-report)。历史报告中的 STOP artifact 不作为 v2 核心语义验收项；本次未运行 v2 模型调用，不把 v1 结果冒充 v2 效果。

#### 正式职责边界（2026-09-19）

Benchmark/User Simulator 在上游负责生成语义合理、可学习的 trajectory，消除或避免确认同时终止等交互 artifact。Diagnosis 只归纳规律、判断 Skill 可修改问题并保持 Analysis→Addressability→Gap 的语义与确定性，不负责识别、解释或补救 benchmark/runtime artifact。

Prompt v2 不包含 STOP、termination marker 等特判，已移除环境结束/下一轮/恢复交互的专门约束；输入不新增 terminated、termination_reason、agent_has_next_turn。结构、引用和语义验收不加入终态专项要求或测试。历史输入原样复现，其 artifact 解释不参与 v2 核心语义验收。Simulator 层自己的终止测试继续保留，与 Diagnosis 验收分开。

#### Prompt v2 固定输入 Pilot

2026-09-19 对三组历史输入及两个构造操作边界样本各运行一次，无重试或修补。5/5 结构 VALID；核心语义 4 PASS、1 PARTIAL_FAIL。v2 消除了历史定价组的额外 summit guard，并保持人数与渠道规律的候选性质；SHOULD_REMOVE 判定符合预设边界。NEEDS_REVISION 样本仍保留了来源未证明必要的 transfer fallback，说明已有保守条款在修订时仍可能被无依据保留。详见 [v2 Pilot 报告](DIAGNOSIS_VALIDATION.md#v18-diagnosis-v2-pilot-report)。

<a id="v18-compiler-contract"></a>

## v18 Compiler：确定性 ADD / REPLACE / DELETE

状态：第 4 步已实现，2026-09-19。独立于 v17，不调用模型，不改写 Diagnosis，不执行文本编辑，不产生 Candidate。

### 1. 实现与输入绑定

- `compiler_contract_v18.py`：不可变输入/计划类型、独立 JSON Schema。
- `compiler_v18.py`：来源重新验收、确定性映射、目标合并、冲突检查与排序。
- `compiler_validation_v18.py`：提交计划的严格结构及完整内容验收。
- `compiler_audit_v18.py`：无覆盖、无重试的审计落盘。

`CompilerInput` 保留 round_id、Parent 原文、UTF-8 SHA-256 及完整选定来源 tuple。每个 `CompilerDiagnosisSource` 包含 diagnosis_ref、原始已签名 GroupDiagnosisInput 和 `V18_VALIDATED_DIAGNOSIS` Envelope。来源引用为 `DIAGNOSIS/<validated.payload UTF-8 SHA-256>`。

输入必须非空。逐份验证：来源类型及签名、引用摘要、唯一 group/source、同一 round、同一精确 Parent 与摘要；使用原始响应对原始组输入重新执行 v18 Diagnosis 验收，要求重建结果与保存的完整 payload 相同。沿用当前组证据归属与当前 Parent 规则目录。拒绝 v17 Diagnosis 封装，不自动转换。

调用方负责提供完整选定来源集合，Compiler 不能证明外部是否漏传组。provenance 是可信运行时元数据：本层检查一致性，不认证恶意 Python 调用方。没有通过原始输入/响应重验的历史 JSON，不能仅靠 VALID 字样或重新签名直接编译。

### 2. 唯一映射与编辑权限

| Diagnosis | 计划 |
|---|---|
| NO_ISSUE / NOT_ADDRESSABLE | NOOP record，原样保留 status/reason |
| ADDRESSABLE + MISSING | ADD |
| ADDRESSABLE + NEEDS_REVISION | REPLACE |
| ADDRESSABLE + SHOULD_REMOVE | DELETE |

ADD 无目标规则，每个 MISSING 单独生成一个单元。REPLACE/DELETE 目标严格等于其 supporting gaps 的 related_rule_refs 并集，不扩展范围；两者都要求当前 Parent 的非空规则引用。每个 ADDRESSABLE gap 必须恰好覆盖一次，gap_index 保留原始零起始索引；非 ADDRESSABLE 来源恰好对应一个 NOOP。

Compiler 不读取自然语言来选择操作，不根据语义评分筛选来源，不证明 SHOULD_REMOVE 达到了更高证据门槛。Pilot 中保留无依据 transfer fallback 的 NEEDS_REVISION 仍原样映射为 REPLACE，其内容问题留在 Diagnosis/语义评估侧。

### 3. 合并、冲突和顺序

同操作单元的目标规则相同或原始行范围重叠时，按传递闭包合并为一个单元，保留全部 GapRef。REPLACE 与 DELETE 分别合并，不把相邻但不重叠的规则自动合并。多个不连续目标可属于同一单元，它们之间未指定的内容不属于编辑权限。

任一 REPLACE 与 DELETE 的目标原始范围重叠，拒绝整份输入：`stage=PLAN`、`reason=MIXED_OPERATION_TARGET_CONFLICT`。无论冲突来自同组还是不同组，都不选择赢家、不转换操作、不降为 NOOP、不输出部分计划。ADD 不基于语义相似性合并。

确定性排序：

1. source_diagnosis_refs 字典序；GapRef 按 `(diagnosis_ref, gap_index)`。
2. 每个目标集合按 `(start_line, end_line, ref)`。
3. 所有 REPLACE/DELETE 单元按最早目标行、operation 字典序、supporting GapRef 排序。
4. ADD 在后，按 GapRef 排序；NOOP 按 diagnosis_ref 排序。

所有坐标来自同一原始 Parent，不做顺序编辑后的重新定位。相同来源集合即使输入排列不同，产生相同计划。全 NOOP 是合法空 edit_units；纯 DELETE 包括删除全部规则仍是有编辑的计划，不当作 NO_UPDATE。

### 4. 版本、验收及审计

计划版本 `compiler_edit_plan_v18.1`；审计输入版本 `compiler_input_audit_v18.1`。计划字段为 schema_version、round_id、parent_skill_digest、source_diagnosis_refs、edit_units、noop_records。每个 edit unit 只有 operation、target_rule_refs、supporting_gap_refs，不含替换/删除文本、模型解释或额外推理字段。

`compile_edit_plan(CompilerInput)` 是纯函数，返回 EditPlan 或抛出 `CompilerRejected`。`validate_edit_plan(plan, compiler_input=...)` 接受本版 DTO 或 JSON，重验来源、重建规范计划，严格检查类型、字段和完整相等性；布尔 gap_index、遗漏/重复来源、越界目标、修改操作或顺序均拒绝，不排序或修补提交内容。此校验以确定性编译结果为基准，不是独立算法证明或语义裁判。

错误阶段沿用 INPUT / BINDING / PLAN。任何错误整份拒绝，不发布可执行部分计划。

`run_compiler(..., artifact_dir=新目录)` 先写 RUNNING，全部成功后保存 input.json、edit_plan.json，最后写含文件摘要的 VALID validation.json；每个文件通过临时文件原子替换。输入拒绝只留下 REJECTED validation.json；文件系统错误传播，不留下 VALID 完成标记。已有目录拒绝覆盖。

消费方必须检查 VALID 和文件摘要；仅文件存在不代表可用。input.json 原样保留 Parent、原始 learner payload、provenance 和 validated payload，不把临时 HMAC 当作跨进程认证。文本应用、空替换限制、纯删除执行及混合原子应用属于第 5 步，不在本步实现。

### 5. 验证结果

v17/v18 Compiler、审计与 v18 offline pilot 测试共 **62 项通过**。覆盖三类映射、纯 DELETE/全规则 DELETE、同操作传递合并、24 种输入排列一致性、非连续目标间穿插其他操作、同组/跨组混合操作冲突、计划篡改、过期目标、拒绝旧版封装、完整覆盖、全 NOOP、确定性文件摘要和防覆盖。没有语义质量关键词检查。

离线入口：

```bash
python scripts/runs/v18/run_v18_compiler_pilot.py --output artifacts/v18_compiler_pilot_new
```

源清单 [sources.json](../../../experiments/methods/v18/v18_compiler_pilot_001/config/sources.json) 固定 v2 Pilot 全部五份输出的摘要；逐一从原始固定请求重建并重验响应，不按人工评分筛选。不同 Parent/round 的五个开发样本分别编译，不混为一轮，也不声称提供了历史正式轮次的完整组集合。

构造样本原 provenance 缺少 parent_skill_digest。离线入口核对原始 provenance 后，仅针对明确标记为构造开发样本的输入，从精确 Parent 原文计算并补充本次可信调用方元数据；Compiler 的绑定要求没有放宽。learner payload、原始响应及历史文件均不改动。

本次产物：[summary.json](../../../artifacts/methods/v18/v18_compiler_pilot_001/summary.json)。五份均 VALID，总计 **4 ADD、1 REPLACE、1 DELETE**，全部 6 个 gap 覆盖一次，0 模型调用、0 Candidate。语义部分失败的修订和历史 artifact 相关 gap 仍原样保留；编译有效性不表示学习语义正确或 Gate ACCEPT。

<a id="v18-editor-contract"></a>

## v18 Editor 与确定性文本应用

状态：第 5 步已实现，2026-09-19。v17 不改动；尚未接入 v18 formal/Monitor 调度。本步工程测试和真实删除样本验证不代表模型语义效果或 Gate ACCEPT。

### 1. 模块与职责

| 模块 | 职责 |
|---|---|
| `editor_contract_v18.py` | 独立运行时/模型类型和 Schema |
| `editor_input_v18.py` | 重新验收来源与计划，打包单元依据，过滤模型输入 |
| `editor_prompt_v18.py` | `v18-bounded-editor-1`，受限语义改写 Prompt |
| `editor_apply_v18.py` | 严格解析、覆盖检查、原始范围原子应用 |
| `editor_v18.py` | 一次模型调用或纯确定性执行，审计落盘 |

入口仍为 `EditorInput(compiler_input, plan)`，只接受本版类型和已绑定来源。每次构造请求/应用响应都重新验收 Compiler 计划；修改 Parent、操作或目标不能绕过校验。

Compiler 决定操作和范围，Editor 不改变计划、不重新 Diagnosis、不跨 unit 借用证据或自行增删规则。模型只为 ADD/REPLACE 表达文本，DELETE 由程序执行。

### 2. 运行时包与模型输入

运行时 `EditorRequest` 保留完整计划对应的 ADD/REPLACE/DELETE 单元。每个单元包括原始 edit_unit_index、operation、精确目标原文与坐标、backing gaps、相关两维 Analysis/unresolved 和引用证据目录。各 unit 的来源独立解析；NOOP 不作为编辑单元。来源归属与引用绑定可验证，单次模型调用的注意力隔离不是物理隔离。

`editor_payload()` 只序列化 ADD/REPLACE 单元，DELETE 不作为模型待办。原始索引不重编号，例如完整计划为 DELETE(0)、REPLACE(1)、DELETE(2)、ADD(3)，模型只接收索引 1 和 3。共享 Parent 仍提供完整原文以理解上下文，不授予改动其他规则的权限。

请求 schema_version 为 `editor_request_v18.1`，response format 名称为 `v18_bounded_editor`。记录 Parent、完整计划、模型输入和 Prompt 摘要；计划摘要与 Compiler 审计中的 JSON 字节摘要一致。

`build_editor_request()` 在无文本单元时返回 None。这包括全 NOOP 和纯 DELETE，调用方须由应用器区分，不得一律解释为 NO_UPDATE。

### 3. Prompt 的语义边界

Prompt 要求忠实保留 Diagnosis 支持的可观察条件、具体行为关系、适用范围与 epistemic status。候选规律在指导文本本身保持条件性和暂定性质，不能先强化为普适命令再附免责声明，也不能将已有具体规律缩写为泛泛建议。

禁止自行增加 verification duty、execution prerequisite、prohibition、escalation 或 stopping condition，或为显得安全/保守而扩展范围。未知机制不自动生成 Agent 核实义务；真实 policy、工具契约和用户约束仍有效。

REPLACE 保留仍有效的 Parent 内容，服从 backing gaps 授权的修改。Analysis 与 gap 在条件、义务或确定性上冲突，或现有依据不足以完成编辑时，应整份返回 UNABLE，不选择更强表述、不重新诊断、不暗中漏掉部分计划。已有 transfer fallback 语义问题不由程序关键词过滤或自动修补；Prompt 的实际遵循质量尚需独立模型试验。

本版没有加入 benchmark/runtime artifact 特判，Diagnosis/Editor 的职责不扩展为运行器语义解释。

### 4. 模型输出与覆盖

模型输出字段仍为 status、reason、edits；状态只有 EDITED 或 UNABLE。每条 edit 恰有 edit_unit_index 和 text。

- EDITED 必须按索引递增恰好覆盖所提供的 ADD/REPLACE 单元，允许索引不连续。
- 不接受 DELETE 的 text，不允许填补索引空缺、重新编号、遗漏、重复、乱序或越界。
- text 必须为非空白、可编码 UTF-8 的字符串；REPLACE 不允许空文本充当隐式删除。
- UNABLE 的 edits 必须为空，reason 非空；整份计划不应用，包括 DELETE。
- JSON 围栏、附加文字、重复 key、非有限值、额外字段、布尔索引等直接拒绝，不提取或修复。

纯 DELETE 和全 NOOP 必须传 raw=None，任何伪造模型响应都拒绝。模型拒绝、截断和传输错误不重试，也不退化为仅执行 DELETE。

### 5. 确定性文本应用

所有范围基于原始 Parent 的保留换行符行列表换算，不按已修改内容重新定位。目标原文必须精确匹配原始切片，所有范围先验收，再拼接 Candidate；任何错误不返回部分 Candidate。

DELETE 删除所列原始范围，不生成替代文本，不删除未指定标题、空行或中间内容，不格式化文档。允许删除全部规则后得到空字符串或仅标题 Candidate。

REPLACE 将模型文本放在该单元最早目标位置，其余目标范围移除；不连续目标之间的未指定内容原样保留。替换文本不 strip，仅末尾缺 LF 时补 LF 作为边界分隔。

ADD 固定按计划索引追加到完成目标编辑后的文本末尾：非空文本先补 LF（如缺失），再加一个 LF；每条新增文本末尾缺 LF 时补 LF，项间加一个 LF。已有空白不折叠。这沿用 v17 的明确分隔约定，不是模型输出修补。

应用结果：

| 情况 | `apply_editor_response` | runner 最终状态 | Candidate | 模型调用 |
|---|---|---|---|---:|
| 含 ADD/REPLACE，全部通过 | EDITED | VALID | 有 | 1 |
| 纯 DELETE | APPLIED_DETERMINISTIC | APPLIED_DETERMINISTIC | 有，包括空文本 | 0 |
| 全 NOOP | NO_UPDATE | NO_UPDATE | 无 | 0 |
| 模型 UNABLE | UNABLE | UNABLE | 无 | 1 |
| 校验/调用失败 | 异常或拒绝 | REJECTED | 无有效产物 | 0 或 1 |

后续调度必须同时识别 VALID 与 APPLIED_DETERMINISTIC 为已生成 Candidate，不能因空文本或无模型响应而跳过 Monitor。该调度接入属于第 6 步，本步不改 v17 formal。

### 6. 审计与失败

runner 使用 deepseek-v4-pro、temperature=0、reasoning_effort=high、24,000 completion tokens、300 秒 timeout、SDK max_retries=0。无自动重试、fallback 或输出修补。

新目录首先写 RUNNING。保存精确 parent_skill.md、edit_plan.json；有模型时保存 request.json、原始 response.json 和合法 edits.json。成功应用另存 `application.json`，schema_version 为 `editor_application_v18.1`，包括：

- Parent/plan/Candidate 摘要；
- 模型生成单元的原始索引；
- 确定性删除单元的原始索引、精确目标原文/引用/坐标，以及原样 backing gaps 和来源引用。

纯 DELETE 不生成伪造 request、response 或 edits。成功后写 candidate_skill.md，最后以终态 validation.json 发布产物摘要。UNABLE 或拒绝不写 application/Candidate；从不覆盖传入的 Parent。

各文件通过临时文件原子替换。文件系统错误传播，可能留下中间文件，但没有成功终态就不得消费。逻辑原子性不等于整个目录文件系统事务；读取方必须检查终态和全部文件摘要。已有目录拒绝覆盖。

### 7. 验证记录

相关 v17/v18 Editor、应用、输入以及 v18 Compiler/审计测试共 **117 项通过**。覆盖原始索引 1/3 的混合计划、非法删除 text、空替换、完整覆盖、重复/乱序/布尔索引、非连续目标、中文与 CRLF、空/仅标题 Candidate、无模型纯删除、全 NOOP、UNABLE、截断/拒绝/传输失败、写盘失败无成功终态，以及原始 Parent 保持。

另使用已保存的 v2 Pilot `constructed-should-remove` 诊断与第四步计划，完成真实确定性删除应用（无新增模型调用）：

- 输出目录：[v18_editor_delete_pilot_001](../../../artifacts/methods/v18/v18_editor_delete_pilot_001)。
- 状态：APPLIED_DETERMINISTIC，model_calls=0。
- 删除完整“姓名含数字则拒绝并转人工”规则，保留原有标题和空行。
- [application.json](../../../artifacts/methods/v18/v18_editor_delete_pilot_001/application.json) 记录删除原文、来源及摘要；[candidate_skill.md](../../../artifacts/methods/v18/v18_editor_delete_pilot_001/candidate_skill.md) 为开发样本产物。

本次 ADD/REPLACE 与混合路径使用模拟 transport 验证工程行为；未调用真实 Editor 模型，不能宣称语义改写质量已验证。未提升 Candidate、未运行 Monitor/Gate 或完整 v18 campaign，v17 文件与历史产物保持不动。

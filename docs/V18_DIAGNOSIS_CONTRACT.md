# v18 Diagnosis 输入输出与验收契约

状态：第 2 步契约与第 3 步 Prompt/transport 已实现；2026-09-19 第 4 步 [Compiler](V18_COMPILER_CONTRACT.md) 和第 5 步 [Editor/应用器](V18_EDITOR_CONTRACT.md) 已接入，尚未进入完整 v18 campaign。Prompt 实施说明见文末。

## 1. 模块与版本

| 模块 | 职责 |
|---|---|
| `src/skill_evolution/diagnosis_contract_v18.py` | strict JSON Schema、字段/类型/枚举及跨字段结构约束 |
| `src/skill_evolution/diagnosis_references_v18.py` | 当前组证据、可见 policy、当前 Parent 规则的引用解析 |
| `src/skill_evolution/diagnosis_validation_v18.py` | PARSE → STRUCTURE → REFERENCES → LINKAGE 验收与独立封装 |

三份模块从 v17 对应实现独立复制并修改；v17 文件、Schema、验收行为不变。未变化的输入装配仍复用 `group_diagnosis_input_v17.GroupDiagnosisInput`（payload 版本 v17.2、签名种类 `V17_GROUP_DIAGNOSIS_INPUT`），引用寻址规则完全兼容。暂不为未变化的 Grouping/经验输入另建协议。

模型 response format 名称为 `v18_group_diagnosis`，strict=true。成功输出的 Envelope kind 为 `V18_VALIDATED_DIAGNOSIS`，payload schema_version 为 `validated_diagnosis_v18.1`。不能用 v17 的 Envelope kind 解包，也不能直接送入 v17 Compiler；v18 Compiler 接入属于第 4 步。

## 2. 输出结构

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

## 3. 三种 gap

每个 gap **恰好五个字段**：`kind`、`gap`、`evidence_refs`、`related_rule_refs`、`source_dimensions`。不新增 removal_justification、operation、gap_id 或最终 Skill 文本字段。

| kind | 含义 | related_rule_refs | 后续确定性映射 |
|---|---|---|---|
| MISSING | 缺少证据支持的指导 | 必须为空 | ADD |
| NEEDS_REVISION | 已有规则核心方向仍有价值，条件、范围或内容需要修改 | 必须非空 | REPLACE |
| SHOULD_REMOVE | 整个目标规则被证明不必要、错误或不应继续存在，删除优于修改 | 必须非空 | DELETE |

上述操作映射是未来 Compiler 的约定，不是本步输出字段或已实现的编辑操作。`kind="DELETE"` 非法。

所有 gap 的 evidence_refs 必须非空，解析后至少含一个本组轨迹事件；仅有 policy 引用不够。source_dimensions 必须为 SUCCESS、COMPLIANCE 或两者，无重复。NEEDS_REVISION/SHOULD_REMOVE 的目标均须解析到当前 Parent 的完整规则块；未知、过期或其他类型引用拒绝。

### SHOULD_REMOVE 的更高证据门槛

Diagnosis 应在已有 finding/gap 文本及引用中明确说明：

1. 规则的核心指令被什么证据否定，或为何没有应继续保留的作用；
2. 结论为何涉及整个引用块，而非局部条件或措辞；
3. 为什么缩小范围、补齐条件、降低确定性或保留有效部分的修订不适合；
4. 删除将改变 Agent 的哪个具体决策，并且不绕过有效 policy、用户约束或工具契约。

规则范围过宽、条件缺失、表述过强，优先 NEEDS_REVISION。一个 Markdown 块仍有有效指导时，也应 REPLACE 保留有效部分。单次失败、规则本轮未触发、未观察到收益、尚不确定，不能单独构成删除依据；证据不足则不强制产生 gap。不以固定最小样本数代替证据质量。

这是语义契约，由第 3 步 Prompt 和后续离线语义评估落实。确定性验收不使用关键词、文本长度或引用数量来伪装验证删除理由；结构 VALID 不证明已经达到更高证据门槛。

## 4. 确定性验收

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

## 5. 验证记录

测试：`test_diagnosis_contract_v18.py`、`test_diagnosis_references_v18.py`、`test_diagnosis_validation_v18.py`；测试输入复用未变化的 v17 经验/分组构造 fixture，不复用 v17 输出验收。

已运行 v18 三份测试与对应 v17 回归测试，共 **150 项通过**。覆盖三类 gap 目标基数、删除规则引用、跨组/过期/错误类型引用、Analysis 关联、结构拒绝、原始响应保留、独立封装版本和新旧 Schema 隔离。构造样本中的 SHOULD_REMOVE 通过只验证协议，不代表样本的删除理由在语义上成立。

## 6. 第 3 步：通用 Prompt 与请求接入

`diagnosis_prompt_v18.py` 当前定义 `v18-group-diagnosis-2`（2026-09-19），通过以下顺序约束一次模型调用内的推理：

1. 两维 Analysis 优先对比可观察条件、行为与结果，保留反例；不完整的机制解释不能抹掉已支持的候选关系，也不能补造精确映射。
2. Addressability 的 reason 指出修改 Skill 能改变的具体决策或行为，以及现有信息/工具/合法交互依据；不检查 runtime 回合可达性。
3. Gap 保留 Analysis 中条件、行为、适用范围和 epistemic status；候选规律在 gap 本身仍须为条件性、暂定指导，不能写成普适强规则后再加免责声明。未知不自动产生核实、前置、禁止、转人工或停止义务；新增限制必须已有来源 Analysis 支持其必要性，需要核实或满足的前提还须存在合法可行路径。不得额外安全化、保守化或扩展义务。真实用户和 policy 限制继续有效。
4. 三种 gap 按第 3 节区分。删除需要说明整块规则为何不应保留、为何修订不足、会改变什么决策；仍有有效内容时优先修订。

固定 Prompt 不包含任务编号、渠道/姓名/人数案例、隐藏 benchmark 标签或样本答案；没有新增输出字段。`build_diagnosis_prompts` 和 `build_diagnosis_request` 保留完整 learner payload，不发送运行时 provenance。默认 experiment_scope 为空，只有可信调用方显式指定时才附加，并记录实际 system prompt SHA-256；不隐含沿用历史 pilot 的目标排除条款。

独立 `diagnosis_v18.py` 复用 v17 的一次调用审计方式，接入 v18 Prompt/Schema/验收封装：deepseek-v4-pro、temperature=0、reasoning_effort=high、24,000 completion tokens、300 秒 timeout、SDK max_retries=0，无自动修补/重试/fallback。调用前保存 request/provenance，之后保留原始 response、完成状态、provider model/id、usage 和验收结果；不覆盖已有目录。版本化模型名称不保证远端后端固定。

新增固定输入 pilot：`scripts/run_v18_diagnosis_pilot.py`，输入清单在 `experiments/configs/v18_diagnosis_pilot_001/sources.json`。清单固定 R2 g5、R2 g3、R3 g6 三组已保存的 Evolution 请求，绑定 request/provenance/response/validated 文件摘要并复验历史请求和响应，只将原始 learner payload 发给 v18。历史 Diagnosis 输出仅用于来源复验，不进入新模型输入；不读取 Monitor。该入口是对可信本地历史产物的显式回放，不是任意外部 JSON 的可信装载器。

```bash
# 仅复验固定输入，不调用模型；目录必须不存在。
python scripts/run_v18_diagnosis_pilot.py --output artifacts/v18_diagnosis_preflight_new
# 同样的三组输入，每组一次模型调用。
python scripts/run_v18_diagnosis_pilot.py --run --output artifacts/v18_diagnosis_pilot_new
```

Prompt、模型请求和 pilot 新增测试连同 v17/v18 契约相关回归，共 **184 项通过**。检查完整输入与 v17 相同、实际 SDK 消息/Schema 一致、Prompt 摘要绑定、源文件漂移拒绝、删除输出进入 v18 验收、拒绝与传输失败不重试。语义效果需单独看 pilot 分析，不能由这些测试推断。

上述三次真实调用使用 Prompt v1，均结构 VALID；新增执行门槛和经验规律强度仍有疑问。完整记录见 [首次固定输入试验报告](V18_DIAGNOSIS_PILOT_REPORT.md)。历史报告中的 STOP artifact 不作为 v2 核心语义验收项；本次未运行 v2 模型调用，不把 v1 结果冒充 v2 效果。

### 正式职责边界（2026-09-19）

Benchmark/User Simulator 在上游负责生成语义合理、可学习的 trajectory，消除或避免确认同时终止等交互 artifact。Diagnosis 只归纳规律、判断 Skill 可修改问题并保持 Analysis→Addressability→Gap 的语义与确定性，不负责识别、解释或补救 benchmark/runtime artifact。

Prompt v2 不包含 STOP、termination marker 等特判，已移除环境结束/下一轮/恢复交互的专门约束；输入不新增 terminated、termination_reason、agent_has_next_turn。结构、引用和语义验收不加入终态专项要求或测试。历史输入原样复现，其 artifact 解释不参与 v2 核心语义验收。Simulator 层自己的终止测试继续保留，与 Diagnosis 验收分开。

### Prompt v2 固定输入 Pilot

2026-09-19 对三组历史输入及两个构造操作边界样本各运行一次，无重试或修补。5/5 结构 VALID；核心语义 4 PASS、1 PARTIAL_FAIL。v2 消除了历史定价组的额外 summit guard，并保持人数与渠道规律的候选性质；SHOULD_REMOVE 判定符合预设边界。NEEDS_REVISION 样本仍保留了来源未证明必要的 transfer fallback，说明已有保守条款在修订时仍可能被无依据保留。详见 [v2 Pilot 报告](V18_DIAGNOSIS_V2_PILOT_REPORT.md)。

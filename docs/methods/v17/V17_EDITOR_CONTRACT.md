# v17 Bounded Editor 输入输出契约

状态：第 1 步。类型与模型输出 Schema 位于
`src/skill_evolution/v17/editor_contract_v17.py`。尚未实现输入包构建、prompt、验收、
文本应用、模型调用或审计写入。类型注解不是验收。

## 职责与隔离边界

一次模型调用处理整份 Edit Plan，每个 edit unit 有独立证据包，输出一份对应的
局部文本。Compiler 决定操作和目标；Editor 表达已有修改依据，不重新 Diagnosis，
不选择 ADD/REPLACE/DELETE，不修改计划，不跨 unit 合并或借用证据补充结论。

共享 Parent 用于理解已有指导，不作为其他 unit 经验的替代来源。单次调用仍能
看到所有 unit，因此这是逻辑隔离，不是物理上下文隔离。程序检查包的来源归属、
输出覆盖和修改范围，不能证明模型没有暗中利用另一包的信息。

## Runtime 输入

`EditorInput(compiler_input, plan)` 保留 CompilerInput 的完整可信来源及 EditPlan。
后续入口必须调用既有计划校验，确保 round、Parent、来源与计划一致，不接受只凭
文件中的 VALID 标签。运行时来源和审计路径不直接作为模型输入。

Parent 摘要使用精确原始 UTF-8 文本 SHA-256。plan_sha256 固定为计划 JSON 的
`json.dumps(plan_payload, ensure_ascii=False, sort_keys=True, indent=2,
allow_nan=False) + '\n'` 的 UTF-8 字节摘要，与 Compiler edit_plan.json 一致。

## 模型输入包

EditorRequest 共享字段：schema_version=editor_request_v17.1、parent_skill、
parent_skill_digest、plan_sha256、edit_units。NOOP 不打包为编辑单元，不传其
Diagnosis 文本。edit_unit_index 是原计划 edit_units 的零起始索引，不重编号。

每个 EditorUnitPackage：

| 字段 | 内容 |
|---|---|
| edit_unit_index | 固定计划单元索引 |
| operation | 由计划提供的 ADD 或 REPLACE |
| target_rules_json | 目标规则原文、ref 和行范围的记录列表；ADD 为 [] |
| backing_gaps_json | 列表，每项含 gap_ref（diagnosis_ref/gap_index）与原始 gap |
| analyses_json | 列表，每项含 diagnosis_ref、success_analysis、compliance_analysis |
| evidence_json | 本 unit 引用的解析目录，原始引用 ID → typed record |

JSON 字符串仅是 Python DTO 内的不可变快照；构造实际模型消息时解码成嵌套对象，
不要求模型解析双重编码。analyses 保留关联 Diagnosis 的两维 finding/unresolved
与引用，不能把同一组内的其他 gap 顺带加入 backing_gaps。

目录包含 backing gaps 与上述 analyses 实际引用的 trajectory/policy/supervision
记录及相关 Parent rule，不复制完整 trajectory 或全局经验库。解析结果沿用现有
引用解析器的原始字段。多个来源同 ID 若内容不一致，拒绝，不选一份覆盖另一份。
同一证据确实被多个单元独立引用时可分别打包，不视为跨单元借用。

该目录定义避免分析中留下悬空引用；并非断言每条 group-level finding 只谈一个
局部 gap。模型只能依据本包中明确绑定的 gap 进行该单元编辑。

## 模型输出

```json
{
  "status": "EDITED",
  "reason": "完成计划内编辑。",
  "edits": [
    {"edit_unit_index": 0, "text": "局部 Skill 指导文本"}
  ]
}
```

- EDITED：恰好覆盖所有编辑单元一次，按索引递增输出，text 必须包含非空白内容。
  不允许缺失、重复、越界、字符串/布尔索引或新增操作/目标字段。
- UNABLE：reason 非空，edits=[]，表示整份计划无法完成；不产生部分 Candidate。
  不强制模型通过删除 gap、选择一个来源或自创规则解决冲突。
- reason 两种状态均为非空字符串。无额外字段、不接受 Markdown JSON 围栏，重复
  JSON key 拒绝。文本中合法 Markdown 是 Skill 正文，不是 JSON 格式修复对象。

计划全为 NOOP 时由程序跳过模型：runtime 状态 NO_UPDATE，不伪造 EDITED/UNABLE
响应、不生成 Candidate。NO_UPDATE 不是模型输出枚举。

## 确定性文本应用（后续实现）

所有坐标解析自原始 Parent，使用保留行结束符的行列表，不以顺序修改后的文本
重新定位。目标必须与计划和当前 Parent 规则目录完全匹配。未指定文本保持精确
原样，包括标题、空行与换行符；不格式化整份文档。

### REPLACE

一个单元的目标可包含不连续规则。将其 text 写入最早目标规则的位置，移除该
单元其余目标规则原范围；中间未指定内容原样保留。替换段定义为 text 原文，
若末尾没有 LF 则追加一个 LF 作为边界分隔。模型文本不 strip、不改写。
各单元原始目标范围若交叉则 APPLY 拒绝，不依靠后写覆盖前写。
禁止空替换，因此不把 REPLACE 当成隐式 DELETE。多个目标合成一个非空段是
Compiler 已授权的合并替换；后续规则引用基于 Candidate 重新生成。

### ADD

第一版固定追加，不选择章节、不改动 Parent 标题。按计划索引排列所有 ADD 文本，
写到文档末尾的追加块；不新增固定章节标题，也不搜索/改写历史追加块。

精确分隔约定：在 REPLACE 完成的文本后，若非空，先补 LF（仅当未以 LF 结尾），
再追加一个 LF；随后逐项加入 text 原文，各项若未以 LF 结尾则补一个 LF，项间
再加一个 LF。空 Parent 不加前置分隔。已有结尾空白不折叠。这些分隔字节属于
确定性新增内容，不是对模型输出的自动修补，raw text 始终原样保存。

### 范围验收

校验通过后一次性应用全部编辑；任何错误都不输出部分有效 Candidate。程序可
验证拼接中的非目标 Parent 片段逐字保留，但不能保证替换文本在语义上忠于 gap。
不增加新的语义判别层，不声称输出格式合法即表示 Skill 有效。

## 失败与审计边界

EditorRejected 阶段：INPUT/BINDING、PARSE、STRUCTURE、COVERAGE、APPLY。
非法输入和输出直接拒绝，不纠错、不补漏、不重排、不重试模型。UNABLE 是有效的
模型拒绝编辑结果，不混同于格式错误。网络失败、截断等在后续 runner 定义。

后续审计需绑定 Parent/plan/实际 prompt/request/response/Candidate 摘要。只有
严格验收和应用完成才发布有效 Candidate，绝不覆盖当前 Parent。原输出保留；
Candidate 是否接受交给 Monitor/Gate。第 1 步不创建任何 Candidate 或调用模型。

## 后续步骤

2. 构造独立输入包与通用固定 prompt；不加入 G1–G9 特例。
3. 严格输出验收与上述确定性文本应用，验证越界/重复/非连续替换/全 NOOP 等。
4. 一次模型调用及审计，不重试、不修补。
5. 使用当前 Compiler 七个 ADD 单元试运行。REPLACE 应用另用构造输入验证。

## 第 2 步已实现

`editor_input_v17.build_editor_input(EditorInput)` 先重新验收计划，再构建各 unit
独立包；`editor_prompt_v17.build_editor_request(EditorInput)` 是对外请求入口，
不接收任意预打包对象作为可信输入。固定 prompt 为 v17-bounded-editor-1，只有
通用编辑职责、unit 内证据约束与输出规则，无 benchmark 样本特例。

包中保留绑定 gap 的原文和两维 analysis/unresolved；只解析这些内容引用的记录，
不加入其他 gap 或全局目录。相同来源 analysis 在同一 unit 内仅打包一次。目录
同 ID 内容冲突直接拒绝。target_rules 按计划顺序提供原文及位置。

请求保存 Parent/plan/input/prompt 摘要和响应 Schema，实际 user_prompt 是嵌套
JSON，不是重复编码的 JSON 字符串。全 NOOP 时请求入口返回 None，后续调用方
据此报告 NO_UPDATE 并跳过模型。当前没有模型调用或文本应用。

已验证两组独立目录、输入顺序无关性、NOOP 排除、Parent/计划篡改拒绝，以及
policy/Parent rule 原文解析。本步骤不保证单次调用的物理上下文隔离。

## 第 3 步已实现

`editor_apply_v17.apply_editor_response(raw, editor_input=...)` 每次重新验收输入和
计划，严格解析原始 JSON，不提取围栏、不修补、不重排。EDITED 必须精确按顺序
覆盖所有单元，索引不接受布尔值，空文本和非法 UTF-8 文本拒绝。UNABLE 不产生
Candidate；全 NOOP 仅接受 raw=None，返回 NO_UPDATE。

应用使用原 Parent 行范围转换出的字符位置，以原始片段拼接实现非目标内容原样
保留；替换仅作用于目标范围，非连续目标间的标题、空白和规则不被删除。追加与
换行采用前述固定约定。返回原始响应、解析输出、Parent/plan 摘要和 Candidate
及其 SHA-256；不写文件、不覆盖 Parent。运行时错误不返回部分结果。

测试覆盖空 Parent、无结尾换行、CRLF/Unicode、非连续 REPLACE 与 ADD 混合、
非目标片段精确保留、重复 JSON key、非法输出/索引/覆盖、UNABLE、全 NOOP 和
过期 Parent。这里只保证结构与编辑边界，不保证新文本的语义质量。

## 第 4 步已实现

`editor_v17.run_editor(EditorInput, artifact_dir=..., transport=None)` 接入一次调用。
固定 deepseek-v4-pro、temperature=0、reasoning_effort=high、24,000 completion
预算、300 秒超时；OpenAI SDK max_retries=0，无应用层重试、fallback 或格式修补。
不依赖 Diagnosis runner 的可变配置常量。模型别名不保证后端版本永久固定，响应
中的 provider model/id 原样保留。

新审计目录首先记录 RUNNING；输入验收后保存 parent_skill.md、edit_plan.json，
调用前保存 request.json（输入、prompt、参数和摘要）。响应保存在 response.json，
包含未经 strip 的原始内容、finish_reason、refusal、usage 和模型标识。截断或拒绝
直接 REJECTED/COMPLETION；合法响应进入第 3 步严格校验与应用。

成功保存 edits.json 与 candidate_skill.md，最后发布 VALID validation.json。
UNABLE 保存合法输出但无 Candidate；全 NOOP 保存 Parent/plan 并返回 NO_UPDATE，
没有模型请求。非法输出无 edits/Candidate，输入错误无模型调用。TRANSPORT 只
记录异常类型/HTTP 状态，不倾倒连接参数。文件摘要按实际 UTF-8 字节计算。

每个文件通过临时文件原子替换写入，新目录要求禁止覆盖历史结果。I/O 异常传播，
没有 VALID 完成标记的目录不能消费；即使 Candidate 文件存在也必须核验终态与
摘要。这里的 VALID 不代表 Gate ACCEPT。此次只使用假 transport 验证，无真实
模型调用；真实七单元试运行留待第 5 步。

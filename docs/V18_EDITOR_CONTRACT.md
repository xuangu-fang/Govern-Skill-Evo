# v18 Editor 与确定性文本应用

状态：第 5 步已实现，2026-09-19。v17 不改动；尚未接入 v18 formal/Monitor 调度。本步工程测试和真实删除样本验证不代表模型语义效果或 Gate ACCEPT。

## 1. 模块与职责

| 模块 | 职责 |
|---|---|
| `editor_contract_v18.py` | 独立运行时/模型类型和 Schema |
| `editor_input_v18.py` | 重新验收来源与计划，打包单元依据，过滤模型输入 |
| `editor_prompt_v18.py` | `v18-bounded-editor-1`，受限语义改写 Prompt |
| `editor_apply_v18.py` | 严格解析、覆盖检查、原始范围原子应用 |
| `editor_v18.py` | 一次模型调用或纯确定性执行，审计落盘 |

入口仍为 `EditorInput(compiler_input, plan)`，只接受本版类型和已绑定来源。每次构造请求/应用响应都重新验收 Compiler 计划；修改 Parent、操作或目标不能绕过校验。

Compiler 决定操作和范围，Editor 不改变计划、不重新 Diagnosis、不跨 unit 借用证据或自行增删规则。模型只为 ADD/REPLACE 表达文本，DELETE 由程序执行。

## 2. 运行时包与模型输入

运行时 `EditorRequest` 保留完整计划对应的 ADD/REPLACE/DELETE 单元。每个单元包括原始 edit_unit_index、operation、精确目标原文与坐标、backing gaps、相关两维 Analysis/unresolved 和引用证据目录。各 unit 的来源独立解析；NOOP 不作为编辑单元。来源归属与引用绑定可验证，单次模型调用的注意力隔离不是物理隔离。

`editor_payload()` 只序列化 ADD/REPLACE 单元，DELETE 不作为模型待办。原始索引不重编号，例如完整计划为 DELETE(0)、REPLACE(1)、DELETE(2)、ADD(3)，模型只接收索引 1 和 3。共享 Parent 仍提供完整原文以理解上下文，不授予改动其他规则的权限。

请求 schema_version 为 `editor_request_v18.1`，response format 名称为 `v18_bounded_editor`。记录 Parent、完整计划、模型输入和 Prompt 摘要；计划摘要与 Compiler 审计中的 JSON 字节摘要一致。

`build_editor_request()` 在无文本单元时返回 None。这包括全 NOOP 和纯 DELETE，调用方须由应用器区分，不得一律解释为 NO_UPDATE。

## 3. Prompt 的语义边界

Prompt 要求忠实保留 Diagnosis 支持的可观察条件、具体行为关系、适用范围与 epistemic status。候选规律在指导文本本身保持条件性和暂定性质，不能先强化为普适命令再附免责声明，也不能将已有具体规律缩写为泛泛建议。

禁止自行增加 verification duty、execution prerequisite、prohibition、escalation 或 stopping condition，或为显得安全/保守而扩展范围。未知机制不自动生成 Agent 核实义务；真实 policy、工具契约和用户约束仍有效。

REPLACE 保留仍有效的 Parent 内容，服从 backing gaps 授权的修改。Analysis 与 gap 在条件、义务或确定性上冲突，或现有依据不足以完成编辑时，应整份返回 UNABLE，不选择更强表述、不重新诊断、不暗中漏掉部分计划。已有 transfer fallback 语义问题不由程序关键词过滤或自动修补；Prompt 的实际遵循质量尚需独立模型试验。

本版没有加入 benchmark/runtime artifact 特判，Diagnosis/Editor 的职责不扩展为运行器语义解释。

## 4. 模型输出与覆盖

模型输出字段仍为 status、reason、edits；状态只有 EDITED 或 UNABLE。每条 edit 恰有 edit_unit_index 和 text。

- EDITED 必须按索引递增恰好覆盖所提供的 ADD/REPLACE 单元，允许索引不连续。
- 不接受 DELETE 的 text，不允许填补索引空缺、重新编号、遗漏、重复、乱序或越界。
- text 必须为非空白、可编码 UTF-8 的字符串；REPLACE 不允许空文本充当隐式删除。
- UNABLE 的 edits 必须为空，reason 非空；整份计划不应用，包括 DELETE。
- JSON 围栏、附加文字、重复 key、非有限值、额外字段、布尔索引等直接拒绝，不提取或修复。

纯 DELETE 和全 NOOP 必须传 raw=None，任何伪造模型响应都拒绝。模型拒绝、截断和传输错误不重试，也不退化为仅执行 DELETE。

## 5. 确定性文本应用

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

## 6. 审计与失败

runner 使用 deepseek-v4-pro、temperature=0、reasoning_effort=high、24,000 completion tokens、300 秒 timeout、SDK max_retries=0。无自动重试、fallback 或输出修补。

新目录首先写 RUNNING。保存精确 parent_skill.md、edit_plan.json；有模型时保存 request.json、原始 response.json 和合法 edits.json。成功应用另存 `application.json`，schema_version 为 `editor_application_v18.1`，包括：

- Parent/plan/Candidate 摘要；
- 模型生成单元的原始索引；
- 确定性删除单元的原始索引、精确目标原文/引用/坐标，以及原样 backing gaps 和来源引用。

纯 DELETE 不生成伪造 request、response 或 edits。成功后写 candidate_skill.md，最后以终态 validation.json 发布产物摘要。UNABLE 或拒绝不写 application/Candidate；从不覆盖传入的 Parent。

各文件通过临时文件原子替换。文件系统错误传播，可能留下中间文件，但没有成功终态就不得消费。逻辑原子性不等于整个目录文件系统事务；读取方必须检查终态和全部文件摘要。已有目录拒绝覆盖。

## 7. 验证记录

相关 v17/v18 Editor、应用、输入以及 v18 Compiler/审计测试共 **117 项通过**。覆盖原始索引 1/3 的混合计划、非法删除 text、空替换、完整覆盖、重复/乱序/布尔索引、非连续目标、中文与 CRLF、空/仅标题 Candidate、无模型纯删除、全 NOOP、UNABLE、截断/拒绝/传输失败、写盘失败无成功终态，以及原始 Parent 保持。

另使用已保存的 v2 Pilot `constructed-should-remove` 诊断与第四步计划，完成真实确定性删除应用（无新增模型调用）：

- 输出目录：[v18_editor_delete_pilot_001](../artifacts/v18_editor_delete_pilot_001)。
- 状态：APPLIED_DETERMINISTIC，model_calls=0。
- 删除完整“姓名含数字则拒绝并转人工”规则，保留原有标题和空行。
- [application.json](../artifacts/v18_editor_delete_pilot_001/application.json) 记录删除原文、来源及摘要；[candidate_skill.md](../artifacts/v18_editor_delete_pilot_001/candidate_skill.md) 为开发样本产物。

本次 ADD/REPLACE 与混合路径使用模拟 transport 验证工程行为；未调用真实 Editor 模型，不能宣称语义改写质量已验证。未提升 Candidate、未运行 Monitor/Gate 或完整 v18 campaign，v17 文件与历史产物保持不动。

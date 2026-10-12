# v17 Compiler 输入输出契约

状态：已完成第 3 步计划验收与审计产物。类型与 Schema 位于
`src/skill_evolution/v17/compiler_contract_v17.py`，编译入口位于
`src/skill_evolution/v17/compiler_v17.py`。独立计划验收与审计写入已实现；历史文件加载与 Editor
尚未实现。类型注解和 JSON Schema 不代表已通过验收。

## 职责

Compiler 将一个 Round 的已验收 Diagnosis 转换为确定性编辑计划。它不调用
模型，不判断根因，不根据自然语言重新判定 addressability，不补充隐藏规则，
不生成 Skill 文本。计划有效不等于 gap 正确，也不等于 Gate ACCEPT。

首版支持 ADD / REPLACE / NOOP；不支持 DELETE。NEEDS_REVISION 没有提供可供
程序确定删除的字段，因此不能从 gap 文本猜测删除意图。

## 输入

`CompilerInput`：

| 字段 | 含义 |
|---|---|
| round_id | 可信调用方指定的当前轮次 |
| parent_skill | 精确 Parent 文本；允许空文本或只有标题 |
| parent_skill_digest | 原始 UTF-8 文本 SHA-256，不做空白归一化 |
| diagnoses | 非空、完整的本次选定 Diagnosis 来源集合 |

每个 `CompilerDiagnosisSource` 包含：

- diagnosis_ref：`DIAGNOSIS/<digest>`，digest 为 validated Envelope.payload 原始
  UTF-8 字节 SHA-256。标识内容，不依赖文件路径、时间戳或输入顺序。
- request：原始 `GroupDiagnosisInput`，保留 learner_view 和 runtime provenance，
  用于验证 round、Parent、group 和 evidence 的绑定。
- validated：`V17_VALIDATED_DIAGNOSIS` Envelope，保留 semantic、resolved_references、
  raw_response 和 input digest。

现有 Diagnosis 输出不包含完整 round 绑定，因此不能只传 semantic 或读取一个
含 `validation_status=VALID` 的 JSON 就直接编译。跨进程历史产物应由可信上游
从原始输入和原始响应重新验收；Compiler 不提供绕过验收的自动 reseal。
来源的文件路径、模型/prompt 配置保留在既有审计文件，不作为规则来源标识。

可信调用方负责选定本轮完整输入集合，不按 gap 内容择优。本首版不额外设计
实验清单管理器：Compiler 能验证传入集合的一致性，不能证明外部是否漏传了一组。
同一个 round/group 的多个来源一律拒绝，即使内容相同；不自动挑选某次输出。

## 输入绑定要求（后续实现）

1. 所有来源都必须是有效的类型和已签名验收产物；来源标识与 payload digest 一致。
2. request provenance 的 round 与输入一致；精确 Parent 文本和 digest 一致。
3. validated.input_sha256 必须绑定该 request 的 learner payload；原始响应、semantic
   和解析引用必须符合既有 Diagnosis 验收，不接受任意拼装的摘要。
4. 每条 Parent rule 必须解析到当前 Parent，证据必须解析到对应 group 输入。
5. 输入中不得存在重复 group、混合 round、混合 Parent 或未验收响应。

错误直接拒绝整个输入，不跳过坏组继续返回看似完整的计划。

## 输出

`EditPlan` / `compiler_edit_plan_v17.1`：

```json
{
  "schema_version": "compiler_edit_plan_v17.1",
  "round_id": "round-1",
  "parent_skill_digest": "<64 lowercase hex characters>",
  "source_diagnosis_refs": ["DIAGNOSIS/<digest>"],
  "edit_units": [
    {
      "operation": "ADD",
      "target_rule_refs": [],
      "supporting_gap_refs": [
        {"diagnosis_ref": "DIAGNOSIS/<digest>", "gap_index": 0}
      ]
    }
  ],
  "noop_records": []
}
```

上例 digest 是说明性占位符。Python DTO 使用不可变 tuple，JSON 序列化为数组。
计划不复制 gap 文本、证据、维度或 Parent 规则正文；通过来源引用解析原始内容，
避免产生互相不一致的第二份解释。Editor 必须同时获得计划绑定的来源与 Parent，
不能只拿上述引用字符串独立执行。

`GapRef` 是 diagnosis_ref 与零起始 gap_index 的组合。index 精确指向
`semantic.parent_skill_gaps`，不能因排序、合并而重新编号。不同 Diagnosis
即便 gap 文字相同也保留各自来源，不做语义去重。

### 状态映射

| 来源 | 计划条目 |
|---|---|
| NO_ISSUE | NOOP record |
| NOT_ADDRESSABLE | NOOP record |
| ADDRESSABLE / MISSING | ADD edit unit |
| ADDRESSABLE / NEEDS_REVISION | REPLACE edit unit |

NOOP record 固定包含 operation=NOOP、diagnosis_ref、原始 status、原始 reason。
不为每个无 gap 的 analysis 单独生成 NOOP，也不为 ADDRESSABLE 中的 unresolved
问题创建新类别。全为 NOOP 时仍生成有效计划，edit_units=[]，不调用 Editor。
空输入是配置错误，不能伪装成全 NOOP。

### 编辑权限与结构合并

- ADD：target_rule_refs=[]；一个 MISSING gap 一个单元。允许增加指导，不允许
  改写既有规则。是否选择插入位置属于后续 Editor 契约，不由 Compiler 猜测。
- REPLACE：目标必须恰好覆盖所支持 NEEDS_REVISION gaps 的 related_rule_refs 并集。
  只允许替换所列规则，未列出的规则及其他 Parent 文本不在编辑授权内。
- 多个 REPLACE gaps 共享目标规则，或解析后的规则行范围有交集时，按传递闭包
  合并成一个编辑单元。例如 A/B 与 B/C 合并为目标 A/B/C 的一个单元。
- 合并只汇集目标和来源，不改写 gap、不决定哪个语义更优、不丢弃冲突意见。
  Editor 无法协调时须报告失败；Compiler 不用自然语言规则猜测冲突并选择胜者。
- ADD 不因与另一个 gap 看起来相似而合并，ADD 与 REPLACE 也不自动语义合并。
- 每个 ADDRESSABLE gap 必须恰好出现在一个编辑单元；每个非 ADDRESSABLE 来源
  必须恰好对应一个 NOOP。不能漏掉、复制或虚构来源。

### 确定性顺序

source_diagnosis_refs 按字典序。GapRef 按 (diagnosis_ref, gap_index) 排序。
REPLACE 目标按当前 Parent 的 (start_line, end_line, ref) 排序。
edit_units 中 REPLACE 在前，按最早目标行及 supporting_gap_refs 排序；ADD 在后，
按 GapRef 排序。noop_records 按 diagnosis_ref 排序。相同输入集合即使传入顺序
变化也产生相同计划；计划不含时间戳、随机 ID 或运行路径。

## 失败行为

`CompilerRejected(stage, reason)`：

| stage | 原因 |
|---|---|
| INPUT | 格式/类型不合法、空集合、未验收来源、重复 group 等 |
| BINDING | Parent/round/input digest 不一致、过期规则、无法解析的来源或引用 |
| PLAN | 操作不合法、目标范围错误、来源覆盖错误、合并或排序违反契约 |

严格拒绝，不纠正 ID、不替换引用、不重写 gap、不把错误转成 NOOP、不调用模型重试。
失败不输出可执行的部分计划。后续审计可记录 stage/reason 和输入来源，但不能留下
标为有效的计划。文件覆盖策略和具体审计目录在第 3 步实现。

失败是结构或绑定问题；诊断语义不够好不是一个可由当前程序识别的拒绝理由。
该边界尤其适用于 v7 pilot 中的弱 gap：编译成功不能证明它们值得 promotion。

## 后续实现边界

第 2 步实现来源绑定、映射、结构合并与排序；第 3 步实现计划校验和审计；第 4 步
使用当前 v7 九组离线试编译。其七个 MISSING gap 应产生七个 ADD，两组
NOT_ADDRESSABLE 应产生两个 NOOP。此处只是契约预期，尚未执行该试编译。
REPLACE/重叠目标/全 NOOP/非法输入路径另用小型构造输入验证，不重新 rollout。

## 第 2 步实现

`compile_edit_plan(CompilerInput) -> EditPlan` 是纯函数，不调用模型或写入文件。
它验证封装签名、来源 digest、唯一 group、round、精确 Parent 及其摘要，然后将
每个原始响应与原始 group 输入重新执行现有 Diagnosis 验收，要求完整产物一致。
所有来源通过以后才构建计划，失败不返回部分结果。

来源 provenance 沿用 GroupDiagnosisInput 的可信 runtime 边界：当前检查是绑定
一致性，不是对任意恶意调用方伪造 round/group metadata 的独立认证。历史 JSON
不能直接当作有效 Envelope 传入。

编译包含 ADD/REPLACE/NOOP 映射、按 Parent 行范围求 REPLACE 目标连通分量、稳定
排序。独立 ADD 保留原 gap 索引；不判断自然语言质量，不做模糊去重。全部 NOOP
返回空 edit_units 的正常计划。尚未进行当前 v7 九组试编译，留待第 4 步。

测试覆盖三状态、重复文字仍保留独立来源、传递目标合并与相邻目标不合并、24 种
来源排列的一致性、错误 Parent/round/来源、篡改验收内容和整体拒绝。第 3 步再补
独立计划验收与持久化审计，不在当前编译入口中增加自动修补。

## 第 3 步：计划验收与审计

`compiler_validation_v17.validate_edit_plan(plan, compiler_input=...)` 接收 DTO
或 JSON 对象，返回 None 表示通过。它重新验收来源、重编译规范计划，再严格检查
提交计划的字段/类型/枚举和完整内容一致性。遗漏、重复、越界、顺序变化、错误
原因等均拒绝，整数索引不接受布尔值或字符串。不排序或改写待验计划。这是相对
确定性编译结果的验收，不是独立的编译算法证明，也不是语义评审。

`compiler_audit_v17.run_compiler(input, artifact_dir=...)` 要求新目录。成功保存：

- input.json：稳定排序的来源快照，保留原始 learner payload、validated payload、
  provenance、Parent 与 round。不持久化会话 HMAC 作为跨进程认证。
- edit_plan.json：已验收的完整计划。
- validation.json：VALID、输入和计划实际文件字节的 SHA-256、编辑与 NOOP 数量。

开始先保存 RUNNING，完成全部文件后才写 VALID。文件使用临时文件原子替换；
消费方必须检查 VALID 及文件摘要，不能仅因 edit_plan.json 存在就执行。
同样输入集合（包括 provenance）产生字节一致的三份文件，无时间戳或输出路径。

输入拒绝只保存 REJECTED/stage/reason，不倾倒不可信任意对象、不保存部分计划，
不自动重试。文件系统异常直接传播，不能留下 VALID 完成标记。已有目录直接抛出
FileExistsError，原产物不覆盖。全 NOOP 正常 VALID，不触发 Editor。
历史快照不是重新签名的授权；未来加载器仍须经可信上游重新验收。

新增测试验证非法操作、布尔索引、引用/Parent/NOOP 原因篡改、缺失单元、排序、
输入排列无关的文件字节、摘要、拒绝产物、全 NOOP 与防覆盖。本步未调用模型，
未运行九组真实试编译，该步骤仍留待第 4 步。

## 第 4 步完成：v7 九组离线试编译

运行 `scripts/runs/v17/run_v17_compiler_pilot.py`，产物位于
[compiler_pilot_001](../../../artifacts/methods/v17/pilot/v17_compiler_pilot_001/report.md)。九组经过原始
响应复验与来源绑定后得到 VALID：7 ADD（G2–G8）、2 NOOP（G1/G9）。七个 gap
完整且恰好覆盖一次，倒序输入计划一致，落盘计划复验及文件摘要校验通过。
traceability.json 提供组、原产物路径/摘要与计划引用之间的映射。没有模型调用、
新 rollout、Diagnosis 改写或 Candidate Skill。真实 REPLACE 路径不在本次数据范围内。

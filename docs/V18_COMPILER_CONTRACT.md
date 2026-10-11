# v18 Compiler：确定性 ADD / REPLACE / DELETE

状态：第 4 步已实现，2026-09-19。独立于 v17，不调用模型，不改写 Diagnosis，不执行文本编辑，不产生 Candidate。

## 1. 实现与输入绑定

- `compiler_contract_v18.py`：不可变输入/计划类型、独立 JSON Schema。
- `compiler_v18.py`：来源重新验收、确定性映射、目标合并、冲突检查与排序。
- `compiler_validation_v18.py`：提交计划的严格结构及完整内容验收。
- `compiler_audit_v18.py`：无覆盖、无重试的审计落盘。

`CompilerInput` 保留 round_id、Parent 原文、UTF-8 SHA-256 及完整选定来源 tuple。每个 `CompilerDiagnosisSource` 包含 diagnosis_ref、原始已签名 GroupDiagnosisInput 和 `V18_VALIDATED_DIAGNOSIS` Envelope。来源引用为 `DIAGNOSIS/<validated.payload UTF-8 SHA-256>`。

输入必须非空。逐份验证：来源类型及签名、引用摘要、唯一 group/source、同一 round、同一精确 Parent 与摘要；使用原始响应对原始组输入重新执行 v18 Diagnosis 验收，要求重建结果与保存的完整 payload 相同。沿用当前组证据归属与当前 Parent 规则目录。拒绝 v17 Diagnosis 封装，不自动转换。

调用方负责提供完整选定来源集合，Compiler 不能证明外部是否漏传组。provenance 是可信运行时元数据：本层检查一致性，不认证恶意 Python 调用方。没有通过原始输入/响应重验的历史 JSON，不能仅靠 VALID 字样或重新签名直接编译。

## 2. 唯一映射与编辑权限

| Diagnosis | 计划 |
|---|---|
| NO_ISSUE / NOT_ADDRESSABLE | NOOP record，原样保留 status/reason |
| ADDRESSABLE + MISSING | ADD |
| ADDRESSABLE + NEEDS_REVISION | REPLACE |
| ADDRESSABLE + SHOULD_REMOVE | DELETE |

ADD 无目标规则，每个 MISSING 单独生成一个单元。REPLACE/DELETE 目标严格等于其 supporting gaps 的 related_rule_refs 并集，不扩展范围；两者都要求当前 Parent 的非空规则引用。每个 ADDRESSABLE gap 必须恰好覆盖一次，gap_index 保留原始零起始索引；非 ADDRESSABLE 来源恰好对应一个 NOOP。

Compiler 不读取自然语言来选择操作，不根据语义评分筛选来源，不证明 SHOULD_REMOVE 达到了更高证据门槛。Pilot 中保留无依据 transfer fallback 的 NEEDS_REVISION 仍原样映射为 REPLACE，其内容问题留在 Diagnosis/语义评估侧。

## 3. 合并、冲突和顺序

同操作单元的目标规则相同或原始行范围重叠时，按传递闭包合并为一个单元，保留全部 GapRef。REPLACE 与 DELETE 分别合并，不把相邻但不重叠的规则自动合并。多个不连续目标可属于同一单元，它们之间未指定的内容不属于编辑权限。

任一 REPLACE 与 DELETE 的目标原始范围重叠，拒绝整份输入：`stage=PLAN`、`reason=MIXED_OPERATION_TARGET_CONFLICT`。无论冲突来自同组还是不同组，都不选择赢家、不转换操作、不降为 NOOP、不输出部分计划。ADD 不基于语义相似性合并。

确定性排序：

1. source_diagnosis_refs 字典序；GapRef 按 `(diagnosis_ref, gap_index)`。
2. 每个目标集合按 `(start_line, end_line, ref)`。
3. 所有 REPLACE/DELETE 单元按最早目标行、operation 字典序、supporting GapRef 排序。
4. ADD 在后，按 GapRef 排序；NOOP 按 diagnosis_ref 排序。

所有坐标来自同一原始 Parent，不做顺序编辑后的重新定位。相同来源集合即使输入排列不同，产生相同计划。全 NOOP 是合法空 edit_units；纯 DELETE 包括删除全部规则仍是有编辑的计划，不当作 NO_UPDATE。

## 4. 版本、验收及审计

计划版本 `compiler_edit_plan_v18.1`；审计输入版本 `compiler_input_audit_v18.1`。计划字段为 schema_version、round_id、parent_skill_digest、source_diagnosis_refs、edit_units、noop_records。每个 edit unit 只有 operation、target_rule_refs、supporting_gap_refs，不含替换/删除文本、模型解释或额外推理字段。

`compile_edit_plan(CompilerInput)` 是纯函数，返回 EditPlan 或抛出 `CompilerRejected`。`validate_edit_plan(plan, compiler_input=...)` 接受本版 DTO 或 JSON，重验来源、重建规范计划，严格检查类型、字段和完整相等性；布尔 gap_index、遗漏/重复来源、越界目标、修改操作或顺序均拒绝，不排序或修补提交内容。此校验以确定性编译结果为基准，不是独立算法证明或语义裁判。

错误阶段沿用 INPUT / BINDING / PLAN。任何错误整份拒绝，不发布可执行部分计划。

`run_compiler(..., artifact_dir=新目录)` 先写 RUNNING，全部成功后保存 input.json、edit_plan.json，最后写含文件摘要的 VALID validation.json；每个文件通过临时文件原子替换。输入拒绝只留下 REJECTED validation.json；文件系统错误传播，不留下 VALID 完成标记。已有目录拒绝覆盖。

消费方必须检查 VALID 和文件摘要；仅文件存在不代表可用。input.json 原样保留 Parent、原始 learner payload、provenance 和 validated payload，不把临时 HMAC 当作跨进程认证。文本应用、空替换限制、纯删除执行及混合原子应用属于第 5 步，不在本步实现。

## 5. 验证结果

v17/v18 Compiler、审计与 v18 offline pilot 测试共 **62 项通过**。覆盖三类映射、纯 DELETE/全规则 DELETE、同操作传递合并、24 种输入排列一致性、非连续目标间穿插其他操作、同组/跨组混合操作冲突、计划篡改、过期目标、拒绝旧版封装、完整覆盖、全 NOOP、确定性文件摘要和防覆盖。没有语义质量关键词检查。

离线入口：

```bash
python scripts/run_v18_compiler_pilot.py --output artifacts/v18_compiler_pilot_new
```

源清单 [sources.json](../experiments/configs/v18_compiler_pilot_001/sources.json) 固定 v2 Pilot 全部五份输出的摘要；逐一从原始固定请求重建并重验响应，不按人工评分筛选。不同 Parent/round 的五个开发样本分别编译，不混为一轮，也不声称提供了历史正式轮次的完整组集合。

构造样本原 provenance 缺少 parent_skill_digest。离线入口核对原始 provenance 后，仅针对明确标记为构造开发样本的输入，从精确 Parent 原文计算并补充本次可信调用方元数据；Compiler 的绑定要求没有放宽。learner payload、原始响应及历史文件均不改动。

本次产物：[summary.json](../artifacts/v18_compiler_pilot_001/summary.json)。五份均 VALID，总计 **4 ADD、1 REPLACE、1 DELETE**，全部 6 个 gap 覆盖一次，0 模型调用、0 Candidate。语义部分失败的修订和历史 artifact 相关 gap 仍原样保留；编译有效性不表示学习语义正确或 Gate ACCEPT。

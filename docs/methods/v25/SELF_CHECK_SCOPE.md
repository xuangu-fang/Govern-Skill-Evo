# 自检结论的范围边界

2026-10-27，本次仅在 Diagnosis 的 Checks 说明和 Preconditioner 的完成条件说明中，
各增加以下同一段文字：

> Interpret a self-check only as evidence for the property it actually tests. Readability, non-empty output, or agreement with a program's own computed values does not by itself establish task correctness.

自检结论必须限于实际检查的性质。可读取、非空、与程序自身计算值一致，均不能单独
证明任务正确。已有程序自检可作为局部证据，计划中的 Checks 也应据此解释验证结果；
本次不要求每项任务增加自检，不增加审查阶段、输出字段或语义校验器。

## 版本与兼容

- Diagnosis：`v25_diagnosis_self_check_scope_v3`。
- Preconditioner：`v25_preconditioner_self_check_scope_v6`。
- 输出契约仍为 `v25_explicit_references_v2`，输入投影及模块之间的交接结构不变。
- 上一版 Diagnosis v2、Preconditioner v5 模板分别保存为 `diagnosis_legacy_v2.md`、
  `preconditioner_legacy_v5.md`，旧归档仍按其原版本校验，更早版本兼容路径保留。

源 Prompt 与文档镜像同步；15 题批次配置模板采用新版本。旧 campaign 配置与实验归档
不变。Editor、Replay、Verifier、Repair、Gate 和 Actor 执行策略不在本次修改范围。

## 固定正反案例

案例保存在 `tests/skill_evolution/v25/fixtures/self_check_scope/`。它们是构造的局部
自检观察，不是原始模型输出或完整模块请求；`scenarios.json` 保存事实，
`evaluation.json` 单独保存判据，不作为模型输入。

| 案例 | 离线观察 | 合理结论 |
| --- | --- | --- |
| 错误的 0 通过非空检查 | 要求 2+3，保存 0，非空检查通过 | 只证明非空，不能证明计算正确 |
| 错算后回读一致 | 程序算出 6，保存后仍为 6 | 只证明保存一致，不能独立证明计算正确 |
| 正确公式缺少缓存 | 保存求和公式，`data_only` 回读为空 | 回读检查有用，可发现值不可读；不能据此认定公式逻辑错误或取消公式要求 |
| 检查确实覆盖局部要求 | 回读值 5 与独立计算的 A1+A2 一致 | 可以确认该输入上的求和要求；未检查的内容、格式保持不能一并宣称通过 |

离线测试用临时工作簿实际保存、回读，验证上述观察，并检查版本路由、归档兼容和
文档镜像。它们不评判模型是否正确理解新说明；模型语义评估尚未运行。

## 验证边界

不调用模型，不启动训练，不改变现有实验。离线测试通过只证明案例事实及工程兼容，
不能宣称模型已经减少了过度推断。Docker 执行器专项测试不属于此次 Prompt 修订验证。

本次验证结果：V25 离线测试 214 项通过（33.94 秒），命令为
`python -m pytest tests/skill_evolution/v25 --ignore=tests/skill_evolution/v25/test_executor.py -q`。
同时只读重载 `_007` R05 的 Diagnosis → Preconditioner → Editor 真实归档链，兼容性检查通过。
对照旧模板确认两份 Prompt 均仅增加上述段落，文档镜像一致。

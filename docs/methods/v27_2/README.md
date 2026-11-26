# LMB v27.2

2026-11-05。当前版本包含两项调整。第一部分把 SkillAdam 的量词、结论强度、假设与边界条件、选项精确比较纳入 LMB 领域指导。第二部分让 Preconditioner 判断每个 Original 相对完整 Parent 的行为增量，再依据当前执行和相关 Memory 选择 KEEP、REPLACE 或 WITHDRAW。

| 模块 | 第一部分 → 当前 prompt | 职责 |
|---|---|---|
| [Diagnosis](prompts/diagnosis.md) | v1 → v2 → v3 | 按可以独立采纳或暂缓的行为组织 Update，将同一行为的条件、例外和例子放在一起。用全批当前证据提出具体行为、适用条件和保护边界，引用支持案例，可指出可见冲突。由 Preconditioner 最终确定 Parent 的覆盖程度、旧规则处理和跨 Update 协调。 |
| [Preconditioner](prompts/preconditioner.md) | v1 → v2 → v3 | 比较当前 Parent 中有关规则的触发条件、动作、范围、强度和优先级。即使 Memory 为空，也可依据 Parent 与 Plan 引用的 runs 判断增量。若变更触发条件、优先级或停止条件，回查支持案例，并在完整 REPLACE 文本中交付必要的例外和旧条款处理。 |
| [Editor](prompts/editor.md) | v1 | 读取 Parent 和 Effective Plan，按 Update 实施 patch。 |
| [Replay](prompts/replay.md) | v1 | 根据选项内容变化与实际修改解释 EM 翻转，记录关联及其不确定性。 |

若 Parent 完整覆盖提案且没有受支持的行为差异，撤回重复项。若修正有依据但与已有条款冲突，REPLACE 应明确指出需要限定哪条规则以及保留哪个分支。若 Original 已经表达了充分、完整的修正，则 KEEP。相关历史按机制和适用条件解读。单个标签只显示 Actor 的选择，独立定理、证明草图及隐藏推理均在输入边界之外。

[正式配置](../../../experiments/configs/v27_2_lmb53.json)使用 53 道优化题、六批 10/10/10/10/10/3 的调度以及独立的 124 题 Test。第二部分只升级 Diagnosis 与 Preconditioner 的 prompt 身份，沿用原有 I/O、Gate、Memory、Actor 和预算合同。方案参考 [v28.5 的支持案例回查](../v28_5/prompts/preconditioner.md)和 [v29.6 的 Parent 差异判断](../../../src/skill_evolution/v29_6/prompts/preconditioner.md)。

## 第一部分对照

[第一部分快照及 SHA-256 清单](revisions/parent_memory_delta_v1/part1/manifest.json)保存改动前的四份 prompt、配置、v27.2 运行包、CLI 和原版说明，共 18 个文件。快照内沿用仓库相对路径。在具有相同共享依赖与数据的独立工作副本中，按清单路径还原文件即可复原第一部分。只替换配置不足以还原旧 prompt，当前运行器会拒绝第一部分的配置。

## Preconditioner v3 对照与静态检查

[改动前的完整对照](revisions/update_strength_v3/control/manifest.json)保存四份 prompt、正式配置、v27.2 运行包、CLI 和说明。对照使用 Diagnosis v2、Preconditioner v2、Editor v1 和 Replay v1。按清单中的仓库相对路径在独立工作副本中还原，可复现这一版绑定。

Preconditioner v3 仅替换 D/S/C 末尾的一段英文，要求在比较策略升级为偏好、默认或义务时，说明改变选择的可见条件和保留另一分支的条件，并核对联合修改的证据及停止规则的执行条件。以下历史检查适用于 Diagnosis v2 / Preconditioner v3 的工作副本。可按[原版本清单](revisions/decision_replay_v4/control/manifest.json)还原后执行。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python docs/methods/v27_2/revisions/update_strength_v3/verify_static.py
```

[本次静态检查结果](revisions/update_strength_v3/static_validation.json) · [上一版离线检查归档](revisions/parent_memory_delta_v1/offline_validation.json)

R03、R06 的 v4 回放已归档，当前正式配置使用 v3。[冻结回放结果](../../../experiments/analysis/v27_2_preconditioner_v4_r03_r06_20261105/comparison.md)。

Diagnosis v3 仅替换 Update 划分段落。[R02、R03 冻结 Diagnosis 回放](../../../experiments/analysis/v27_2_diagnosis_v3_r02_r03_20261105/comparison.md)。

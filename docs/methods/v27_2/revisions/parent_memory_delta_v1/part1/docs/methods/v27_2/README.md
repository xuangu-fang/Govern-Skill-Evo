# LMB v27.2 · 第一部分

2026-11-05。v27.2 将 SkillAdam 的量词、结论强度、假设与边界条件、选项精确比较四个维度写入 Diagnosis。其余模块按职责使用这些区别。训练仍从原始 LMB Skill 和空 Memory 开始。此版将 prompt 作为相对 v27.1 的实验变量，Preconditioner 使用 v27.1 的调整协议。

| 实际系统 prompt | 主要调整 |
|---|---|
| [Diagnosis](prompts/diagnosis.md) | 四个维度用于解释可见选项差异、识别值得保留的成功模式、提出可迁移的 Update。保留单案例提案，允许其他有依据的模式。原稿中对证明、附加检查、选项长短的多处限制合并为条件、证据和单轮预算要求。 |
| [Preconditioner](prompts/preconditioner.md) | 将具体策略禁令替换为评估 Original 时应保留的数学区别和指令强度。输入、D/S/C、调整动作及编译均沿用 v27.1。 |
| [Editor](prompts/editor.md) | 实施 Effective Update 时保留量词作用域、假设、定义域、等号条件与结论强度。条件性比较仍然是条件性的。 |
| [Replay](prompts/replay.md) | 用前后选中选项的具体数学差异与实际 patch 建立有限关联。只有 EM 翻转生成事件，单一 Update 无法区分时记录 null。 |

三份读取执行记录的 prompt 均说明题干、选项、普通回答、映射参考答案及评分的证据权限。标签不能展示解题过程或指令遵循情况。独立定理、证明草图和隐藏推理不进入模型输入。Actor 的逐字协议、格式与 EM 的区分、共享执行视图、引用语法及四阶段输出合同沿用 v27.1。数学维度用于分析，既不写入输出 schema，也不要求将初始 Skill 改成固定结构或为每题执行同一检查表。

领域依据为 SkillAdam 固定提交 `b6c9640` 的[失败类别](https://github.com/ruc-datalab/SkillAdam/blob/b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1/skilladam/benchmarks/lmb/prompts/failure_types.md)、[成功模式](https://github.com/ruc-datalab/SkillAdam/blob/b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1/skilladam/benchmarks/lmb/prompts/success_types.md)和[写作规则](https://github.com/ruc-datalab/SkillAdam/blob/b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1/skilladam/benchmarks/lmb/prompts/skill_writing_policy.md)。可直接与 [v27.1 原稿](../v27_1/prompts)逐段比较。

## 运行与验收

[正式配置](../../../experiments/configs/v27_2_lmb53.json)使用独立的 method 身份及四个 prompt ID。运行器冻结实际 prompt 全文，在归档、请求和恢复时校验。Actor、评分、逐 Update Gate、Memory 及输入输出校验复用 v27.1。优化池 53 题分为 10/10/10/10/10/3 六批，独立 Test 为 124 题。Actor 输出预算 65,536，四个方法模块各 32,768。

从仓库根目录按以下命令做只读预检。预检不读取凭据、不创建 campaign。正式运行时由[独立 CLI](../../../scripts/runs/run_v27_2_campaign.py)显式选择 train 或 test。

```bash
/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python scripts/runs/run_v27_2_campaign.py train experiments/campaigns/v27_2_lmb53_001 --config experiments/configs/v27_2_lmb53.json --validate-only
```

以下命令复现 [v27.2 离线测试](../../../tests/skill_evolution/v27_2/test_campaign.py)。五项测试通过，包括正式配置预检、合成训练与独立 Test、跨版本恢复和 prompt 漂移拒绝、中断恢复，以及无翻转时跳过 Replay。端到端检查逐字比对送入模型和写入归档的四份系统消息，并验证 Gate 选择、Memory 事件和最终 Selected Skill。v27.1 原有 141 项回归也已通过。本次只有合成模型响应，没有 LMB 实测成绩。

```bash
PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python -m unittest discover -s tests/skill_evolution/v27_2 -t . -v
```

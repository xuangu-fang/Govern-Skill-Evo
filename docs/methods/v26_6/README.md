# OfficeQA v26.6

本版以 v26.5 为对照，检验三个模块能否把当前轨迹支持的答案格式修正，准确传递到 Actor 最终读到的 Skill。假设是：区分指标名称和报告形式，可以减少过度推广；在补丁中区分答案标签数量和值的数量，可以保留多值输出。

| 模块 | 修改 |
|---|---|
| [Diagnosis](prompts/diagnosis.md) | 分辨题目在命名所求量还是在规定答案的呈现形式。自然语言也能明确指定报告形式。同批中有助于区分两种读法的执行应写入 Update 的 `basis`。 |
| [Preconditioner](prompts/preconditioner.md) | 遇到 only 或 unless，检查它排除了哪些原本有效的响应，以及证据是否支持排除。证据只决定一个分支时，只修正该分支。 |
| [Editor](prompts/editor.md) | 在单项和联合补丁的阅读检查中，区分一个答案元素和元素中的多个值。按计划授权的范围修订冲突文字，保留值数、顺序和结构。 |

正式配置沿用 v26.5 的初始 Skill、空 Memory、七批 74 道优化题、172 道独立测试题、模型和预算。Replay 使用 v26.5 对应的同一份正式提示词，Gate 与 Memory 使用相同契约。[正式配置](../../../experiments/configs/v26_6_officeqa_train74.json)

## 行为审查

训练后可沿相同 Update ID 对照 Original、Effective、单项补丁和 Selected，查看排他条件的依据及实际选中组合的文字。三个已知训练案例仅供事后审查：UID0052 检查明确要求以百分比形式报告时的输出，UID0086 检查以百分比变化命名指标并指定精度时的输出，UID0123 检查百分点差和相关系数的双值列表。每轮的解释应以当时可见的证据为准。整体收益以独立测试的完成数、EM、平均 token F1 和同预算配对题目的双向翻转衡量。

## 离线校验

从仓库根目录运行以下命令可渲染并校验正式提示词、配置和数据。此模式的模型请求数为零。

```sh
python3 scripts/runs/run_v26_6_campaign.py train experiments/campaigns/v26_6_officeqa_train74 --config experiments/configs/v26_6_officeqa_train74.json --validate-only
```

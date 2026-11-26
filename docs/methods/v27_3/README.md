# LiveMathematicianBench v27.3 设计

2026-11-13。v27.3 以 v27.2 的正式 LMB 运行为对照，研究两个问题：已有 Skill 漏掉了哪个可以执行的判断？如何让 Actor 在合适的情境下读到这个判断？实验变量是 Diagnosis、Preconditioner 和 Editor 的三份提示词。实验沿用 v27.2 的 Actor、初始 Skill、空初始 Memory、阶段输入输出契约、Replay、Gate、批次和评测口径。[v27.2 方法](../v27_2/README.md) · [基线配置](../../../experiments/configs/v27_2_lmb53.json)

## 模块如何交接

| 模块 | 本版的判断 | 交付内容 |
|---|---|---|
| Diagnosis | 结合 Parent 当批作答，找出一个可尝试的动作和适用条件。题目细节只有在影响动作、强度或适用边界时才进入行为文本。由参考答案引出的比较动作和默认选项偏好，需要分别说明依据。 | 沿用 Original Plan。行为要求放入 text，支持案例通过 basis 回查。[Diagnosis 提示词](proposals/prompts/diagnosis.md) |
| Preconditioner | 在同一个 Actor 可见情境里，对照完整 Parent、基础协议与 Original，说明照原文已经会做什么，照提案还需要做什么。新检查、触发条件变化、有根据的优先级或强度变化均可构成增量。单标签作答只能观察到所选选项。 | KEEP 表示整项按原文成立。REPLACE 表示有价值的行为需要调整范围、删去重复要求或校准强度，输出完整有效文本。WITHDRAW 表示已有相同判断，或证据不足以支持项内完整修正。reason 写明决定性差异。[Preconditioner 提示词](proposals/prompts/preconditioner.md) |
| Editor | 根据有效行为与原文的关系决定表达形式。改变原规则的含义或适用范围时，改写可以明确新边界；可以独立执行的检查，即使主题相近，也可以单列。同一 Update 可兼用两种形式。 | 每个 Update 对应一个可独立组合的补丁。reason 说明所选写法如何表达二者关系。评审检查动作清晰度、旧规则是否仍准确、是否重复以及是否丢失条件。[Editor 提示词](proposals/prompts/editor.md) |

## R06 冻结回放

v27.2 的 R06 包含三道训练题。三个 Original 均获 KEEP，Editor 将三段正文原样加入，Gate 随后全部采纳。以保留换行的 Unicode 字符计，Parent 4,401 字符，Selected 6,244 字符。下表按原 Update ID 记录增量及评审问题。[原始提案](../../../artifacts/methods/v27_2/v27_2_diag_v3_precond_v3_lmb53_20261105_210532/rounds/R06/diagnosis/attempts/001/parsed.json) · [实际补丁](../../../artifacts/methods/v27_2/v27_2_diag_v3_precond_v3_lmb53_20261105_210532/rounds/R06/editor/attempts/001/parsed.json)

| 冻结提案 | v27.2 净增 | v27.3 评审问题 |
|---|---:|---|
| u1 分类与逆命题 | 623 字符 | 能否给出“单独验证反向构造是否满足原定义”这个检查？若有效文本还要求默认偏向无逆命题选项，哪条证据支持这一步？ |
| u2 精确次数、系数与元选项 | 639 字符 | 把 Parent 的“检查较弱推论”用于本题后，还缺哪一步？若理由只列出新的弱化形式，预期撤回，此项净增为零。其他决定应指出可执行的差异。 |
| u3 基点、半径与量词 | 581 字符 | 能否保留“见证量能依赖哪些先前变量”的检查？整项撤回可能遗漏有用细化；保留元选项偏好则需要单独的理由。 |

先以冻结 Original Plan、Parent、获准的当前 runs 与 Memory 回放新 Preconditioner，再将其有效文本交给新 Editor。这条路径直接检验对同一批提案的判断。随后从同一 R06 Parent 与当批 Parent 作答开始回放三模块，按行为含义对照新提案，允许数量和 ID 随 Diagnosis 输出变化。使用阶段既有的模型输入视图；上表只给评审人员使用。

两条回放均查看 Original、调整决定与理由、有效文本、逐项补丁及合成后的 Candidate。冻结回放产生的是候选文本。实际发布的 Selected 及其收益要在 Actor 执行、Replay 和 Gate 完成后另行记录。R06 的期望是零净增长或少量有依据的增长。逐项核对新增和删除，避免一处删短掩盖另一处复述原题。该期望用于评审，训练不设字符配额。

## 完整训练与效果判断

从共同初稿和空 Memory 开始，在相同的 53 道训练题上依次运行 10、10、10、10、10、3 六个批次。完整训练的 R06 会继承 v27.3 自己的 R05 Parent；冻结回放与完整训练分别报告。逐轮记录 Parent、Candidate、Selected 的字符数和各项实际补丁，并举出保留下来的新检查、被撤回的重复项和可能遗漏的有效行为。

在这套提示词固定后，用独立的 124 道测试题评估最终 Selected，与 v27.2 做逐题配对，报告总正确数、双方各自独对的题数及完成情况。分别判断 R06 的重复是否减少、可迁移的数学区别是否保留、测试表现如何。单次少量题差不足以判断稳定收益。当前状态为设计稿；冻结回放和完整训练结果待测。

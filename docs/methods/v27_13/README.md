# v27.13 · 从训练证据学出可执行的选择规则

v27.13 是 LiveMathematicianBench 上的四模块 prompt 设计。目标是让训练产生一条能改变提交答案的 Skill 指令。给定同一道题和同样的信息，应该能指出 Parent 允许哪种选择、提案在哪一步改变它、什么证据足以改选。只有训练样本支持某个方向时，模块才有理由把它写成经验默认。

正式设计采用本目录下的四份英文 prompt。模块输入、JSON 输出、补丁编译、Actor、Gate 和 Memory 继承 v27.12。四份 prompt 直接使用既有加载器支持的文件名，版本标识采用 `v27_13_lmb_<模块名>_v1`。方法版本标识为 `v27_13_campaign_v1`。[v27.12 冻结配置](../../../experiments/launches/v27_12_lmb53_20261118/config.json) · [原四份 prompt](../../../experiments/launches/v27_12_lmb53_20261118/frozen_prompts)

## 为什么要改

v27.12 在 R01 保留了“把该类选项优先纳入判断”的提案，关联增益 2 题、回退 0 题。R02 又保留了“未决时设为默认”的提案，关联增益 3 题、回退 0 题。R03 试图扩大默认规则，R05 试图收紧改选条件，两次都是 0 增益、0 回退，Gate 判为 Defer。问题已经从“能否发现这条规律”推进到“新指令能否在原 Skill 仍会选错的场景里改变选择”。这些归因来自同时执行全部改动的 Candidate，无法单凭它们确定某段措辞的独立贡献。[R01](../../../artifacts/methods/v27_12/v27_12_lmb53_20261118/rounds/R01/gate/result.json) · [R02](../../../artifacts/methods/v27_12/v27_12_lmb53_20261118/rounds/R02/gate/result.json) · [R03](../../../artifacts/methods/v27_12/v27_12_lmb53_20261118/rounds/R03/gate/result.json) · [R05](../../../artifacts/methods/v27_12/v27_12_lmb53_20261118/rounds/R05/gate/result.json)

SkillOpt 两次独立训练选出的 Skill 都把同一种选项语义转成了提交偏好。这提示我们检验两种时机的差别：在所有检查结束后用规律打破平局，或识别条件时先有暂定选择、只在出现区分性证据时改选。后者有机会影响原本提前提交的题，也可能引入新的回退。两种时机都由训练证据和当前 Parent 决定。目标选项的原句、题号、答案分布和 SkillOpt 学出的具体规则均不进入四个模块 prompt。[SkillOpt 首次最佳 Skill](../../../experiments/methods/skillopt/lmb/lmb_skillopt_deepseek_flash/results/final_skill.md) · [第二次最佳 Skill](../../../experiments/methods/skillopt/lmb/lmb_skillopt_deepseek_flash_repeat_20261123_010400/results/final_skill.md)

## 四个模块各自负责什么

| 正式 prompt | 保留的机制 | v27.13 的决策要求 |
| --- | --- | --- |
| [Diagnosis](prompts/diagnosis.md) | 看当前 Parent 和整批执行，输出 Original Plan 或 `no_change`。 | 按新题上能识别的**选项含义和决策条件**分组。检查触发组中的错题、已答对题及相反方向的参考答案。取一对候选，在相同信息下指出旧、新策略最早分歧的位置。把影响提案方向或例外的执行放入该 ID 的 `basis`，以便下游读到。 |
| [Preconditioner](prompts/preconditioner.md) | 只看被转发的当前执行、Parent、原计划和已有 Memory。每个原 ID 得到一次 KEEP、REPLACE 或 WITHDRAW。 | 在同一对选项上分别应用 Parent、Parent 加 Original。若 Parent 已有默认，检验提案是否真正改变了改选门槛。尝试找一个**两个选项都满足**的发现，检验原门槛是否过松。替换须说明新的区分性发现，撤回须指出已有覆盖或证据缺口。 |
| [Editor](prompts/editor.md) | 只看 Parent 和 Effective Plan，每个 ID 输出一份可单独采纳的原文补丁。 | 在 Actor 首次可以提交的位置编辑。入口默认与改选条件写在一起，末尾决胜保留在指定检查之后。只授权提前比较时，就只改变比较顺序。按“触发但未决、证据足以改选、未触发”三种情况检查补丁，保留其他分支。 |
| [Replay](prompts/replay.md) | 只看联合 Candidate 中 EM 翻转的配对，每题一条 Knowledge。 | 按顺序记录 Parent 选了什么、Candidate 改选什么、EM 怎样变化，以及实际补丁哪一处能区分两次提交。增益与回退采用同一归因标准。多个补丁都说得通时留下 `null`，便于后续区分“观察到变化”和“能归到某个 ID”。 |

**什么样的变化值得保留？** 例如，两个答案报出相同的上界，只有一个声称上界能取到。若 Parent 已要求检查数值，新增“更仔细地验证上界”仍允许两种提交。若提案要求用定义域内的等号见证区分两者，找到见证可以支持取到，排除全部允许的见证可以支持取不到，单纯找不到见证则仍属未决。这样，Preconditioner 有依据保留新操作，Editor 也知道不能把“没找到”写成“已排除”。对于纯经验选择，Diagnosis 另用合成的舍入中点例子说明如何检验方向及例外。两个例子都允许模型在实际证据不足时放弃提案。

## 如何判断是否有效

1. **先比较两个冻结的 R04 输入。** 分别沿用 v27.11 首次训练与重复训练的 Parent、整批执行和当时的 Memory，只替换模块 prompt，各自按新 Original 的引用形成下游输入。首次组用于观察从“允许比较”到“未决时有明确提交”的变化；重复组的 Parent 已有暂定答案，用于检查是否能指出真实的改选门槛差异，或撤回重复提案。未触发的题不能算作触发组内的反例。两组允许得到不同提案。[冻结回放与两组 Parent 的区别](../../../experiments/analysis/v27_12_r04_diagnosis_v2_20261118/结果对照.md)
2. **再以 v27.12 作五轮配对比较。** 同一初始 Skill、53 道优化题、批次顺序（11、11、11、10、10）、模型、预算及 Gate。逐轮跟踪一条规则从 Original、裁定、实际 diff、配对提交到 Gate 的去向。分析分母取自全批 Parent/Candidate 执行，分列触发及未触发题、稳定对错和双向翻转。Replay 的 Memory 只含 EM 翻转，不能代替这张统计表。若要判断收益来自哪个模块，可增加“只换 Diagnosis”和“再换 Preconditioner”的对照。
3. **最后测实际选项和总体分数。** 用同一选定 Skill 和相同测试设置，在历史 124 题上报告触发组（53 题）、其余组（71 题）的正确数，以及相对 v27.12 的逐题增损和未完成数。既看是否学到规则，也看 Actor 是否执行、其他题是否退步。该测试集已经参与过方法分析，在这个集合上的提升属于历史对照；泛化需要另用未参与设计的新题验证。

## 已验证的边界

四份 prompt 已用仓库的真实加载器和 v27.12 正式 R02 归档逐模块离线核对。新系统消息可以加载，四条用户消息与原归档逐字一致，旧输出可以通过对应校验器。另用合成 Actor 和模块输出走通了补丁、选择性 Gate、Memory、恢复、最终测试及无翻转时跳过 Replay 的分支。这些检查验证接线与协议。上述 R04 模型回放、五轮训练和 124 题行为评估仍待执行。

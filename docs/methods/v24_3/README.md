# ALFWorld v24.3 设计稿：依据 Actor 当步可见信息调整 Update

[六轮正式训练、109/134 首测及两次 R02 快检](../../../experiments/methods/v24_3/README.md)

训练与独立 Test 入口已接入。两份完整英文 system prompt 已展开共享指南，可分别阅读：[Diagnosis](../../../src/skill_evolution/v24_3/prompts/diagnosis.md) · [Preconditioner](../../../src/skill_evolution/v24_3/prompts/preconditioner.md)。本目录保存设计，方法包保存实际使用的提示词；训练与保留集评测分别显式启动。

## 要验证的问题

面对同一份有依据但笼统的 Original，Preconditioner 能否从训练轨迹中找出 Actor 当步可判断的线索，交付一个实际改变动作选择、又保留合理例外的 Update？考察对象是优化方法。柜子、灯、物体位置等具体案例只用于审阅或分析，不作为预置答案写入 Skill。

v24.2 正式训练 R02 的 Parent 在 10 题中成功 7 题。唯一 Original 要求覆盖尚未访问的容器，Preconditioner 选择 KEEP；Candidate 仍成功 7 题，逐题没有翻转。v24.1 在相同 Parent、相同批次和相同逐题 Parent 成败下，生成了包含同类推进、类型切换和发现目标后退出等动作选择的 Skill，Candidate 成功 10 题。这是值得复验的对照，不能从一次联合修改判断哪一句起了作用。[v24.2 调整](../../../artifacts/methods/v24_2/v24_2_alfworld_20261106_195800/rounds/R02/preconditioner/result.json) · [v24.2 同批配对](../../../artifacts/methods/v24_2/v24_2_alfworld_20261106_195800/rounds/R02/pair_audit.json) · [v24.1 Candidate](../../../artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/S1/rounds/R02/editor/attempts/001/candidate.md)

## 改动与交接

| 位置 | v24.2 已有要求 | v24.3 的具体增量 |
|---|---|---|
| Diagnosis，FORM THE PLAN | 对照 Parent、区分不可观察的触发器和未遵循规则，引用决定边界的反例 | 在一次真实决策上对照实际动作、当时可选动作和旧指导，指出旧指导留下的选择。允许提出待检验的方向，将可执行性调整交给下游。 |
| Preconditioner，Direction | 判断相对 Parent 的行为增量 | 在有代表性的决策上比较 Original 与 Parent 对候选动作的优先级或退出条件。允许有用的偏好，无需强制唯一命令。 |
| Preconditioner，Scope | 回查支持步骤，要求触发器可观察 | 先用完整轨迹理解问题，再按该步 Actor 的可见范围重建判断。若原触发器不可用，查找同一目的下有依据的替代线索；必要时明确推进、切换和退出，并以获准的成功或状态改变案例检查边界。 |
| Preconditioner，KEEP / REPLACE | 逐 ID 保留、完整替换或撤回；Editor 只看有效文本 | KEEP 要有可辨认的决策增量；REPLACE 把可见线索、动作和必要边界交给 Editor。找不到受支持的替代时沿用 WITHDRAW。 |

这里的“当步视角”是**模型对已有输入的审查步骤**。Preconditioner 仍接收 Original 引用的完整 runs、Parent 和历史 Memory。它可以用后续反馈判断先前行为产生了什么结果，也可以用 Memory 比较类似提案；交给 Actor 的规则只能依赖执行时的可用信息。它不要求多调用一次模型、增加输出字段或为每题制作中间表。

落地时继续使用 v24.2 的轨迹去重和候选菜单引用。读取省略的 before 时，首步用本 run 的 initial，其他步用前一步 after。两组历史取自先前的动作前观察和实际动作。一次交接中的历史轨迹仍只限上游授权的范围。独立采纳检查、JSON 合同、Editor 的冻结 Actor 协议、Replay、Gate、Memory 和最终 Test 均沿用 [v24.2 基线](../v24_2/README.md)。正式接入使用独立方法和提示词标识、输出目录与冻结记录。

## 一个可实际核对的决策

R02 的 P4:8，Actor 刚打开空的 cabinet 2，菜单里既有前往 cabinet 3 的命令，也有前往 drawer 1 的命令，实际选了后者。优化器能回看此前搜过哪些位置。Actor 单靠这一步能区分“继续当前编号序列”和“切换类别”，却无法根据编号本身断定 cabinet 3 从未访问。若多条获准证据支持向前推进，REPLACE 可以写成“当前序列还有合适的后续候选时优先向前；目标已有合法拿取动作时退出搜索”。若证据仅支持某个阶段，应把阶段限制写入 text。此步没有执行另一条命令，经验说明不得宣称改选一定成功。[冻结的 R02 Preconditioner 输入](../../../artifacts/methods/v24_2/v24_2_alfworld_20261106_195800/rounds/R02/preconditioner/input.json)

P6:9 提供反向检查：开完 cabinet 3 后，菜单列出 examine cabinet 4 和 go to cabinet 5 等动作，没有 go to cabinet 4。一个硬编码“下一步必须 go to 编号加一”的规则在此无法执行。类似地，物体已可拿、取物后必须处理、第二件物体有可见线索支持回访时，应允许行为随阶段变化。若当前 Original 与这些情形无关，无需附加相应规则。两个案例属于设计审阅材料，不进入新 prompt。

## 实验次序与判断标准

1. **R02 单次快检。** 给新版 Preconditioner 一次原始 R02 归档输入，与已有 v24.2 调整并排查看。检查输出能否通过既有合同，并在一个引用的决策步上核对有效 Update：Actor 能否用当步观察、合法菜单和最近两步判断该怎么选？若撤回提案，核查理由是否有据。发现明确的接线或措辞问题时修正；快检只用于审查提案，结果独立归档。
2. **完整训练一次。** 冻结新版 Diagnosis 和 Preconditioner，从与 v24.2 相同的初始 Skill、空 Memory 开始，按既有顺序跑完 57 题、六批，发布最终 Selected Skill。R02 快检产物只作审阅依据，正式训练按原流程生成每一批自己的提案。
3. **独立 Test 一次。** 对该最终 Skill 使用与 v24.2 相同的 Actor 和 134 道保留题。主结果为环境成功数和成功率，同时与已有 v24.1、v24.2 两次 Test 和 SkillAdam 结果做逐题配对。优先解释持续得失及可复查的行为变化。结论针对本次完整 v24.3；两个模块各自的独立贡献仍属未测。

## 正式入口

从仓库根目录运行，调度进程使用与 v24.2 相同的 Python 环境。训练目录使用新的 v24.3 路径。train 从初始 Skill、空 Memory 开始，或从同一目录恢复，完成六轮后导出 final_skill.md。

```sh
/Users/didi/miniforge3/bin/python -m src.skill_evolution.v24_3 train --campaign /path/to/v24_3-training
/Users/didi/miniforge3/bin/python scripts/runs/v24_3/run_v24_3_test.py --campaign /path/to/v24_3-training --evaluation /path/to/v24_3-test
```

Test 支持 `--validate-only` 和 `--resume`，仅接受全部轮次已发布的 v24.3 正式提交链。使用与 v24.2 相同的 134 题清单和逐题校验，评估结果独立保存。训练还支持 `prepare`、`run-round`、`status`。

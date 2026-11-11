# ALFWorld v24.4 设计稿：从决策证据生成和修正 Update

本版要验证的假设是，Diagnosis 可以从整批执行中找出一个值得改变的动作选择，Preconditioner 可以借助当前案例和 Memory 判断这项改变应在什么条件下生效。预期收益是让 Actor 更早做出有用的选择，同时保住 Parent 已经能完成的任务。成功率由实际环境终局衡量。

## 设计依据

- v24.1 R02 的 Diagnosis 提出了依据当前位置向前搜索的办法。Preconditioner 发现当前位置可能不在导航菜单中，菜单排列也不等于编号顺序，于是改用当前观察中的地点和可选命令定义下一步。该轮联合 Candidate 达到 10/10。可借鉴的是检查动作选择的做法，单轮结果无法分解各条搜索偏好的贡献。[v24.1 的实际修正](../../../../../artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/S1/rounds/R02/preconditioner/attempts/003/parsed.json)
- v24.4 第二次复跑中，补入 P8 后的 Candidate 和进一步收紧 Editor 触发范围后的 Candidate 都是 7/10，同一个 Parent 是 8/10。区别“在循环时才优先换类”修正了补丁的适用范围，但两版在同三题达到步数上限。[逐题对照](../../../../../artifacts/methods/v24_4/v24_4_r02_p8_editor_trigger_quickcheck/r02_comparison.json)
- R05 的一次快检从 6/10 提到 9/10，但同一联合 Candidate 在历史平底锅题上达到步数上限，配对 Parent 能从柜子 9 拿到平底锅。这个结果要求审阅新偏好会在何时打断有效搜索。它也给出了 Gate 当轮十题以外、训练期间已经可以使用的证据。[R05 与三道历史训练题](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/CANDIDATE_REVIEW.md)

## Diagnosis 如何提出 Original

Diagnosis 读完整 Parent 批次。在失败轨迹中，从卡住的阶段往前找到一个还有选择余地的步骤。用当时的观察、最近两步和可选命令说明 Actor 做了什么，另一个动作能直接完成什么检查或推进哪项任务要求。可以提出尚待检验的偏好。目标藏在哪里、改走另一条路能否成功，都应按当时证据标为未知。

用成功轨迹检查同一提案的边界。若某条成功轨迹会被新偏好改变，或能说明一个动作应保留为可选，把它和支持修复的失败步骤一起写入原有 `basis`。这使只读取引用轨迹的 Preconditioner 能看到有分量的反例。若同一批有多种失败，只合并共享同一选择依据、可以用同一条规则修复的案例。

提示词拟增加以下要求，使用现有 `reason`、`plan.updates[].text` 和 `basis`。

> Identify a decision where the proposed change could alter an available action. Explain what the Actor could observe then and what the alternative would accomplish immediately. Cite a successful branch when it limits the proposal. State a reusable preference at the strength the evidence supports.

例如，海绵题的菜单出现了直接打开另一个柜子的命令，值得提出关于“何时先做一次就地检查”的假设。生菜题在台面时可以去餐桌或水槽，最近两步没有提供两者的访问状态。成功路线可以限制强制搜索顺序的适用范围。题目和地点实例只用于审阅；正式提示词使用上面的通用要求。

## Preconditioner 如何利用 Memory

Preconditioner 将 Original 放回 Parent 的现有指令中，找出它会提高或降低优先级的具体动作。如果新增文字只重复 Parent 的“检查每个位置一次”，就需要找出实际的行为差异。可使用启发式，例如当前位置的编号和菜单可以支持继续向前搜的偏好，即使 Actor 无法证明下一处整局从未访问。

从 Memory 里选一条处在相似决策情形下的成功轨迹，包括退步事件中成功的 Parent 一侧。把拟交付的文字放到证据能定位的最早一步，看它何时开始降低成功动作的优先级。若当时可见的证据足以支持改选，则写明区别；若收益和退步案例在当时无法区分，则减弱或撤回这项偏好。记录未提供精确步号时，按能定位的选择描述。

| 决定 | 判断与交付 |
|---|---|
| KEEP | Original 相对 Parent 已有可说明的动作差异，触发条件可用，现有相关证据支持它的适用范围和强度。理由指出代表性决策。 |
| REPLACE | 改变原提案的触发条件、动作优先级或强度，可以保留值得尝试的行为。理由说清相对 Parent 新增了哪个选择、相对 Original 又在哪种情形下改变选择。有效 `text` 自身写全触发、行动和必要例外，包含应收窄的旧条款。 |
| WITHDRAW | 剩余要求已被 Parent 覆盖，或同一可见情形下强制排序会压低有依据的成功分支，且在 Original 目的内找不到仍能产生实际差异的修正。 |

本次仅替换[英文 Preconditioner](../../../../../src/skill_evolution/v24_4/revisions/decision_evidence/prompts/preconditioner.md) 中原有的历史收益与退步对照要求。

> Apply the proposed wording to a previously successful trace at the earliest decision the evidence supports where it would lower the priority of the action taken. What could the Actor observe then that justified favoring the alternative? If comparable cases offer no such distinction, weaken or withdraw the preference so the successful action retains its priority.

各有效 Update 独立交给 Editor。若新增偏好必须同时限制 Parent 的一条旧指令，两处属于同一 Update。成功标准是模型本次输入能支持该决定；KEEP、REPLACE、WITHDRAW 的比例不作为目标。

## Replay 写入 Memory 的证据

保留每道翻转题的终局方向和实际行为。若声称 Actor 遵守或违反了某条规则，说明在对应步骤能看到什么触发条件。若某一步的证据不足，查看整对轨迹中其他有区分力的选择。仍无法将变化关联到具体补丁时，写入完整事件并令 `update_id=null`。后续 Preconditioner 仍能看到这次退步及其不确定性。

> When describing compliance with a rule, identify evidence that its trigger was visible at that decision. Use the paired traces to support any Update association. Preserve the outcome and the observed divergence with a null association when the evidence cannot distinguish a patch-specific effect.

生菜题应记录 Parent 去餐桌后取到生菜、Candidate 最终没有访问餐桌。若要把回水槽解释为违反“去未查位置”，还需指出 Actor 当时如何知道水槽已经查过。该要求同样适用于收益归因。Gate 继续按现行逻辑统计有归属的事件，因此开发对照同时报告原始翻转数、关联票数和空归因；归因变少本身不算行为改善。

## 开发验证与采用条件

1. **R02 检验提案生成。** 使用第二次复跑的冻结 Parent、全十条 Parent 轨迹、菜单和该轮既有 Memory，从 Diagnosis 开始一次。Preconditioner 按本次新 Plan 的 basis 取证。审阅 Original 能否指出当时可选的动作、主动引用对适用范围有影响的成功分支，以及有效 Update 相对 Parent 的具体差异。P8 按正常引用路径进入下游。最新两版 7/10 的 Candidate 轨迹只供事后对照。
2. **R05 检验历史预条件。** 使用既有 R05 快检的 Parent、Original、引用轨迹及 Memory，只替换 Preconditioner 提示词。审阅同一有效文本在历史“换类有收益”和“继续同类才找到目标”两类决策中会如何排序。检查退步一侧时，看优先级第一次改变的位置；仅在搜索后期提供兜底，可能已经错过前面的成功分支。
3. **用实跑检验有实质差异的 Candidate。** 采用上一轮已审阅过触发范围的 Editor。若有可实现的有效修改，用对应冻结的十题 Parent 做一次配对实跑，记录终局、翻转和实际动作。R02 对照 8/10 Parent 和上一版 7/10 Candidate；R05 另外列出现有历史训练题观察，与当轮 Gate 分开。若合理地撤回全部提案，则记录理由；文字审阅通过和撤回提案都不计作成功率收益。
4. **用已有配对检验 Replay。** 可先用冻结的 R02 生菜退步和 R05 有收益的翻转对照新旧 Replay。保持轨迹、补丁与配对一致，审阅判断是否有对应的可见依据，并记录重算后 Gate 的变化。进入完整训练前冻结三个模块的版本。最终以从 R01 开始的六轮训练及最终发布 Skill 的 134 题独立 Test 评价；已分析的 Test 个例只作既往风险说明。R02 已被反复用于开发，单轮 10/10 不作为采用条件。

**R05 单处替换的开发结果。** 同一份冻结输入、同一调用配置，替换前后均为 u1 WITHDRAW、u2 REPLACE。新 u2 将首选写成 prefer，并给已确认的目标位置明确例外，但仍要求尽可能先采样每一类。M3、M4 的目标尚未发现时，这些例外均未触发。等所有类别各查一次后再回柜子，只保留了回去的可能，仍会降低早期继续查下一个柜子的优先级。本次输出未达到上述采用条件，无法据此推断成功率。[替换前](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/R05/preconditioner/result.json) · [替换后](../../../../../artifacts/methods/v24_4/v24_4_r05_success_priority/preconditioner/result.json)

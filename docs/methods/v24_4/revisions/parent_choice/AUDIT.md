# v24.4 Preconditioner 重写审阅稿

建议冻结 decision_evidence 的 Diagnosis 作为开发对照，单独审阅[重写后的英文 Preconditioner](../../../../../src/skill_evolution/v24_4/revisions/parent_choice/prompts/preconditioner.md)。本次审计针对快检实际使用的提示词。正式训练的默认配置另有版本。

| 审计对象 | 现象 | 对重写的影响 |
|---|---|---|
| Diagnosis 的证据选择 | 第二次复跑的 R02 新 Diagnosis 主动引用 P8:24，程序将完整生菜成功轨迹交给下游。Original 却仍要求维护整局访问表，并把 P8 读作扩大搜索的正例。 | 交接足以测试下游。只有一份这样的生成记录，提案质量和选择反例的稳定性仍待验证。[快检对照](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/REVIEW.md) |
| 当前证据与 Parent | R02 中，补足“先打开当前关闭容器”的优先级是对 Original 的澄清，但 Parent 在 P4:4 已经这样做。P4:11 实际回水槽时，菜单有直接查看另一容器的机会。 | 从一个真实决策上的 Parent 行为和选项开始，允许放弃 Original 的做法。机会存在只说明值得比较，不能证明另一个动作会救回该题。[R02 有效文本](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/R02/preconditioner/result.json) |
| 历史证据与优先级 | 冻结 R05 上，替换历史审查段落前后均撤回 u1、改写 u2。两版 u2 都会在首遍继续查同类时要求优先换类。模型用“之后会回来”解释如何保住 M3。 | 让反例直接决定有效文字的适用范围。若证据无法区分两种选择，可在该处保留裁量，再判断其余场景是否仍有值得提交的行为变化。[替换前](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/R05/preconditioner/result.json) · [替换后](../../../../../artifacts/methods/v24_4/v24_4_r05_success_priority/preconditioner/result.json) |
| 文本与实跑 | 较早 R05 联合 Candidate 从 6/10 到 9/10，同时在历史平底锅题上从成功变成超时。v24.1 R02 曾依据菜单实际结构替换 Original 的实现办法，并明确保留对新启发式的疑问。 | 接受有依据的探索；历史案例限制规则强度，实跑检验终局。单次配对无法识别每条补丁的独立效果。[R05 实跑](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/CANDIDATE_REVIEW.md) · [v24.1 修正](../../../../../artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/S1/rounds/R02/preconditioner/attempts/003/parsed.json) |

原稿在评估 Original、比较当前成功、读取 Memory、决定 KEEP 或 REPLACE 时反复要求说明优先级。在 R05，理由可以逐项回应，交付文本仍保留同一条首遍排序。重写把这些说明归入一次选择：在 Parent、Original 和证据允许的较窄做法之间，究竟要试哪一种？输入语义、证据时序、局部 Update ID、每项可独立保留和 JSON 契约仍与现有程序相容。完整文字照常进入 Editor，模型理由只供审阅。

开发验证可直接使用已存档的 R05 Preconditioner 输入和新 Diagnosis 已生成的 R02 Preconditioner 输入。先读有效指令在历史换类成功与继续同类成功两端会怎样排序，再判断它在当前失败决策上有没有超出 Parent 的实际作用。两项都撤回也需要检视是否错失了有根据的动作。识别出原有排序、理由更长或撤回更多均不能单独说明改善。本稿仅作设计审阅，尚无新模型输出或 Candidate 成绩。

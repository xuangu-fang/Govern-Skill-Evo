# Skill 文件与生成证据

本目录保存 SuiteCRM 实验生成的 Skill，以及用于理解生成过程的结构化证据。

这里的“候选版本（Candidate）”是尚未经过选择评测的新 Skill；“当前版本（Parent）”是生成候选版本时作为起点的 Skill。

## 快速入口

如果只想阅读 Agent 实际使用的 Skill，请查看：

- `outcome_only_skill.md`
- `filtered_skill.md`
- `governed_candidate_s1_skill.md`

Governed Candidate S1 是 Day 9 根据 S0（没有附加 Skill）完成训练任务时积累的成功经验生成的候选版本。

生成时不只看“任务是否成功”，也看“执行过程是否符合规则”。系统把成功经验中的行为分成两类：已经有效且合规的做法予以保留；虽然完成任务但违反规则的做法，则根据校验器提供的证据进行修复。代码中把这一步称为 `Verifier-guided Behavior Attribution`。

## 文件类型

| 文件 | 说明 |
|---|---|
| `*_skill.md` | 经过解析和校验、实际注入 Agent 的最终 Skill 正文。 |
| `*_skill.patch` | 最终 Skill 相对起点版本的文本差异。S1 的起点是空白 S0，因此文件会显示整份 Skill 都是新增内容。 |
| `*_learner_response.txt` | Learner 模型返回的原始文本，保留用于调试和审计，不直接作为运行时 Skill。 |
| `*_provenance.json` | 逐条记录每项 Skill 规则来自哪些经验，以及该规则属于“保留有效做法”还是“修复违规做法”。`provenance` 即来源证据。 |
| `*_metadata.json` | 记录生成输入、模型配置、输入数量、输出位置和源任务记录。 |

## Governed Candidate S1

```text
51 条 S0 Train 轨迹
        ↓
51 条同时带有任务结果和合规判断的经验
        ↓
选择 21 条 Task Success 经验
├── 11 条 Violating Success
└── 10 条 Compliant Success
        ↓
根据校验证据区分“保留”与“修复”
        ↓
18 条候选 S1 规则
├── 11 条 Preserve 规则
└── 7 条 Repair 规则
```

S1 相关文件的推荐阅读顺序：

1. `governed_candidate_s1_skill.md`：Candidate 最终内容。
2. `governed_candidate_s1_provenance.json`：每条规则来自哪些经验，以及属于保留还是修复。
3. `governed_candidate_s1_skill.patch`：S0 到 S1 增加了什么。
4. `governed_candidate_s1_metadata.json`：Candidate 如何生成。
5. `governed_candidate_s1_learner_response.txt`：模型原始输出。

# Skill Artifacts

本目录保存 SuiteCRM 实验生成的 Skill，以及用于审计和复现这些 Skill 的证据。

## 快速入口

如果只想阅读 Agent 实际使用的 Skill，请查看：

- `outcome_only_skill.md`
- `filtered_skill.md`
- `governed_candidate_s1_skill.md`

Governed Candidate S1 是 Day 9 从 S0 No Skill 的成功 Train 经验中生成的 Candidate。它同时使用任务结果和 Policy Evaluation，通过 Verifier-guided Behavior Attribution 保留有效操作，并修复有 Verifier 证据支持的违规行为。

## 文件类型

| 文件 | 说明 |
|---|---|
| `*_skill.md` | 经过解析和校验、实际注入 Agent 的最终 Skill 正文。 |
| `*_skill.patch` | 最终 Skill 相对 Parent 的文本差异。S1 的 Parent 是空白 S0，因此 Patch 显示整份 Skill 为新增内容。 |
| `*_learner_response.txt` | Learner 模型返回的原始文本，保留用于调试和审计，不直接作为运行时 Skill。 |
| `*_provenance.json` | 逐条记录 Skill 规则的学习依据，包括来源 experience、`preserve` 或 `repair` 归因，以及 Repair 规则涉及的 Policy。 |
| `*_metadata.json` | 记录生成输入、模型配置、Prompt 哈希、输入数量、输出位置和源轨迹哈希。 |
| `*_freeze.json` | Candidate 进入 Selection 前的冻结记录，保存关键产物的路径、SHA-256 和完整性状态。 |
| `*_generation_source/` | 保存生成 Candidate 时所用代码的恢复材料，用于处理生成后代码发生变化的情况。 |

## Governed Candidate S1

```text
51 条 S0 Train 轨迹
        ↓
51 条 Governed Experiences
        ↓
选择 21 条 Task Success 经验
├── 11 条 Violating Success
└── 10 条 Compliant Success
        ↓
Verifier-guided Behavior Attribution
        ↓
18 条 Candidate S1 规则
├── 11 条 Preserve 规则
└── 7 条 Repair 规则
```

S1 相关文件的推荐阅读顺序：

1. `governed_candidate_s1_skill.md`：Candidate 最终内容。
2. `governed_candidate_s1_provenance.json`：每条规则来自哪些经验，以及属于保留还是修复。
3. `governed_candidate_s1_skill.patch`：S0 到 S1 增加了什么。
4. `governed_candidate_s1_metadata.json`：Candidate 如何生成。
5. `governed_candidate_s1_freeze.json`：Selection 实际冻结和使用的文件及哈希。
6. `governed_candidate_s1_learner_response.txt`：模型原始输出。
7. `governed_candidate_s1_generation_source/`：生成时代码的恢复证据。

`freeze.json` 是实验完整性入口，但不是 Skill 正文；Agent 运行时实际读取的是其中指向并经过哈希校验的 `*_skill.md`。

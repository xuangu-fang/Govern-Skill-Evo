# SearchQA v28.12

本版沿用 v28.11 的同批 Parent / Candidate 对照和 Replay 归因。Gate 对每条 Update 单独决策。G 是本轮归到该 Update 的错转对题数，L 是对转错题数。未归因的题不计票。Δ 是只把该补丁应用于原始 Parent 时的 Unicode 字符数变化，包括换行。

| 条件 | Gate 决策 |
| --- | --- |
| 空补丁，Parent 已满足要求 | 无决策 |
| G − L ≥ 2 | Retain |
| G − L = 1 且 Δ ≤ 0 | Retain |
| G = L = 0、Δ < 0，且 Preconditioner 显式标为纯精简 | Retain |
| G − L < 0 | Reject |
| 其余情况 | Defer |

纯精简仅指合并等义表述或压缩措辞，保留原有的触发条件、例外、默认选择和动作。Preconditioner 通过可选布尔字段 `pure_simplification` 声明，缺省为假。Gate 仅合入 Retain 的补丁，在 `gate/result.json` 记录每条 Update 的 G、L、Δ、精简标记与决策。Defer 不进入后续批次的待验证队列。

Diagnosis 将跨题材但依据同一可见线索作出同一选择的案例归为一条提案。Preconditioner 对照 Parent 和其他入选提案撤回重复项，遇到同题相互冲突的指导时优先原位修订。每轮最多入选四条，也可以全部撤回。

Preconditioner 和 Editor 使用整份 Skill 约 3,000–4,000 字符的软预算。篇幅低于 3,000 字符且已完整表达本轮决策时即可结束。接近或超过 4,000 字符时，优先在本轮授权范围内合并重复措辞。

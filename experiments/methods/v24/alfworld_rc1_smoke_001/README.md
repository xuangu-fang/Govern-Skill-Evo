# V24 RC1 单轮 smoke 材料

[历史报告](REPORT.md) · [机器可读汇总](summary.json) · [逐任务对照](task_comparison.csv) · [RC1 候选导航](../candidates/README.md) · [完整原始归档](../../../../artifacts/methods/v24/alfworld_rc1_smoke_001/)

## 实际结果与版本

已有记录显示本轮完成了原第一批 10 个任务的 Parent/Candidate 配对执行。两者均为 **10/10 成功**，总步数为 130/79，Gate 为 **RETAIN**，最终保留初始 Skill。没有运行其余五批或最终 Test，不能将 Candidate 步数减少解释为被 Gate 接受。

执行代码来自 [RC1 冻结副本](../candidates/v24_alfworld_verified_feedback_001_rc1/code/)，不是后来修改 Preconditioner 的当前源码。2026-10-27 本次整理只读取已有文件、补齐阅读副本，没有运行实验、测试或项目校验入口。

## 配置、Skill 与发布结果

| 材料 | 阅读入口 |
|---|---|
| 实际单轮配置 | [config/campaign.json](config/campaign.json) |
| 原任务划分 | [RC1 data/](../candidates/v24_alfworld_verified_feedback_001_rc1/data/)；本轮仅执行配置中的 train:0000–train:0009 |
| 最终保留 Skill | [results/final_skill.md](results/final_skill.md) |
| 原发布状态与轮次决策 | [state.json](evidence/S1/state.json) · [R01/result.json](evidence/S1/rounds/R01/result.json) |
| 本轮 Parent | [parent.md](evidence/S1/rounds/R01/parent.md) |
| Editor 候选与补丁 | [candidate.md](evidence/S1/rounds/R01/editor/attempts/001/candidate.md) · [patch.diff](evidence/S1/rounds/R01/editor/attempts/001/patch.diff) · [actual.diff](evidence/S1/rounds/R01/editor/attempts/001/actual.diff) |
| Editor 结果与校验 | [editor.json](evidence/S1/rounds/R01/editor/attempts/001/editor.json) · [validation.json](evidence/S1/rounds/R01/editor/attempts/001/validation.json) |
| Gate 与十组任务配对 | [gate/result.json](evidence/S1/rounds/R01/gate/result.json) |

配置是原 `artifacts/…/config/campaign.json` 的完整副本，与 S1 的 config、initial_config 及 RC1 单轮计划正文一致。它保留冻结环境文件，因此约 8.4 MB；没有用六轮正式配置替代单轮实际配置。运行入口继续使用原归档配置。

`results/final_skill.md` 按已保存 state 的 `parent=initial_skill.md` 提取，与 [原 initial_skill.md 副本](evidence/S1/initial_skill.md)一致。Editor Candidate 只作为本轮被比较的候选保留，不是最终发布 Skill，也不是最终 Test 的结果。

## Preconditioner 三次尝试

| 原编号 | 保存的事实 | 证据 |
|---|---|---|
| 001 | ReadTimeout；没有保存 response，不补造回答 | [error](evidence/S1/rounds/R01/preconditioner/attempts/001/error.json) · [validation](evidence/S1/rounds/R01/preconditioner/attempts/001/validation.json) · [运行元数据](evidence/S1/rounds/R01/preconditioner/attempts/001/run.json) |
| 002 | finish_reason=length；保存了截断正文，未生成合法输出 | [完整已保存回答](evidence/S1/rounds/R01/preconditioner/attempts/002/response.json) · [error](evidence/S1/rounds/R01/preconditioner/attempts/002/error.json) · [validation](evidence/S1/rounds/R01/preconditioner/attempts/002/validation.json) |
| 003 | 正常结束、通过校验，被 result.json 选中 | [回答](evidence/S1/rounds/R01/preconditioner/attempts/003/response.json) · [parsed](evidence/S1/rounds/R01/preconditioner/attempts/003/parsed.json) · [规范化结果](evidence/S1/rounds/R01/preconditioner/attempts/003/preconditioner.json) · [Effective Plan](evidence/S1/rounds/R01/preconditioner/attempts/003/effective_plan.json) · [Diff](evidence/S1/rounds/R01/preconditioner/attempts/003/actual_diffs.json) · [validation](evidence/S1/rounds/R01/preconditioner/attempts/003/validation.json) |

[原选择记录](evidence/S1/rounds/R01/preconditioner/result.json)仍为 `attempts/003`。三次的运行元数据、请求开始时间和反馈上下文分别保留，没有重编号或合并。三次均使用原 32,768 输出额度，属于同一额度内的技术/截断重试，不是追加授权或语义重采样。第一次超时没有用量记录，不能将未知用量计为零。

上游 [Grouping](evidence/S1/rounds/R01/grouping/attempts/001/grouping.json) 与 [Diagnosis](evidence/S1/rounds/R01/diagnosis/attempts/001/diagnosis.json)及其选择、校验结果也保留。完整输入、messages、HTTP 回答和 Prompt 均在 [原 Preconditioner 目录](../../../../artifacts/methods/v24/alfworld_rc1_smoke_001/S1/rounds/R01/preconditioner/)；阅读副本中的 response.json 是必要回答证据，不包含完整 HTTP 原文。

## Replay、核验与 Memory 发布

- [Replay 输出](evidence/S1/rounds/R01/replay/attempts/001/replay.json)与[校验结果](evidence/S1/rounds/R01/replay/attempts/001/validation.json)保留；[选择记录](evidence/S1/rounds/R01/replay/result.json)为原 `attempts/001`。
- [Verifier 输出](evidence/S1/rounds/R01/verifier/attempts/001/verifier.json)包含 7 项 SUPPORTED、0 项 CONFLICT；[核验流程结果](evidence/S1/rounds/R01/knowledge_review/result.json)记录未触发 Repair。没有生成不存在的 Repair 结果。
- [核验后的发布候选](evidence/S1/rounds/R01/knowledge_review/candidate.json)、[初始空 Memory 索引](evidence/S1/initial_memory/active.json)、[发布后索引](evidence/S1/rounds/R01/memory/active.json)和[来源状态](evidence/S1/rounds/R01/memory/base.json)保留。
- [Memory 发布摘录](evidence/memory_publication.json)提取原 commit 的发布前后 ID、两条已发布条目及七项 Knowledge，并记录普通 JSON 内容对照：Replay、核验候选和 commit result 一致，发布条目与原 view 相符。它不包含完整历史 sources 或配对执行上下文，也不是项目校验器输出。

完整 [Memory commit](../../../../artifacts/methods/v24/alfworld_rc1_smoke_001/S1/rounds/R01/memory/archive/S1_R01.json) 和 [view](../../../../artifacts/methods/v24/alfworld_rc1_smoke_001/S1/rounds/R01/memory/view.json)仍在原归档。RETAIN 保留 Skill，同时仍发布 Memory；Verifier 的 SUPPORTED 不等于已经穷尽验证语义正确性。

## 路径与保存边界

本目录保存原报告、实际配置、Skill 和精选证据。`evidence/S1/` 尽量保留原层次和原尝试编号；文件内的来源路径按原 Campaign 解析，未改成阅读副本。它不包含完整恢复所需输入，不能当作 Campaign 运行或恢复。

完整轨迹、输入、调用、HTTP、日志、源码快照和 Memory 留在 `artifacts/methods/v24/alfworld_rc1_smoke_001/`，未移动或改写。后续 Preconditioner 重放仍从该归档的 R01/attempts/003 读取。RC1 冻结代码、配置、任务划分及 v25 预算依赖均保持原位。

目录内 `.gitignore` 仅放行上述精选尝试文件。阅读副本不会自动随未来运行更新；Git 克隆不包含原始归档。

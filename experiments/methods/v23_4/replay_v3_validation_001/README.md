# replay_v3_validation_001

本目录保留用户提供的 [候选 Prompt](v23_4_replay.md)、研究定义、报告、合法提案、必要失败证据和 Memory 审计。原始数据按原相对层级存入 [本地归档](../../../../artifacts/methods/v23_4/replay_v3_validation_001/)，其中第二轮仍位于 `round2/`。

## 保留材料

- [设计](DESIGN.md)、[协议](PROTOCOL.md)、[方法与边界](METHOD.md)、[冻结配置](config/freeze.json)、[输入对照](config/INPUT_COMPARISON.json)。
- [报告](REPORT.md)、[R05 审查](R05_REVIEW.md)、[R06 审查](R06_REVIEW.md)、[比较指标](COMPARISON_METRICS.json)、[关键证据](EVIDENCE.json)。
- [来源关系](LINEAGE.json)、[已有 Parent 调查](ALTERNATIVE_LINEAGE_INVENTORY.json)：属于实验来源证据，保留原文。
- [调用审计](AUDIT.json)、[整体结果](RESULTS.json)，以及既有 `protected_before.json`。
- 全部尝试与选择记录、原始结构化提案和结果。首轮选择 [R05 第 3 次](runs/R05_replay/attempt_003/parsed.json)、[R06 第 2 次](runs/R06_replay/attempt_002/parsed.json)；Memory 审计保留在 [R05](cases/R05/results/MEMORY_AUDIT.json)、[R06](cases/R06/results/MEMORY_AUDIT.json)。
- 第二轮保留 [控制条件](round2/config/CONTROL.json)、[历史来源关系](round2/config/history_pair_sources.json)、[冻结配置](round2/config/freeze.json)、[调用审计](round2/AUDIT.json)、[第 2 次合法提案](round2/runs/ROUND2_replay/attempt_002/parsed.json)、[Memory 审计](round2/cases/ROUND2/results/MEMORY_AUDIT.json)、[审查](ROUND2_REVIEW.md)、[证据](ROUND2_EVIDENCE.json)、[修订指标](ROUND2_REVISION_METRICS.json)。

## 失败证据与调用统计

首轮五次调用、第二轮两次调用，共七次；三份选择结果不变。

- 首轮 R05 第一次达到输出上限且正文为空，保留 [失败记录](runs/R05_replay/attempt_001/attempt.json) 和 [简短响应](runs/R05_replay/attempt_001/response.json)。
- R05 第二次读取超时，保留 [失败记录](runs/R05_replay/attempt_002/attempt.json) 和 [发送记录](runs/R05_replay/attempt_002/http/send_events.json)。没有收到 response 或 usage，继续标为未知，不计为零。`RESULTS.json` 的已报告用量小计为 2,050,302 tokens，不代表完整计费用量。
- R06 第一次为非法 JSON，保留 [失败记录](runs/R06_replay/attempt_001/attempt.json) 和 [响应原文](runs/R06_replay/attempt_001/raw_output.txt)。
- 第二轮第一次同样达到输出上限且正文为空，保留 [失败记录](round2/runs/ROUND2_replay/attempt_001/attempt.json) 和 [简短响应](round2/runs/ROUND2_replay/attempt_001/response.json)。

## 原始归档与 Memory 依赖

- [首轮 config/](../../../../artifacts/methods/v23_4/replay_v3_validation_001/config/)、[runs/](../../../../artifacts/methods/v23_4/replay_v3_validation_001/runs/)、[cases/](../../../../artifacts/methods/v23_4/replay_v3_validation_001/cases/)：完整输入、调用数据、两套 Memory 预览和完整投影。
- [第二轮归档](../../../../artifacts/methods/v23_4/replay_v3_validation_001/round2/)：完整 bundle、model_input、messages、调用数据、第三套 Memory 预览及完整投影。
- 两轮的 `run.log`、`live.lock` 也按原相对层级归档。

第二轮的前置 Memory 仍等于首轮 R05 的 `memory_candidate.json`，读取首轮 R05 的完整 `memory_preview/`；未改为 R06 或其它 Memory。该实验是离线受控再次修订，其来源与时间边界仍以 METHOD 和 CONTROL 为准。

[公共读取工具](../archive_io.py) 支持原路径读取、合并枚举和归档输出位置；V2 比较、两轮审计及 Memory 读取均已适配。历史 JSON 路径及冻结记录保持原文。本次整理未调用模型、重新提交 Memory 或新增校验清单。完整原始数据被 Git 忽略，仅克隆 Git 不包含这些数据。

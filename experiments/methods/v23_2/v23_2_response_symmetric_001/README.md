# 原始与替代 Update 的对称证据约束

已完成：[最终报告](reports/REPORT.md)与[共享 Original／四版 Effective 全文对照](reports/OUTPUTS.md)。三次逻辑调用均首次合法，0重试，1,288,086 tokens。R06原取舍有局部改善，但替代排序与续行限制仍缺少充分依据；不晋升优先候选或默认配置。171项离线回归通过，11,891个历史保护文件未变。完成后停止，未开展行为实验。

先完成[调用前 R06 核查与设计理由](reports/PRECALL_REVIEW.md)，再冻结候选、Diff 和设计材料。冻结快照位于 `config/implementation.json`，编排启动前及结束后核对，不能根据输出修改候选。

- [完整 Prompt](config/preconditioner_prompt.md)
- [相对 V23](config/v23.diff)、[相对 alignment](config/alignment.diff)、[相对 construction](config/construction.diff) 的精确 Diff
- [原始轨迹与 Memory sources 一致性核验](config/precall_evidence_checks.json)
- [当轮固定配置](config/plan.json)与[离线测试](reports/offline_tests.txt)
- [最终冻结、输入与历史保护核验](results/final_checks.json)

[run.py](run.py) 仅设置独立路径，复用原三轮局部编排及 `local_validation`；不复制框架，不改原模块和默认 Prompt。每轮输入仍是正式 V23 的 Parent、Original Plan、证据选择和实际当轮 Memory，不输入此前候选输出或后续行为结果。只替换同一处 system 规则；Actor 背景、模型、输入容量及契约不变。

最多 R04/R05/R06 各一次逻辑调用，每组首次加最多两次技术重试；不因语义结果重采样，不手工修补输出。已有产物时拒绝重跑分配新预算。合法停止及技术耗尽按原契约保留。

最终分别判断 A 原取舍、B 替代构造、C 合理探索，不以 Adjustment 数量或某个旧错误未出现替代判断。不运行 Editor、Candidate、Replay、Actor、ALFWorld 或正式六轮，不写 Memory，不执行 Gate，不使用最终 Test 轨迹。

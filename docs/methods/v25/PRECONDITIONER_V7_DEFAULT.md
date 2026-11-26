# 默认 Preconditioner 回退至 v7

2026-10-28。默认恢复为 `v25_preconditioner_evidence_decision_boundaries_v7`，v8 保留为实验版本。

## 依据与边界

v8 干净输入单模块对照中，R05 未解决默认子串匹配和未知数值边界前提的问题；R06 在原六次请求上限内三次超时、三次耗尽输出额度，没有完整回答。没有足够收益支持继续以 v8 替换 v7。这不证明 v7 判断全面正确，也不证明 v8 必然导致调用失败。

原结果不改写，见 [v8 实验报告](../../../experiments/methods/v25/preconditioner_v8_deepseek_r05_r06_clean_20261028_001/reports/README.md)。

## 修改范围

- 默认运行正文 `preconditioner.md` 按字节恢复为已归档的 v7；文档镜像同步。
- 修改前 v8 正文按字节另存为运行资源和文档下的 `preconditioner_legacy_v8.md`。
- 新增独立 v8 版本映射，旧 v8 输出仍按 v8 模板重读；v3–v7 兼容路径保留。默认版本变量及新配置指向 v7。
- 只同步未来运行使用的 batch15 配置模板；所有已冻结 campaign、单模块配置、请求、输出和实验报告保持原档。
- Replay / Memory、Diagnosis、Editor、Actor、证据视图、评分及调用参数均未修改。完整训练仍须按当前源码重新冻结，归档可读不等于可绕过旧冻结契约续跑。

## 离线验证

38 项已有测试通过：`test_task_requirement_versions.py`、`test_configuration.py`、`test_preconditioner_context.py`。版本兼容测试覆盖保留的 v8 模板；仅使用固定响应与临时模拟数据，没有模型调用或 benchmark 实验。

另原生重读 R05 原始 / v7 / v8 和 R06 原始 / v7 五份 Preconditioner 归档；追溯审计重读 R01–R05 Replay 与 Memory，核对 150 份历史 Actor 记录。v7 恢复、v8 保留和两处镜像均按字节校验通过。

回退前固定的 4,640 份文件中，只有获准修改的 Preconditioner 代码和默认运行模板发生变化；历史实验及 Replay / Memory 生产实现未变。详见 [验证记录](../../../artifacts/methods/v25/analysis/replay_memory_r05_r06_audit_20261028_001/rollback_validation.json)。

## 下一阶段

默认固定在 v7，将研究重点转到 Replay / Memory 的事实提取、经验范围和下游使用。先区分模块没有看到事实、看到了却未利用，以及经验或决策本身超出证据。此次只完成 [R05 / R06 证据审计](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v25/REPLAY_MEMORY_R05_R06_AUDIT.md)，不实施 Replay / Memory 修改，不运行新实验。

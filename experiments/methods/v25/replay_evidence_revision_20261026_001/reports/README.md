# Replay 共性问题修订包

已完成用户授权的第一步（Prompt 与文档）和第二步（固定对照案例）。这是主工作区当前源码的隔离覆盖副本，不是已启用的新训练版本。

- 候选标识：`v25_replay_evidence_revision_v2`，尚未注册到运行适配器。
- 新版正文：[运行资源路径副本](../../../../../artifacts/methods/v25/analysis/replay_evidence_revision_20261026_001/overlay/src/skill_evolution/v25/benchmarks/spreadsheetbench/prompts/replay.md)，[文档镜像](../../../../../artifacts/methods/v25/analysis/replay_evidence_revision_20261026_001/overlay/docs/methods/v25/prompts/replay.md)。
- 职责说明：[REPLAY_ROLE.md](../../../../../artifacts/methods/v25/analysis/replay_evidence_revision_20261026_001/overlay/docs/methods/v25/REPLAY_ROLE.md)。
- 固定案例：[评估说明](../../../../../artifacts/methods/v25/analysis/replay_evidence_revision_20261026_001/evaluation/README.md)，[9 个案例](../../../../../artifacts/methods/v25/analysis/replay_evidence_revision_20261026_001/evaluation/cases.json)，[5 份输入来源与哈希](../../../../../artifacts/methods/v25/analysis/replay_evidence_revision_20261026_001/fixtures/manifest.json)。
- `before/`：修改前文件；`overlay/`：拟接入的文件；`changes.patch`：完整修改差异。
- `protected_source_hashes.json`：准备前主工作区 V25 源码和文档的 107 个文件哈希。
- `verify_package.py`：仅本地检查；无模型、网络、训练或写入旧实验的行为。
- `verification.json`：实际静态检查结果，不是模型质量评估。

正文围绕“观察与主张的证据支持”“实际修改—行为—结果解释”“历史观察保留与解释校正”整理。输出契约和配对说明逐字保留，没有增加模块、字段或任务专用策略。Verifier／Repair 和 Actor 协议不变。

当前 `_007` 的源码、配置与实验归档未被本包替换。不要向正在运行的主工作区应用补丁。后续单独重放和正式启用需使用隔离执行环境或新的冻结实验，并显式注册新 Prompt 版本。

执行本地检查：在仓库根目录运行 `/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/analysis/replay_evidence_revision_20261026_001/verify_package.py`。该脚本向标准输出报告结果，执行者可保存为本包 `verification.json`。

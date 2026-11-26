# R05 / R06 Replay–Memory 只读审计

完整结论：[审计报告](../../../../../docs/methods/v25/REPLAY_MEMORY_R05_R06_AUDIT.md)。

默认版本回退：[回退说明](../../../../../docs/methods/v25/PRECONDITIONER_V7_DEFAULT.md)。

`audit.py` 仅重建和校验历史视图，不执行模型或 Actor。`lineage_audit.json` 记录传递一致性；`memory_evidence.md`、`module_evidence.md` 和 `Rxx_execution_evidence.md` 提供原文、来源路径和定位；`before_sha256.json` 与 `rollback_validation.json` 记录保留校验。

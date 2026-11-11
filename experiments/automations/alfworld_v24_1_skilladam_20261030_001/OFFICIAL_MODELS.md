# ALFWorld 官方模型绑定修订

用户授权将 v24.1 和 SkillAdam 的 Actor、优化器统一到官方 deepseek-flash，使用 SheetBench V25 的仓库 .env 凭据。

- 新实验及完整训练、恢复、测试命令：plan.json
- 原启动时间保持 2026-10-30 04:44:03 +08:00；首次唤醒后仍每 30 分钟监测。
- 原计划和自动化快照：revisions/before_official_models/
- 原实验文件和旧结果未修改；其他参数与恢复、最终测试条件不变。
- 所有命令通过 with_official_credentials.py 校验时间、冻结输入并加载同一官方凭据，不打印或保存密钥。
- 离线核验结果：official_models_checks.json、offline_checks.json。二者包含未启动状态断言，仅在首次训练前运行。
- 本次没有启动训练、测试或发起真实模型请求。

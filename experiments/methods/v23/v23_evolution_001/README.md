# V23 统一轮次调度验证

已完整完成两轮：Gate 均 RETAIN，Parent 仍为 null，Active Memory 从空发展为 M1/M2/M3。16 个 episode、253 个 Actor 请求、13 个模块请求，总用量 835,903 Token。第二轮真实引用历史 Memory 调整更新，但存在事实混淆与过度概括；未证明行为或泛化收益。

- [报告 A：实现、离线串联与恢复验证](reports/IMPLEMENTATION.md)
- [报告 B：真实小规模验证](reports/LIVE.md)
- [冻结任务与实际配置](config/campaign.json)
- [请求和输出预算](config/budget.json)
- [离线回归日志](results/offline_tests.txt)

运行产物位于 `artifacts/methods/v23/v23_evolution_001/`。仅使用 Train，不设置 Validation，不使用 Test。首轮 null Parent、空 Memory，不复用此前探索实验 M1/M2/M3。真实停点后不自行恢复，完整结果以报告 B 为准。

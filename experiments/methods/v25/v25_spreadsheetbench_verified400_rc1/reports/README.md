# v25_spreadsheetbench_verified400_rc1

此候选包含独立代码副本、完整配置、原始任务列表、初始 Skill、空 Memory 和离线验收记录。

- 代码：`code/src/skill_evolution/v25/`
- 配置：`config/campaign.json`
- 划分：`data/splits.json`，80 Train＋40 Val 参与优化；280 Test 仅最终评估。
- 验收：[离线报告](../../../../../artifacts/methods/v25/candidates/v25_spreadsheetbench_verified400_rc1/validation/OFFLINE_ACCEPTANCE.md)、[运行说明](../../../../../artifacts/methods/v25/candidates/v25_spreadsheetbench_verified400_rc1/validation/RUNNING.md)。
- 结果：176 项测试通过；15 个合成任务完成 30 次真实容器程序执行。
- 真实模型请求为 0；真实数据集任务执行为 0。

120 个优化任务的区域元信息检查通过。三个 Test 标注问题为 60-7、283-32、73-45，原始任务均保留；解决并统一评分配置前不启动最终 Test 评估。

# V24 ALFWorld：并发 10，关闭 Verifier/Repair

状态：配置及离线预检已准备，未启动训练、真实模型请求、环境 episode 或 Test。`S1/` 尚未创建。

来源为已完成的 `artifacts/methods/v24/alfworld_history_and_plan_v3_20261027_001/S1/config.json`，采用后来更新的 Preconditioner v3，不是 RC1 smoke。旧结果及授权记录保留，哈希清单见 [preserved_source_results.json](config/provenance/preserved_source_results.json)。

| 项目 | 来源配置 | 新配置 |
| --- | --- | --- |
| Actor 训练并发 | 8 | 10，与当前 SkillAdam 一致 |
| knowledge_review | obvious_fact_verifier_targeted_repair_v1 | disabled_v1 |
| Memory 发布 | Verifier 与必要的 Repair 后提交 | Replay 校验后直接提交 |
| Verifier/Repair 输出预算 | 各 32768 | 删除，模块不执行 |

新流程：Parent → Grouping → Diagnosis → Preconditioner → Editor → Candidate → Gate → Replay → Memory。no_change 分支和严格成功数 Gate 保持原行为；Replay 结构及引用校验、Memory 提交校验、恢复与最终导出校验仍生效。`knowledge_review/result.json` 仅记录 disabled 状态，不代表发生过模型核验。

其余配置与来源逐项一致：同一 57 题优化池和 134 题 Test；六批 10/10/10/10/10/7；原始初始 Skill；deepseek-v4.1-flash、medium、temperature=1；Actor 16384 输出、50 步、最近 2 步历史；Actor 与方法模块最多 6 次总尝试。Preconditioner、Replay 输出上限仍为 32768，其他启用模块为 16384。每轮五个方法模块，方法请求总上限为 180。完整差异见 [alignment.json](config/provenance/alignment.json)。

不继承旧最终 Skill、Memory、检查点、执行缓存或 R01/R03 的 Verifier 追加额度。旧实验的 121/134 成绩不属于本配置。自动 Test 关闭。

`config/campaign.json` 为新配置，`config/source_config.json` 保存来源配置；`config/source_contract.json` 和 [manifest.json](config/provenance/manifest.json) 保存准备时的源码及文件身份。旧源码冻结与授权快照保留在原实验中；修改后的工作区源码不能直接用于恢复旧 Campaign。

只有用户明确要求启动后，才在仓库根目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python -m src.skill_evolution.v24.evolution run --campaign artifacts/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001/S1 --config experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001/config/campaign.json
```

本次未执行该命令。离线验证结果见 [preflight.json](results/preflight.json) 和 [verification.json](results/verification.json)。

[离线验收摘要](results/validation_report.json)

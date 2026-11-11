# v24.1：ALFWorld 四模块设计更新

已将 `draft_20261030_001` 中复审后的 `review_02` 草案接入独立包 `src/skill_evolution/v24_1`。四份 Prompt 与批准的文本逐字节一致；execution context、Knowledge Only 历史视图仍按原流程装配。草案目录保持原样。

以 `experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001` 为唯一基线：训练并发 10，Verifier/Repair 关闭。新配置位于 `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_20261030_001`。

- Diagnosis 仅接受 `revise` / `no_change`；允许有依据、待验证的修复假设；删除旧 `need_evidence` 决策及其硬停止分支。未知决策进入原有格式重试，不会被静默转换。`no_change` 沿用原来的继续下一批策略，不证明 Skill 无问题。
- Preconditioner 保留原引用契约与结构校验，按批准草案检查条件、强度、阶段及必要能力，不新增显式类型、字段或额外模型审查。
- Editor 忠实保留方案的条件和强度；补丁结构、应用规则不变。
- Replay 采用批准的真实行为与行动机会比较要求；保留归纳边界；不改变输入配对、Memory 结构和 Gate。

除方法与模块版本标识外，实验配置逐字段与基线相同。Actor、重试、数据、批次、初始 Skill、预算、Gate、历史视图和测试规则均保持不变。新实验从原初始 Skill、空 Memory 开始，不继承旧实验的最终 Skill、Memory 或断点。

代码使用独立命名空间、本地模块和 Prompt 副本。底层证据、Actor 等未改语义的契约 ID 保留；新方法和 Prompt 版本禁止将旧产物误认作新版本。旧 v24 的代码、配置、结果保持原样。新默认评估路径也指向 v24.1 目录。

离线验证脚本：`scripts/runs/v24_1/verify_v24_1_offline.py`。它阻止网络、真实模型与 Actor 调用，使用预设响应核对接线、契约、重试、恢复和 Memory 发布，并回归原 v24 测试。原验收摘要见[准备配置的离线报告](../../../experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_20261030_001/results/verification_report.json)。这些检查不证明实际成功率改善。

原复审配置仅完成准备。官方路由配置后来完成六轮训练、首测和复测。[版本实验索引](../../../experiments/methods/v24_1/README.md) · [正式结果](../../../experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/README.md)。`prepare` 不创建 S1。后续启动须使用 v24.1 入口及独立结果目录；不能用旧 v24 入口加载新配置。

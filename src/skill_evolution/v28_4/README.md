# SearchQA v28.4

独立四阶段链路：Diagnosis → Preconditioner → Editor → Replay。Parent/Candidate 执行、确定性 Gate、追加 Memory 与恢复由本版本运行器接线；没有 Grouping。

- 直接继承 SearchQA v28.3 的运行算法，以独立包、方法身份、配置和 Prompt 路径隔离；不修改旧版本。
- 逐字加载已确认的 [v28.4 提示词](../../../docs/methods/v28_4/prompts/)。Diagnosis 选择问题与 Parent 对应的修正；Preconditioner 审查完整修正；Editor 准确实施。组织建议不变成标题、数量或长度校验器。
- Actor、数据、评分和原始 question/context 表示保持不变。Actor/Editor 为 32,768 tokens；Diagnosis/Preconditioner/Replay 为 65,536。训练/Test workers 均为 15。
- 保留原有六次总请求额度、精确 patch 映射/组合、EM 翻转 Replay/Gate、顺序 Memory 提交与轻量恢复。旧版本配置、Prompt 或检查点不能通过重标记恢复到本版本。
- 两个通用引用解析函数仍通过既有纯文本工具复用；不需要 DocVQA benchmark、图片、数据或 Pillow。

入口：[run_v28_4_campaign.py](../../../scripts/runs/run_v28_4_campaign.py)。配置：[v28_4_searchqa_train600_batch30.json](../../../experiments/configs/v28_4_searchqa_train600_batch30.json)。合同及结果见 [IMPLEMENTATION.md](../../../docs/methods/v28_4/IMPLEMENTATION.md)。

本次只实现与离线验收，不启动正式训练或 Test。train/test 保持独立显式入口；训练完成不会自行启动 Test。

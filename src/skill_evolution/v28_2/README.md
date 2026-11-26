# SearchQA v28.2

独立的五模块自进化链路：无 Checks、全文 Preconditioner 动作、Update 对应 patch、EM 翻转 Replay、选择性 Gate、追加式 Memory 和原子发布。

- [设计、合同与定稿提示词](../../../docs/methods/v28_2/README.md)
- [实现映射、离线验收和运行说明](../../../docs/methods/v28_2/IMPLEMENTATION.md)
- [独立 train/test 入口](../../../scripts/runs/run_v28_2_campaign.py)
- [冻结的 600 / batch30 配置](../../../experiments/configs/v28_2_searchqa_train600_batch30.json)

直接加载设计目录的五份 Prompt。复用 SearchQA Actor/数据/原生评分，不注册到旧 v28/v28.1 入口。正式训练与 Test 本轮未启动。

# SearchQA v28.5

当前为 SearchQA 领域指导 Prompt v2：Diagnosis、Preconditioner、Replay 使用独立的 v2 标识；Editor 保持 v1。三个运行模块仅修改 `PROMPT_VERSION` 常量，方法／stage／runtime／contract 身份与算法均未改变。

Preconditioner 继续接收完整 Parent、冻结 Original Plan、引用的当前执行和历史 Memory，按 Direction／Scope／Coordination 决定 KEEP／REPLACE／WITHDRAW。Editor 负责忠实实施；Replay 仍仅处理 EM 翻转。新领域分类不增加输入输出字段或 Memory 状态。

- [正式 Prompt 与当前状态](../../../docs/methods/v28_5/README.md)
- [修订、冻结与离线验证](../../../docs/methods/v28_5/revisions/searchqa_guidance_v2_20261105/README.md)
- [默认 batch60 配置](../../../experiments/configs/v28_5_searchqa_train600_batch60.json)
- [显式运行入口](../../../scripts/runs/run_v28_5_campaign.py)
- [当前离线检查入口](../../../scripts/verification/verify_v28_5_prompt_v2.py)

当前未启动训练、Test 或自动化。历史 Prompt v1 的配置与检查点不能在新 Prompt 下恢复；历史归档及旧版源文件快照保留。旧 batch30／batch50 配置不随本次修订更新。

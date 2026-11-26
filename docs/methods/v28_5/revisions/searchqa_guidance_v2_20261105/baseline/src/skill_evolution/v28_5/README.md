# SearchQA v28.5

基于 v28.3 独立派生的运行实现，直接读取已定稿的 [四份 Prompt](../../../docs/methods/v28_5/README.md)。除版本身份、导入路径和 Prompt 路径外，运行代码与 v28.3 保持一致；不扩展 Memory、不改 Gate 或实验参数。

Preconditioner 继续接收完整 Parent、Original Plan、Plan 引用的完整当前执行和历史 Memory。Editor 接收 Effective Plan；Replay 继续只处理 EM 翻转。改进来自已定稿的 Prompt，程序不增加规则压缩、额外评审或模型验收阶段。

入口：[run_v28_5_campaign.py](../../../scripts/runs/run_v28_5_campaign.py)。配置：[v28_5_searchqa_train600_batch30.json](../../../experiments/configs/v28_5_searchqa_train600_batch30.json)。实现状态与离线检查见 [IMPLEMENTATION.md](../../../docs/methods/v28_5/IMPLEMENTATION.md)。

train/test 是独立显式命令；训练 CLI 完成不会自行启动 Test。用户随后授权完整实验，已由独立 supervisor 串联训练、最终 Test 和比较；当前进度见 [实现说明](../../../docs/methods/v28_5/IMPLEMENTATION.md)。

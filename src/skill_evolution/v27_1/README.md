# LiveMathematicianBench v27.1

独立四模块链路：Parent → Diagnosis → Preconditioner → Editor → 完整 Candidate 批次 → EM 翻转 Replay → 逐 Update Gate → Memory/Selected 原子发布。

Actor 单次输出上限 65,536，四个方法模块各 32,768，Train/Test workers 20/16，均为六次总尝试。原生选项打乱、答案解析、二值 EM 和既有数据/执行摘要校验保持不变；不修改旧 v27 全局协议。

入口：[run_v27_1_campaign.py](../../../scripts/runs/run_v27_1_campaign.py)。配置：[v27_1_lmb53.json](../../../experiments/configs/v27_1_lmb53.json)。提示词直接读取已审阅设计稿。实现与验收：[IMPLEMENTATION.md](../../../docs/methods/v27_1/IMPLEMENTATION.md)。

train/test 是独立显式命令；训练完成不会自动启动 Test。目前只完成离线验收，没有真实 v27.1 实验结果。

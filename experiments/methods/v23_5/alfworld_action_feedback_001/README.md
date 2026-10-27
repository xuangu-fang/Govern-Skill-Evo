# V23.5 Actor 有限反馈配置

## 2026-10-27 当前材料状态

仅有配置与准备材料；截至本次检查，未发现对应 artifacts 运行目录，不生成轮次结果或最终 Skill。

正式 config/、任务 data/ 原样保留；以下结果来自已有文件，本次没有运行实验或测试。

仍保留 config/campaign.json、budget、provenance、initial_baseline_reference、全部 data/ 和准备验证报告。没有执行记录，因此不借用其他配置的结果来补齐本目录。

当前通用脚本 [run_v23_5_alfworld.sh](../../../../scripts/runs/run_v23_5_alfworld.sh) 默认指向 alfworld_action_feedback_001；下方旧入口说明保留历史阶段含义，通用脚本不会自动恢复旧目录。本次未执行任何入口。

未来运行的既定输出仍为 `artifacts/methods/v23_5/alfworld_action_feedback_001/`；本次不创建空归档冒充已运行。

## 历史说明（保留原阶段记录）

从 `alfworld_action_only_001` 派生，仅启用 `actor_action_feedback=true`。
初始 Skill、两份基础模板、模型参数、任务批次、Gate、输出预算与每步六次总请求额度不变。

缺少完整 action 标签或提取命令不在原动作列表时，附最近一次失败正文及具体诊断。
不推荐替代动作；技术重试保留整份既有请求，反馈不累积，验证通过才执行环境动作。
每次请求的 messages、反馈来源、失败正文、诊断和原始 HTTP 响应均保存并在审计时核对。

`scripts/runs/run_v23_5_alfworld.sh` 默认指向本配置。这里只完成离线准备，尚未启动训练或 Test。
旧实验的请求、结果、冻结配置和额度不改写，不在旧 Campaign 中直接切换执行协议。

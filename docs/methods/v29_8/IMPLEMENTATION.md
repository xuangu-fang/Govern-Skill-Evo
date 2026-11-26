# v29.8 DocVQA 训练、评测与离线验收

训练和评测共用一个版本化 CLI。训练使用显式配置，从初始 Skill 开始，导出最终选中的 `final_skill.md`。评测使用已完成训练的 campaign 和独立输出目录，核对导出文件与最终选中 Skill 一致后读取测试集。首次正式实验已于 2026-11-12 完成，最终 Skill 在 374 题中完全匹配 333 题。[正式评测摘要](../../../experiments/evaluations/v29_8_docvqa160_20261112_125216_test374/summary.json)[入口](../../../scripts/runs/run_v29_8_campaign.py) · [配置](../../../experiments/configs/v29_8_docvqa_optimization160.json) · [运行模块](../../../src/skill_evolution/v29_8)

| 项目 | 已核对的配置 |
|---|---|
| 训练与评测身份 | `v29_8_campaign_v1`、`v29_8_stages_v1`、`v29_8_light_runtime_v1`、`v29_8_final_test_v1` |
| 提示词 | Diagnosis 和 Preconditioner 采用 v29.8 设计稿。Editor 和 Replay 的正文与 v29.7 训练归档相同。四个模块各自记录本版本的提示词身份和实际内容。 |
| 数据 | 优化集 160 题，10 批各 15 题、最后一批 10 题。独立测试集 374 题。 |
| 模型与资源 | deepseek-flash；训练并发 15，评测并发 60；Actor 和四个方法模块各有 32,768 token 输出预算。 |

## 离线验收

116 项测试全部通过，失败、错误和跳过均为 0。合成用例覆盖 CLI 训练、更新提案到 Editor 的交付、Gate 选择、Memory 发布、最终 Skill 导出及独立评测；还覆盖中断恢复、版本混用拒绝和归档一致性。新增的 CLI 贯通用例在同一临时目录内先训练、再评测，逐字节核对评测 Skill 与训练导出物。验收期间网络连接和子进程由守卫拦截，触发次数为 0。冻结清单中的 50 个文件均通过 SHA-256 核对。[验收报告](../../../artifacts/verification/v29_8_offline/validation.json) · [测试日志](../../../artifacts/verification/v29_8_offline/unittest.log) · [冻结清单](baseline_sha256.json)

另外从仓库外调用训练 CLI 的 `--validate-only`，使用正式配置及不存在的凭据文件，返回 `valid` 并确认 11 批划分。预检未创建 campaign。评测入口的只读预检使用已完成的合成训练归档验证。以上结果用于确认运行链路，Skill 写作质量与基准成绩待实测。[CLI 预检记录](../../../artifacts/verification/v29_8_offline/cli_preflight.json)

在仓库根目录使用 DocVQA Python 环境可复核离线验收：

```sh
python -B scripts/verification/verify_v29_8_campaign.py
```

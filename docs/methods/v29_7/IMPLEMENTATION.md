# v29.7 独立运行链路与离线验收

v29.7 已接入独立的训练和最终 Test 入口。使用正式训练归档中的新方案 v29.6 作为基线，四份实际加载的 Prompt 中，仅 Preconditioner 正文存在差异。运行时加载的 Preconditioner 与已通过设计检查的 SHA-256 一致。正式实验尚未启动。

[独立 CLI](../../../scripts/runs/run_v29_7_campaign.py) · [正式配置](../../../experiments/configs/v29_7_docvqa_optimization160.json) · [运行模块](../../../src/skill_evolution/v29_7/) · [完整设计 Prompt](prompts/)

## 运行身份与参数

| 项目 | v29.7 |
|---|---|
| 方法、阶段 | `v29_7_campaign_v1`、`v29_7_stages_v1` |
| 运行时、最终 Test 归档 | `v29_7_light_runtime_v1`、`v29_7_final_test_v1` |
| 四模块的 Prompt 身份 | `v29_7_docvqa_<module>_v1` |
| 优化集、Test | 160 题，原顺序与 10×15＋10 批次；Test 374 题 |
| 资源 | 训练并发 15、Test 并发 60，Actor 与四模块各 32,768 token |

验收逐字段比较正式配置，版本身份以外的配置与新方案 v29.6 相同。各阶段记录实际 Prompt 内容与源码身份；混搭 Prompt 身份或跨版本续跑会在执行前被拒绝。训练从初始 Skill 和空 Memory 开始，Test 读取完成训练后的最终选中 Skill，在独立目录评估。

## 验收结果

115 项 v29.7 离线测试全部通过，无失败、错误或跳过。覆盖临时目录中的合成训练、四个模块的实际加载与归档、Gate 和 Memory 发布、恢复与重试、最终 Skill 导出，以及最终 Test 的隔离、恢复和计分。检查中禁止网络连接和子进程调用。51 项冻结文件的 SHA-256 均与基线清单吻合。

[验收报告](../../../artifacts/verification/v29_7_offline/validation.json) · [离线日志](../../../artifacts/verification/v29_7_offline/unittest.log) · [冻结文件清单](baseline_sha256.json)

另从工作区外直接调用真实 CLI，使用正式配置、`train --validate-only` 和不存在的凭据文件，入口返回 `valid` 并核对了全部 11 批，预检查未创建 campaign。所有执行过的训练或 Test 流程均使用合成响应和临时数据。模型效果留待正式实验评估。[CLI 预检查记录](../../../artifacts/verification/v29_7_offline/cli_preflight.json)

可用以下命令复核离线验收，使用项目的 DocVQA Python 环境。

```sh
python -B scripts/verification/verify_v29_7_campaign.py
```

# SpreadsheetBench v25.8

v25.8 基于当前 v25.7，修改 [Diagnosis](../../../src/skill_evolution/v25_8/prompts/diagnosis.md) 和 [Preconditioner](../../../src/skill_evolution/v25_8/prompts/preconditioner.md)。目标是围绕可观察的工作簿操作决策组织更新：同一决策变化只提出一次，单例仍可贡献独立操作，每项更新明确相对 Parent 的行为增量。不设置 Update 数量目标，也不要求每项必须有多题证据。

[正式运行归档](../../../experiments/methods/v25_8/README.md)汇集当次冻结配置、每轮保留 Skill、19 次评测及对应的离线读回入口。

## 提案形成

Diagnosis 先从任务要求、程序、执行反馈和保存结果定位有证据支持的操作分歧，再跨题比较共同决策，最后分配 ID 并撰写 goal。多题支持同一动作时合并证据；同题暴露独立操作时允许分别提出。区分可见错误与推测原因，纳入会实际改变适用范围的成功或反例。

更新单位是带有必要条件、动作和例外的行为改变。验证或恢复是动作的必要完成条件时随动作保留，不拆成重复提案；不因为多个修正共同影响一题成败而合并。已有规则适用时，明确需要改变的条件、动作或例外，避免按任务重复附加完整的定位、读取、计算、写入、检查流程。单例去掉具体坐标和答案后，仍应提供未来脚本能执行且 Parent 尚未提供的操作。

Preconditioner 审查这些划分及其与完整 Parent 的关系。它保留 ID，在提案原有问题范围内完善修正、撤回已覆盖或重复的提案，不把独立修正转移到另一 ID。旧规则的整合要求进入有效文本，不能只写在 Editor 看不到的 reason 中。每项有效修改在仅它被采纳时也应与 Parent 一起成立。

## 保持不变的部分

- Replay 保留 v25.7 的完整提示词，包括两题 JSON 示例和整题翻转归因条件。
- Gate、输出合同、证据可见性、Memory、Editor、执行上下文及训练引擎复用 v25.7。
- 不增加结构化字段、分组阶段、题数门槛或 Update 数量上限。
- 官方配置仍为 `https://api.deepseek.com`、`deepseek-flash`，120 题、8 批训练，训练并发 15；固定 280 题最终评测，并发 40。Actor 与优化模块使用同一模型配置。凭据按现有规则从成对的环境变量或项目 `.env` 读取。

方法标识为 `v25_8_selective_updates_prompt_v1`，候选标识为 `v25_8_spreadsheetbench`。[入口](../../../scripts/runs/v25_8/run_v25_8_train_test.py)支持 `prepare`、`verify`、`train`、`run`，默认输出到 `artifacts/methods/v25_8/v25_8_spreadsheetbench_deepseek`，并保留 `--api-profile public|internal`。这是独立版本，不用于接续已冻结的 v25.7 campaign。

## 离线验证

[验收程序](../../../scripts/verification/v25_8/verify_offline.py)检查 v25.7 [基线哈希](baseline_sha256.json)、两个新提示词的运行时绑定、Replay 和 Editor 消息一致性、Gate 及共享实现字节一致性、配置、快照、恢复与最终 Skill 交付。预设响应驱动合成流程，验证期间阻止网络连接与子进程，不调用模型、不启动真实训练。

不创建正式 campaign 的验收方式：

```sh
/Users/didi/miniforge3/envs/spreadsheetbench/bin/python - <<'PY'
import json
from scripts.runs.v25_8.run_v25_8_train_test import configurations
from scripts.verification.v25_8.verify_offline import verify
for profile in ('public', 'internal'):
    print(json.dumps(verify(*configurations(profile), api_profile=profile), indent=2))
PY
```

提示词评审应检查以下区别；离线预设响应不能证明模型会作出这些判断。

| 对照情况 | 期望判断 |
|---|---|
| 筛选与聚合都把公式缺失缓存当作真正空白 | 同一取值决策可由多题共同支持，只提出一次 |
| 同一程序既不遵守分配上下限，又向尾部空白行写零 | 可以保留两个独立操作 |
| Parent 已完整规定缓存处理，新任务需要修改行列选择 | 提出选择行为的增量，复用已有缓存规则 |
| 公式交付动作需要保存后核验与修复才能完整 | 必要闭环随动作保留，避免重叠提案 |
| 单例显示跨文件系统原子替换失败并有可复用修复 | 不因只有一道题而排除新操作 |
| 单例的阈值等号落入特定分支 | 不把该题答案推广成所有 before/after 任务的默认值 |

上述验收使用预设响应。正式训练与评测的历史材料见[实验归档](../../../experiments/methods/v25_8/README.md)。

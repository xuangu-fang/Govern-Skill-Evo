# OfficeQA v26.4 实现与离线验证

2026-11-17 完成实现和离线验收。正式训练和测试仍待启动。

## 实现

[v26.4 入口](../../../scripts/runs/run_v26_4_campaign.py) 分别提供训练、独立测试和历史测试比较。[可执行配置](../../../experiments/configs/v26_4_officeqa_train74.json) 与 [v26.3 真实训练归档](../../../experiments/campaigns/v26_3_officeqa_train74_20261117_125845/config.json) 逐字段对比，差异仅有 `method.version` 和 `method.prompts` 中的四个提示词标识。训练从正式初始 Skill 和空 Memory 开始。七轮结束后，独立测试入口从完成的训练归档读取最终 Skill。

[Diagnosis](prompts/diagnosis.md) 按整批 Parent 轨迹寻找同一决策失误，把支持同一修正的多题证据归入一条 Original Update，并用相近成功作答检验适用边界。[Preconditioner](prompts/preconditioner.md) 对照相关 Parent 段落，在同一组 Actor 可见线索下判断提案会改变哪个动作、条件或优先级，据此保留、改写或撤回。[Editor](prompts/editor.md) 只实现获准的行为改动。[Replay](prompts/replay.md) 对照两侧轨迹和真实评分归一化规则归因。四份固定提示词都移除了预设领域清单、重复提示和题号预算说明，每份都有独立的 v26.4 文件、修订标识和加载时校验的 SHA-256。[提示词与配置绑定](../../../src/skill_evolution/v26_4/protocol.py)

每个已完成轮次的 `round_summary.json` 和最终的 `training_summary.json` 记录 Selected Skill 的字符数（含标题和换行）和以 `- ` 起始的顶层条目数。两项统计供逐轮阅读，可结合归档中的 Original、调整理由、有效文本和补丁解释增长。Gate 继续按原归因结果作决定。[逐轮统计实现](../../../src/skill_evolution/v26_4/reporting.py)

## 验证结果

| 检查 | 本次结果 |
|---|---|
| 正式题单只读预检 | 已逐题准备 74 个优化输入和 172 个独立测试输入。七批题数依次为 11、11、11、11、10、10、10。模型请求为 0，目标目录未创建。 |
| 固定提示词 | 核对四个阶段实际收到的英文全文及其修订标识。三个可见轨迹的模块逐字保留正式评分段落，Editor 只接收 Parent 和有效提案。 |
| 合成多题交接 | R01 的两道失分题和一道相近成功题进入同一条提案的依据。模拟审查改写该提案、撤回一项已覆盖的行为。Editor 只收到保留原 ID 的有效改写。最终 Skill 含有该改写，Gate 按既有合同归因两项改善。 |
| 七轮模拟与恢复 | 覆盖有编辑、全部撤回和 Diagnosis 无新提案三个分支。Memory 提交后中断，再恢复该轮时调用数保持不变。模拟训练完成时尚未进入测试。另行验证 v26.4 拒绝从 v26.3 断点恢复。 |
| 独立模拟测试 | 中断时报告已完成数、答对数和待完成题目，全量 EM/F1 留空。恢复后完成 172 题，测试 Skill 与训练产物逐字节一致，训练 Memory 一致。核对训练逐题预算和测试统一的 32,768 token 预算。 |
| 回归用例 | v26.1 至 v26.4 合并运行，135 项测试及 278 个子测试全部通过，其中 v26.4 专项 8 项。 |

在仓库根目录使用 OfficeQA Python 环境可复核。第一条运行真实题单只读预检，第二条运行禁网的测试套件。

```sh
python -B scripts/runs/run_v26_4_campaign.py train /tmp/officeqa_v26_4_readonly_preflight \
  --config experiments/configs/v26_4_officeqa_train74.json --validate-only
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam:external/SkillOpt \
  python -m pytest -q -p no:cacheprovider \
  tests/skill_evolution/v26_1 tests/skill_evolution/v26_2 \
  tests/skill_evolution/v26_3 tests/skill_evolution/v26_4
```

合成用例验证提案、归档、预算和恢复路径。真实模型能否减少重复规则，以及最终测试集 EM 和 F1，仍待正式实验测量。[v26.4 专项用例](../../../tests/skill_evolution/v26_4/test_campaign.py) · [定稿设计](README.md)

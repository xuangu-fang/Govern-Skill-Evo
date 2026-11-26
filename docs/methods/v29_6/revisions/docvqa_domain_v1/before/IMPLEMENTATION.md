# v29.6 独立运行实现与离线验收

日期：2026-11-05。独立实现与离线验收已完成。后续正式训练于 01:22（Asia/Shanghai）启动，成功后顺序运行最终 Test；没有定时任务。实时状态见 [status.json](../../../experiments/launches/v29_6_docvqa160_20261105_012220/status.json)，以下验收记录保留离线阶段的事实。

## 1. 实现范围

直接复制 v29.5 的独立模块组织，建立 [v29.6 包](../../../src/skill_evolution/v29_6/)、[独立 CLI](../../../scripts/runs/run_v29_6_campaign.py) 和 [正式配置](../../../experiments/configs/v29_6_docvqa_optimization160.json)。未重构共享组件、Actor、评分器、Gate/Memory 算法或旧版本。

| 接入项 | 实际绑定 |
|---|---|
| 方法 / 阶段 | v29_6_campaign_v1 / v29_6_stages_v1 |
| 运行时 / 最终测试归档 | v29_6_light_runtime_v1 / v29_6_final_test_v1 |
| Diagnosis | v29_6_docvqa_diagnosis_v1；本包 prompts/diagnosis.md |
| Preconditioner | v29_6_docvqa_preconditioner_v1；本包 prompts/preconditioner.md |
| Editor | v29_6_docvqa_editor_v1；本包 prompts/editor.md |
| Replay | v29_6_docvqa_replay_v1；本包 prompts/replay.md |

四份运行 Prompt 与本目录设计稿逐字节一致。Replay 不再加载 v29.2 的旧 Prompt；其结构合同、显式引用及共享输入工具继续复用原代码。运行来源清单记录本地代码、四份本地 Prompt、CLI 与共享依赖，阶段归档也保存实际使用的版本和 Prompt。

函数/类算法与 v29.5 保持一致，资源来源清单仅调整为新 CLI 和四份本地 Prompt。方法配置拒绝旧版本或新旧混合 Prompt 身份；双向跨版本恢复在发出请求前拒绝。

## 2. 参数与初始化

正式配置相对 v29.5 仅有 method.version、method.stage_contract 和四份 Prompt 身份变化，其余逐字段相同。保持 160 题、10×15+10 批次及原顺序、374 题 Test、原初始 Skill 和空 Memory；Actor 与四模块预算均为 32,768，训练/Test 并发 15/60，原超时及六次总请求预算不变。完整表见 [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md)。

离线合成测试使用临时目录、微型数据、手写响应及较小测试预算，不写入正式配置，也不构成真实模型实验。真实数据加载器仅用于配置和 CLI 只读预检查；不会调用 Actor 或模块，不读取 API 凭据，不创建正式 campaign。

## 3. 验收范围与入口

[verify_v29_6_campaign.py](../../../scripts/verification/verify_v29_6_campaign.py) 在禁止网络与子进程的环境中运行 v29—v29.6 必要回归及本版接入检查。覆盖：

- 四份实际加载 Prompt 与设计稿一致，包括 Replay 的本地文件、阶段归档及旧 Prompt 身份拒绝。
- 正式参数逐字段冻结、CLI 训练并发 15、Test 并发 60、只读预检查不读凭据或创建 campaign。
- Original 行为提案 → Preconditioner 补充旧规则处理 → Effective → Editor 的完整文本交接；Goal/ID/basis 冻结、reason 不泄漏到 Editor。
- 逐 Update 映射、多位置修订与删除、混合空 patch、null blocker、全部撤回、无修改和无 hard 翻转分支。
- hard-only Replay、关联覆盖和 null、确定性 Gate、Selected 执行来源、Memory 顺序与原子发布。
- 中断恢复、原始归档复用、验证反馈、请求预算不重置、旧版本隔离与冻结来源校验。

从仓库根目录复现离线验收：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_6_campaign.py --output artifacts/verification/v29_6_implementation_20261105 --baseline artifacts/verification/v29_6_implementation_20261105/baseline.json
```

仅检查正式配置，不创建 campaign：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/runs/run_v29_6_campaign.py train /tmp/v29_6_preflight --config experiments/configs/v29_6_docvqa_optimization160.json --validate-only
```

以上为离线验收和只读预检查命令，不是训练启动命令。训练与 Test 仍需显式分开执行，离线验收阶段没有执行真实运行。

## 4. 记录与结论

验收结果：**844 项全部通过，0 失败、0 错误、0 跳过**。其中 v29 110 项、v29.1 29 项、v29.2 332 项、v29.3 36 项、v29.4 109 项、v29.5 113 项、v29.6 115 项。完整数据集配置与 CLI 只读预检查通过，214 个受保护文件哈希未变，未触发网络或子进程阻断器。

四份设计 Prompt 未修改，Brutus 后续两处修订和已撤回的 Editor 压缩微调均未加入；只读预检查未创建 campaign，验收结束时真实训练与 Test 均未启动。记录位置：

- [validation.json](../../../artifacts/verification/v29_6_implementation_20261105/validation.json)：测试计数、正式配置检查、来源保护及网络/子进程记录。
- [unittest.log](../../../artifacts/verification/v29_6_implementation_20261105/unittest.log)：逐项日志。
- [baseline.json](../../../artifacts/verification/v29_6_implementation_20261105/baseline.json)：实现前冻结的旧版本代码、配置、测试和设计 Prompt 等来源。
- [设计阶段原始记录](../../../artifacts/verification/v29_6_implementation_20261105/design_before_implementation/)：实现前设计文档、source_map、静态检查脚本与报告快照。
- [design_validation.json](design_validation.json)：设计范围、排除补丁及实际绑定的静态复核。

这些检查验证代码接入、合同、选择/持久化和恢复行为。手写模型输出不能证明新 Prompt 会产生合理提案或正确协调旧规则；正式训练与 Test 已完成，结果和比较见 [analysis.json](../../../experiments/analysis/v29_6_docvqa160_20261105_012220_comparison/analysis.json)。本次单次实验不能独立识别各模块改动的因果贡献。

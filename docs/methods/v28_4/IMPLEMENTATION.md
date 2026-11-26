# SearchQA v28.4 独立实现与离线验收

2026-11-04：第 4—5 步独立实现与离线验收已完成。未启动正式训练或 Test。已确认的四份提示词逐字保留；配置除独立版本身份外与冻结的 v28.3 配置一致。

## 正式运行记录

2026-11-04 18:04（Asia/Shanghai），用户另行授权后，已在 SearchQA 环境启动独立正式训练：`v28_4_searchqa600_batch30_20261104_180344`。监督器 PID 72766、训练 PID 72768。完整 20 轮/600 题成功并核验最终 Skill 后，自动运行独立 1,400 题 Test；启动检查时处于 R01 Diagnosis，30 条 Parent stop 执行已归档。配置、预算和 Prompt 未改动，v28.2 仍暂停。

当前状态以 [status.json](../../../experiments/automations/v28_4_searchqa600_batch30_20261104_180344/status.json) 为准；目录、冻结文本和自动 Test 编排见 [launch_plan.json](../../../experiments/automations/v28_4_searchqa600_batch30_20261104_180344/launch_plan.json)。下面的“未启动”表述描述此前独立实现/离线验收阶段，不表示当前训练仍未启动。

## 实现与职责

| 交付 | 位置 |
|---|---|
| 独立运行包 | [src/skill_evolution/v28_4](../../../src/skill_evolution/v28_4/) |
| 独立 CLI | [run_v28_4_campaign.py](../../../scripts/runs/run_v28_4_campaign.py) |
| 可执行配置 | [v28_4_searchqa_train600_batch30.json](../../../experiments/configs/v28_4_searchqa_train600_batch30.json) |
| SearchQA 验收入口 | [verify_v28_4_campaign.py](../../../scripts/verification/verify_v28_4_campaign.py) |
| 专项测试 | [tests/skill_evolution/v28_4](../../../tests/skill_evolution/v28_4/) |
| 修正传递测试 | [test_correction_handoff.py](../../../tests/skill_evolution/v28_4/test_correction_handoff.py) |

运行身份为 `v28_4_campaign_v1`、`v28_4_stages_v1`、`v28_4_light_runtime_v1`。20 个运行 Python 文件在归一化版本身份、忽略模块文档字符串后，AST 与 v28.3 一致；[implementation_audit.json](../../../artifacts/verification/v28_4_implementation_20261104/implementation_audit.json) 记录了算法、配置和 Prompt 核对。独立模块加载本目录四份 Prompt；Diagnosis、Preconditioner、Editor 的决策指导来自已确认设计，Replay 原文不变。没有通过 monkeypatch 让旧链路临时加载新提示词，也没有改动 v28.3 原实现。

本版本保留既有接口和运行算法。Diagnosis 的完整 Original Update 经 Preconditioner 的 KEEP/完整 REPLACE/WITHDRAW 编译后进入 Editor；Editor 只接收 Parent、Goal 与 Effective Update 的 id/text，不能依赖上游 reasons 或 basis 实施修正。原规则修改、合并、替换和删除仍通过同一精确 patch 合同完成，不新增操作字段。

Workflow / Error Avoidance 只存在于自然语言组织建议中，不新增章节、条目数、长度、操作比例的结构校验或重采样条件。合并 Skill 规则不合并 Update IDs；所需配合可在一个 Update 的多个 patch hunks 中完成。

Actor 及 Editor 为 **32,768** tokens，Diagnosis/Preconditioner/Replay 各为 **65,536**。其余模型、超时、六次总请求额度、workers=15、600 题/20×30 批次、1,400 题独立 Test、原始空白规则占位 Skill 及空 Memory 保持不变。完整 task.question/context 与 Actor 原始 user message 保留，通用三项去重及 Replay 同题共享保留。

## 验收口径

报告：[validation.json](../../../artifacts/verification/v28_4_implementation_20261104/validation.json)；逐项日志：[unittest.log](../../../artifacts/verification/v28_4_implementation_20261104/unittest.log)。**537 项全部通过，失败/错误/跳过均为 0**：v28 133 项、v28.1 23 项、v28.2 118 项、v28.3 129 项、v28.4 134 项。正式配置只读预检查通过，未发生网络/子进程或 DocVQA/Pillow 导入尝试。

验收仅包含 SearchQA v28、v28.1、v28.2、v28.3 回归及 v28.4 专项。测试在 SearchQA Python 环境运行，网络连接与子进程创建被阻断，DocVQA/Pillow 导入被拒绝。两个仍位于 v29_2 包内的通用文本引用解析函数不加载 DocVQA benchmark、图片、数据或模型，不构成 DocVQA 验收依赖。

离线执行使用临时目录中的合成任务、伪 Actor transport 和手写方法响应。测试中合成的 600 题训练/1,400 题 Test 只验证调度、隔离、评分与恢复流程，**不是正式数据集的模型运行**。正式 600 题配置只通过只读 `--validate-only` 预检查，不读取凭据、不创建 campaign、不调用模型。

覆盖范围：

- 新增、改写、合并、替换、删除沿同一 Original→Effective→Editor 合同传递；旧规则处理与必要条件在 text 中完整保留，reasons/basis 不泄漏给 Editor。
- 多 Update 各自映射到原 Parent，允许共享只读 context，选中子集准确重组；规则合并不合并 IDs。
- no_change、全 WITHDRAW、Editor 空串与 null 的分支区别；不因合法语义决定重采样。
- 全批直接事实、引用权限、普通回答可见性、无 Grouping、SearchQA 原生浮点 EM/F1、无损共享视图。
- patch 定位/冲突、EM 翻转 Replay、未归因事件、混合 G/L Defer、Selected Skill 执行来源、Memory 原子提交及轻量恢复。
- 请求开始/结束、响应保存、技术/length/解析失败、六次总额度及耗尽后恢复、HEAD/游标错位及幂等发布。
- v28.3/v28.4 双向恢复拒绝、配置/Prompt/检查点漂移拒绝、预算冻结、无新的 schema 字段或组织硬约束。

## 复现离线验收

以下命令仅运行离线验收，不启动正式训练或 Test：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/SearchQA/bin/python -B scripts/verification/verify_v28_4_campaign.py --output artifacts/verification/v28_4_implementation_20261104 --baseline artifacts/verification/v28_4_implementation_20261104/baseline.json
```

仅只读检查正式配置：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/SearchQA/bin/python -B scripts/runs/run_v28_4_campaign.py train /tmp/v28_4_preflight_not_created --config experiments/configs/v28_4_searchqa_train600_batch30.json --validate-only
```

必须保留 `--validate-only` 才是配置预检查。正式 train/test 仍是独立显式入口，训练完成不会自行启动 Test；今后另行授权的监督器可在训练成功后调用 Test。本次未创建正式实验或定时任务，也未恢复 v28.2。

## 原版本保护与保证边界

设计阶段文件完整保存在 [design_before](../../../artifacts/verification/v28_4_implementation_20261104/design_before/)。原 [design_validation.json](design_validation.json) 是第 1—3 步当时的静态检查记录，保留历史状态；本次运行验收以 implementation 报告为准。

最终保护核对确认 264 个旧版代码、配置和文档文件逐字未变（其中验收入口直接比对 263 个，其余旧版验收脚本在最终核对中一并比对）；v28.3 训练/Test/控制目录及 v28.2 暂停训练/控制目录共 27,723 个文件的清单、大小与纳秒修改时间未变。后者是目录与元数据核对，不声称逐文件内容哈希审计。暂停 PID 30019、30020 在外部只读核验，仍为 Ts/T，不发送继续或终止信号。最终核对见 [preservation.json](../../../artifacts/verification/v28_4_implementation_20261104/preservation.json)。

离线通过证明已覆盖的合同、接线、配置与恢复行为；不能证明模型会正确选择修正方式、忠实理解全部例外或提高最终成功率。手写响应测试不会自动判断自然语言策略是否合理，也不新增语义判官。真实 Prompt 决策质量和泛化效果仍需后续正式实验评价。

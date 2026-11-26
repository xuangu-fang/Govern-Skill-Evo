# v28.3 独立实现与离线验收

2026-11-04：独立 SearchQA v28.3 链路的实现、离线验收及正式训练/Test 均已完成。用户在授权实现时将 Editor max_tokens 调整为 **32,768**，Diagnosis/Preconditioner/Replay 仍为 65,536；其他已确认参数不变。四份已审阅 Prompt 原文保持不变。

正式实验 `v28_3_searchqa600_batch30_20261104_022828` 已完成 600 题、20 轮训练，状态为 complete，Memory HEAD 为 000020，见 [training_summary.json](../../../experiments/campaigns/v28_3_searchqa600_batch30_20261104_022828/training_summary.json)。后续独立 Test 已完成 1,400 题，答对 1,187 题，EM 为 0.8478571428571429，F1 为 0.9148350340136054，见 [summary.json](../../../experiments/evaluations/v28_3_searchqa600_batch30_20261104_022828_test1400/summary.json)。R20 selected.md、训练导出的 final_skill.md 与 Test 的 skill.md 逐字一致。训练汇总中的 test_started=false 仅表示训练入口不自动启动 Test；Test 完成状态以独立测试归档为准。

当前 26 个运行代码、CLI、配置和 Prompt 文件与实验启动前快照逐字一致；配置、运行身份及四份 Prompt 与正式实验归档一致。当前保留通用执行信息去重，question/context 保持完整文本，不使用 SearchQA 字符范围引用。以下离线验收及口径修正记录描述实现阶段的检查，不代表正式实验尚未执行。

## 实现入口与来源

| 部分 | 实现 |
|---|---|
| 独立包 | [src/skill_evolution/v28_3](../../../src/skill_evolution/v28_3/) |
| CLI | [run_v28_3_campaign.py](../../../scripts/runs/run_v28_3_campaign.py) |
| 冻结配置 | [v28_3_searchqa_train600_batch30.json](../../../experiments/configs/v28_3_searchqa_train600_batch30.json) |
| 直接事实入口 | [facts.py](../../../src/skill_evolution/v28_3/facts.py) |
| Diagnosis/Preconditioner | [diagnosis.py](../../../src/skill_evolution/v28_3/diagnosis.py)、[preconditioner.py](../../../src/skill_evolution/v28_3/preconditioner.py) |
| 轮次与恢复 | [evolution.py](../../../src/skill_evolution/v28_3/evolution.py)、[memory.py](../../../src/skill_evolution/v28_3/memory.py) |
| 离线验收入口 | [verify_v28_3_campaign.py](../../../scripts/verification/verify_v28_3_campaign.py) |

Diagnosis 的直接事实和来源合同采用 v29.4，替换为 SearchQA 原始执行验证器、Actor 协议和本目录 Prompt；不经过任何旧 Grouping 交接。Preconditioner 继续扫描完整 Plan 的合法直接引用，reason 不作为运行证据筛选入口。旧 Group 来源在输入、basis、reason 和 REPLACE text 中被拒绝。

SearchQA 的请求日志、原始文本、浮点 EM、F1、重试和 Actor I/O 保持原有行为；Editor/Replay/Gate 采用独立接线副本，以便逐层验证新的上游来源。算法定义通过版本名称归一化后的 AST 比较；不使用全局 monkeypatch 绑定旧方法。

运行身份为 `v28_3_campaign_v1` / `v28_3_stages_v1` / `v28_3_light_runtime_v1`。配置、Prompt 原文和版本不符时拒绝请求或恢复，不能把 v28.2 的响应、Memory 或 Skill 重标记成本版本。新轮清理当前执行注册表，仅注册本轮 Actor 归档；历史只通过 Memory 视图进入 Preconditioner。

Memory 保留顺序提交 ID 和原文/结构比较。当前提交重新校验已完成来源和待发布原文；加载已提交历史只检查提交链、结构、ID 和选择一致性，不重新读取历史 Actor 来源。HEAD 与 campaign 游标错开时复用当前轮保存结果完成发布，不重置请求额度。常规加载不提供历史原始文件逐项篡改检测保证。

## 验收范围与结果

正式验收报告：[validation.json](../../../artifacts/verification/v28_3_implementation_20261104/validation.json)；逐项日志：[unittest.log](../../../artifacts/verification/v28_3_implementation_20261104/unittest.log)。报告和日志由 SearchQA 验收入口直接生成。

必需验收仅包含 **SearchQA 403 项**：v28 133 项、v28.1 23 项、v28.2 118 项、v28.3 129 项；失败、错误、跳过均为 0。四份已审阅 Prompt 原文一致；全量 600 题配置只读预检查通过。DocVQA 回归不计入总数、不决定通过与否，也不要求 DocVQA 环境、数据或 Pillow。

验收范围为 SearchQA 旧链路回归和 v28.3 专项。网络连接与子进程创建在测试进程内被阻断；调用使用临时目录中的合成任务、伪 Actor transport 和手写方法响应。合成 Test 入口测试只验证完成度、隔离与恢复，不是对真实 1,400 题运行模型。

专项范围包括：

- 完整成功/失败批次直接进入 Diagnosis、单案例多提案、Group 引用拒绝、Plan 引用与 reason 的传递边界、context/Skill/评分/来源篡改拒绝。
- 四阶段接线、逐 Update patch、字符范围组合、空 patch/null、F1-only 不投票、无法归因事件、混合 G/L Defer、子集 Selected Skill 不继承 Candidate 分数。
- no_change/全部撤回/无翻转分支、追加 Memory、顺序 ID、当前来源校验、轻量历史加载和新轮注册表范围。
- 请求开始前/后、响应保存、技术/length/输出错误、六次总额度、耗尽后恢复、语义停止、HEAD 与游标发布边界、幂等提交。
- 旧版本及混合配置拒绝、原文 Prompt 冻结、Editor 32,768、其他预算不变、全量 SearchQA 配置只读预检查。

正式 600 题配置的 `--validate-only` 在不读取凭据、不创建 campaign、不调用 Actor/方法模型的条件下验证数据 ID、顺序、批次和参数。验收还逐字比较原快照中的 SearchQA 旧源文件、配置及 v28.2 暂停控制文件，并核对四份 Prompt 与设计阶段原文完全相同。原快照中其他 benchmark 的文件不参与通过判定；两个实际复用的通用引用解析文件仍受保护，虽然位于 v29_2 包内，它们不加载 DocVQA benchmark、图片或数据。v29.4 的方法来源记录也不构成运行或验收依赖。

## 复现离线验收

以下只执行离线验收，不启动正式训练或 Test：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/SearchQA/bin/python scripts/verification/verify_v28_3_campaign.py --output artifacts/verification/v28_3_implementation_20261104 --baseline artifacts/verification/v28_3_implementation_20261104/baseline.json
```

仅检查完整 SearchQA 配置的命令：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/SearchQA/bin/python scripts/runs/run_v28_3_campaign.py train /tmp/v28_3_preflight_not_created --config experiments/configs/v28_3_searchqa_train600_batch30.json --validate-only
```

命令含 `--validate-only` 时不会创建该 campaign 或读取 `.env`。复现离线预检查时应保留该参数；重新启动正式实验需另行授权。train 完成不会自动启动 Test，Test 使用独立显式命令和目录。

此前额外执行的 DocVQA 109 项回归及首次混合环境失败日志仅作为历史记录保存，不是本版本的必需验收。原 512 项汇总已归档至 [history](../../../artifacts/verification/v28_3_implementation_20261104/history/combined_validation_before_scope_correction.json)，由当前 SearchQA 403 项报告取代；不得据此要求安装 Pillow 或运行 DocVQA。此次只修正验收脚本、文档和报告，配置、Prompt 和运行实现保持不变。

实现阶段口径修正的附加检查见 [scope_correction.json](../../../artifacts/verification/v28_3_implementation_20261104/scope_correction.json)：26 个运行代码、CLI、配置和 Prompt 文件逐字不变；拒绝 DocVQA suite；禁止导入 DocVQA/Pillow 时 SearchQA 预检查通过；检查当时 v28.2 进程仍暂停，尚未创建 v28.3 正式实验目录。该报告保留当时状态，不覆盖后续已完成的训练/Test。这些检查不计入 403 项单元测试数量。

## 设计与实际保证

设计阶段原文及静态报告保存在 [design_before](../../../artifacts/verification/v28_3_implementation_20261104/design_before/)。Editor 16,384 是该历史设计的值，当前已按用户指令设置为 32,768；历史快照不改写。当前设计稿、来源映射、运行配置和校验器使用新值。

离线通过只能证明合同、配置、接线和已覆盖恢复行为，不能证明 Prompt 的真实决策质量、归因真实性或测试成功率提升。联合 Candidate 不隔离单条 Update 的因果效果，重组 Selected Skill 也不一定已在本轮执行；这些方法边界保持原设计。

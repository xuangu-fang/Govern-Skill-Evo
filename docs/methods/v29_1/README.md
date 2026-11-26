# v29.1：Diagnosis / Preconditioner 局部 Prompt 修订

确认日期：2026-11-03（Asia/Shanghai）。135 项离线测试全部通过（原 v29 108 项＋v29.1 27 项）。用户随后授权正式训练、训练完成后自动 Test，以及训练/Test 共用最多三次原配置外层恢复；正式训练已于 2026-11-03 01:25（Asia/Shanghai）启动。实时状态见 [监督记录](../../../experiments/comparisons/v29_1_docvqa160_epoch1_20261103_001/v29_1_status.json)，策略见 [监督说明](../../../experiments/comparisons/v29_1_docvqa160_epoch1_20261103_001/README.md)。

按用户要求保留原 v29 的 Prompt、默认版本、算法和历史运行。原 Diagnosis 和 Preconditioner 已恢复修改前原文，与 v29 历史设计稿一致；原测试无需放宽。已确认的新文本独立保存为 v29.1，使用独立版本标识、配置和输出目录，不能覆盖或恢复到已有 v29 运行中。

## 设计资源

- [Diagnosis](prompts/diagnosis.md)：区分答案选择、答案范围和范围内转写，要求说明相对 Parent/base 的具体行为增量；偏好集中且有依据的修改，必要的联合修改仍可保留；优先修订或整合相关旧指导。
- [Preconditioner](prompts/preconditioner.md)：按行为机制比较相关历史，让未改善与回退影响 KEEP、修改或撤回；处理联合修改中的局部收益与回退；协调条件必须进入最终 Update。
- [Diagnosis 差异](diagnosis.diff)和 [Preconditioner 差异](preconditioner.diff)：相对于恢复后的 v29 原文，展示实际替换与合并的段落。

这些文件同时是 v29.1 的实际运行资源，不再复制一份易产生漂移的运行文本。独立入口为 [run_v29_1_campaign.py](../../../scripts/runs/run_v29_1_campaign.py)，配置为 [v29_1_docvqa_optimization160.json](../../../experiments/configs/v29_1_docvqa_optimization160.json)，适配器为 [campaign.py](../../../src/skill_evolution/v29_1/campaign.py)。现有 `scripts/runs/run_v29_campaign.py` 默认仍运行原 v29，不会自动加载本目录。

## 运行接线

- 方法版本为 `v29_1_campaign_v1`；Diagnosis / Preconditioner 分别使用 `v29_1_docvqa_diagnosis_v1`、`v29_1_docvqa_preconditioner_v1`。另三个模块保持原版本和原文。
- 复用 v29 训练与 Test 函数、Actor、阶段执行和恢复代码。共享配置校验、Prompt 渲染、阶段身份记录及 CLI 增加适配器选择接线；没有复制学习流程或使用进程全局 monkeypatch 切换版本。
- 配置与当前适配器的版本必须一致。CLI 在读取凭据或发送请求前校验全部五份 Prompt；阶段记录保存实际 Prompt 版本和完整消息。恢复时检查原配置、阶段身份和消息，拒绝跨版本恢复。
- 原正式配置与已完成 v29 基线配置一致。新配置仅改变方法版本及两个 Prompt 版本；其余参数、160 题顺序、初始 Skill 和空 Memory 初始化保持一致。
- Actor 预算 32,768；Grouping / Editor 为 16,384；Diagnosis / Preconditioner / Replay 为 32,768；超时均为 300 秒，Train / Test 并发为 15 / 60。保持 10×15＋1×10 单遍训练和完成后独立评估 374 题。

共享代码接线及新增入口的审查差异见 [runtime_wiring.diff](runtime_wiring.diff)。原 v29 Prompt、配置和历史归档未修改；共享运行器的兼容接线由原 108 项测试回归覆盖。

以下命令均在仓库根目录执行。只读预检查不读取凭据、不创建训练目录：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/runs/run_v29_1_campaign.py train experiments/campaigns/v29_1_docvqa160_epoch1_20261103_001 --validate-only
```

正式训练命令（已由监督器启动，勿重复执行）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/runs/run_v29_1_campaign.py train experiments/campaigns/v29_1_docvqa160_epoch1_20261103_001
```

训练全部完成后，监督器将使用最终保留 Skill 自动启动独立评估：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/runs/run_v29_1_campaign.py test experiments/campaigns/v29_1_docvqa160_epoch1_20261103_001 --output experiments/evaluations/v29_1_docvqa160_epoch1_20261103_001
```

已有运行恢复时，在对应命令后加 `--resume`；新运行不加。正式入口不会自动启动 Test，不继承 v29 最终 Skill、Memory 或执行缓存。

## 版本边界

仅改变两个模块的决策指导。Grouping、Editor、Replay、Actor、评分、Gate、Memory、阶段顺序、重试恢复及预算沿用 v29；版本接线不改变它们的行为或 Prompt 资源。

Diagnosis 的输入、`decision/reason/plan`、Update 的 `id/text/basis` 及 Checks 合同保持不变。Preconditioner 保持原输入、D/S/C、`adjustments/checks`、KEEP / 精确 patch / 撤回及引用合同；不新增或拆并 Update ID，不从历史中另起无关修复任务。

集中修改是偏好，不是固定 Update 数量或逐条隔离因果的要求。缺少相关历史时，可以依据当前证据 KEEP；不强制修改或撤回，不要求事先证明因果。图片不可见及 Actor 转述的证据边界保持不变。成功例和反例通过已有 basis 传递，不扩展输入。

## 与基线的关系

主基线为已完成的 `experiments/campaigns/v29_docvqa160_epoch1_20261102_184845/` 及对应 `experiments/evaluations/v29_docvqa160_epoch1_20261102_184845/`。本次未改写运行配置、最终 Skill、Memory 或训练/Test 归档。

v29.1 的待验证假设是改善提案质量、历史利用和规则协调；尚无新版本效果结果。它不解决单批执行波动，也不保证补回原 Test 与 SkillAdam 的三题差距。

## 离线验收

设计隔离阶段的原 20 项方法测试已通过。运行接线验收由 [verify_v29_1_campaign.py](../../../scripts/verification/verify_v29_1_campaign.py) 执行，覆盖原 v29 全套离线回归和 [v29.1 专项测试](../../../tests/skill_evolution/v29_1/test_offline.py)，结果保存在 [validation.json](../../../artifacts/verification/v29_1_runtime_20261103/validation.json) 和 [unittest.log](../../../artifacts/verification/v29_1_runtime_20261103/unittest.log)。

离线验收阶段结果：135 项通过，0 失败、0 错误、0 跳过；网络/子进程尝试和真实模型调用均为 0。独立 CLI 的只读预检查也已通过，使用不存在的 env 文件验证不读取凭据；验收阶段没有创建正式训练或评估目录。后续真实运行状态独立记录，不由离线报告代替。

验收禁用网络和子进程；Actor 和优化器均使用合成响应。覆盖 ACCEPT / RETAIN、三类 no_change、语义停止、六次额度、14 个阶段/发布边界恢复、保存响应恢复、冷启动检查、实际新 Prompt 和版本记录、跨版本拒绝、独立 CLI Train / Test / resume，以及合成 160 题训练＋374 题 Test。原 v29 历史 Prompt 全文一致性断言保留。另静态检查真实 534 题、439 张图片和正式配置；真实题目不发送给模型。

复现命令：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_1_campaign.py --output artifacts/verification/v29_1_runtime_20261103
```

这些检查证明版本接线及程序合同可用，不证明新 Prompt 的提案质量或真实测试成功率已经提高。

## 2026-11-04 共享运行器修复

v29.1 通过共享 v29 引擎同步获得轻量运行检查：删除全历史逐轮重放和文件/图片快照审计，保留当前轮校验、游标与 Active 一致性、原子发布、幂等提交及断点恢复；不设置独立深度审计入口。历史 Prompt、配置、训练与 Test 结果不变。执行边界和离线验收见 [v29 运行说明](../../../src/skill_evolution/v29/README.md#2026-11-04-运行检查简化)。

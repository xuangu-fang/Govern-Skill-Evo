# 最终目录分工与文档归并

日期：2026-10-12。本次完成剩余 benchmark 源码迁移、数据与运行材料分离、依赖更新和专题文档归并。没有新增旧路径入口或软链接。

## 查找材料

| 要找的内容 | 目录 |
|---|---|
| 环境、评测器、可复用实现 | `src/benchmark_governed/v1–v3/`、`src/benchmark_v1/` 至 `benchmark_v5/`、`src/benchmark_shared/` |
| 构建、校准和审计命令 | `scripts/benchmarks/` |
| 自动化测试 | `tests/benchmarks/` |
| 任务、划分、规则、模板和版本定义 | `benchmarks/<series>/editions/<edition>/` |
| 实验配置、清单、精选结果与审计报告 | `experiments/benchmarks/tau2/<edition>/`、`experiments/benchmarks/v5/` |
| 完整调用、轨迹、数据库及运行输出 | `artifacts/benchmarks/`，由 Git 忽略 |
| 设计、协议和结论 | `docs/benchmarks/`、`docs/methods/` |

Governed V1–V3 与 Phase V1–V4 是两条不同谱系；独立 V5 也保留其定义身份。源码中版本号相同，不表示可以混用同一套任务。

## 本次改动

- 288 个实现、脚本及测试文件从 benchmark 数据目录移出；删除 3 个仅有说明文字的包标识文件。
- 原始运行材料共 5395 个文件移入 artifacts，以迁移前后 SHA256 验证原字节不变。725 个配置、精选结果和报告文件分开保留。
- 更新 Python 导入、路径常量、启动命令、文档链接和受影响的源码指纹。只读历史材料中的文件身份使用现有路径映射定位；没有恢复旧文件入口。
- 90 份 V5、V18–V21 文档按主题合并为 30 份，章节保留原协议和结论的阶段边界。原文可在迁移快照中核对。
- 总文档索引缩短；原有阶段叙述保留在 [进展记录](../PROGRESS_HISTORY.md)。两份实验日志原样保留。
- `.gitignore` 统一忽略 artifacts；精选结果 JSON 继续保留，不按扩展名全部排除。

## 验收入口

```sh
python3 scripts/maintenance/verify_final_layout.py
python3 scripts/maintenance/verify_code_layout.py
python3 scripts/maintenance/verify_canonical_paths.py
python3 -m scripts.benchmarks.validate_editions
```

迁移收据：[final-migration.json](final-migration.json)。原文件快照：[final-layout-20261012.zip](../archive/final-layout-20261012.zip)。此前阶段的收据和快照保留，校验器按最新迁移映射检查当前文件。

运行验证不调用实验模型，也不覆盖已有运行结果。整理阶段曾发现 V4 离线集成脚本误用旧联合实验入口，导致 `toolkit_factory` 参数错误；后续已修复并重新验收，见下方记录。

早期 Phase V1 的全仓库历史冻结检查在本次整理前就有 211 个摘要不一致。已保留原始 `source_preservation.json`，将当前构建改为本次运行前后比较，结果另写 `source_preservation_current.json`。测试验证当前构建的产出不会误报，同时外部输入的修改或删除仍会被发现；不再要求项目永久匹配过期快照。

## 验证结果

- 首轮相关套件：1621 项通过，13 项失败；逐项修复目录迁移问题、同步源码摘要，并替换过期的永久冻结断言。
- 复验 benchmark、τ² oracle 与 V20 后端：286 项通过、174 个子测试通过；旧冻结用例当次排除后单独修正并复验。
- 最后单独复验 Phase V1 构建保护与 V20 后端：11 项通过、54 个子测试通过。受影响的 V14 测试另有 7 项通过。
- 八个 benchmark edition 的任务检查通过；44 份任务、划分和版本文件摘要不变。
- V3 开发版和正式版离线集成通过，V18/V20 无模型预检通过。该阶段尚未修复的 V4 参数错误已在下方后续验收中解决。
- 5395 份迁移运行文件 SHA256 全部一致，全部匹配 Git 忽略规则；两份实验日志摘要不变；项目软链接为 0；活动 Markdown 本地文件链接无缺失。

上述为分批验证结果，不表示已重跑全部历史实验或整个仓库的所有环境。

## 后续：V4 修复与关键入口离线验收

V4 验收脚本原来导入旧的 `joint_gate.evaluator`，与正式 V18/V4 运行器不一致。现在统一使用既有的 `joint_gate.v4_evaluator`，保留定制工具重放、规则判断与评分语义。新增真实八任务集成回归，以及 `--output` 参数，方便将本次报告写到独立目录。同步更新四份受影响的当前配置/源码绑定清单，没有改写旧轨迹或实验日志。

| 验收范围 | 结果 |
|---|---|
| Governed V1–V3、Phase V1–V4 的八个 edition | 任务、身份与划分检查通过；加载与构建相关测试通过 |
| V3 开发版 | 32/32 oracle 路径通过 |
| V3 正式版 | 64/64 Core、9/9 控制路径、10/10 回归与 9/9 E0 检查通过 |
| V4 | 81 个任务结构检查、36/45 划分及 8/8 JRA 联合任务 CS 通过 |
| 方法 V18/V4 | 无模型预检通过，36 个 Evolution、45 个 Monitor 任务 |
| 方法 V20 | 无模型预检通过，108 个 Evolution、135 个 Monitor 准备实例 |
| V5 历史记录 | 216 条事件轨迹重放、原评分复核通过；808 个 V5 文件摘要不变 |
| 相关回归 | 357 项测试和 174 个子测试通过；另有 8 项 V21 执行身份测试通过 |

V5 覆盖首轮校准 72 条、预算诊断 18 条、决策探测 15 条、学习实验 40 条、接口修订 4 条、S-C 工程闭环 10 条、S-A 离线轨迹 57 条。原先失败而未执行的四个学习条件保留为未执行。此次验证的是当前代码对历史事件与保存评分的重放一致性，不宣称旧源码指纹与当前源码相同，也不将工程结果升级为正式学习效果。

验收进程禁用网络，没有模型调用。已有实验结果保持原样；V3 的输出报告被重定向到新目录，V4 和 V20 使用独立输出参数。

本机完整验收输出与复跑脚本：[v4-offline-20261012-152335](../../artifacts/validation/v4-offline-20261012-152335/)。该目录由 Git 忽略，克隆仓库后不一定存在。

V4 可从项目根目录离线复验（使用安装了 τ² 依赖的 Python 环境）：

```sh
PYTHONPATH=.:src:external/tau2-bench/src python -m scripts.benchmarks.v4.validate_integration --output artifacts/validation/v4-check/integration.json
```

此次 V4 修复针对验收入口；独立历史联合实验入口没有被统一改写。上述通过范围也不等于全部历史运行脚本已经逐一执行。

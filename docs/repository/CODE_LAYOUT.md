# 第五步：源码、命令和测试归类

日期：2026-10-12。本阶段累计移动 689 个既有文件：187 个方法源码文件、42 个 V5 源码文件、132 个 V3/V4 与共享源码文件、175 个脚本、153 个测试与样例文件。直接更新导入、文件路径、模块启动命令和导航，没有增加旧入口包装文件、模块别名或软链接。

## 目录与归属

| 内容 | 新归属 | 导航 |
| --- | --- | --- |
| 方法专属实现 | `src/skill_evolution/vXX/` | [方法源码](../../src/skill_evolution/README.md) |
| 通用经验、决策、门控和路径工具 | `src/skill_evolution/shared/` | [共享代码](../../src/skill_evolution/shared) |
| 实验启动与预检 | `scripts/runs/vXX/` | [命令入口](../../scripts/README.md) |
| 分析、准备、历史迁移、仓库维护 | `scripts/analysis/`、`preparation/`、`migrations/`、`maintenance/` | [命令入口](../../scripts/README.md) |
| 方法测试 | `tests/skill_evolution/vXX/`、`shared/` | [测试导航](../../tests/README.md) |
| Benchmark V4/V5 测试 | `tests/benchmarks/v4/`、`v5/` | [Benchmark 测试](../../tests/benchmarks) |
| Benchmark V3/V4 与共享实现 | `src/benchmark_v3/`、`benchmark_v4/`、`benchmark_shared/` | [源码导航](../../src/README.md) |
| Benchmark V5 实现 | `src/benchmark_v5/` 下的功能子包 | [V5 源码](../../src/benchmark_v5/README.md) |
| Learner 测试 | `tests/learners/stwebagentbench/` | [Learner 测试](../../tests/learners/stwebagentbench) |

只为实际实现创建版本目录。跨版本复用直接导入所属版本；不复制实现，也不将版本专属逻辑一律归到 shared。Benchmark 自身的构建和环境实现仍属于对应 benchmark。

V5 原来分散的六组测试收拢为 `v5/` 下的 calibration、learning、probe、sa、sc、prototypes。测试子包有独立包标识，同名测试文件可一起运行；五份 V19 固定样例随测试迁移，内容保持一致。

补充收拢 V5 源码：calibration、learning、probe、sa、sc 全部放进 `src/benchmark_v5/`，基础环境仍在包根目录。同步更新 Python 导入、模块启动命令、源码清单和 SA 项目根目录计算，移除五个旧的平铺包目录。

## 运行入口

保留 `scripts/run_method.py` 作为常用运行器选择入口，内部直接调用新位置。例如：

```sh
python scripts/run_method.py v19 --run-id example --stage pilot --print-command
python scripts/runs/v20/run_v20.py --help
python scripts/runs/v18/run_v18_formal_v4.py
python -m pytest tests/skill_evolution/v19 -q
python -m pytest tests/benchmarks/v5 -q
```

最后一个运行器命令默认只做 V18 预检，不执行模型实验。正式运行、准备、恢复脚本保留既有参数和执行条件。

## 改动边界

- 更新绝对及相对 Python 导入、动态源码路径、项目根目录计算、测试样例位置、运行命令和 Markdown 链接。
- 源码指纹扫描改为读取版本目录或递归读取源码，避免迁移后遗漏文件；递归扫描使用相对路径作为键，避免同名包标识互相覆盖。
- 更新受影响的源码与配置指纹，保留对真实源码漂移的校验。新包标识也纳入正式实验的源码清单。
- 历史记录中的旧文件身份由既有路径工具定位到新文件，不创建旧文件或链接。原始运行记录、轨迹、两份实验日志均保持不变。
- 本次不合并算法实现、不修改模型设置、不重跑付费实验。文档内容去重与合并留待第六步。

## 验证结果

- 主测试集：2,318 通过、6 个既有失败；V06 在 ST-WebAgentBench 环境单独运行：43 通过、6 个既有失败。共 2,361 项通过，另有 120 项子测试通过；失败清单与整理前一致。
- 修复动态源码路径后，V19 恢复与迁移的 15 项回归测试通过（包含在上述测试集中，不重复计数）。
- 静态核对 1,169 个 Python 文件，内部模块导入均可定位；活动文件中没有本次迁移遗留的旧模块或文件路径。
- 六项目录整理校验通过，项目兼容软链接为 0；旧文件入口及已迁空的目录均不再存在。
- V18/V20 正常预检通过，模型调用为 0；常用运行器帮助命令和 `run_method.py` 的目标脚本定位通过。
- 132,312 个既有原始文件的大小和修改时间未变化；五份迁移的测试样例逐字节一致，两份实验日志未修改。
- V5 源码收拢后单独重跑：124 项测试和 120 项子测试通过；六个模块的帮助入口正常，SA 根目录定位正确。校准清单原有的三处指纹不匹配仍保留（基础 core、校准协议、校准 runner），没有新增不匹配；本次未重跑上述完整方法测试集。

既有失败仍涉及 V02/V03 状态、V06 恢复、V14 历史源码指纹及合规提示词断言。本次没有更改断言以消除这些失败。

## V3/V4 源码补充归位

Phase V3 的 Day 34 开发版、Day 35 正式版、final_candidate 构造实现以及 Phase V4 已拆分源码和数据。本轮共迁移 237 个文件：132 个实现文件、104 个执行脚本、1 个测试文件。

- [V3 源码](../../src/benchmark_v3/README.md)分为 development、final 和 construction；V4 直接复用这些模块，不复制实现。
- [V4 源码](../../src/benchmark_v4/README.md)提供环境注册与 JRA-01 实现。
- [共享源码](../../src/benchmark_shared/README.md)保存跨版本基础设施，模板与示例仍位于 benchmark 数据目录。
- 脚本位于 `scripts/benchmarks/v3/`、`v4/`；edition 结构检查入口为 `python -m scripts.benchmarks.validate_editions`。
- 更新直接导入、相对导入、模块命令、动态脚本路径及源码清单。603 个可静态求值的路径常量与迁移前逐项对照，均指向原数据或新源码位置。
- 本轮没有迁移早期 Governed/Phase V1/V2 的专属实现；其中对共享模块的调用已更新。30 个任务定义及版本文件逐字节不变，两份实验日志和原始运行数据保持不变。

迁移前相关测试为 1,504 通过、120 子测试通过。迁移过程中五项 V19 预检发现源码清单尚未同步；更新清单后，覆盖这些用例的 606 项相关测试全部通过，其余 1,499 项已在迁移后通过。V18/V20 正常预检均通过，未调用模型。V3 两个阶段的离线报告与迁移前 JSON 内容一致，八个 edition 的任务和划分检查通过。

V4 独立 `validate_integration` 原有的 `evaluate_trace(..., toolkit_factory=...)` 参数不匹配，在迁移前后均可复现。本轮保留这一既有评测接口问题，没有修改评分规则。

本轮详细核对记录见 [本地验证材料](../../artifacts/repository_inventory/code-layout-20261012/benchmark-v3-v4-validation.json)。

## 核对材料

- [逐文件迁移和修改清单](code-migration.json)
- [修改前快照](../archive/code-layout-20261012.zip)
- [本地验证记录](../../artifacts/repository_inventory/code-layout-20261012/validation.json)（忽略的本地产物）

```sh
python scripts/maintenance/verify_code_layout.py
python scripts/maintenance/verify_canonical_paths.py
```

这些校验用于核对本次整理，后续有意改动代码时应同步维护记录，不要求代码永久保持不变。

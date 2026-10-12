# 第 4 步：统一原始运行产物

> 这是前序步骤的历史记录。兼容链接现已删除，当前状态见 [直接路径整理记录](CANONICAL_PATHS.md)。

执行日期：2026-10-12。[统一运行入口](../../experiments/methods/RUNTIME.md) · [方法实验](../../experiments/methods/README.md)。

## 实际迁移

119 组运行材料、129,685 个常规文件（其中 11 个历史导航文件、9 个精选 Skill 文件），迁移前约 10.8 GB；另有 2 个已有报告链接随目录迁移并调整相对目标。采用同磁盘重命名，不复制原始轨迹，不修改实验 JSON、模型输出、冻结配置和历史身份。

| 原位置 | 当前实体位置 |
|---|---|
| `artifacts/methods/v01/autonomous_gse_v01` 至 v14 的各运行 | `artifacts/methods/<版本>/<原运行ID>/` |
| V14 Phase-A 的四个 attempt | `artifacts/methods/v14/phase_a_unified_v14_step1_pilot/` |
| V15/V16 内嵌 benchmark 的 `run/` | `artifacts/methods/v15/benchmark_v2_v15_pilot_001/`、`v16/benchmark_v16_one_step_001/` |
| `artifacts/methods/v17`、`v18`、`v19` | `artifacts/methods/<版本>/`，保留 pilot/formal/archive 分类 |
| `experiments/archive/<版本>` | `artifacts/methods/<版本>/archive/legacy/`，不覆盖原有归档 |
| `artifacts/v18_*` 至 `v21_*` 及关联锁、日志、运行辅助材料 | `artifacts/methods/<版本>/<原名称>` |
| 旧版本 INDEX、阶段 README、此前 path-map | `experiments/methods/<版本>/runtime-history/`，继续可版本管理 |

前一步已经提取的配置、精选结果、独立报告继续位于对应方法实验目录。此次将 V15/V16 的 9 个可版本管理的 Parent/Candidate/最终 Skill 移入各自实验的 `results/skills/`；原运行位置通过相对链接复用同一份文件。原本跟踪的导航文件单独移入 `runtime-history/`。没有根据文件名把每个自动生成的 report/summary 都提升为研究结论。

V15/V16 的共享 Python 实现仍在原模块位置；只有运行数据迁移。benchmark 构建产物、ST-Web POC、早期基线和仓库审计材料不是这些方法运行，未强行归入某个方法版本。两份实验日志保持原字节。

## 兼容与新输出

149 个相对兼容链接维持冻结代码、历史记录及旧导航的读取关系，其中 10 个更早的平铺入口仍被现有代码或冻结输入引用；其余此前已不存在的旧入口只登记路径映射，不新增链接。旧 `artifacts/methods/v17/v18/v19` 是链接，实体材料只存在于 `artifacts/methods/`。完整清单见 [runtime-path-map.json](../../experiments/methods/runtime-path-map.json)。链接不是数据副本，仍有依赖时不能删除。

原有运行实现、启动脚本和 JSON 全部保持原始字节。新增 [run_method.py](../../scripts/run_method.py)，以原 `--output` 参数为 V17、V18、V19、V20 选择规范输出目录；不修改模型设置、运行语义或校验规则。其他入口继续显式传入规范输出位置。路径查询工具也支持此次及此前平铺路径，不读取快照替代当前文件。

`.gitignore` 原有 `/artifacts/` 覆盖新运行目录；历史目录规则作为兼容保留。方法配置、精选结果、报告和新导航仍可版本管理。没有暂存、提交或执行真实模型实验。

## 回溯与核验

- [迁移收据](../../experiments/methods/runtime-migration.json)：实际移动、导航/工具修改的摘要以及完整清单的校验值。
- [变更前快照](../archive/runtime-layout-20261012.zip)：保存本次修改的原导航、路径工具等文件；不打包原始模型请求响应。
- 本机逐文件哈希清单与测试日志位于 `artifacts/repository_inventory/runtime-layout-20261012/`；原有前三步收据保持原文，核验脚本串联后续收据。

```sh
python3 scripts/maintenance/verify_runtime_layout.py --full
python3 scripts/maintenance/verify_method_layout.py --manifest experiments/methods/v18/v18_formal_003/config/manifest.json
```

完整性核验检查迁移后的实际文件，不把历史快照当作当前文件。模型实验成功与否、历史源码漂移导致的恢复限制，不因目录迁移而改变。

## 验收结果

- 129,685 个迁移文件逐一核对 SHA-256；原始运行字节和修改时间未变，11 个导航文件的迁移/编辑单独登记，9 个精选 Skill 保持原字节并保留版本管理。
- 1,180 个既有可版本管理 JSON 保持原字节；原有实验实现和运行脚本未修改，仅路径查询工具、对应测试和迁移核验脚本调整。
- 119 个旧实体入口全部成为相对链接。另保留 10 个被代码/冻结输入引用的更早平铺入口，以及 11 个历史导航入口、9 个精选 Skill 引用，共 149 个兼容链接；没有新增无依赖的旧平铺入口。
- 文档链接检查无新增断链；前三步核验全部通过；V18 formal_003 的 992 个条目全部与当前实际文件匹配。
- 新运行入口只读预检通过，仍绑定 36 个训练任务、45 个 Monitor 任务；17 个主要 campaign/checkpoint JSON 可读取。没有实际执行或恢复模型实验。
- 两组测试共 2,231 项通过、12 项既有失败、0 项新增失败；新增 13 项路径与启动入口测试。迁移前有 17 项失败，其中 5 项 V18 输入路径相关失败在兼容读取修复后通过。剩余失败不在此次目录整理范围。

本机详细证据：[validation.json](../../artifacts/repository_inventory/runtime-layout-20261012/validation.json)。路径迁移和测试通过不代表历史运行已获准恢复；仍需通过原运行器的源码、配置与恢复状态校验。

# 全项目直接路径整理记录

> 本文记录前序兼容链接清理。后续源码、脚本和测试已继续归类，当前位置及入口见 [第五步整理记录](CODE_LAYOUT.md)。

日期：2026-10-12。当前源码、配置、测试和导航直接使用整理后的目录。全部 190 个文件系统兼容链接已删除：`experiments/` 53 个、`artifacts/` 132 个、`benchmarks/` 5 个。链接指向的实际材料均保留。

## 当前目录归属

| 内容 | 位置 |
| --- | --- |
| 方法实验配置、说明、精选结果 | `experiments/methods/vXX/<实验编号>/` |
| 方法原始运行数据 | `artifacts/methods/vXX/<运行编号>/` |
| Benchmark 定义及构造代码 | `benchmarks/` 中对应研究对象目录 |
| Benchmark 实验配置、精选报告 | `experiments/benchmarks/` |
| 方法及 Benchmark 文档 | `docs/methods/`、`docs/benchmarks/` |

`experiments/` 根目录的 `v17`、`v18`、`v19` 以及 `v17_*`、`v18_*` 平铺链接均已移除。V01–V14 的动态输出根据实际 campaign 版本进入 `artifacts/methods/`；复用其他版本控制器时也按当前实验编号归属。

## 本次修正

- 改写活动代码、配置、测试和 Markdown 链接中的旧位置，包括通过 `Path` 拼接得到的路径。
- V15/V16 直接从方法目录读取配置、划分和精选 Skill，从原始数据目录读取轨迹；输出写入相应的新位置。
- 修复三个 benchmark 脚本的项目根目录层级计算；核对源码和脚本中可静态解析的 215 处项目根路径。
- 历史 checkpoint、缓存和结果记录中的文件名在读取时定位到实际文件；路径比较按文件位置判断，避免因目录名不同而误判缓存失效或重跑模型。
- 更新本次路径改动涉及的源码和配置指纹，保留正常校验机制。源码可以继续修改；这次没有以“冻结”为理由保留旧快捷方式。
- `.gitignore` 继续以 `/artifacts/` 覆盖原始运行数据，移除已不再使用的旧平铺目录专用规则。

历史记录的旧路径字符串保留原文，通过 [canonical-paths.json](../../experiments/methods/canonical-paths.json) 在读取时解析。它是记录中路径的定位表，不会创建旧目录或快捷方式。两份实验日志按此前要求未修改。

## 验证结果

- 主项目文件系统兼容链接：**0**。检查范围排除 `.git/`、第三方 `external/`、虚拟环境及缓存。
- 扫描 2,259 个活动代码和配置文件：未发现已迁移路径的旧引用，Python 语法解析通过。历史迁移清单及专门验证旧路径读取的测试不计入此项。
- 原始数据 132,303 个文件的大小、修改时间无变化，无文件丢失。上一轮迁移的 129,685 个文件逐一 SHA-256 校验通过。
- V15/V16 历史记录中的 5,580 处 Skill/轨迹路径均可读取，配置与划分读取通过。
- 方法和适配器测试：2,194 通过、6 个既有失败；V06 单独测试：43 通过、6 个既有失败。失败名称与前序整理基线一致。
- Benchmark V5：124 通过，另有 120 项子测试通过；采用 `--import-mode=importlib` 避免不同测试目录的同名模块收集冲突。
- 路径与正式实验相关补充测试：72 通过（与主测试集有重叠，不重复计入总数）。
- V18/V20 正常预检通过，模型调用为 0。未重跑付费实验，未生成新的实验结论。

既有失败包括 V02/V03 草稿状态及预算约束、V06 恢复/候选选择、V14 历史源码指纹和合规提示词断言。本次没有改动这些断言来消除失败。

## 可核对材料

- [本次变更清单与删除链接清单](../../experiments/methods/canonical-migration.json)
- [本次修改前的文件快照](../archive/canonical-paths-20261012.zip)
- [本地验证汇总](../../artifacts/repository_inventory/canonical-paths-20261012/validation.json)（本地审计产物，不纳入 Git）

可运行 `python scripts/maintenance/verify_canonical_paths.py` 检查本次记录；`python scripts/maintenance/verify_runtime_layout.py --full` 检查原始文件完整性。前序文档、benchmark、方法迁移校验脚本也已接入本次路径变更链。快照校验用于核对本次整理，后续有意修改代码时应相应更新整理记录，不代表代码不可修改。

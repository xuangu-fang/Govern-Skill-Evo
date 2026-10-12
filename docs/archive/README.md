# 文档目录迁移与冻结快照

> 后续 benchmark 目录迁移见[第 2 步记录](../repository/BENCHMARK_LAYOUT.md)与[新快照](benchmark-layout-20261012.zip)。本页记述的是第一次文档迁移；校验脚本已支持其文件的后续位置。

2026-10-12 仅按研究对象调整文档目录，没有合并协议、改写实验结论或重跑模型。

- 方法文档位于 `docs/methods/v17/` 至 `v21/`。
- Benchmark v5 文档位于 `docs/benchmarks/v5/`。
- [总索引](../README.md)提供日常阅读入口；[路径映射](../path-map.json)记录旧路径、新路径及迁移前后摘要。
- `MAIN_EXPERIMENT_LOG.md` 与 `docs/04_EXPERIMENT_LOG.md` 未修改。日志中的旧文档链接保留历史原文，查阅时按路径映射定位。

## 冻结原件

[迁移前快照](docs-layout-20261012.zip)保存本次移动或修改的既有文件原始字节，包括文档、入口 README 和调整文档路径的源码。压缩包内使用原仓库相对路径，没有运行轨迹、凭据或外部依赖。该快照用于历史核验，不是第二套日常维护文档。

历史 `freeze.json`、`protected_before.json`、benchmark lineage 和实验结果未重写。旧清单仍指向原路径和原始摘要；当前文件移动、链接调整或源码路径常量更新之后，不能声称当前文件仍与旧冻结版本完全相同。

从仓库根目录进行只读核验：

```sh
python3 scripts/maintenance/verify_docs_layout.py
python3 scripts/maintenance/verify_docs_layout.py --manifest experiments/benchmarks/v5/calibration/freeze.json
```

核验明确区分当前文件匹配、迁移前快照匹配和不匹配，不覆盖旧清单、不放宽运行器原有哈希检查。快照匹配只证明历史字节可找回，不代表当前源码等同旧版本，也不代表已完成实验重放。迁移前已存在的不匹配仍会报告失败。

## 使用历史运行器

直接在当前工作区运行旧冻结实验的严格校验，可能因路径或源码摘要变化而拒绝执行。若需使用原运行器重放旧实验，应在独立的历史工作副本中恢复匹配的源文件及原路径，并提供原始实验产物；不要将压缩包直接覆盖到当前工作区，也不要修改旧哈希使其通过。快照覆盖本次变更文件，其余历史依赖仍以原实验记录为准。

新实验使用新文档路径和新的冻结记录。当前目录迁移不改变任何实验的准入状态、失败结果或模型成绩。

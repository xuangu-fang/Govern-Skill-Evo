# 命令入口

从项目根目录运行脚本，使用对应实验环境中的 Python。目录按用途划分，再按方法版本归类；benchmark 专属工具按 benchmark 版本归类。

| 目录 | 用途 |
| --- | --- |
| `runs/vXX/` | 方法实验启动、pilot、Monitor 与只读预检 |
| `analysis/vXX/` | 诊断、合规、评审及输入预算分析 |
| `preparation/vXX/` | 输入样例、证据准备及正式实验配置生成 |
| `migrations/vXX/` | 历史运行数据迁移、修复和恢复辅助工具 |
| `benchmarks/v4/` | Benchmark V4 构建与联合任务准入校验 |
| `benchmarks/v3/` | Benchmark V3 开发、正式版与构造阶段的执行脚本 |
| `benchmarks/validate_editions.py` | 各 benchmark edition 的离线任务与划分检查 |
| `maintenance/` | 仓库目录整理与完整性校验 |
| `run_method.py` | 为常用方法运行器选择规范输出目录 |

先检查命令和输出位置：

```sh
python scripts/run_method.py v19 --run-id example --stage pilot --print-command
python scripts/runs/v20/run_v20.py --help
python scripts/maintenance/verify_code_layout.py
```

V18 正式运行器默认只做预检：

```sh
python scripts/runs/v18/run_v18_formal_v4.py
```

各脚本仍保留原有参数与运行/恢复条件。分类不代表脚本只读：分析和准备脚本也可能写文件或调用模型，应先查看参数与对应实验说明。旧平铺脚本已移动，不保留快捷方式。

## Benchmark 谱系

`benchmarks/governed/v1/` 至 `v3/` 属于早期 Governed 系列；`benchmarks/v1/` 至 `v5/` 按 Phase / 独立 V5 组织。共享审计在 `scripts/benchmarks/audits/`，共享实现位于 `src/benchmark_shared/`。

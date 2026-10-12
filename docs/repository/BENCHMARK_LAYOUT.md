# 第 2 步：统一 benchmark 目录与归属

> 这是前序步骤的历史记录。兼容链接现已删除，当前状态见 [直接路径整理记录](CANONICAL_PATHS.md)。

后续进度：[第 3 步方法实验整理](METHOD_EXPERIMENT_LAYOUT.md)已完成；下文保留第 2 步的执行记录。

执行日期：2026-10-12。第 1 步清单保留为历史快照；本记录与 [实际路径映射](../../benchmarks/path-map.json)描述已执行的迁移。

## 当前结构

```text
benchmarks/
  README.md
  path-map.json
  tau2_governed_evolution/
    editions/<原有 8 个 edition>/
    shared/、audits/、final_candidate/  # 历史位置保留
  standalone/
    editions/v5/
      README.md
      prototypes/scenarios.json
      sa/README.md
experiments/benchmarks/v5/
  prototype-engineering/results.json
  calibration/
  decision_probe/
  learning/
artifacts/benchmarks/v5/<原运行 ID>/
docs/benchmarks/v5/
```

## 已完成的归属调整

| 原位置 | 当前位置 | 归属 |
|---|---|---|
| `benchmarks/standalone/editions/v5` 中的定义与原型说明 | [standalone/editions/v5](../../benchmarks/standalone/editions/v5/README.md) | 独立基准原型 |
| 原 `calibration/`、`decision_probe/`、`learning/` | [experiments/benchmarks/v5](../../experiments/benchmarks/v5/README.md) | 配置、冻结证据、精选实验结果 |
| 原 `prototypes/engineering_results.json` | [工程验证摘要](../../experiments/benchmarks/v5/prototype-engineering/results.json) | 工程实验结果 |
| `artifacts/benchmarks/v5` | `artifacts/benchmarks/v5` | 808 个本地原始产物，保留运行 ID 和全部字节 |

共移动 823 个既有文件，其中基准目录原有 15 个文件，原始产物 808 个。没有合并结果、筛掉失败记录或创建重复运行目录。旧目录不保留软链接或第二套副本。

τ² 已具备系列/edition 层级。本轮保留其 8 个 edition、共享实现、构造和审计材料、V15/V16 内嵌实验；这些内容的归属和后续处理依据仍见第 1 步清单。尤其 V16 实现被 V17/V18 复用，拆分将在实验/源码整理阶段处理。

## 引用、Git 与历史冻结

- 日常文档链接、源码中的 fixture/config/output 路径和测试输入已指向新位置；Python 包及模块导入名不变。
- 所有既有 JSON、冻结清单和原始产物均保持原字节。其内部旧路径是历史证据，未批量改写；按路径映射定位当前文件。
- 归档中的两份一次性 Python 分析脚本也是历史运行材料，随产物原字节迁移；在当前布局直接重执行前需在新副本中调整路径，不能覆盖旧证据。
- 原 `.gitignore` 的 `/artifacts/` 已覆盖新产物位置，实验协议与精选结果未被忽略，无须增加宽泛的 JSON 忽略规则。此次未更改 Git 索引或提交状态。
- 两份实验日志不修改；日志内旧路径可通过迁移映射查找。

[迁移前快照](../archive/benchmark-layout-20261012.zip)保存本轮修改的源码/文档及迁移前的 15 个基准目录文件，不包含运行轨迹或凭据。第一次文档迁移的 [快照与说明](../archive/README.md)继续保留。两次快照共同支持历史字节核查。

```sh
# 只读：检查本轮文件位置、字节和历史快照
python3 scripts/maintenance/verify_benchmark_layout.py
python3 scripts/maintenance/verify_benchmark_layout.py --manifest experiments/benchmarks/v5/calibration/freeze.json

# τ² 结构与任务划分；不调用模型
python3 -m scripts.benchmarks.validate_editions

# 当前原型契约测试；不调用模型
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests/benchmarks/v5/prototypes
```

核验区分“当前字节匹配”和“历史快照匹配”。历史快照可找回不意味着当前源码与旧冻结源码相同。运行器的严格哈希检查保留；旧校准、学习、SC、SA 等冻结实验可能拒绝在当前工作区重执行。历史复现应在独立工作副本中恢复匹配源码和原路径，并提供旧产物，不能直接把快照覆盖到当前工作区或改写旧哈希。

此次只做目录迁移及离线核验，不运行模型、不更新分数，不据此改变任何 benchmark 的准入状态。

## 验收结果

迁移后 124 项相关单元测试、46 条确定性原型工程验证和 8 个 τ² edition 结构检查均通过。11 份旧冻结清单的源文件摘要可由当前文件或两次历史快照完整核对，无未匹配项；伪造摘要的负向检查被正确拒绝。

对照迁移前基线核对 3,597 个既有文件，包含 808 个原始产物；1,906 个既有 JSON/原始产物文件保持逐字节一致。扫描 1,248 个非日志 Markdown 链接，无新增断链。两份日志和 Git 索引未变；迁移前已存在的无效链接不计为本次修复。

结果记录于本机 [validation.json](../../artifacts/repository_inventory/benchmark-layout-20261012/validation.json)，包括相关测试、路径和字节检查。逐文件摘要见可版本化的 [path-map.json](../../benchmarks/path-map.json)。

下一步是整理方法实验入口：把 v01–v21 的配置、索引和精选结果按方法组织，先处理 V15/V16 的共享实现依赖，再决定具体迁移。

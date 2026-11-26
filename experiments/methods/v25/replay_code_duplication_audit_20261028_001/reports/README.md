# R05 / R06 Replay response / executed_code 重复量统计

2026-10-28。只读当前共享输入视图 v3 的已保存离线请求，未修改生产代码、输入视图、Prompt 或归档，未调用模型。

## 结论

这两个字段确实占据大量输入。以 cl100k_base 作离线代理分词，合计占 R05 / R06 的 system+user 内容 tokens 约 60.9% / 58.8%。

两轮共 62 条程序记录：43 条（69.4%）的 response 代码体与 executed_code 逐字相同；其余 19 条都仅有两条顶层路径赋值被执行器替换为 pass。按代码体中未改动行的字符量计，两轮合计 99.52% 内容相同。

“大部分代码文本重复”成立；“所有 response 与 executed_code 字段原文完全相同”不成立：response 带代码围栏，且部分执行代码发生确定性的路径适配。

## Token 计量方法

本地没有经过验证、与内网 deepseek-v4.1-flash 一致的 tokenizer。本统计使用 tiktoken 的 cl100k_base，因此以下都是代理计量，不是 DeepSeek API 实际输入/计费 tokens，也不是字符数换算。tiktoken 仅安装在临时目录，不加入项目依赖。

总输入计数为分别编码 system 和 user 内容后求和，不包括未知的 chat framing。字段占用通过在内存中删除对应字段、重新序列化 user JSON 后的 token 差值计算；包括字段本身的 JSON 表示开销。这些删除后的对象仅用于体积统计，不是有效 Replay 请求，没有发送或保存为运行请求。

| 项目（代理 tokens） | R05 | R06 |
|---|---:|---:|
| system 内容 | 6,685 | 6,685 |
| user 内容 | 89,595 | 109,730 |
| system+user 内容 | 96,280 | 116,415 |
| response 字段边际占用 | 29,422 | 34,324 |
| executed_code 字段边际占用 | 29,240 | 34,154 |
| 两字段合计占用 | 58,662 | 68,478 |
| 占 user 内容比例 | 65.5% | 62.4% |
| 占 system+user 内容比例 | 60.9% | 58.8% |

分词以当前已实现 system/user 共享之后的 v3 视图为基线。没有用旧视图的 API usage 代替新视图 token 数。

## 精确重复与差异

| 程序记录 | R05 | R06 | 合计 |
|---|---:|---:|---:|
| 总数 | 31 | 31 | 62 |
| response 整个字段与 executed_code 完全相同 | 0 | 0 | 0 |
| 去围栏后的代码体完全相同 | 21 | 22 | 43（69.4%） |
| 仅两行路径赋值适配 | 10 | 9 | 19（30.6%） |
| 其他代码差异 | 0 | 0 | 0 |
| 代码体未改动行的字符占比 | 99.45% | 99.57% | 99.52% |

31 条而不是 30 条的原因：R05 Q2、R06 P9 各有两次实际程序执行。统计包含这些记录。

所有 19 份差异都是：

```diff
-INPUT_PATH = "input.xlsx"
-OUTPUT_PATH = "output.xlsx"
+pass
+pass
```

使用现有 `protocol.extract_code` 做解析与适配，没有执行 Actor 代码；62/62 条都能精确重建已保存的 executed_code。逐条差异见 [code_differences.md](../../../../../artifacts/methods/v25/analysis/replay_code_duplication_audit_20261028_001/code_differences.md)。该结论限于本次 R05/R06，不能外推其他运行不存在额外差异。

## 可去重体积的上限参考

若只针对代码体完全一致的记录省去一份 executed_code，代理毛节省为 R05 20,108 tokens（当前总内容 20.9%）、R06 26,252（22.6%）。

若未来连路径适配记录也采用经过版本化、可精确还原的表示，移除全部重复 executed_code 的代理毛空间为 R05 29,240（30.4%）、R06 34,154（29.3%）。必须保留生成原文与实际执行代码的区别和适配信息；不能把这解释成允许直接丢弃差异。

这些是删除字段后的毛空间，尚未扣除未来共享指针、差异记录和解码说明的开销，不是已实现的节省或 API 成本收益。本次只统计，没有实施 response/code 去重。

## 复现与原始结果

- [audit.py](../../../../../artifacts/methods/v25/analysis/replay_code_duplication_audit_20261028_001/audit.py)：逐条差异核对、两类字段边际 token 统计。
- [statistics.json](../../../../../artifacts/methods/v25/analysis/replay_code_duplication_audit_20261028_001/statistics.json)：源请求哈希、原生解析器哈希、分词库版本、逐条分类与完整数值。

本地执行命令：

```text
/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/analysis/replay_code_duplication_audit_20261028_001/audit.py
```

脚本依赖临时目录 `/tmp/govern-replay-token-audit-packages` 中的 tiktoken；该临时依赖以后可能需要重新安装。生产代码与所读取的原归档保持不变。

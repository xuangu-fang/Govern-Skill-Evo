# OfficeQA 解析输入修复 v1

本页保留 v1 历史记录。新实验改用 [解析修复 v2](PARSED_CORRECTIONS_V2.md)；v1 数据保留供旧归档恢复。

2026-10-29：基于固定下载 revision `8ecbf18d3833daf4750a903d14963e4c4c1d4cd8`，独立生成修订语料。原始下载、题面、参考答案、50/24/172 划分、来源映射、Actor、评分器及优化器均未修改。

## 已核实的四个单元格

| 相关任务 | 文档 / PDF 页 | 表格、月份 | 解析值 | PDF 原值 |
|---|---|---|---:|---:|
| UID0007 | treasury_bulletin_1950_02 / 15 | Table 6，预算支出，1942-05 | 4100 | 4400 |
| UID0007 | treasury_bulletin_1950_02 / 15 | Table 6，预算支出，1947-11 | 2113 | 2143 |
| UID0004 | treasury_bulletin_1954_02 / 15 | Table 3，国防及相关支出，1953-01 | 3532 | 3632 |
| UID0004 | treasury_bulletin_1954_02 / 15 | Table 3，国防及相关支出，1953-02 | 3531 | 3501 |

两份 PDF 均来自同一固定版本的官方数据。扫描核对证据保存在 `data/officeqa/correction_evidence_v1/`；PDF SHA256、原始行、修改列及新旧值记录在 `benchmarks/officeqa/parsed_corrections_v1.json`。

对每个单元格同步修复 transformed TXT 与 parsed JSON。采用唯一完整表格行匹配，只替换目标数值，保留 JSON 其余字节、元素 ID、bbox、页号及布局。没有重新解析 PDF，也没有按参考答案反推其他数字。

UID0007 的 80 个值经高精度乘积开根得到 `4962.464197734716744543021184…`，舍入后与原参考答案 `4962.46` 一致。UID0004 本次只修复上述两格；不宣称已完成该题全部计算和参考答案的重新审计，参考答案仍为本地原值 `1608.80%`。

## 新实验统一使用的路径

```text
prepared_root = data/officeqa/prepared_v2
parsed_root   = data/officeqa/corrected_v1/treasury_bulletins_parsed
```

No Skill、Initial Skill、V26、SkillOpt 和 SkillAdam 的新训练/评测均应显式使用上述同一 `parsed_root`。SkillOpt/SkillAdam 配置示例、V26 pilot 默认路径及 Campaign/evaluate 文档示例已切换。公共 Runtime 不做隐式路径重定向。

`prepared_v2/manifest.json` 和 `execution.json` 保留原始对齐时的历史来源路径；任务 loader 读取其中的 profile/splits，执行语料根目录由显式 Runtime/launcher 参数决定。修订版来源与文件哈希单独记录在 `corrected_v1/audit.json`。

不要将已有实验目录指向修订语料后继续运行；这会改变输入与文档身份。旧实验继续保留原 `raw/treasury_bulletins_parsed` 路径及原始结果，用原配置恢复/报告。历史 continuation 脚本保持原路径。新实验使用独立目录。

## 离线重建与验收

```sh
conda activate OfficeQA
python -m scripts.benchmarks.officeqa.correct_parsed
python -m scripts.benchmarks.officeqa.correct_parsed --check
python -m pytest -q tests/adapters/officeqa/test_parsed_corrections.py
```

构建程序禁止网络，先核对全部 1,403 个原始下载文件，再复制独立语料、修复并校验后整体发布。原文件不会被覆盖，不使用共享可写硬链接。原始哈希、目标行数量、已有修订语料或审计记录不匹配时直接失败。重复执行只检查已存在内容，不重复修改。`--check` 不写文件。

全库共有 1,394 个语料文件，只有 4 个文件改变，其余文件逐一保持原 SHA256。修订版需约 985 MiB 额外空间。

全部 246 题、493 个页面引用已通过初始消息构造、页面可解析性、文件权限和工具读取检查；没有模型调用或实验执行。报告：`artifacts/benchmarks/officeqa/parsed_corrections_v1/input_audit.json`。

初始消息只有 UID0007 发生变化。UID0004 的初始来源指向 PDF 第 14 页 Table 2，该处原本已是正确值；此次修复的是第 15 页 Table 3，因此其初始消息不变，但工具读取到的文档已修正。引用这两份文档的任务为 UID0003、UID0004、UID0005、UID0007、UID0221；它们统一读取修订语料，不按题目 ID 注入专用证据。

这份修复清单不是全库数字准确性保证，也不将公开 issue 中未独立核实的答案更新纳入修复。

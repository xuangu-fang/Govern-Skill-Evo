# OfficeQA 解析输入修复 v2

2026-10-29，在经过完整性验证的 corrected_v1 上生成独立 corrected_v2。原始下载、v1 及旧实验归档均保留。该版本累计包含 v1 的四个数字修复，以及本轮已核实的 17 个单元格修复和一列缺失数值恢复。

## 修复范围

| 文档 / PDF 页 | 本轮修复 |
|---|---|
| 1950-02 / 15 | 4 个数值：2078→2070、1531→1631、-4499→-499、2302→-302 |
| 1939-10 / 14 | 3 个数值：858→868、9384→9364、8350→8360 |
| 1942-02 / 19 | Table 3：WPA/NYA 列 7 个年度单元格错位、FERA/CWA 列 3 个单元格错误 |
| 1939-11 / 14 | 汇总表恢复 Miscellaneous receipts 列的 20 个值，并按 PDF 层级明确各列标题 |

完整 PDF 证据及错误定位见 `artifacts/benchmarks/officeqa/parsed_audit_20261029_002/findings.json`。缺失列已重新放大逐格核实；20 个值按原始行序为：

```text
225,162,179,216,210,208,195,17,14,15,20,16,15,13,17,14,17,19,16,17
```

该列位于 Customs 与 Expenditures Total 之间。原表头有跨列数量与名称错配；新表头使用保留原层级及脚注编号的单行列名，确保初始页面和 TXT 工具读取均呈现相同 15 列。删除新增的第 8 列后，20 行既有数值与 v1 逐项完全相同，不借此重算或修改其他列。

所有修复同步作用于 TXT 和 JSON；JSON 元素 ID、页号、bbox、description 与其他元数据不变。除目标行和缺失列所在表格外，其余字节保持不变。相对 v1，只有 8 个文件变化；相对原始下载，累计 10 个文件变化（5 份文档各含 TXT/JSON）。任务、参考答案、划分、来源映射、公共 Actor、七模块 Prompt、优化器与输出预算均未改动。

修复依据与逐文件精确替换记录：`benchmarks/officeqa/parsed_corrections_v2.json`。该记录绑定 v1 审计哈希、输入/输出文件哈希、证据审计哈希。原始下载或 v1 漂移、匹配位置不唯一、输出字节不符时拒绝继续；不会覆盖已存在且内容不同的 v2。

## 新实验路径与历史恢复

```text
prepared_root = data/officeqa/prepared_v2
parsed_root   = data/officeqa/corrected_v2/treasury_bulletins_parsed
```

No Skill、Initial Skill、V26、SkillOpt、SkillAdam 的新实验统一显式使用该语料路径。V26 pilot 默认路径、SkillOpt/SkillAdam 配置示例和 Campaign/evaluate 文档示例已切换到 v2。公共 Runtime 不隐式重定向旧路径。

历史运行使用原来冻结的 raw 或 corrected_v1 路径进行恢复/报告；不要将旧实验目录切换到 v2 后续跑。新的语料对应新的实验目录。`prepared_v2` 的历史来源 manifest 不改写，实际语料由 Runtime 参数选择。

## 离线构建与验收

```sh
conda activate OfficeQA
# 若 v1 尚不存在，先构建它。
python -m scripts.benchmarks.officeqa.correct_parsed
python -m scripts.benchmarks.officeqa.correct_parsed_v2
python -m scripts.benchmarks.officeqa.correct_parsed_v2 --check
python -m pytest -q tests/adapters/officeqa tests/skill_evolution/v26
```

构建命令禁止网络和模型调用，复制到独立临时目录后完成全部哈希检查再发布；不使用共享可写硬链接。`--check` 不写语料。v2 额外占用约 985 MiB。

真实数据只做离线输入/工具检查，报告位于 `artifacts/benchmarks/officeqa/parsed_corrections_v2/`。全部 246 题、493 个页面引用可用；相对 v1，只有 UID0007、UID0049、UID0190 的初始消息变化。UID0007 的目标 80 个支出值保持 v1 修复后的内容，计算仍得到 4962.46；UID0049 的 Table 4 国防总额及 UID0190 的目标总收入值保持不变。

该版本只覆盖已核实清单，不将其他自动筛查候选或未核实的参考答案建议作为修复。

2026-10-29 离线验收结果：上述 OfficeQA / V26 测试集共 402 项通过（76.79 秒）；全题输入审计记录网络请求、模型调用和实验运行均为 0。输出预算与修复前一致。

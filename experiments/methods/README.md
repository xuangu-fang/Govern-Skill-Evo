# 方法实验总索引

[ALFWorld 自进化实验索引（v24 至 v24.11）](ALFWORLD.md) · [SkillAdam 的 ALFWorld 实验索引](skilladam/alfworld/README.md) · [SkillOpt 的 ALFWorld 实验索引](skillopt/alfworld/README.md) · [三种方法的实验对照](../../docs/benchmarks/alfworld/V24_11_COMPARISON.md)

[OfficeQA 正式实验与离线评分核验](OFFICEQA.md)

按方法版本和原实验 ID 组织配置、冻结证据及精选结果。版本号不表示已完成正式实验，目录存在也不代表实验成功。

当前结构为 `experiments/methods/<版本>/<实验ID>/{config,results,reports}`，只建立实际存在的材料子目录。完整运行产物已统一归入 `artifacts/methods/`，见[运行导航](RUNTIME.md)。

当前配置和代码直接引用规范目录；v22 的历史修订通过包路径和少量相对链接复用源码，见 [v22 引用关系](v22/README.md)。早期版本的兼容入口整理记录保留在原文档中。历史记录中的路径由读取工具定位，详见[本次清理说明](../../docs/repository/CANONICAL_PATHS.md)。

[迁移记录与验收](../../docs/repository/METHOD_EXPERIMENT_LAYOUT.md) · [Benchmark 实验](../benchmarks/README.md) · [产物政策](../README.md)

| 方法 | 入口 | 冻结包 / 实验材料组 |
|---|---|---:|
| v01 | [v01 实验入口](v01/README.md) | 1 |
| v02 | [v02 实验入口](v02/README.md) | 1 |
| v03 | [v03 实验入口](v03/README.md) | 1 |
| v04 | [v04 实验入口](v04/README.md) | 3 |
| v05 | [v05 实验入口](v05/README.md) | 1 |
| v06 | [v06 实验入口](v06/README.md) | 1 |
| v07 | [v07 实验入口](v07/README.md) | 1 |
| v08 | [v08 实验入口](v08/README.md) | 1 |
| v09 | [v09 实验入口](v09/README.md) | 1 |
| v10 | [v10 实验入口](v10/README.md) | 1 |
| v11 | [v11 实验入口](v11/README.md) | 1 |
| v12 | [v12 实验入口](v12/README.md) | 1 |
| v13 | [v13 实验入口](v13/README.md) | 1 |
| v14 | [v14 实验入口](v14/README.md) | 3 |
| v15 | [v15 实验入口](v15/README.md) | 1 |
| v16 | [v16 实验入口](v16/README.md) | 1 |
| v17 | [v17 实验入口](v17/README.md) | 1 |
| v18 | [v18 实验入口](v18/README.md) | 10 |
| v19 | [v19 实验入口](v19/README.md) | 1 |
| v20 | [v20 实验入口](v20/README.md) | 1 |
| v21 | [v21 实验入口](v21/README.md) | 1 |
| v22 | [v22 实验与修订入口](v22/README.md) | 18 |
| v23 | [v23 验证入口](v23/README.md) | 11 |
| v23.2 | [实验材料与运行记录](v23_2/README.md) · [方法说明](../../docs/methods/v23_2/README.md) | 20 |
| v23.3 | [实验材料与归档读取](v23_3/README.md) | 17 |
| v23.4 | [实验材料、正式结果与归档读取](v23_4/README.md) | 28 |
| v23.5 | [协议对照、核验修复与 ALFWorld 结果](v23_5/README.md) | 24 |
| v24 | [正式训练、首测、RC1、重放与准备配置](v24/README.md) | 6 |
| v24.1 | [准备配置、官方模型训练、首测与复测](v24_1/README.md) | 2 |
| v24.2 | [ALFWorld 正式训练、首测与复测](v24_2/v24_2_alfworld_20261106_195800/README.md) | 1 |
| v24.3 | [正式训练、首测与 R02 快检](v24_3/README.md) | 3 |
| v24.4 | [五次训练、首测进度与独立分析](v24_4/README.md) | 23 |
| v24.5 | [正式训练、首测与 R05 分析](v24_5/README.md) | 2 |
| v24.6 | [ALFWorld 训练与评测](v24_6/README.md) | 2 |
| v24.7 | [ALFWorld 训练与评测](v24_7/README.md) | 2 |
| v24.8 | [ALFWorld 训练与评测](v24_8/README.md) | 6 |
| v24.9 | [ALFWorld 训练与评测](v24_9/README.md) | 3 |
| v24.10 | [ALFWorld 训练与评测](v24_10/README.md) | 1 |
| v24.11 | [两次训练记录，正式运行含九次评测](v24_11/README.md) | 2 |
| v25 | [SpreadsheetBench 原版训练、尝试、对照与专项材料](v25/README.md) | 10 |
| v25.1 | [SpreadsheetBench 正式训练和首测](v25_1/README.md) | 1 |
| v25.2 | [SpreadsheetBench 正式训练和首测](v25_2/README.md) | 1 |
| v25.3 | [SpreadsheetBench 正式训练和取消的预约](v25_3/README.md) | 2 |
| v25.4 | [SpreadsheetBench 正式训练、复测和专项](v25_4/README.md) | 1 |
| v25.5 | [SpreadsheetBench 正式训练及两条准备记录](v25_5/README.md) | 3 |
| v25.6 | [SpreadsheetBench 训练、11 次全量评测和两题专项](v25_6/README.md) | 1 |
| v25.7 | [SpreadsheetBench 两次训练、准备档和 11 次全量评测](v25_7/README.md) | 3 |
| v25.8 | [SpreadsheetBench 正式训练和 19 次评测](v25_8/README.md) | 1 |
| v26 | [OfficeQA Pilot、正式训练与预算续跑](v26/README.md) | 5 |
| v26.1 | [OfficeQA 正式训练、逐轮评测和 UID0111 补测](v26_1/v26_1_officeqa_train74_roles_20261105_202041/README.md) | 1 |
| v26.2 | [OfficeQA 正式训练与两次部分评测](v26_2/v26_2_officeqa_train74_20261117_013308/README.md) | 1 |
| v26.3 | [OfficeQA 配置与历史训练缺失登记](v26_3/README.md) | 1 |
| v26.4 | [OfficeQA 暂停的训练，已提交至 R03](v26_4/README.md) | 1 |
| v26.5 | [OfficeQA 正式训练与四次部分评测](v26_5/README.md) | 1 |
| v26.6 | [OfficeQA 正式训练与两次部分评测](v26_6/README.md) | 1 |
| v26.7 | [OfficeQA 正式训练、部分评测与补测尝试](v26_7/README.md) | 1 |
| v26.8 | [OfficeQA 正式训练与部分评测](v26_8/README.md) | 1 |
| v26.9 | [OfficeQA 正式训练与逐轮评测](v26_9/v26_9_officeqa_train74_20261118_180409/README.md) | 1 |

[SpreadsheetBench SkillAdam 实验索引](skilladam/spreadsheetbench/README.md) · [SpreadsheetBench SkillOpt 实验索引](skillopt/spreadsheetbench/README.md) · [三种方法对照](../../docs/benchmarks/spreadsheetbench/V25_8_COMPARISON.md)

## 原始运行统一入口

[运行材料、启动与恢复](RUNTIME.md) · [第四步整理记录](../../docs/repository/RUNTIME_LAYOUT.md)。原始数据实体统一位于 `artifacts/methods/`，旧入口已删除。

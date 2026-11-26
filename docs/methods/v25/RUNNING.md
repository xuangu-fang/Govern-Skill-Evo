# V25 运行与交付说明

当前评分采用 [SkillAdam 值比较规则与区域解析兼容修复](SCORING_COMPATIBILITY.md)。新准备的配置包含完整 280 题；下文 rc1 的三题待处理说明仅对应旧配置，不能直接据此排除新版测试题。

新配置输出额度按 [TOKEN_BUDGETS.md](TOKEN_BUDGETS.md) 执行；下文旧配置和实验启动示例为历史记录，不会自动升级。

2026-10-27：最新配置使用 [统一配对准备入口](PAIRED_PREPARATION.md)，默认并发 4、Actor 49152、无任务总时限、实际执行计数和新历史协议。仅准备配置，未启动 campaign；已有配置不自动升级。

## 历史后续训练配置（2026-10-26）

使用 [8 批 × 15 题配置说明](BATCH15_TRAINING.md)及其链接的 `experiments/methods/v25/configurations/v25_spreadsheetbench_full120_batch15.json`。该配置保留 120 题原顺序、1 epoch、Actor 并发 4／32,768 输出 tokens、无整题累计时限，绑定当前 Preconditioner。10 题方案已撤销，新配置准备器默认每批 15 题。以下 rc1 候选、离线验收及启动示例为历史交付记录，不作为当前训练配置。

## 历史 rc1 交付记录

实现入口为 `src/skill_evolution/v25/cli.py`，候选配置为 `artifacts/methods/v25/candidates/v25_spreadsheetbench_verified400_rc1/config/campaign.json`。当前实现只支持明确绑定的 SpreadsheetBench 适配器，运行时不导入旧版本或两个参考仓库的代码。准备配置时读取参考数据目录和划分清单；配置准备完成后，执行仅需清单中的数据文件、v25 代码和执行镜像。

## 环境

在仓库根目录执行以下命令。API 凭据只通过运行环境提供，不写入候选配置或程序容器。

```sh
python3 -m venv .venv-v25
.venv-v25/bin/python -m pip install -r src/skill_evolution/v25/requirements.txt
docker build -t govern-skill-v25-python:rc1 -f src/skill_evolution/v25/benchmarks/spreadsheetbench/Dockerfile src/skill_evolution/v25/benchmarks/spreadsheetbench
```

程序容器为 Python 3.10，固定 openpyxl 3.1.5、pandas 2.2.3 等包版本。每个程序使用新容器、原始输入和独立输出目录，网络关闭；不挂载标准答案、其他任务、上一轮文件或凭据。内存 2 GiB、CPU 配额 1、最多 64 个进程，是本候选新增并明确固定的执行环境参数，不声称继承自两个参考仓库。正式执行前须统一三种方法的运行环境。

Docker 守护进程必须能读取任务输出所在的宿主目录。macOS 的 Colima 默认可共享用户目录；系统临时目录可能未共享。下面的离线命令把测试临时目录放在用户目录中。

## 离线验收

```sh
.venv-v25/bin/python -m pytest -q tests/skill_evolution/v25 tests/skill_evolution/v24 --basetemp "$HOME/.cache/govern-skill-v25-acceptance"
.venv-v25/bin/python scripts/runs/v25/verify_v25_offline.py --output artifacts/methods/v25/offline/new_offline_run
```

第二条命令要求新目录。它生成 15 个合成工作簿，使用预设 Actor／方法响应，在真实 Docker 执行器内运行 15 个 Parent 和 15 个 Candidate，并完成 Gate、Replay、Verifier、一次定向 Repair 和发布。它不读取真实任务输入、不调用模型服务，所得成功率不能作为 benchmark 效果。

## 候选配置

- 原始 Train 80 题后接 Val 40 题，保留各列表顺序；Val 明确参与优化。8 批，每批 15 题，遍历一次。
- 原始 Test 280 题仅最终评估，不进入优化；初始 Skill 为 SkillOpt 原文，初始 Memory 为空。
- Parent、Candidate 和 Test 都无评分纠错反馈。同一 Parent 记录用于诊断、Gate 和 Replay；Candidate 从原始输入独立执行。
- Actor 上限 30 轮代码生成；输出 16,384 tokens；API 请求 300 秒、每轮最多六次总请求；单个程序和 Actor 总预算各 600 秒，进行中请求／程序受剩余时间限制。
- 预览每表 5 行 × 20 列，单元格 40 字符；完整预览超过 100,000 字符时报错；当前任务历史完整保留。错误详情为前 3,000 字符。
- 方法模块沿用既定输出额度：Grouping／Diagnosis／Editor 16,384，其余四个模块 32,768；请求超时 300 秒、总尝试六次。
- 严格按任务成功数增加才接受 Candidate；单元格正确率不参与 Gate。辅助指标保留精确比值并对任务平均，SkillAdam 的四位小数显示不用于中间舍入。
- 评分读取保存的值，无额外公式重算。错误坐标以列优先、行次序排列，模型摘录取前 100 项；标准答案值不进入模型消息。

当前绑定模型为 `deepseek-v4.1-flash`、既定代理地址、temperature 1、medium reasoning 和 enabled thinking；并发为 1。具体完整值以候选 JSON 为准。程序环境和执行模式是 SpreadsheetBench 的新配置，不能用 v24 的 ALFWorld 效果作为等价证明。

## 数据标注预检发现

三个待确认问题都位于 Test：

| 任务 | 原始区域 | 处理 |
|---|---|---|
| 283-32 | `Sheet3'!A:G,'Sheet4'!A:G` | 整列范围没有有限行边界，保留原标注并登记问题 |
| 60-7 | 表名字段为 `Consolidated Tracker,Existing Task,Additions,Retired`，区域为 `A3:E11` | 多个表名合并在同一字段，无法唯一确定评分区域，保留并登记问题 |
| 73-45 | `'Sheet1'!BD2:308` | 右端缺少列名，保留原标注并登记问题 |

不删除任务、不替它们选取新范围。120 个优化任务的区域语法预检通过；最终 Test 入口会在执行前明确拒绝尚有上述问题的配置。需在三种方法共同采用的 benchmark 配置中明确修正后，再准备新的候选配置。

检查本地参考代码发现，SkillAdam 对第二项报错，而 SkillOpt 的解析器产生空单元格列表，可能造成空比较被视为通过。因此评分器在正常标注上的一致性不意味着所有异常标注行为也相同；v25 不把这类空比较记为成功。

输入和标准答案存在两种文件命名方式，准备器显式支持 `*_init.xlsx`／`*_golden.xlsx` 与 `initial.xlsx`／`golden.xlsx`。无工作表前缀时优先使用任务的 `answer_sheet`；缺省时读取标准答案工作簿的工作表名元数据，按参考实现选第一张表。此步骤不读取标准答案单元格内容。训练任务 `170-13` 的区域存在不规整的引号，按参考实现先以逗号分段，再剥离表名与范围两端的引号；三段区域可正确解析为 200 个单元格。该处理只兼容表示方式，不更换目标表或范围。

## 后续真实运行入口（本次未执行）

```sh
.venv-v25/bin/python -m src.skill_evolution.v25.cli prepare --output artifacts/methods/v25/runs/new_preparation
.venv-v25/bin/python -m src.skill_evolution.v25.cli run --config artifacts/methods/v25/runs/new_preparation/config/campaign.json --campaign artifacts/methods/v25/runs/new_campaign
.venv-v25/bin/python -m src.skill_evolution.v25.cli status --campaign artifacts/methods/v25/runs/new_campaign
.venv-v25/bin/python -m src.skill_evolution.v25.cli resume --campaign artifacts/methods/v25/runs/new_campaign
```

`run` 执行配置内的全部优化批次，不能直接当作 15 题试跑入口。本次没有启用小规模真实实验入口；后续应先明确任务子集及对应配置，再单独启动验证。不要修改已开始的 Campaign。

最终评估通过 `python -m src.skill_evolution.v25.evaluation run --root <独立评估目录> --experiment <候选目录> --campaign <完整优化目录>` 启动。它要求优化流程完整结束和数据问题已解决，只产生评估记录，不运行优化模块。

恢复时复用同一 Actor 状态，代码轮数、请求次数和已用时间不归零。 API 超时耗尽总预算且未取得响应时，恢复仍保留技术中断，不生成零分结果或进入学习／Gate；已有完整响应和程序正常预算耗尽分别按原有规则处理。Test 汇总保留实际终止原因，区分有效提交与预算耗尽。已保存的响应、程序结果、提交或评分可以继续完成，已发布的轮次不会重复发布。如果进程在程序执行中断且没有留下执行结果，会明确停止，不能自动重跑同一个未知结果的程序。此类异常需要单独处理，不得伪装成任务失败或重新发放预算。

## 历史运行入口

[官方线路 R08 入口](../../../scripts/runs/v25/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001/run.py) 的 `status` 读取已归档的 Campaign；新目录可用 `--output` 指定。[上游 Actor 调度入口](../../../scripts/runs/spreadsheetbench/schedules/v25_skilladam_upstream_actor_prompt_20261030_001/scheduled/control.py) 按方法选择运行包。两次历史 Actor 快照的维护路径及各次成绩见[原版实验索引](../../../experiments/methods/v25/README.md)。

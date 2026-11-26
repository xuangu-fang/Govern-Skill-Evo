# 首次保留的V25 / SkillAdam对照配置核对

结论：按用户要求统一的环境与Actor参数保持一致，没有发现对照配置漂移。SkillAdam方法机制按约定保留，不要求与V25逐模块相同。

- V25：`/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v25/training/v25_full120_timeline_actor32k_w4_20261026_002`，北京时间2026-10-26 03:06:10启动。
- SkillAdam：`/Users/didi/Desktop/Govern-Skill-Evo/experiments/baselines/skilladam_spreadsheetbench_v25matched_20261026`，北京时间2026-10-26 05:08:42启动。
- 更早并发1的V25目录已按用户要求删除，不在本次可核对范围。

## 直接证据

- V25 campaign/config.json与SkillAdam shared_config.json整个JSON完全相等。
- SkillAdam清单中63个共享V25冻结源文件的哈希与V25历史contract逐项一致；240个优化数据工作簿文件通过清单核对。
- 原始initial Skill逐字一致，SHA-256为`5c49d03008aea2c7151b134da20f2258a746c7323b76f0e49ec2c1ea8c131f26`。
- 首批15道题的task、Skill、模型、Actor profile、executor、初始消息、首次实际请求参数和消息、输入工作簿快照全部一致。
- V25全部74次、SkillAdam全部29次保存的Actor请求，调用参数均与同一冻结配置相符，实际max_tokens均为32768。

## 统一条件

| 项目 | 两边设置 |
|---|---|
| 数据和顺序 | Verified-400；80 Train＋40 Val，8批×15题，1 epoch，显式顺序相同、不打乱；280 Test不参与优化 |
| 初始Skill | 原始initial Skill；SkillAdam Stage0禁用 |
| 模型/API | deepseek-v4.1-flash，同一内部代理路由 |
| Actor采样 | temperature=1.0；reasoning_effort=medium；thinking=enabled；stream=false；未传API seed |
| Actor并发/输出 | 4 / 32768 tokens |
| 当时尝试规则 | 30次代码尝试，完整格式错误和截断均消耗一次；每次代码尝试的技术请求最多6次 |
| 当时时限 | API最多300秒、程序最多600秒、整题累计600秒；API与执行受剩余整题时间限制 |
| 等待与恢复 | 2×请求编号秒；保存次数，resume不重置 |
| Actor反馈 | 仅执行和格式错误；无标准答案、差异单元格或评分纠错反馈；首次有效工作簿即提交 |
| 预览 | 每表5行×20列、单元格40字符、总预览上限100000字符 |
| 输入容量 | 4000000字符 / 6000000 UTF-8字节 |
| 执行环境 | govern-skill-v25-python:rc1；Docker、2g内存、1CPU、禁网和同样挂载隔离；启动预检匹配V25运行时快照 |
| 容器运行时 | Python3.10.22，openpyxl3.1.5、pandas2.2.3、numpy2.2.6 |
| 宿主启动环境 | 同一个/tmp/govern-skill-v25-venv/bin/python；宿主环境与容器环境为不同层，不应拿宿主Python3.13/NumPy2.5与容器版本做横向比较 |
| 评分 | 同一评分实现、相同区域/数据，读取保存的data_only值，无额外公式重算 |

call_config.max_tokens=16384是基础/方法配置，Actor传输会用actor_profile.actor_max_output_tokens=32768覆盖。已检查实际请求，两边Actor均为32768，并非一边16K一边32K。

## 有意保留的方法差异

- SkillAdam：原生优化器输出16384、LLM轨迹压缩、96000上下文估计阈值、Momentum、自适应编辑预算、原生Gate。
- V25：Grouping/Diagnosis/Editor输出16384，Preconditioner/Replay/Verifier/Repair输出32768；连续时间线去重及V25自身Gate/Memory机制。
- 训练/baseline/candidate的执行与复用方式不同，实际任务执行次数可以不同，这是用户此前允许的差异。
- SkillAdam内部seed42用于原生机制；任务顺序已经显式固定且相同，两边均未向Actor API添加seed。
- 方法重试均配置每阶段6次总请求，技术/截断保持请求不变，完整输出校验错误携带上一输出与错误信息，关闭叠加SDK/外层重试。Momentum的原生工具输出契约仍保留。

## 核对边界与解释

- SkillAdam首轮中断在Actor训练轨迹阶段，尚无真实优化器请求；上述优化器条件由冻结配置、保存的桥接源码及当时预检证明，不能说已经实际跑完验证。
- 实际API timeout在V25最小约47.92秒、SkillAdam最小约23.02秒，是同一规则裁剪到各自剩余任务预算，不是API超时配置不一致。
- 旧规则两边相同，但累计600秒会把服务延迟和重试时间算入任务预算；这会影响结果，是后来统一取消的原因。
- 请求顺序、服务负载和模型采样不保证相同。相同参数不意味着同题输出或得分必须相同。
- 本次只读取历史档案，不用当前源码的冻结检查去判定旧实验配置错误，也未改动当前训练。

详细核对结果：[report.json](../results/report.json)。

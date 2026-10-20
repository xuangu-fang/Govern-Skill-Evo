# V23 统一轮次调度：实现说明

本文件记录正式实现；机制依据为[模块串联与轮次调度设计方案](EVOLUTION_ORCHESTRATION_DESIGN.md)。现有模块算法、Prompt 和输出契约不变。

## 入口与配置

`src/skill_evolution/v23/evolution.py` 提供 `run_round()`、`resume_round()`、`run_campaign()` 及 CLI：

```bash
python -m src.skill_evolution.v23.evolution run --campaign <path> --config <json>
python -m src.skill_evolution.v23.evolution resume --campaign <path>
python -m src.skill_evolution.v23.evolution status --campaign <path>
```

`run_campaign()` 持有非阻塞单写入者文件锁。直接调用 round 函数时，由调用方保证单写入者。`status` 只读，不要求加载环境或连接模型。

配置包含有序 Train batches、Actor Python/模型/50 步协议、模型 call_config、字符与 UTF-8 字节输入预算、三次请求上限，以及正常 no_change 后是否继续。真实实验另保存实际任务 item 与环境文件全文，用于执行前比较。`initial_config.json` 保存初始配置内容，`contract.json` 保存执行源码和 Prompt 原文，不增加哈希字段。冻结的模型配置不含密钥。

开始状态为 null Parent、空 Memory。`state.json` 只有 next_round、parent、active_memory；引用相对 Campaign 根目录。active_memory 指向该状态的 Memory 目录，其 active.json 与 Archive 可由现有 load_memory() 直接读取。

## 模块与配对

依次复用现有 run_grouping、run_diagnosis、run_preconditioner、run_editor。Actor 调用现有 run_task_skill CLI，完整任务通过已有 facts.py 核验后保存实际路径；正常失败也会复用，绝不为提高成功数重跑。

Candidate 必须是 Editor 严格应用后的文本。用 build_replay() 与 build_gate() 读取同批真实执行、验证任务、Skill、协议和初始状态，再保存 pairs。Gate 只比较环境成功数。Replay 保持七字段输入，不接收 Gate 决定。新轮次 Gate 不依赖 Replay 学习输出。

Preconditioner 与 Replay 都使用 round_input.json 冻结的本轮初始 Memory。各阶段 result.json 指向唯一合法 Attempt；读取时再次执行现有模块的输入、配置和来源校验。

## 尝试与恢复

每个模型阶段在 attempts/001、002、003 中独立运行，采用首个合法结果。每次保留请求、原始 HTTP、响应、usage、解析、校验和耗时。只有临时传输错误或已收到响应后的契约错误可以重试；认证、配置、输入容量等错误停止。合法 no_change、need_evidence、空/null Patch、空 entries 不重采样。

Grouping 的 HTTP 响应转换提取为一个共用 response_value()，既有模型解析语义不变。中断后若 response.json 或可恢复的原始 HTTP 已保存，使用原始消息与参数核对并在原 Attempt 的 recovered/ 子目录完成现有模块校验，不增加 API 请求。原始请求结果不可知时保留未知标记和未知用量。

重试耗尽保存 stop.json，run 不会悄悄重启。用户执行 resume 可开始新一组三次尝试，编号延续；有效阶段和任务不再调用。语义阻碍不能通过相同输入的 resume 自动重新采样。

允许显式恢复文件：

```bash
python -m src.skill_evolution.v23.evolution resume --campaign <path> --recovery <json>
```

恢复文件包含 stage、非空 reason，以及可选 call_config。只接受当前技术失败的模型阶段；仅允许该阶段源码/Prompt 的变动及显式参数变动，记录旧内容、新内容和原因。共享实现或已完成上游变化拒绝恢复，需独立 Campaign。未经明确声明的漂移直接报错。真实验证本身不使用临时修改 Prompt 或输出预算的恢复。

Actor 新增可选 `--request-attempts 3 --strict-response`。历史默认行为保留；新 Campaign 显式使用三次单步请求预算，覆盖临时 HTTP/网络、空回复、损坏 JSON和截断，不叠加旧六次重试。实际请求由 RecordingSession 逐次归档。步骤请求耗尽即停止，不在本次 run 自动重跑 episode；用户 resume 时从初始状态新开失败任务 Attempt，完整的其他任务复用，部分轨迹不拼接。

## 原子发布

本轮 Memory 目录先引用上一状态的不可变 Archive（同文件系统硬链接，必要时复制），复制有效索引作为本轮基线，再调用原有 commit_memory()。这样只有本轮待发布索引变化，正式状态引用的旧 Memory 不变。沿用原有身份、提交幂等、证据规范化及修订规则。

Gate、Replay、Memory 准备完成后，写轮次 result.json，验证新 Skill 与 Memory 可读，最后一次原子替换 state.json。ACCEPT 引用 Candidate；RETAIN 引用原 Parent；两者均采用本轮 Replay 后的 Memory。

发布前失败保留旧正式状态。Memory 已准备但未发布时，resume 复用同轮提交，不增加 M ID。发布后中断时，state.json 的 next_round 决定后续位置，不重复提交上一轮。空 entries 可以保存空学习提交，Active 认识保持不变。

## 观测与局限

status 显示正式状态、各轮阶段、Attempt 数和已知 Token。cost_summary() 从全部实际请求记录汇总，失败请求也计入；未知用量单列，不能当成零。Token 预算与金额预算不同；没有可信账单时不虚构货币费用。

正式支持单进程顺序执行。磁盘或进程中断可依靠原子替换与已保存产物恢复，但外部服务无法提供本地 exactly-once：请求已发出而响应未保存时，必须承认结果和消耗可能未知。Actor 环境不做进程内状态恢复，显式 resume 从任务起点开始。

每轮使用同批 Train 作为 Gate 与 Replay 来源，不设置 Validation，Test 不参与演化。小规模运行只能验证接口、恢复和真实更新构造，不能证明泛化收益或历史 Memory 的独立因果效果。

本次验证见[统一调度与恢复报告](../../../experiments/methods/v23/v23_evolution_001/reports/IMPLEMENTATION.md)和[两轮真实验证报告](../../../experiments/methods/v23/v23_evolution_001/reports/LIVE.md)。真实结果以报告记录的完成轮次和停点为准。

## 正式优化池与最终 Test 交接（2026-10-19）

新 Campaign 可以显式设置 `optimization_splits: ["train", "val"]`，并冻结全部 `task_items`。Selection 保留 `val:` ID 与原始 gamefile，Actor 以 `purpose=optimization` 执行；它作为优化证据，而不是独立 Gate 验证集。默认配置仍仅 Train，Test 不允许进入优化。执行前核对 manifest 映射；可显式冻结 `environment_root` 与 `actor_base_url`。

`final_parent(campaign)` 只读核验所有轮次已发布，返回正式 Parent 文件或 `None`。不选择被 RETAIN 的 Candidate。六轮正式准备及相同 Test 的两组配置见[正式实验准备](../../../experiments/methods/v23/v23_alfworld_formal_001/README.md)；该准备没有启动 Campaign 或 Test。

## Actor 任务级并行（2026-10-19）

`actor_max_workers` 默认 1；正式六轮配置为 8，仅作用于同轮 Parent/Candidate Execution。线程池监督独立的既有 Actor 子进程，每条 Episode 独立环境、历史和输出目录；单条动作与跨模块、跨轮顺序保持不变。最多提交 worker 数个任务，完成后补充；失败即停止补充，等待已启动任务保存真实结果再向上抛出停点，不发布下一状态。完成结果按冻结列表顺序交接，不按完成顺序编号。Actor 请求重试仍在原 Adapter 内最多三次，不叠加任务级自动重试；显式 resume 复用合法任务。

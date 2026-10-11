# v19 统一 run / resume

正式入口：`scripts/run_v19.py`。仅服务于新入口创建的当前版本实验；不自动迁移旧 Pilot。

## 启动新实验

在项目根目录执行：

```bash
python scripts/run_v19.py run \
  --config experiments/configs/v19_run/pilot.json \
  --output experiments/v19/pilot/v19_unified_pilot_001
```

`run` 会调用真实模型，输出目录必须不存在。Pilot 是固定 Evolution / Monitor 切分上的最多 **2 轮**，不是减少任务数量。正式实验配置为 `experiments/configs/v19_run/formal.json`，最多 **4 轮**；输出应放入 `experiments/v19/formal/<新名称>`。

JSON 配置只包含 `mode`（pilot/formal）与 `max_workers`（1–32，Replay/Monitor 并发）。Attribution 并发沿用 2。当前协议固定：

Parent Evolution → Current Diagnosis → 逐 edit Memory Review → Issue Fusion → 逐提案 Evidence Review → Compiler / Editor → Candidate Replay → Attribution v19.2 → Monitor / Gate → Memory。

模型配置、预算、契约、Four-Delta Gate 不因统一入口而调整。初始 Skill、任务及配置仍来自冻结 benchmark v4。连接环境从 `.env` 读取，不写入运行绑定。

## 恢复

```bash
python scripts/run_v19.py resume \
  --output experiments/v19/pilot/v19_unified_pilot_001
```

无需重新提供配置。配置和 run_id 从 `binding.json` 读取，源码、初始 Skill、任务及运行 manifest 必须一致；变化时停止并要求迁移。已有锁禁止同一实验并发运行。

- 完成且校验通过的结果复用；已提交 Memory 按权威 head 恢复，不重复提交。
- Replay / Monitor 使用原有逐任务检查点；已完成轨迹不因评估失败而重跑。
- 模型调用发生 `APITimeoutError` / `APIConnectionError` / `TimeoutError` / `ConnectionError` 且无响应时，resume 自动归档该调用，再请求一次。失败再出现则仍停止/记录 INCOMPLETE，不无限循环。
- 进程中断留下请求、但既无响应也无完成标记时，同样保留并重新请求；无法保证远端没有执行过该请求。
- 每个 Diagnosis 分组、历史 edit、Evidence Review 提案、Attribution pair 独立恢复，不重新生成已完成单元。
- 契约修复仍最多一次：若这唯一一次修复本身网络超时，恢复它，不额外增加修复轮数。
- 完整响应截断、拒答、最终契约失败、输入超预算不会被自动清除或盲目重试；需要检查原因。
- 已保存响应但缺完成标记属于检查点异常，停止检查，不直接重发。鉴权等非网络失败也不会自动归档重试。

自动归档位置：`<实验>/recovery/<唯一编号>/`，保存 `receipt.json`（原相对路径、失败类型、文件摘要）与 `call/` 原始调用。归档在各阶段目录之外，不污染阶段完成摘要，也不进入 learner 输入。

## 范围与状态

该入口在前台运行，日志输出到终端；可自行重定向日志。`campaign.json` 记录已完成/失败阶段，细粒度进度见各阶段检查点，提交状态以 `memory/head.json` 为准。

历史两轮 Pilot 经过协议变化及目录迁移，不能直接用此 resume。旧入口及历史实现保留；未使用统一入口的调用依然维持原来显式处理失败尝试的行为。

本次仅实现入口与恢复，并使用构造模型响应进行工程测试，未启动真实实验。当前 Pilot 迁移、第三轮启动均不在此次执行范围内。

## 离线重启：复用 round-01 Current Diagnosis，重建 Memory

使用 `scripts/migrate_v19_memory_restart.py --source OLD --archive ARCHIVE --output NEW`。
该命令不读取 `.env`、不调用模型，只使用本地冻结 benchmark 和已有完整响应。
必须先停止 OLD 的运行进程，ARCHIVE、NEW 必须不存在，三个目录不能互相包含。

它逐文件 SHA-256 核验整份旧运行副本，保留 OLD 不动；在 NEW 中仅导入第一轮
Parent Evolution、Grouping、Current Diagnosis（含相关调用/修复/失败记录）。
旧两轮结果、旧 Memory 和日志只进入整体归档，不进入新 Memory。
归档只覆盖 OLD 目录内文件；外部终端重定向日志需要另行保留。

迁移检查执行配置、冻结数据、任务/seed、上游代码摘要、原始请求/响应完成标记及
Findings 本地契约。任何缺失或不兼容都会停止，不能自动调用模型补齐。
NEW 的 Memory revision 为 0。第一轮 Memory Review 生成空结果，不调用模型。
resume 会校验并复用上游，然后首次调用模型的阶段是 Issue Fusion。

NEW 沿用 OLD 的内部 run_id 和执行清单标识，以保持证据引用不变。它是一个不同输出
目录中的显式实验分支，并非另取 run_id 后伪造旧模型响应。migration.json 记录来源、
归档全文件摘要、复用文件摘要、时间、旧绑定、实际新代码和执行清单以及 Memory 协议。
新 binding 绑定迁移记录摘要。恢复时同时检查当前代码、运行配置、复用文件及归档。
历史清单保留用于证据身份；实际执行代码版本以迁移记录和新 binding 为准。

迁移准备使用独立 `.pending-*` 目录，核验后发布。已有目标一律拒绝覆盖，迁移失败
保留临时目录供检查；不要把半成品当作可 resume 运行。恢复启动失败若涉及网络，使用
普通 resume；若提示代码漂移或证据改变，先调查，不能修改摘要绕过校验。

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo
/Users/didi/miniforge3/bin/python scripts/migrate_v19_memory_restart.py \
  --source experiments/v19/formal/v19_memory_formal_001 \
  --archive experiments/archive/v19/v19_memory_formal_001_before_issue_memory \
  --output experiments/v19/formal/v19_memory_formal_002

/Users/didi/miniforge3/bin/python scripts/run_v19.py resume \
  --output experiments/v19/formal/v19_memory_formal_002
```

正式配置继承旧运行，仍最多运行四轮（可能按已有 NO_UPDATE/UNABLE 机制提前停止）。
原始运行、归档、新运行及临时目录均已被现有 `.gitignore` 规则覆盖。

## 第一轮已提交后迁移 Attribution → Memory 语义

`migrate_v19_attribution_memory.py` 适用于：统一 local/pair 运行，恰好提交一轮，
第二轮尚未进入 generation。必须停止旧进程；三个路径互不包含，目标不存在。

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo
/Users/didi/miniforge3/bin/python scripts/migrate_v19_attribution_memory.py \
  --source experiments/v19/formal/v19_memory_formal_002 \
  --archive experiments/archive/v19/v19_memory_formal_002_before_attribution_facts \
  --output experiments/v19/formal/v19_memory_formal_003

/Users/didi/miniforge3/bin/python scripts/run_v19.py resume \
  --output experiments/v19/formal/v19_memory_formal_003
```

迁移命令不调用模型：复制核验整个旧目录；复用第一轮逐 pair 完整响应生成
attribution_batch_v19.3；通过正式 commit_round_memory 重建 revision 1 及哈希引用链。
使用原始 ledger、Parent/Candidate Replay 和重新校验的 Monitor Gate，验证保留 Skill
不变。旧 Memory、旧汇总和此前 migration.json 都保存在整个归档中。

第二轮 Parent 必须完整且与保留 Skill、原执行清单一致。已完成 Grouping 原样验证；
未完成 Grouping 的完整响应保留，没有响应的中断/网络失败请求在新目录 recovery 中
归档；存在部分响应或非网络失败时拒绝自动迁移。恢复后按普通检查点流程继续。
若第二轮尚无产物，恢复从其 Parent 开始。存在第二轮 generation 时拒绝此入口，
避免悄悄丢弃已生成的 Current Diagnosis 或消费旧 Memory 的下游产物。

新目录保留来源 run_id 和执行清单身份，实际新源码、旧/新 Memory head、第一轮新
record、归档/复用文件摘要及协议写入新 migration.json，并由 binding 绑定。
恢复检查归档、第一轮不可变文件及 Memory 第一条提交。后续网络失败仍使用同一 resume。
正式配置继承旧运行，最多四轮；不重跑第一轮，第二轮开始使用 issue_memory_v19.2。
迁移失败的 .pending 目录保留供检查，已有目标禁止覆盖。外部日志不在源目录内的，
不属于整体目录归档范围。

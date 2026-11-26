# OfficeQA 共同执行环境

2026-10-29 解析输入修订：新实验使用 `data/officeqa/corrected_v2/treasury_bulletins_parsed`，累计修复 21 个单元格并恢复一列 20 个数值；原始下载、corrected_v1 和历史归档保留。构建、校验及恢复边界见 [解析修复 v2](../../docs/benchmarks/officeqa/PARSED_CORRECTIONS_V2.md)。下文执行协议 v2 的原始验收记录不代表修订语料。

当前协议：`officeqa_skilladam_aligned_v2`。以本地 SkillAdam `b6c9640` 为基础，供 Govern-Skill-Evo、SkillOpt、SkillAdam 共用。只完成离线验收；没有模型请求、真实任务 rollout、Stage0 或训练。

## 环境与复核

```sh
conda activate OfficeQA
cd /Users/didi/Desktop/Govern-Skill-Evo
python -m pip check
python -m scripts.benchmarks.officeqa.align --check
python -m pytest tests/adapters/officeqa -q
```

Python 3.12.16，SkillOpt 0.2.0、SkillAdam 0.1.0.dev0，OpenAI SDK 2.54.0。两个项目均从本地源码非 editable 安装。SDK 版本同时满足 SkillOpt `>=1.30` 与 SkillAdam backend `>=2.49,<3`。

从项目根目录重建一个尚不存在的环境：

```sh
conda env create -f benchmarks/officeqa/environment.yml
```

`requirements.lock.txt` 固定当前 44 个 Python distributions；`conda-osx-arm64.lock.txt` 固定 conda 层。同名环境已存在时不重复创建。上游安装源码与本地文件的哈希已在验收报告中核对。SkillOpt 仓库既有 config/trainer/model backend 修改没有重置，不能仅凭包版本号认定安装一致。

## 共同规则

| 项目 | v2 |
|---|---|
| 数据 | 固定 revision `8ecbf18d3833daf4750a903d14963e4c4c1d4cd8`，50/24/172 |
| URL | JSON、换行、逗号分隔字段统一拆成独立链接 |
| 文档映射 | 采用已核对的 `source_aligned`，四题的来源文件列表修正 |
| Actor 输入 | SkillAdam system prompt、用户消息布局、来源页面追加方式、工具 schema |
| 工具 | 原生 SkillAdam glob/read/grep、错误返回、路径校验；限定明确语料目录与逐题文件名单 |
| 页面限制 | 单页 24000、累计 80000 字符；保留原生截断标记和行为 |
| 模型轮数 | 24，最终回答占一轮，没有额外收尾轮 |
| 工具次数 | 不设每轮 8 次和累计 96 次限制；同轮按返回顺序执行 |
| 每轮最大输出 | 调用方逐方法显式传入，没有共同默认值 |
| 初始 Skill | 调用方传入已有文本或明确传入 None，不读取默认 Skill，不执行 Stage0 |
| 停止/答案 | 保留 SkillAdam 非空无工具响应即结束、answer 标签/末行回退、预算耗尽空答案 |
| 评分 | 原生 SkillAdam EM/F1，Actor 结束后访问参考答案 |

原始数据、题面、答案、划分和上游源码均未改写。工具仅能读取显式 `parsed_root/transformed` 下当前题允许的文件；准备后的任务 JSON、CSV、参考答案和原始记录在工具根目录之外。新实验的 `parsed_root` 使用上面的修订版路径。

## 数据和入口

`data/officeqa/prepared_v2/{train,val,test}/items.json` 是共同任务数据；`manifest.json` 固定来源和划分，`mapping_changes.json` 记录四题差异，`source_rows.json` 保留原始 CSV 行，仅用于来源审计，不传给 Actor。`execution.json` 记录共同执行规则及三条入口；其中输出 token 参数为待调用方显式选择，不代表 0 或无限值。

所有入口都调用 `src.adapters.officeqa.runtime.Runtime`，而非分别维护三份 rollout：

| 方法 | 接入类 | 边界 |
|---|---|---|
| Govern-Skill-Evo | `src.adapters.officeqa.bridges.GovernActor` | actor_batch / actor_task / check_record，读取明确传入的 Skill 文件或 None，保存共同轨迹 |
| SkillOpt | `src.adapters.officeqa.bridges.SkillOptAdapter` | 原生 EnvAdapter、loader、rollout 返回值；保存原生 conversation.json 和完整共同轨迹 |
| SkillAdam | `src.adapters.officeqa.bridges.SkillAdamAdapter` + `SkillAdamBackend` | 原生任务请求、execute_batch、parse_result/evaluate；优化器需后续显式绑定 |

构造顺序为 `Dataset(prepared_root)` → `Runtime(parsed_root)` → `ChatTransport(endpoint=完整的_chat_completions_URL, api_key=调用方显式提供, model=明确模型, max_completion_tokens=该方法预算)` → 对应适配器。生产传输直接使用 `requests`，不构造 OpenAI 客户端；模块导入和对象构造不会读取凭据或联网。离线单元测试使用互斥的 `offline_create=固定响应回调`，不能把 SDK 客户端当作该测试接口使用。旧 `create=` 接口已移除。

## 并发、超时和题目级恢复

公共配置由 `src/adapters/officeqa/execution.py` 定义，并写入 `prepared_v2/execution.json`：线程池、每道题一个任务、默认 `workers: 4`，结果按完成顺序收集。同一道题内的轮次和工具仍顺序执行。三条批执行入口是 Govern `actor_batch(...)`、SkillOpt `rollout(...)`、SkillAdam `execute_batch(...)`。Govern 原有 `actor_task(...)` 是单题入口，需要批并行时调用 `actor_batch`。

每轮 Actor 响应生成最多 **6 次总请求尝试，包含首次**。连接超时 10 秒、读取超时 300 秒；直接 HTTP 的内层重试设为 0，禁止自动重定向。请求次数由公共 Actor 独占管理，不改变具体优化器。重试前等待 `2 × 已用请求次数` 秒，所有三种方法使用同一规则。

| 分类 | 行为 |
|---|---|
| 超时/连接失败、HTTP 408/409/429/500/502/503/504 | 当前请求不变，使用剩余额度重试；明确额度耗尽的 429 除外 |
| 空响应、截断、API JSON/响应结构损坏 | 当前请求不变；原始响应及已知 usage 仍归档 |
| 完整响应的工具调用结构错误 | 仅附加最近失败输出和具体校验错误，要求修正；不执行该响应中的任何工具 |
| 合法工具调用的参数值或文件访问错误 | 保留原生工具观察，进入下一轮，不算格式生成重试 |
| HTTP 400/401/403、明确额度耗尽、拒绝或不可重试终止原因 | 停止，恢复也不自动重发 |
| 正常最终答案 | 保留原生答案回退解析和评分，不根据评分重新生成 |

工具结构校验覆盖整轮，包括 JSON 对象参数、调用 ID 唯一性、函数类型和已提供的工具名称。参数窗口/路径等语义仍由原生工具处理。临时纠错上下文为“正式历史 + 最近失败输出文本 + 诊断”；新的格式错误替换旧反馈，技术错误保留当前请求，响应被接受后清除。无效工具调用以文本归档并反馈，不把未匹配的 tool_calls 塞回 API。正式轨迹只包含接受的响应及真实工具观察；所有尝试另存于 `request_audit` 和本地 Actor 检查点。

每题在 `cases/<题目ID的SHA256>/actor_state.json` 保存轮次、正式消息、临时反馈、所有已用请求和工具进度。直接调用 `Runtime.run` 必须提供独立 `directory`。请求发出前原子保存并扣除额度：进程中断且没有持久化响应时，该次仍计入额度；已保存响应先恢复解析，即使它是第六次也不会误判为耗尽。完整保存的最终结果可直接复用。

六次生成额度耗尽记为 `generation_incomplete`，不评分、不写完成结果，恢复不补发额度。同一轮的技术和格式问题共享六次；只有该轮合法响应被接受并完成工具执行后，下一轮才获得新额度。仍最多 24 轮，理论上每题最多 144 次请求尝试；不恢复 8/96 工具调用限制。

每个工具执行前保存 started，观察和正式历史一起原子提交。恢复跳过已完成工具，从尚未开始的工具继续；如果工具已开始但结果未知则停止，不重新请求该轮、不自动重放工具。正常工具错误观察仍按原生语义继续。

每完成一题，主线程向该批目录的 `results.jsonl` 追加 `{"id": ..., "record": 完整共同轨迹}` 并 flush/fsync。重启按题目 ID 跳过已完成题，先保留已保存顺序，再追加新完成题。答错或 24 轮耗尽属于已完成题；六次请求耗尽或技术中断不记零分。批中其他任务允许保存结果，再向调用方抛出错误。

同目录 `run.json` 校验方法、任务、Skill、模型配置和执行配置；不匹配则在调用前报错。日志最后一行因中断而未写完时，只丢弃该尾行；完整行损坏会报错。同目录禁止两个运行器同时写入。日志是恢复依据；缺少的派生 `trajectory.json` / SkillOpt 会话文件可以从日志补建。

**每轮、每阶段、每次独立重复评估使用独立目录**，即使 Skill 相同也不能共享目录。SkillAdam 构造时必须指定 `output_dir=本批目录`；直接调用可以用 `execute_batch(execution, out_dir=另一批目录)` 覆盖，接入原生 EvaluationRunner 时需由 launcher 为各批绑定对应目录。禁止把一个固定目录复用于整个优化过程。SkillAdam 后端返回值和日志按完成顺序；其上游 EvaluationRunner 在评分聚合前仍会按 ID 重排到输入顺序，这不改变执行或写盘顺序。

这些日志是公共适配层的新格式，不自动导入上游旧 `results.jsonl`。重试协议版本进入批次身份，旧的无请求检查点配置不能混用。优化器训练 checkpoint 的机制没有改动。

**这不是三条现有实验命令的自动替换。** 后续 launcher 必须显式实例化上述类；直接运行上游原命令仍会采用原生行为。GovernActor 只实现执行边界，尚不是可绑定完整 V25 优化循环的 Benchmark：OfficeQA 的诊断资源、facts/evidence 和 Gate 适配不在本次环境任务中。两种基线的优化算法、数据池、训练预算与 checkpoint 规则也没有调整。不要把环境验收当作完整方法训练已验收。

## 离线结果与已知问题

全部 246 题的输入和本地工具已检查，493 条页面引用可解析。回归测试使用独立合成题和固定响应，包含三条真实入口各执行 100 次工具调用、差异输出预算、原生 SkillAdam 差分校验、24 轮耗尽、错误恢复、文件范围和答案隔离。

UID0057 原始来源包含 October 公告，且仍发生累计上下文截断；UID0077 的 CY/FY 口径疑点保留。映射修正不等于修改题意、标准答案或修复 OCR。

详见 [v2 对齐验收](../../docs/benchmarks/officeqa/ALIGNMENT_V2.md) 和 [机器报告](../../artifacts/benchmarks/officeqa/offline_v2/report.json)。

`prepared_v1`、`offline_v1` 和原始 ZIP 保留为历史基线；`archive/requirements-v1.lock.txt` 保存旧依赖。旧 prepare.py 的 --check 会比较旧环境快照，因此当前升级后的环境应使用上面的 v2 复核命令。

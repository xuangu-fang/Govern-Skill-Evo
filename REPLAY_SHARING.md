# v28 Replay 轻量去重与离线验收

2026-11-02。实现目录：`/Users/didi/Desktop/Govern-Skill-Evo-memory-opt-20261102`。
以已验收的 Memory 优化为基线；未应用到原 `Govern-Skill-Evo`，未调用模型、恢复训练或推进原实验。

## 实现范围

只调整 Replay 的模型输入展示：

1. 确认恰好一个完成轮次、SearchQA 单轮上下文，以及 `request_messages` 与该 run 的 `initial.messages` 精确相同后，省略前者。条件不满足明确报错。
2. 按完整消息精确比较，跨执行共享相同 system 消息，不假定只有两种 system。
3. 仅在已验证的 Parent/Candidate 配对内，完整 user 消息序列相同时共享；不同配对不共享 user。

使用既有 `shared_initial.messages`、`shared_message` 和 `replay_shared_initial_v1`。共享函数就近移植自冻结 v25.2 工作区的 v25 实现，三个函数的 AST 与原实现一致。`restore_initial` 只用于离线检查初始消息槽位，不在实际发送链路增加通用解码步骤。

每条 run 的 `initial.task`、pairs、执行身份、原引用、响应、结果、计数和顺序保留。顶层 Parent/diff/plan 和 Knowledge-only 历史不变。没有 task 表、模板重建、多轮历史重建或历史引用压缩。

生产改动仅四个文件：

- `src/skill_evolution/v28/benchmarks/searchqa/replay_input_view.py`：95 行，包含移植的精确消息共享与初始消息还原，以及单轮请求省略。
- `src/skill_evolution/v28/benchmarks/searchqa/prompting.py`：仅 Replay 接入展示投影。
- `src/skill_evolution/v28/benchmarks/searchqa/prompts/replay.md`：只调整两处输入描述并增加共享说明；其他学习规则和输出合同保持原文。
- `src/skill_evolution/v28/config.py`：在既有冻结字段记录新的 Replay 输入视图；其余模块视图不变。

现有 Prompt 版本更新为 `v28_searchqa_replay_v2`；现有 Replay 输入视图字段记录 `v28_searchqa_pairs_shared_initial_v1`。没有新增版本管理框架。

`Call.input`、`input.json` 和 Memory 审计继续使用原始完整 bundle；`Call.messages`、`base_messages.json` 和实际请求保存去重后的展示。输出仍针对原完整 payload 验证。原始事实构造、Actor Prompt、评分、Gate、Memory 校验和发布实现均未修改。

## R01–R10 真实输入结果

下表统计完整 system/user 消息数组的紧凑 JSON 字符数，包含新增 Prompt 说明、共享表和消息包装。不是 token 数。

| 轮次 | 原字符数 | 去重后字符数 | 减少 |
|---|---:|---:|---:|
| R01 | 998,723 | 455,959 | 54.3% |
| R02 | 984,658 | 455,719 | 53.7% |
| R03 | 1,149,618 | 456,867 | 60.3% |
| R04 | 1,215,972 | 486,973 | 60.0% |
| R05 | 1,475,895 | 508,605 | 65.5% |
| R06 | 1,661,371 | 506,513 | 69.5% |
| R07 | 1,738,253 | 506,710 | 70.8% |
| R08 | 2,088,119 | 543,744 | 74.0% |
| R09 | 2,338,577 | 567,387 | 75.7% |
| R10 | 2,576,022 | 574,568 | 77.7% |

R10 单独的 user 正文为 2,538,078 → 544,299 字符；完整消息 UTF-8 字节数为 2,576,264 → 574,574。新增 system Prompt 说明约 1,234 字符，已计入上表。

每轮仍为 30 对、60 个独立执行；这些真实输入各共享 2 个 system、30 个 user 消息。展示投影耗时约 6.5–18.0 毫秒，不包含原始归档验证。这些是一次离线测量，非性能承诺。

历史 R10 API 实际输入仍是 567,681 tokens；本次未请求模型，没有新的 API token 用量，也没有按字符比例推算 token 节省。

## 内容、引用与回归

- R01–R10：使用真实 `replay_call()` 构造消息；展开共享初始消息并补回已证明相同的请求后，完整可见输入的确定性 JSON 与原输入一致。原始 bundle 未变。
- 每轮当前/历史允许引用集合一致；原归档 Replay 输出仍通过原有输出验证。共享键不能作为证据 ID。
- 119 项离线测试全部通过：包含 111 项既有测试与 8 项新增测试；网络和外部进程调用被禁止，无模型请求。
- 新增覆盖：多种 system、跨配对隔离、不完全相同的 user 序列、空白/Unicode/元数据、错误请求和轮次、错误共享指针、输入不被修改、真实阶段保存与无生成器恢复、旧 Prompt 身份拒绝。
- 重新验证 2,000 条数据与 4,000 种 Actor 消息构造，Actor 参数保持不变。
- 原目录 7,902 个保护文件、389 项启动清单、81 个 campaign 冻结源码均未变化。

R09 使用原归档 Replay 输出，在独立副本中执行真实的发布主流程。主流程耗时 15.340 秒（含性能分析器与依赖复核），文件打开 36,473 次。时间仅是本次离线测量，不与历史 27 分钟直接计算加速倍数。

- 完整 Memory 加载 1 次、历史提交扫描 1 次、完整 Actor 记录校验 540 次、批次签名 18 次、源码身份重建 1 次，与已验收基线一致。
- 新旧 commit、全部历史 commit、Active、view、知识记录、选中 Skill 和最终发布状态一致；仅隔离副本的 base 源目录路径按实际位置变化。
- 新适配器空缓存审计 9.816 秒，文件内容不变；`memory_prepared` 中断后恢复成功。
- Active、view、历史 commit、Skill、Actor 响应、冻结源码合同六种篡改全部拒绝，正式游标不推进。
- 发布验收隔离层记录一次已阻止的 `socket.bind`，没有模型请求；完整测试阶段网络/进程尝试为 0。

完整结果：

- `artifacts/verification/replay_sharing_inputs/summary.json`：逐轮字符、字节、引用及内容检查。
- 同目录 `R01_messages.json` 至 `R10_messages.json`：实际新展示消息，可直接审阅。
- `artifacts/verification/replay_sharing_regression/validation.json`、`unittest.log`：完整离线回归。
- `artifacts/verification/replay_sharing_r09_publication/summary.json`：R09 完整发布复验。

## 基线与身份边界

已验收 Memory 基线保存在 `artifacts/replay-baseline/files/`，指纹在 `artifacts/replay-baseline/sha256.json`。Memory 实现、原验收脚本和已有 Memory 补丁保持原样。Replay 改动独立形成增量补丁，不覆盖原 Memory 补丁。

- `artifacts/v28-replay-sharing.patch`：相对于已验收 Memory 基线的 Replay 增量。
- `artifacts/v28-memory-replay.patch`：原 Memory 补丁与本次 Replay 增量的合并交付，供对原目录审阅应用；本次未应用。

旧 Actor 归档绑定原源码身份。离线验收仅在测试进程中检查精确的 Memory/Replay 改动白名单，再建立显式身份映射；生产入口仍拒绝直接读取旧身份归档用于续跑。R09 复验复用原发布验收脚本，只扩展测试白名单，不修改生产验证。

离线固定输出验证证明内容、引用和发布合同保持一致，不证明改换展示后模型行为完全一致。

## 复现

在实现目录中执行，输出目录须不存在：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam \
  /Users/didi/miniforge3/envs/SearchQA/bin/python \
  scripts/verification/verify_v28_replay_sharing.py \
  --original-root /Users/didi/Desktop/Govern-Skill-Evo \
  --campaign /Users/didi/Desktop/Govern-Skill-Evo/experiments/campaigns/v28_searchqa600_batch30_20261102_022539 \
  --launch-manifest /Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/searchqa_v28_skilladam_batch30_20261102_022539/launch_manifest.json \
  --output artifacts/verification/replay_sharing_inputs_new
```

同样参数加 `--publication`、换一个新输出目录，执行 R09 完整发布复验；加 `--regression` 则执行全部 v28 离线测试与数据检查。两种选项互斥。

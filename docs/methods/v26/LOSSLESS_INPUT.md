# OfficeQA 专用无损输入视图

2026-10-29。当前策略版本：`v26_officeqa_lossless_input_v2`。无局部历史收益时继续发送 v1 或原始表示；七模块学习 Prompt 版本不变。

这是七模块发送消息前的表示层优化。公共 Actor、任务/页面、工具、原始请求归档、正式事实、七模块学习 Prompt 与输出契约、评分、Gate、重试额度均不改动。没有选择正式模型、token 预算或训练批大小，没有调用模型或启动实验。

## 原则与结构

实现位于 `src/skill_evolution/v26/benchmarks/officeqa/input_view.py`，不是直接调用 SpreadsheetBench 的 timeline 或 code 去重代码。

1. **完整轨迹的正式历史只表达一次。** 在删除每轮重复的 `request_messages` 前，逐轮验证它严格等于 `initial.messages + 所有先前 assistant + 按执行顺序排列的 tool observations`。保留所有轮次、assistant 内容、完整 tool_calls、参数、工具返回、错误、截断标记、答案、评分、计数及引用。`restore()` 逐轮重建原字段；不把排除的临时格式反馈补进正式轨迹。
2. **共享完整且完全一致的初始消息。** `_officeqa_encoding.messages` 保存原消息，`{"officeqa_message":"mN"}` 在原位置引用它。不改变空格、大小写、Unicode、角色或文字。完全一致的 system 可以在本次输入内共享；user 只在同一执行中，或初始 user 完整序列完全一致的显式 Parent/Candidate 配对内共享。不跨任务合并 user；这个初始消息表不收录后续工具结果/assistant，也不拆分相似消息或把不同 Skill 强行合并。局部历史前缀使用独立编码，见下一项。
3. **局部证据不依赖缺失的全轨迹。** Verifier/Repair 的局部 `request_messages` 可引用本次输入中先前已提供的局部上下文的精确前缀，并保留自身后缀。共享限制在同一 run ID、task ID、角色及历史命名空间内；不跨 Parent/Candidate，不取回档案或补充未授权步骤。每个引用的上下文边界、顺序和事件出现次数均可精确还原。单个引用没有共享对象时仍保留完整上下文。完整历史 run 只有在本来就已提供时才使用时间线表示。
4. **配对邻接不变。** 现有事实构造仍先按 task ID 校验配对，保持 pairs 在 runs 前，runs 为 `P1,Q1,P2,Q2,...`。表示层不重新推断或排序配对，也不按轮次编号对齐双方。
5. **全输入可逆。** 编码后先解码并核对整个原 payload，包含数值 JSON 类型、Memory、所有字段及列表顺序。解码还会重新编码核对规范形式，拒绝未知指针、无用表项、混合表示和越过配对范围的 user 引用。引用表键不是证据 ID；引用仍用原来的 `P1:0`、`P1:2_t1`、完整历史前缀等。

模型收到的顶层结构仍保留 parent、plan、pairs、runs、memory 等原字段，只在确实采用编码时增加 `_officeqa_encoding`。模型 system 末尾追加一段解码说明；七模块原学习 Prompt 文件原文不变。Editor 通常没有可去重轨迹，消息保持原样。

局部前缀格式为 `{"officeqa_history":"SOURCE_REF","prefix_messages":N,"suffix":[...]}`：先展开来源的 request_messages，取前 N 个消息，再追加后缀。只能指向 source_records 中先前出现的同执行引用，允许向后引用链，禁止前向/自引用。即使来源上下文更长，也只取 N 个消息。表示引用不增加可引用的证据 ID。编码器选择序列化字符成本最小的精确前缀；解码器检查边界、身份并重新编码验证规范形式。

新增 `partial_history_view.md` 说明只在实际使用局部前缀时追加。包括说明在内，字符或 UTF-8 字节未优于 v1 时回退 v1；v1 仍保留原始表示回退。其他五模块的实际消息与 v1 一致。这个保护检查不是字符到 token 的换算，不声称对任意未知分词器都保证 token 数非增。

## 实际调用与恢复

- Grouping、Diagnosis、Preconditioner、Editor、Replay、Verifier、Repair 都在 `prompting._messages()` 经过同一表示层。
- 特别补齐 `modules.verifier_call/repair_call`，避免辅助 Prompt builder 已优化、Campaign 实际调用却绕过的情况。
- `Call.input`、输出验证使用的事实、Memory archive 均保留原始契约；只有 `Call.messages` 是编码后的模型输入。
- 表示优化发生在临时输出校验反馈追加之前，不改方法重试逻辑或恢复额度。`base_messages.json` 和请求消息保存实际编码及说明，恢复必须精确匹配。
- `prompt_identity` 为七模块记录新的输入视图版本和解码说明哈希；Campaign 的 method freeze 新增 `model_input_view`。Replay 原有配对事实格式独立保留。
- `restore()` 支持原始、v1 和 v2 编码；`prompting._messages(..., input_view=LEGACY/PREVIOUS)` 可构造原始/v1 请求用于离线比较。不会改写旧请求或自动升级已冻结的 Campaign。源码/方法身份已变化的旧 Campaign 仍按现有严格校验拒绝续跑；这不是跨源码版本的恢复迁移。

## v1 离线长度测量（历史基线）

复现命令（只读真实输入、构造合成消息；不执行 Actor）：

```sh
conda run -n OfficeQA python scripts/runs/verify_v26_input_view.py /absolute/path/to/new_measurement \
  --tokenizer-python /Users/didi/miniforge3/bin/python --encoding cl100k_base
```

`--tokenizer-python` 可省略，此时只报告精确字符/字节数，token 为 null。指定时必须已在该 Python 中安装并缓存对应分词器；子进程禁用网络，缺缓存即失败，不下载或安装依赖。本次使用本地 `tiktoken 0.14.0 / cl100k_base`。

token 统计为各 system/user content 的编码长度之和，包含新增解码说明，不含供应商私有 chat framing。**它是参考分词器测量，不是正式模型 API 用量，也不决定正式 token 预算。**

真实 74 题只用于初始可见页面、题目、来源及本地 TXT 切片。所有 assistant 输出、工具事件、结果与分数均是显式合成结构样例，不是实际任务轨迹或模型效果。检查覆盖单轮全题分布及 1/4/8 题、2/8/24 轮压力组合；这些数字是容量样例，不是训练配置。Verifier/Repair 压力样例只选择第一对的 Parent 全轨迹和 Candidate outcome，来源范围单独说明。

74 道题逐题、单轮合成轨迹的合计结果：

| 模块 | 原输入参考 tokens | 优化后参考 tokens | 减少 |
|---|---:|---:|---:|
| Diagnosis | 1,043,321 | 729,677 | 30.06% |
| Replay | 1,886,916 | 919,048 | 51.29% |

选择初始上下文最大的 4 题、每条 8 轮的压力样例：

| 模块 | 原输入参考 tokens | 优化后参考 tokens | 减少 |
|---|---:|---:|---:|
| Grouping | 739,834 | 104,304 | 85.90% |
| Diagnosis | 741,815 | 106,285 | 85.67% |
| Preconditioner | 744,397 | 108,867 | 85.38% |
| Editor | 2,919 | 2,919 | 0% |
| Replay | 1,481,499 | 149,344 | 89.92% |

完整七模块、逐题字符/字节/token 数据、来源指纹与往返校验见 `artifacts/methods/v26/input_view_20261029_001/input_lengths.json`。优化后的长输入仍可能很大；本次没有截断有效证据或自动缩小批次，也没有完成正式模型上下文容量配置。

## 验收边界

新增测试覆盖：完整输入往返、工具错误及多工具顺序、1/2/8/24 轮、24 轮耗尽、临时失败不混入事实、空格/Unicode 精确保留、不同 Skill、同任务配对/跨任务隔离、局部与历史引用、无用/错误指针、原始小输入回退、七模块真实 Call 路由及测量脚本。

现有 Campaign、阶段持久化、格式反馈、恢复及 Actor 回归继续离线运行。固定响应测试验证可逆性与契约不变，不证明模型实际学习效果保持或改善。

最终验收 **348 项通过，新增 34 项**。公共 Actor 的 8 个源码文件、七模块原学习 Prompt 及此前冻结的 196 个基线文件哈希均未改变。报告及源码快照位于 `artifacts/methods/v26/input_view_20261029_001/`，权威长度报告是 `input_lengths.json`；目录内 preliminary/before_review_scope 文件仅保留开发过程测量。

## v2 局部历史增量测量

复现：

```sh
conda run -n OfficeQA python scripts/runs/verify_v26_partial_history.py /absolute/path/to/new_measurement \
  --tokenizer-python /Users/didi/miniforge3/bin/python --encoding cl100k_base
```

脚本从 v1 归档加载原编码器和原说明，验证它与 PREVIOUS 路径生成的消息一致，再比较当前实际消息。报告同时提供原始、v1、v2 策略的长度，增量收益以 v1 为分母。网络、供应商客户端及 Runtime.run 均被禁止；只准备初始消息，不执行实际 Actor。结果包含新说明开销，使用本地 cl100k_base，不包含服务端聊天封装。

74 题逐题构造双方各 8 轮合成轨迹，引用每侧第 2/4/6/8 轮（共 8 个局部引用）的合计结果：

| 模块 | v1 参考 tokens | v2 策略参考 tokens | 本次再减少 |
|---|---:|---:|---:|
| Verifier | 4,552,966 | 2,918,388 | 35.90% |
| Repair | 4,524,476 | 2,889,898 | 36.13% |

压力样例中：4 题 × 双方各 8 轮，引用全部轮次和工具，共 120 个局部引用，Verifier 从 763,446 降至 347,197（54.52%）；1 题 × 双方各 24 轮，共 94 个局部引用，从 1,518,187 降至 236,438（84.43%）。单个引用样例完全回退，36,237 → 36,237。历史命名空间样例也单独测量。

所有轮次、工具事件、评分和审查内容都是合成样例；真实数据只用于题目初始内容和本地 TXT 切片。没有使用模型生成轨迹，未模拟持续增长的 Memory；这些结果不是生产长度预测或上界。没有选择正式 token 预算。

新增测试覆盖精确前缀、相同轮次多个引用、分叉/倒序上下文、历史命名空间、跨角色/任务/执行隔离、错误边界/循环/前向引用拒绝、v1 解码、说明过长回退、实际 Verifier/Repair Call、临时纠错与无生成器归档恢复；其他五模块消息与 v1 相同。最新测量和验收位于 `artifacts/methods/v26/partial_history_20261029_001/`。

v2 最终离线回归 **373 项通过，其中新增 25 项**。公共 Actor 的 8 个文件、七份学习 Prompt、输出契约和 196 个继承基线文件均保持不变。未调用模型或启动实验。

剩余重复包括：完整 run 与局部引用之间的重叠、各引用自身 call/observation 与历史中相同事件的重复、历史 execution_context，以及跨执行完全相同的文档内容。此次没有合并这些部分。真实长证据、Memory/Skill 增长和模型实际 token 容量仍需单独处理。

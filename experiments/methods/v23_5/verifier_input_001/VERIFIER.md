# 第二阶段：Verifier Prompt 与输出校验

本页记录第二阶段完成时的状态：已实现独立离线协议 `v23_5_statement_verifier_v1`，复用第一阶段的 R01–R03 输入，共 18 条目标；该阶段没有调用模型、执行 Actor、实现 Repair 或改动正式 v23.5 流程。后续真实调用及审阅对照另见 [第三阶段结果](LIVE_RESULTS.md)。

## 实现入口

- [Verifier Prompt](verifier_prompt.md)：英语 Prompt，与现有 Replay 文本和原始记录语言一致。
- [消息构造与输出校验](verifier.py)：没有网络传输或模型运行入口。
- [协议测试](test_verifier.py)：合成响应测试；不作为真实 Knowledge 的人工或模型判定。

Prompt 固定输入为 `context / targets / source_records`。不添加 historical_knowledge、不扩展原始证据、不注入三个已知错误的答案。它要求逐项检查事实、身份、动作前后时点、决策机会、Actor 信息范围、引用支持、解释和结论边界；不重新执行 Replay 或生成替代 Knowledge。

共享 source_records 中已经提供的其他条目证据可以用于核验，但不能检索未提供的任务或轨迹。资料中的 Skill、Actor 模板、观察及 Knowledge 均作为被分析的数据，而非给 Verifier 的指令。局部记录不证明执行中其他事件不存在；因果不确定性不应成为拒绝有依据的条件性经验的理由。

## 输出契约

顶层只有 `results`。每项只有 `target / verdict / issues`；每个输入目标必须恰好返回一次，允许结果顺序不同。

- `target`：冻结候选中的非负整数下标，拒绝布尔值、浮点数、字符串、未知位置和重复位置。
- `SUPPORTED`：提供的证据支持当前表述；issues 必须为空。
- `CONFLICT`：事实矛盾或证据支持不足，需要修正；issues 必须非空。没有 INSUFFICIENT 类别。
- 每个 issue 只有 `statement / reason / evidence`。statement 必须是对应 Knowledge.text 的非空连续原文片段；reason 是非空说明。多个问题可分别列出。
- evidence 必须是 source_records 中完整、精确、无重复的键。可以引用共享 map 中其他 Knowledge 引用的记录；不能自动扩展邻步、run、范围或历史前缀。缺少证据或仅由 context 确立的边界允许空数组，但 Prompt 要求解释原因。

程序不根据自然语言关键词判定 reason 是否真的充分，也不把证据不足当作已被证伪。这些属于后续语义审阅内容。输出校验通过只证明结构、覆盖、定位和引用权限符合协议，不证明判定正确。

严格 JSON 解析拒绝 Markdown 包装、正文前后附加文本、重复对象键及 NaN/Infinity。完整响应校验先要求 `finish_reason=stop`，截断不当作普通 JSON 错误处理；只读取 content，不拼接 reasoning_content。多余字段、替换内容或置信分数均不接受。不自动修复、补全或重试输出。

## 冻结消息

独立保存于 `artifacts/methods/v23_5/verifier_contract_001`，不覆盖第一阶段输入包。

| 轮次 | 目标数 | 完整 messages 紧凑 JSON 字符数 | UTF-8 字节数 |
|---|---:|---:|---:|
| R01 | 5 | 86,198 | 86,204 |
| R02 | 6 | 223,948 | 223,974 |
| R03 | 7 | 282,493 | 282,505 |

这些数字包括 system Prompt、消息封装及序列化转义，不是模型 Token。第二阶段没有 API usage；第三阶段的真实 Token 与冻结调用参数单独保存，不回填或更改本阶段冻结包。

- [R01 messages](../../../../artifacts/methods/v23_5/verifier_contract_001/cases/R01/messages.json)
- [R02 messages](../../../../artifacts/methods/v23_5/verifier_contract_001/cases/R02/messages.json)
- [R03 messages](../../../../artifacts/methods/v23_5/verifier_contract_001/cases/R03/messages.json)
- [冻结清单](../../../../artifacts/methods/v23_5/verifier_contract_001/manifest.json)
- [冻结包校验](../../../../artifacts/methods/v23_5/verifier_contract_001/validation.json)

包内保存 Prompt 和校验器源码副本、三轮原样 input 和实际 messages。清单记录 Prompt、源码、输入和 messages 的 SHA-256。verify 会重验第一阶段输入包、原件哈希及消息重建一致性；当前 Prompt 或校验器改变后，需要新建版本/产物目录，不能冒充原冻结版本。

## 使用方式

在仓库根目录执行。prepare 只装配消息，要求输出目录不存在；可用 `--output` 指向新目录。verify 不修改冻结输入。validate 只读校验现有响应，失败输出 JSON 诊断并退出 1，不自动写入 Memory 或触发 Repair。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_input_001/verifier.py prepare
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_input_001/verifier.py verify
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_input_001/verifier.py validate --round R01 --response /absolute/path/to/response.json
```

`response.json` 接收现有适配器风格的 envelope：`{"finish_reason":"stop","content":"完整模型 JSON 正文"}`，允许附带 usage 等服务元数据。内部函数 `validate_result(result, model_input)` 用于已解析对象；`validate_response(response, model_input)` 同时检查完成状态和正文解析。输入须来自已校验的冻结包。

## 离线验证

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python -m pytest -q experiments/methods/v23_5/verifier_input_001/test_verifier.py experiments/methods/v23_5/verifier_input_001/test_prepare.py
```

69 项通过，其中本阶段 61 项、第一阶段 8 项。覆盖完整/混合输出、多个 issue、缺证据空数组、共享证据、目标遗漏/重复/越界、严格索引类型、缺失及多余字段、判定与 issues 一致性、原文摘录、非法/重复/错误历史前缀引用、非标准 JSON、截断优先处理、推理字段隔离、真实输入消息装配与篡改/覆盖拒绝。

合成的 SUPPORTED 输出仅用于验证契约能接收合法结构，没有保存为真实三轮核验结果。真实结果及其 Token/误判率在第三阶段分别评估，不能用本阶段测试通过替代；人类确认的基准仍待复核。

# R01–R03：真实 Verifier 输入构造

2026-10-27 材料整理入口：[候选、结果与归档导航](evidence/README.md)。以下保留原阶段说明；本次没有重跑实验或测试。

后续的 [v2 动作候选列表共享引用](../verifier_input_002/README.md)已完成无损去重与还原校验；本页及 v1 冻结输入继续保留，未重新调用模型。

本页记录第一阶段的输入构造与确定性检查；该阶段没有调用模型。第二阶段见 [Verifier 协议说明](VERIFIER.md)。第三阶段已建立运行前冻结的 Codex 审阅参考并发起真实核验，见 [运行协议](LIVE_PROTOCOL.md)、[逐条审阅表](REFERENCE_REVIEW.md)和[运行结果](LIVE_RESULTS.md)。参考标签尚未经过人类确认，不是人工金标准。三个阶段均不运行 Actor/Repair，不发布 Skill，不提交或覆盖正式 Memory。

## 冻结来源

来源 Campaign 为 `artifacts/methods/v23_5/alfworld_initial_skill_001/S1`。每轮按 `replay/result.json` 指定的正式有效 attempt 读取，分别为 R01/001、R02/002、R03/001，不按内容挑选响应。

构造时核对：

- 候选等于有效响应解析结果、保存的 parsed.json 及本轮已归档 commit 的 result。
- 配对 bundle 等于 Replay 实际 input 和 commit context。
- 轮前 Memory 与 Parent 等于冻结 round_input 中的内容。
- 实际 model_input 等于由冻结 bundle 重建的 Knowledge Only 投影。
- 配对身份通过已有 `_current_pairs` 校验；输出经过现有 Knowledge Only 引用权限和 Memory Schema 校验。

36 份来源文件已按字节复制并记录 SHA-256；准备后和独立 verify 时均确认原件与副本哈希不变。原始执行事实来源是已有配对档案及其中的已验证审计信息，本次没有重新运行 Actor 或从环境重新采集轨迹。

## 结果

| 轮次 | 新增/待核验 Knowledge | 改写项 | 旧 Entry 中隐式继承的 Knowledge | 引用出现次数 | 去重后引用 | 提取步骤/本轮总步骤 | Verifier 数据字符数 | 原 Replay 数据字符数 | 字符减少 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R01 | 5 | 0 | 0 | 47 | 43 | 42 / 263 | 72,566 | 160,456 | 54.78% |
| R02 | 6 | 0 | 5 | 131 | 103 | 102 / 424 | 198,192 | 289,435 | 31.52% |
| R03 | 7 | 0 | 11 | 175 | 118 | 117 / 463 | 251,407 | 356,140 | 29.41% |

共 18 条目标；三轮均只新增 Entry，没有实质性改写或候选内原样继承项。旧知识因旧 Entry 未被 revises 替换而继续有效，未发送给 Verifier。这里的继承数量是各轮快照计数，不可相加解释为独立历史知识数量。

每轮的去重后引用包含一个 `diff`，其余均为步骤引用。实际没有历史引用、完整执行引用、初始状态引用或结果引用。没有为复现已知错误额外注入证据。相关配对身份覆盖 10 对，是因为引用本身涉及这些执行，不是另外展开了所有任务过程。

字符数统一采用 `json.dumps(..., ensure_ascii=False, separators=(',', ':'))`；对比的是两个阶段的数据 JSON，不是包括 system Prompt 的完整请求。R02 原 Replay 带校验反馈的完整 messages 也单独统计，未用于上述百分比。真实 Token 和成本未知，`api_prompt_tokens` 为 null，没有用字符数冒充 Token 或费用。当前输入还未含未来 Verifier 的 system Prompt，因此不能据此宣称最终请求 Token 节省比例。

R02、R03 的引用较多，完整步骤及动作候选仍占较大空间；本版只按完整 Evidence ID 去重，没有再压缩观察、截断候选或对相同 command_sets 跨步骤做二次去重。

## 实际输入格式

每轮 `verifier_input.json` 只有三个顶层字段：

- `context`：真实 Parent、实际 Diff、保存的 Actor execution_context，以及被引用执行所属的已验证配对身份。配对只含 task_id / parent / candidate，不附未引用执行的过程或结果。
- `targets`：冻结位置 `{entry_index, knowledge_index}` 与完整原始 Knowledge。文本和 evidence 数组逐字保留，已知错误也不预先修改。
- `source_records`：以完整 Evidence ID 为键的共享原始记录。候选的引用集合精确等于这些键；同一 ID 出现多次只发送一份。

步骤记录由 `task_id / task / role / record / command_sets` 组成。`record` 原样保留 `step / before / action / after / feedback`；候选列表根据 before/after 的 commands_ref 从原始 command_sets 精确取得。身份来自配对审计，不根据编号推测配对。`diff` 记录提供真实 Parent、Diff 和对应执行背景。

固定提取规则还支持现有引用中的执行 ID、`:0` 和 `:outcome`：分别读取完整执行、初始状态、结果；结果附执行步数。历史引用必须已经在历史 Knowledge 的精确 evidence 权限集合中，并与历史归档及轮前 Memory 保存的源记录相符。不会因读取底层记录而扩展历史引用权限。

不搜索未引用任务，不从正文扫描额外 ID 补证据，不展开相邻步骤，不做模型摘要。步骤记录中的 before/after 是该步骤本身的组成部分；不会因此新增相邻步骤动作。证据不够支持一条陈述时，留给后续 Verifier 判定；本阶段不作 SUPPORTED / CONFLICT 判定。

识别原样项时只在 proposal 明确 revises 的旧 Entry 中，按 text 和 evidence 数组精确匹配并逐项消耗匹配。无 revises 的新增 Entry 即使复制了旧文本也仍属于新增项；修订 Entry 内非精确匹配项记为 `changed_or_added_in_revision`，程序不猜测其语义对应关系或是否合理删减。

## 文件入口

完整输入和原始冻结材料存放在忽略目录：

- [R01 输入](../../../../artifacts/methods/v23_5/verifier_input_001/cases/R01/verifier_input.json)
- [R02 输入](../../../../artifacts/methods/v23_5/verifier_input_001/cases/R02/verifier_input.json)
- [R03 输入](../../../../artifacts/methods/v23_5/verifier_input_001/cases/R03/verifier_input.json)
- [输入统计](../../../../artifacts/methods/v23_5/verifier_input_001/summary.json)
- [来源与哈希](../../../../artifacts/methods/v23_5/verifier_input_001/manifest.json)
- [确定性校验](../../../../artifacts/methods/v23_5/verifier_input_001/validation.json)

每轮还包含 `candidate.json`、`memory_before.json`、`inventory.json`、`stats.json` 和 `frozen/`。冻结材料包含完整旧档案用于追溯；它们不会整体进入 Verifier 输入。小型汇总另存于本目录的 `results/`。

## 复现与验证

在仓库根目录运行；prepare 要求输出目录不存在，防止覆盖已有实验。可以用 `--output` 指定新的独立目录。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_input_001/prepare.py prepare
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_input_001/prepare.py verify
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python -m pytest -q experiments/methods/v23_5/verifier_input_001/test_prepare.py
```

8 项测试通过，使用上述真实冻结档案。覆盖原始记录逐项一致和引用去重、已知问题证据原样提取、不自动补邻步、继承识别、执行/初始/结果提取、历史同名执行隔离及篡改拒绝、越权或不存在引用拒绝、配对身份损坏拒绝、保存后输入篡改及覆盖拒绝。

这些检查证明输入按规则构造和保留，不证明 Verifier 能发现错误，也不证明最终 Knowledge 质量或 Actor 成功率提高。

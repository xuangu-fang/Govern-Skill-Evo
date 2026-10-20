# V23.2：历史搜索进度集中性与共享能力说明对照

日期：2026-10-19。先只读核查历史输出并冻结分类，再决定是否调用模型。本次集中性达到预设门槛，允许固定 R03、R06 各一次 Preconditioner。最终结论见[完整报告](reports/REPORT.md)。

## 唯一实验变量

使用正式 V23 `S1/contract.json` 冻结的 Diagnosis／Preconditioner 原模板，仅显式覆盖共享背景中的历史能力说明。不继承前两轮 V23.2 的可执行性检查文字，不改原 V23 文件或旧实验档案。本次未调用 Diagnosis；核对其配置是为了明确候选方案的继承关系。

- [调用前冻结的集中性核查](reports/CONCENTRATION.md)：13 份 Plan，4 类去重的信息缺陷；另列 5 组其他语义问题和 2 项不确定性。
- [唯一能力说明 Diff](config/context.diff)与[完整背景模板](config/execution_context.md)。
- [原始 Prompt 核对](results/prompt_checks.json)：对正式冻结契约核验，不以 Git HEAD 作为基准。
- [最小调用适配 Diff](config/adapter.diff)：既有 V23.2 局部入口增加可选 `context_path`，默认行为不变。
- [冻结材料／参数](config/plan.json)与[实现及核查快照](config/implementation.json)。
- [离线测试](reports/offline_tests.txt)：600 passed、19 subtests passed；禁用网络及环境进程。
- [四版本输出全文](reports/OUTPUTS.md)、[运行日志](reports/live.log)和[原始产物](../../../../artifacts/methods/v23_2/v23_2_capability_001/)。

## 固定输入与调用边界

R03／R06 的 Parent、Original Plan、Grouping、当前执行事实、历史证据、当轮 Active Memory 和模型参数均取自原正式实验，与前两轮相同。R03 的 Memory 为 M1/M2/M3，R06 为 M1/M2/M6/M7/M9/M10/M11。R06 沿用原优化池中的 Selection 身份，不混入 Test。

容量沿用当时配置：R03 为 1,000,000 字符／1,500,000 UTF-8 字节；R06 为 4,000,000／6,000,000。输出上限、temperature、Thinking、重试判定不变。每组最多首次加两次技术重试，合法语义结果立即结束该组；原始失败和成功输出全部保留。没有压缩 Memory 或扩大容量。

## 运行方式

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /tmp/gse-v23-py313/bin/python \
  experiments/methods/v23_2/v23_2_capability_001/run.py prepare
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /tmp/gse-v23-py313/bin/python \
  experiments/methods/v23_2/v23_2_capability_001/run.py run
```

已有原始产物时拒绝重新分配调用预算。重读档案须显式传入原 V23 `prompt_path` 和本实验 `context_path`，继续严格核对消息及确定性编译结果。使用旧 V23.2 模板读取本实验应失败。

本入口只复用既有材料读取、V23 输入装配、契约、编译和请求机制，不执行 Editor、Candidate、Replay、Actor 或 ALFWorld，不写 Memory，不开展第二项优化或正式六轮实验。单次固定输入的文本改善不构成严格因果证明或 ALFWorld 成功率提升证据。

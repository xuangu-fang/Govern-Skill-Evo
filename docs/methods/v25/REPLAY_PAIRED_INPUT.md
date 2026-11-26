# Replay 配对输入布局恢复

2026-10-28。本次只恢复 v24 已有的 pairs 前置及配对邻接；不修改 Replay Prompt 的学习要求，不增加去重，不运行模型实验。

同日后续更新：当前默认已升为 [共享初始消息输入视图 v3](REPLAY_SHARED_INITIAL.md)，保留本文 v2 布局与兼容路径。下文是配对布局恢复时的实现与离线验证记录。

## 迁移缺口与实现

v24 的 `evidence_contracts_replay_view._current_pairs` 按已验证的 pairs 顺序，将每对 Parent、Candidate 加入模型视图；`evidence_replay_view.model_input` 将 pairs 放在 runs 前面。
v25 的 SpreadsheetBench 适配器保留了配对身份校验，但直接返回原始 payload 的 runs 顺序，模型输入也沿用原字段顺序。在此前 R05/R06 中表现为 P1…P15、Q1…Q15，以及 runs 后才出现 pairs。

新布局在 `src/skill_evolution/v25/replay_view.py` 中、适配器完成原有校验后构造，只改变模型视图：

| 项目 | 旧视图 | 新视图 |
|---|---|---|
| input_view | `v25_replay_pairs_knowledge_only_v1` | `v25_replay_pairs_knowledge_only_v2` |
| 字段顺序 | parent、diff、plan、runs、pairs、memory | parent、diff、plan、pairs、runs、memory |
| runs 顺序 | 保持原 payload 顺序 | 按 verified pairs 顺序，每对先 Parent、后 Candidate |
| 每条 run 的内容与内部顺序 | 完整保留 | 完整保留 |
| Memory、引用、评分、执行证据 | 原内容 | 原内容，无筛选或补充 |

排序依据是 pair 中显式的 `parent`/`candidate` 引用，而非编号推测或原数组位置。原有配对身份、覆盖范围、任务与执行来源校验仍先执行，不按 attempt 编号对齐两侧。没有引入 v24 运行依赖。

## 版本与归档兼容

- 输入视图版本独立于 Prompt 版本。本页实施时 Replay Prompt 为 `v25_replay_evidence_calibrated_v2`；后续已更新为 [Replay v3](REPLAY_CONDITIONAL_COMPARISON.md)，配对布局不变。Preconditioner 仍默认 `v25_preconditioner_evidence_decision_boundaries_v7`。
- `messages_for`、`run_replay`、`load_replay` 和输出引用校验均支持两个输入视图；新运行默认新布局，读取归档时使用其保存的 `run.json.input_view`。
- 旧视图保留原 user 消息的字段与记录顺序，可精确重建旧请求。旧 Prompt v1 和当前 Prompt v2 均能搭配旧视图读取。
- 原始 `input.json` bundle、Memory archive、既有模型请求及实验结果不重写。只篡改版本标签而不改变请求内容会校验失败。
- 新视图在原有时间线投影之前构造。timeline 仍只执行原去重，临时校验反馈仍在原始两条消息之后追加；技术重试和格式修正规则不变。
- 方法默认配置及未来 batch15 配置同步新 input_view。旧 campaign、既有单模块实验及其冻结契约不升级。能够重读旧归档不意味着可以绕过冻结源码检查续跑旧 campaign。

## 本次没有做的去重

没有共享跨 run 的 Actor system，没有合并配对双方任务输入，没有删除或合并 response/executed_code。原来的 request_messages 时间线去重保持不变。本次只重排，消息字符数不因布局变化而减少。

## 离线验证

- 46 项测试通过：新输入视图、Replay Prompt 版本、时间线、配置和流程测试。使用固定响应及临时合成任务，不调用真实模型或执行模型生成代码。
- 新增覆盖：两个视图在时间线投影前后仅顺序不同；乱序 runs 仍按 verified pairs 排列；无效配对拒绝；旧视图搭配两个 Prompt 版本可只读重载；伪改版本拒绝；格式反馈沿用相同 base messages；默认 Prompt 与 Preconditioner 不变。
- 原始训练 R01/R04/R05/R06，以及此前 Replay v2 Prompt 的 R05/R06 六份归档，按保存版本只读重建。验证新布局没有遗漏/改变任何 run，system、Memory 和其余输入字段不变；具体结果见下方校验记录。

离线记录：[replay_paired_view_v2_offline_20261028_001](../../../experiments/methods/v25/replay_paired_view_v2_offline_20261028_001/reports/README.md)。

上述检查验证布局、兼容性和证据完整性，不证明新布局改善了 Replay 的程序比较或经验概括。

# Knowledge Only：R03–R06 单轮冻结对照

## 问题与假设

Knowledge Only 能否减少跨轮历史输入，同时保留 Preconditioner 的 D/S/C 判断与
Replay 的条件性知识？假设是输入 token 会减少；判断质量与知识保留需要单独核查，
不能由结构有效、输出较短或逐字保留率推定。

## 冻结来源与对照边界

来源为 `artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1` 的正式 R03–R06，
按各阶段 `result.json` 指定的有效 attempt 读取，不挑选任意一次响应。
原版本加载器校验 Grouping、Diagnosis、Preconditioner、Editor、Replay 来源链；
再用原始 Actor records 重建当前配对，核对实际 Diff、Parent、Effective Plan 和任务身份。

每轮只复制 `round_input.json` 指定的轮前 Memory 的 active index 与其 commits。
commit ID 必须来自该轮之前，重载后的 Memory 必须等于两个模块当时的输入。
R03/R04/R05/R06 分别从 R02/R03/R04/R05 的 Memory 快照出发，彼此独立，不串联新输出。

这属于历史输入评估边界，不伪装成 V23.5 生产来源链。不重跑 Diagnosis、Editor、
Actor 或 Gate，不发布 Memory 或 Skill。两组均使用 V23.5 Preconditioner 微调、
无行号补丁契约及相同输出 schema；Replay 使用 v3/P4 或 Knowledge Only 配套 Prompt。
历史 Original Plan 保持不变，所以这不是完整 V23.5 方法的效果测试。

Preconditioner 与 Replay 独立评估。Replay 固定使用历史实际 Effective Plan、Diff
及配对轨迹，不使用本次 Preconditioner 的新方案，也不把旧轨迹归因于新方案。

## 固定配置

配置见 [config/protocol.json](config/protocol.json)。4 轮 × 2 模块 × 2 视图 = 16 个单元。
每单元取第一个结构有效响应，不按语义质量选择；最多三次总请求，含 resume 前的请求，
因此最多 48 次。每单元仅一个样本，不能据此得出稳定统计或泛化结论。

模型与路由沿用正式实验配置，temperature=1.0、reasoning_effort=medium、thinking enabled。
两组所有单元统一输出上限为 32,768：正式 R03/R04 Preconditioner 的有效尝试已使用该上限。
该预算同时用于两组，固定不增长；不是直接复用旧实验各次不同预算的成本。
输入上限为 4,000,000 字符、6,000,000 UTF-8 字节，超限在准备阶段报错，不截断。
模块顺序固定；奇数轮先 v3、偶数轮先 Knowledge Only，减少固定先后顺序的偏差。

只对技术性失败（如截断、JSON/接口/引用/补丁校验失败和允许重试的网络错误）重试。
重试发送同一份消息，不追加失败反馈、不修补输出、不更换 Prompt/视图、不扩大预算。
达到三次上限后 resume 不补充额度。中断前已落盘的响应会重新校验而不重新请求；
无可恢复响应的请求计入尝试，usage 标为未知。非重试错误直接停止该单元。

## 产物与校验

实现入口：`python -m src.skill_evolution.v23_5.comparison`。
原始材料放在被忽略的 artifacts 下；实验协议和小型报告在本目录。

- `freeze.json`：来源目录、模型配置、单元顺序和版本。
- `cases/Rxx/`：原始材料、独立轮前 Memory 档案、两组实际 messages/model_input/Prompt。
- `input_checks.json`：无未来 Memory、来源链、配对重建、当前事实及 Knowledge 一致性检查。
- `runs/Rxx/module/arm/attempts/NNN/`：消息、响应、usage、解析、验证、错误和请求参数。
- `reports/summary.json`、`cells.csv`、`REPORT.md`：成本、结构信号和匹配单元差异。
- `reports/review_material/`：Original/Effective Update、实际 Update Diff、逐项历史知识核查材料。

保存/重载直接比较实际消息与参数，检查输出结构、引用权限和重试次数。
原始记录在准备阶段通过已有加载器读取；v3 的历史视图直接复用其已验证的输入。
保留输入、Prompt 与配置记录即可，不扫描全部来源文件，不保存整套源码快照。
普通代码维护或 JSON 排版变化不会阻止实验；修改实验输入或参数时另建一组对照。

## 统计口径与语义核查

字符数和 UTF-8 字节数只描述消息大小，不冒充 tokenizer 或 API token。
真实 token 来自每次响应的 usage；缺失值为 null，同时提供 known_* 已知部分与缺失次数。
所有失败尝试均纳入成本，并分别提供首次请求输入 token 与含重试累计 token。
不推算服务价格。API 返回的实际 response_model 保留在每次尝试统计中。

Preconditioner 统计 Keep/修改/撤回、D/S/C、Checks 与历史引用，附前后文本供核查。
Replay 区分未修订条目、逐字保留项、需要语义核查的非逐字保留项。
“非逐字保留”可能是合理收窄、合并或遗漏，程序不自动裁定。
所有 semantic_verdict 保持 null，不增加额外评判模型调用。

核查重点：判断是否针对当前问题、是否忠实使用历史条件与反例、是否无依据断言、
是否丢失仍成立的知识，以及是否过度泛化。固定轨迹不证明新 Skill 成功率提高。

## 执行命令

在仓库根目录执行。prepare / verify / summarize 不发模型请求。
run / resume 调用配置中的真实服务；不会调用 Actor。

```bash
python -m src.skill_evolution.v23_5.comparison prepare \
  --source artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1 \
  --root artifacts/methods/v23_5/knowledge_only_single_round_001 \
  --config experiments/methods/v23_5/knowledge_only_single_round_001/config/protocol.json

python -m src.skill_evolution.v23_5.comparison verify \
  --root artifacts/methods/v23_5/knowledge_only_single_round_001

python -m src.skill_evolution.v23_5.comparison run \
  --root artifacts/methods/v23_5/knowledge_only_single_round_001

python -m src.skill_evolution.v23_5.comparison resume \
  --root artifacts/methods/v23_5/knowledge_only_single_round_001

python -m src.skill_evolution.v23_5.comparison summarize \
  --root artifacts/methods/v23_5/knowledge_only_single_round_001
```

`--rounds R03 --stages preconditioner --arms memory_v3 knowledge_only` 可以只运行指定单元。
默认一次运行全部 16 个单元；部分运行的报告会明确显示尚未运行的单元。
运行时读取现有环境凭据，并检查 OPENAI_BASE_URL 与冻结配置相同；凭据不写入产物。

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](README.md)。

# v19 第 2 步：edit 账本与跨轮追踪

日期：2026-09-21。状态：第 2 步独立实现；没有接入 v19 运行调度、训练回放、归因模型或持续经验 Memory。

## 1. 实现范围

- `src/skill_evolution/edit_tracking_v19.py`：生成/重验完整 edit 账本、确定性重建 Candidate、核验历史连续性、生成当前规则来源视图。
- `src/skill_evolution/edit_tracking_store_v19.py`：账本与跨轮审计快照的不可覆盖保存、摘要校验、读取后重验。
- `tests/skill_evolution/test_edit_tracking_v19.py`：构造的多轮操作、边界和故障测试。

仅以只读方式复用现有 Compiler / Editor 的纯函数接口和引用解析。v18 文件、Prompt、配置与历史产物不变；模块不调用模型、回放任务或 Monitor。

依据：[第 1 步数据契约](V19_DATA_CONTRACT_AND_FLOW.md)。本步实现其中的 EditRecord 与跨轮追踪部分；ReplayPair、AttributionRecord、RoundMemoryRecord、MemoryContext 尚未实现。

## 2. 生成完整账本

入口：

```python
from src.skill_evolution.edit_tracking_v19 import build_edit_ledger

ledger = build_edit_ledger(
    run_id="v19-example",
    editor_input=editor_input,       # 当前已绑定的 EditorInput
    raw_response=raw_response,      # 纯 DELETE 为 None
    candidate_skill=candidate,     # 精确原始文本，包括空字符串
    history=(),                    # 已完成决策的先前轮次，按时间排列
    related_history=(),            # 显式的修改意图关联，可为空
)
```

输入首先经过既有 Compiler 来源/计划检查和 Editor 确定性应用校验。应用结果必须逐字等于给定 Candidate；NO_UPDATE、UNABLE、无效计划或错误文本都不能发布账本。一个合法 Candidate 的所有单元必须完整记录，纯 DELETE 也产生账本。

`EditLedger` 是不可变的序列化输入/输出容器；`.source` 和 `.payload` 每次返回新对象，不向调用方暴露可原地篡改的内部字典。

每条 EditRecord 保存契约要求的操作、原始目标块、实际应用的 after_text、gap 引用、来源证据和历史关系。after_text 包含应用器补齐的末尾 LF；原始模型响应另外保存在输入审计中。段间分隔符按同一应用规则重建，不把它们误标为某条规则的语义内容。

`edit_id` 绑定 run、round、完整计划摘要、Candidate 摘要及原始单元索引。额外绑定 Candidate 摘要是必要的：同一个计划可以被 Editor 表达成不同文本，这些不能共享同一个修改身份。

所有记录再次经 v19 文本拼接重建 Candidate，与既有应用器的结果对照。CRLF、Unicode、非连续目标和非目标原文均保留；不做全文格式化。

## 3. 证据与历史关系

`source_gap_refs` 指向原始 Diagnosis 和 gap_index。`source_evidence_refs` 使用 v19 的 EVIDENCE ID，绑定 run、round、Diagnosis、引用类型和原引用；账本中的 evidence 目录保存解析后的轨迹事件或可见 policy。不会把同名的跨轮局部引用当成同一证据。

完整原始 Diagnosis 输入、来源元数据、原始响应及计划保存在账本输入审计中。读取时重建并重新验证，不能仅信任 `VALID` 或已经落盘的来源摘要。

`related_history` 的输入形式：

```python
related_history = [{
    "edit_unit_index": 0,
    "prior_edit_id": earlier_edit_id,
    "relation": "RETRIES",          # 或 REVISES / REVERTS
    "basis_refs": [earlier_evidence_id],
}]
```

校验同 run、较早轮次、有效单元索引、非空唯一依据及引用归属。依据必须来自这次修改或所关联历史修改的来源证据；不接受 Monitor 引用、任意字符串、同轮/未来 edit 或重复冲突关系。

当前还没有 AttributionRecord，因此本步不接收尚不存在的归因 ID。第 4–6 步接入时，应通过有类型且可解析的归因来源扩展依据目录，不通过放开任意引用绕过验收。

关系只记录修改意图，不证明语义正确、已解决或已经部署，也不授予新的修改范围。即使没有显式关系，已接受修改对已有文本的实际覆盖仍会被结构追踪发现。

## 4. 决策、内容绑定与来源分别表达

```python
from src.skill_evolution.edit_tracking_v19 import DecidedEdits, trace_edit_history

history = (DecidedEdits(ledger, "RETAIN"),)
view = trace_edit_history(history)
```

`DecidedEdits` 是可信调用方传入的已完成整包决策；本层只校验 ACCEPT / RETAIN，不伪造或代替 Monitor 验证。后续调度负责只在 Monitor COMPLETE 后提供真实决策。

历史链校验：轮次不可重复、run 一致、下一轮 Parent 精确等于上一轮保留 Skill；历史绑定摘要包含之前每个账本和决策，不能替换、重排或遗漏先前轮次。首个历史轮次的 Parent 作为本次追踪起点，不假定它必然是空 Skill。

视图逐项报告：

- 原始整包 gate_decision，永久保留 ACCEPT / RETAIN 的事实。
- binding_status：EXACT / PARTIAL / ABSENT / UNRESOLVED。
- 当前可定位的 rule refs、可能位置和结构后继规则。
- 后续实际接受的结构修改（REPLACE / DELETE 等）及显式意图关系；拒绝的意图仍保留，但不改变当前文本来源。

**绑定采用保守的字面规则：**

| 状态 | 实现语义 |
|---|---|
| EXACT | 完整应用文本在当前 Skill 中有唯一的行边界匹配；DELETE 检查原来被删除的目标块 |
| PARTIAL | 完整文本已不在，但仍能唯一匹配其中的完整 Markdown 规则块 |
| ABSENT | 没有完整/部分文字匹配，也没有需要保留为未知的当前结构后继或已接受关联后继 |
| UNRESOLVED | 文本重复、部分匹配有歧义，或内容已改写但存在结构/显式关联后继，无法判定语义保留程度 |

EXACT 是文本事实，不证明原 edit 被部署过。例如被拒绝的修改后来由另一轮重新加入，旧记录可以同时为 gate=RETAIN 和 binding=EXACT；实际 writer 是新 edit。

DELETE 的绑定对象为被删目标，after_text 为空不参与匹配。原内容后来重新出现时可以是 EXACT/PARTIAL，而不能把 DELETE 解释成一条“现存新增规则”。

PARTIAL 当前支持完整规则块的保留；不对改写句子的语义相似度作猜测。单块部分改写但仍有后继时报告 UNRESOLVED，不静默宣告 ABSENT。

## 5. 当前规则的结构来源

结构追踪按照实际接受的修改范围逐段传播：未触及片段保留 writer；ADD 的文本 writer 是本轮 edit；REPLACE 的新文本 writer 是本轮 edit，ancestor 保存被覆盖片段的 edit 来源；DELETE 移除对应片段。

当前每个规则报告 writer_edit_ids、ancestor_edit_ids 和是否含有初始/分隔文本。对于一次合并多个目标的 REPLACE，ancestor 表示结构上的来源集合，不表示每个祖先都对新规则的每个字有贡献，更不是效果归因。

显式 RETRIES / REVISES / REVERTS 单独报告，不凭意图关系伪造结构来源。重复文本的具体来源可由实际写入路径追踪，但历史内容的泛化文字绑定仍保留歧义。

## 6. 保存与恢复

- `save_edit_ledger` / `load_edit_ledger`：保存 input.json、ledger.json、validation.json。只有最后发布的 VALID 标记及摘要一致时才可消费；读取后仍从来源重新计算全部记录。存在历史关联时必须提供同一历史前缀。
- `save_edit_history` / `load_edit_history`：保存含 ACCEPT/RETAIN 的完整有序历史和可重建视图；不依赖进程内对象继续追踪。恢复后核验整条历史并对照视图。
- 所有目标目录要求不存在；写入中断保留未完成产物，不覆盖旧记录，不自动换成有效 UNKNOWN。
- SHA-256 与来源重验防止意外损坏和错绑，不认证恶意调用方重新伪造的整套证据。实际轨迹真实性与 Monitor 决策来源仍由可信运行时保证。

这里的历史快照是审计存档，**不晋升 Skill、不提交未来的 M_t，也不代替第 5/7 步的原子 Memory 提交**。

## 7. 验证

专项命令：

```bash
python -m pytest -q tests/skill_evolution/test_edit_tracking_v19.py
```

39 项专项通过，覆盖三种操作、空 Candidate、原始索引、精确文本、身份稳定性、正反决策、后续修订/重试/撤销、部分保留、重复文本、历史顺序/Parent 绑定、非法关系、篡改、不可覆盖保存、中断重载及新进程恢复。

连同既有 v18 Compiler、Editor 和 v4 调度相关回归共 154 项通过。没有真实模型调用。

另对现有四轮历史产物做只读离线账本重建，输出位于 `artifacts/v19_edit_tracking_001`。这仅验证真实产物上的追踪能力，不是 v19 运行结果，也没有补跑训练或 Monitor。详细统计以该目录 summary.json 为准。

- 逐轮完成 11、2、3、1 个 edit unit 的重建，共 17 个，包含两轮 ACCEPT 和两轮 RETAIN。
- 重建后的当前 Skill 摘要为 `687bdcd051a4e93a75cee6b034582420d0f99fa838043b04dbb5df38aa7daf9d`，与历史实验最终保留文本逐字节一致。
- 当前绑定为 13 EXACT、4 ABSENT。EXACT 包括后来被修订但完整旧文本仍被保留的历史修改，不能把它当成当前规则数量或有效修改数量。
- 原历史目录 2,689 个文件的摘要未变；v18 冻结 manifest 的 992 个文件均匹配。

下一步为第 3 步：训练集 Parent–Candidate 配对回放。本步只提供其所需的精确 edit 和版本身份。

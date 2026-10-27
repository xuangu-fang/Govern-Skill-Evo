# 多 Knowledge P2：存储、修订与兼容读取

日期：2026-10-22。P2 已实现；新格式必须显式启用，现有默认仍为旧格式。P3 下游链路、P4 Prompt、P5 跨链验收与 P6 真实实验尚未完成。契约见 [MULTI_KNOWLEDGE_CONTRACT.md](MULTI_KNOWLEDGE_CONTRACT.md)。

## 实现范围

实现位于 `src/skill_evolution/v23/memory.py`，复用既有不可变 archive、文件锁与原子 Active 索引。没有引入新的 Memory 服务或模型调用。

- 新提案严格采用 `entries[{revises, knowledge[{text,evidence}]}]`。逐条校验非空文本、非空且不重复的合法引用；Entry 的证据并集须同时包含实际编辑与执行。跨 Knowledge 重复引用合法。
- 修订采用整个数组替换。保留数组、文本与引用的原始顺序；程序不自动复制、合并或补全旧 Knowledge。仍为整个新 Entry 分配新的 M ID。
- 提交时逐条限定本轮引用，历史引用不重写；原始 result/context 不变。归档 Entry 无顶层 evidence。
- `entry_evidence` 对已验证的 Entry 提供按首次出现顺序去重的引用并集，供来源解析使用，不改变逐 Knowledge 的证据绑定。本轮尚未接入 v3 窗口投影。
- 新读取器按每个 commit 的版本核验原始提案和归档内容，再呈现统一新格式。对新读取路径还核验完整 payload 与每轮提交前的 Active 快照。旧读取器遇到新 commit 明确拒绝，包含零 Entry 的新 commit。
- 继续使用不可变提交文件、锁内快照比较及原子索引切换。失败不部分发布；中断后只接受同 context、同版本、同输入与结果的恢复。重复请求不再次分配 ID。

`src/skill_evolution/v23/replay.py::validate_payload` 仅增加 `memory_contract` 关键字参数，供存储提交和重载验证完整上下文；默认不变。Replay 的运行入口、Prompt 选择与版本化模型归档未在 P2 切换。

## 显式 API

```python
from src.skill_evolution.v23 import memory

OLD = memory.LEGACY_CONTRACT  # entries_sources
NEW = memory.MULTI_KNOWLEDGE_CONTRACT  # entries_sources_multi_knowledge_v1

# 只读兼容视图：不修改源字典或磁盘，不从 shape 猜版本。
legacy = memory.load_memory(legacy_directory)
normalized = memory.normalize_memory(legacy, source_contract=OLD)
assert normalized == memory.load_memory(legacy_directory, memory_contract=NEW)

# 新目录或含旧/新提交的隔离目录：每个 commit 按自身版本验证。
active = memory.load_memory(isolated_directory, memory_contract=NEW)
bundle["payload"]["memory"] = active

memory.validate_entries(result, bundle["payload"], memory_contract=NEW)
committed = memory.commit_memory(
    isolated_directory,
    context_id="isolated_R1",
    context=bundle,
    result=result,
    memory_contract=NEW,
)
reloaded = memory.load_memory(isolated_directory, memory_contract=NEW)
```

示例中的 `bundle/result` 需为合法完整事实上下文及新格式提案；P2 的测试使用人工合成提案，不产生学习结论。真实实验仍须在隔离目录运行，不能将示例直接指向正式 Active Memory。

新增/扩展接口：

| 接口 | 版本参数 | 作用 |
|---|---|---|
| `validate_memory` | `memory_contract`，默认 OLD | 严格验证指定格式完整快照，返回可引用历史事实 |
| `validate_entries` | 同上 | 验证整个提案、逐 Knowledge 引用及 Memory 级修订关系 |
| `normalize_memory` | 必填 `source_contract` | 先验证、再生成独立新格式副本；对合法新格式为值恒等转换 |
| `entry_evidence` | `memory_contract`，默认 OLD | 已验证 Entry 的证据有序并集；不是语义支持审核 |
| `load_memory` | 同上 | OLD 仅读旧；NEW 兼容旧及混合提交历史 |
| `commit_memory` | 同上 | 锁内验证快照、完整替换、分配 ID、不可变提交和原子发布 |
| `replay.validate_payload` | 同上 | 在现有完整事实检查中选择 Memory 格式 |

## 兼容边界

旧 commit 缺少 `memory_contract` 时固定按 `entries_sources` 处理；新 commit 写入 `entries_sources_multi_knowledge_v1`。未知版本、版本与结构不匹配均报错。旧默认提交不新增版本字段，保持已有格式。

旧字符串和顶层 evidence 仅在派生视图中包装成一条 Knowledge；不进行语义拆分，不迁移旧文件。旧 Replay 重载仍返回原始字符串提案。新目录第一次接续旧历史时，调用方必须提供经过转换的完整快照，不能直接提交未转换的非空旧快照。

`entries: []` 仍可记录一个空结果 commit，不修改 Active IDs，也不分配新 ID；其版本仍参与复用检查。`knowledge: []` 始终非法。

旧算法不能读取新格式。当前 Preconditioner、Memory v3、Replay 模型视图和 history_pair_sources 还不能消费新的数组，需在 P3 显式贯通，不能直接切换生产默认参数。

## 离线证据与限制

新增测试：[test_multi_knowledge_memory.py](../../../tests/skill_evolution/v23_4/test_multi_knowledge_memory.py)。本次回归结果、原文件完整性核验及改动前源码保存在 [P2 报告目录](../../../experiments/methods/v23_4/multi_knowledge_p2_001/REPORT.md)。

验证覆盖严格结构与引用、JSON 解析、只读转换、来源保留、完整替换/合并、不自动补回旧认识、唯一修订目标、旧新提交混合、版本边界、空结果、精确幂等、快照冲突、中断恢复及篡改拒绝。另只读加载真实 R05/R06 对应历史 Memory 和旧 Replay。

这些检查证明技术行为，不证明 Knowledge 事实准确、历史认识保留完整或语义学习改善。未运行真实模型，未发布新的正式 Memory。P1 历史报告和哈希清单保留原样，其测试数与源码哈希描述的是当时状态。

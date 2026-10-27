# 多 Knowledge P2 实现与离线报告

日期：2026-10-22。仅实现 P2 存储层；没有真实模型调用、没有发布正式 Memory，也未覆盖当前生产默认 Prompt。

## 结果

- 新增 52 项 P2 测试，全部通过。
- V23、V23.3、V23.4 全目录回归：919 项，909 passed、1 failed、9 errors，耗时 77.67 秒；没有跳过或排除测试。完整结果见 [pytest.xml](../../../../artifacts/methods/v23_4/multi_knowledge_p2_001/pytest.xml) 与 [TEST_RESULTS.json](TEST_RESULTS.json)。
- 10 个未通过项在 P2 改动前的源码下同样失败，名单完全一致。9 个 formal_evaluation 测试在 fixture 阶段要求当前完整源码/Prompt 等于旧正式实验冻结版本；1 个 Gate 旧归档测试因历史 Editor Prompt 与当前模板不同而失败。未取消这些保护、改写冻结版本或扩展为 Gate/正式评估的重设计。
- 保护范围内 10,166 个已有文件逐字节 hash 未变，包括正式 V23 实验归档、Replay 输入视图及候选 Prompt 实验、P1 契约实验。见 [INTEGRITY.json](INTEGRITY.json) 与 [protected_before.json](protected_before.json)。

## 代码与接口

生产变更仅涉及：

1. `src/skill_evolution/v23/memory.py`：显式新旧契约，逐 Knowledge 验证，有序证据并集，只读 N 转换，完整数组替换，逐条限定引用，混合提交重载，幂等与恢复版本校验。
2. `src/skill_evolution/v23/replay.py::validate_payload`：增加默认旧值的 `memory_contract` 参数，仅供 P2 的完整上下文验证。本轮未适配真实 Replay 运行器。

本次相对改动前的准确补丁见 [code_changes.diff](code_changes.diff)，两个 `before_*.py` 是改动前的只读源码副本，不能作为运行器使用。由于工作区此前已有修改，不将整体 git diff 误记为本次改动。

新增测试 `tests/skill_evolution/v23_4/test_multi_knowledge_memory.py`；接口使用、兼容边界见 [P2 说明](../../../../docs/methods/v23_4/MULTI_KNOWLEDGE_P2.md)。P1 冻结报告和清单没有改写。

## 验证内容

- 新旧严格字段与显式版本；未知版本、混合 Entry 形状、空 Knowledge、重复/未知引用均拒绝。
- 每条 Knowledge 独立绑定 Evidence；Entry 并集要求实际编辑及执行；跨条重复合法，有序汇总不改变原始 Evidence。
- 复用既有严格 JSON 解析；原始文字、数组、引用顺序不改写。
- 修订分配新的 M ID，支持多个 Memory 合并；完整数组覆盖，不自动补回被省略的旧认识；未修订 Entry 保留。
- 本轮引用逐条限定，历史限定引用不重复加前缀；原始 result 不变；来源包含所有条目需要的完整执行与实际编辑。
- 旧目录读取为只读新视图；旧+新+新多轮重载；旧读者拒绝新 commit，空结果同样有版本边界。
- 同 context 精确幂等、空结果、两个写入者持有同一快照时拒绝后到的过期请求、中断后拒绝不同请求并精确恢复。
- 篡改归档文本、引用、版本、原始提案、快照、Active 转移或当前轨迹均失败。
- 冻结 R05/R06 使用的原始 Memory 读取后与 N(旧读取结果) 相等，sources 内容不变；旧 R03 Replay 仍可按旧输出重载。

## 历史失败的基线复核

[check_pre_p2_failures.py](check_pre_p2_failures.py) 将改动前 memory/replay 源码仅执行到隔离 Python 进程的模块字典；正式冻结检查使用替换回改动前源码字符串的 `frozen_contract`。没有临时覆盖工作区文件或历史归档。随后运行同一 formal_evaluation 测试文件及失败的 Gate 测试。

结果：1 passed、1 failed、9 errors；10 个失败/错误节点与本轮完全相同。见 [pre_p2_failures.json](pre_p2_failures.json)、[XML](../../../../artifacts/methods/v23_4/multi_knowledge_p2_001/pre_p2_failures.xml) 和 [日志](../../../../artifacts/methods/v23_4/multi_knowledge_p2_001/pre_p2_failures.log)。此复核用于区分既有冻结冲突与 P2 回归，不表示全套测试已无条件通过。

## 尚未完成

P3 需贯通 Replay 模型输入/输出与归档版本、Memory v3 证据窗口、历史 Pair 来源、Preconditioner 输入/编译/重载；P4 需独立候选 Prompt。新格式目前不能直接交给这些旧默认入口。

技术完整数组替换不等于历史知识在语义上被完整保留。本次仅验证存储行为，没有验证模型会否遗漏重要历史认识，也没有证明事实准确性或 Knowledge 学习质量得到改善。P5 和 P6 仍需后续独立验收。

# v20 第 2 步：问题 Memory 保存与增量更新

日期：2026-10-02。状态：已实现独立存储和确定性增量合并；尚未接入 v20 Issue Fusion、真实模型或多轮 campaign。

实现文件：

- `src/skill_evolution/issue_memory_v20.py`
- `tests/skill_evolution/test_issue_memory_v20.py`

## 接口

```python
from src.skill_evolution.issue_memory_v20 import (
    initialize_issue_memory,
    load_issue_memory,
    merge_update,
    commit_issue_memory_update,
)

snapshot = initialize_issue_memory(store_dir=memory_dir, run_id="run-1")

update = {
    "schema_version": "issue_memory_update_v20.1",
    "run_id": "run-1",
    "round_id": "round-01",
    "issues": [{
        "new_issue_key": "settlement-price",
        "problem": "搜索报价不能确定最终结算金额。",
        "source_refs": ["FINDING/1"],
        "attempts": [{
            "new_attempt_key": "disclose-and-confirm",
            "approach": "披露搜索报价，不把它当作最终结算金额。",
            "assessment": "已有配对观察支持披露行为，但最终金额仍不可见。",
            "edit_refs": ["EDIT/1"],
            "source_refs": ["ATTRIBUTION/1"]
        }]
    }]
}

ref = commit_issue_memory_update(
    store_dir=memory_dir,
    update=update,
    expected_head_ref=snapshot.memory_ref,
)
snapshot = load_issue_memory(memory_dir)
```

模型或上游语义分析负责判断两个问题/方案是否相同；本模块不做关键词或 embedding 匹配。新对象使用 `new_issue_key` / `new_attempt_key`，程序根据运行 ID 和 key 生成稳定的 `ISSUE/<sha256>`、`ATTEMPT/<sha256>` 身份。已有对象用正式 ID 更新。

更新是部分提交：只处理本轮涉及的问题，省略的问题和尝试原样保留。来源引用和 edit 引用按首次出现顺序去重合并；同一方案没有新结论时不会追加新的自然语言段落。相同临时 key 重试时，如果问题和方案一致，会复用已有对象并合并新增引用；方案冲突则拒绝。已有尝试可更新 `assessment`，但不会因为更新请求遗漏字段而删除旧字段。

## 存储与恢复

目录为独立的 v20 memory root：

```text
memory/
  genesis.json
  head.json
  revisions/<memory-sha256>/memory.json
```

每次有实际变化写入新的不可变 revision，再原子替换 `head.json`。`load_issue_memory` 会校验版本、运行 ID、完整问题/尝试结构和当前 memory 摘要；`expected_head_ref` 提供比较并提交，过期更新会停止。完全相同的已提交更新可安全重试并返回原引用，不重复增加 revision。

Gate、Parent/Candidate、Monitor 分数和完整轨迹不进入问题 Memory；它们由后续 v20 闭环保存的外围档案引用。ACCEPT/RETAIN 的区别不在本模块内生成，也不会把 Gate 结果复制成尝试效果标签。

本步没有实现语义判断、Evidence Review、Memory 消费视图或压缩流程。完整原始证据仍由后续闭环归档；当前实现只保存学习侧问题状态及其来源引用。

## 验证

专项测试覆盖：

- 空 Memory 初始化、幂等恢复和运行 ID 隔离；
- 新问题/尝试的稳定 ID；
- 同一方案更新 assessment 与来源集合；
- RETAIN/ACCEPT 不改变问题状态模型；
- 新方案在同一问题下保留；
- 省略字段不删除旧问题/尝试；
- 重复临时 key 追加新证据而不复制正文；
- 非法重复、未知 ID、运行冲突和篡改 revision 拒绝；
- 原子提交、CAS 冲突和完全相同提交幂等。

`pytest -q tests/skill_evolution/test_issue_memory_v20.py`：**10 项通过**。

相关 v19 回归：`pytest -q tests/skill_evolution/test_memory_v19.py tests/skill_evolution/test_memory_consumption_v19.py`：**45 项通过**。本步没有模型调用或实验运行。

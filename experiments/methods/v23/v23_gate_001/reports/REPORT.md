# V23 Gate 实现与验证报告

Gate 已完成实现。按原始环境反馈核验的四组配对，Parent 成功 3 条、Candidate 成功 2 条，结果为 **RETAIN**。本次模型调用 0，新增环境任务 0，正式 Skill/Memory 状态更新 0。

## 实现与契约

新增 `src/skill_evolution/v23/gate.py`：标准化输入校验、纯计数决定、原始执行核验、既有 Replay 配对档案读取、原子保存、读取复用、技术停点及 CLI。

修改 `src/skill_evolution/v23/replay.py`：仅将既有任务/配置/初始状态/实现差异核验提取为 `verify_pair()`，供 Replay 和 Gate 共用。保留原检查，没有改变 Replay 输入、输出、Prompt 或 Memory 学习规则。

新增 `tests/skill_evolution/v23/test_gate.py`、`docs/methods/v23/GATE_DESIGN.md` 及本实验目录；更新源码 README、方法文档索引、实验索引及实验日志。

输入严格为 `pairs`，每项为 `task_id / parent / candidate`；两侧严格为 `run_id / success`。run_id 为真实原始执行身份，success 为环境布尔结果。独立冻结清单从原实验 plan 的 `candidate_tasks` 提取为 `config/tasks.json`，不能从有效结果反推或删除失败任务。

核心输出只有四字段：

```json
{
  "decision": "RETAIN",
  "parent_success": 3,
  "candidate_success": 2,
  "compared": 4
}
```

Candidate 成功数严格更多才 ACCEPT，其他情况 RETAIN。任务步数及退化案例不参与决定。不引入第三类语义决策；技术异常保存错误并抛出，不冒充 RETAIN。

## 真实来源与配对核验

入口为 `artifacts/methods/v23/v23_replay_memory_001/replay/input.json`。按照该档案的 `record_paths` 重新读取 4 条 V22 Parent 和 4 条既有 Candidate 原始轨迹，没有使用聊天汇总作为结果来源。

复用 facts.py 对完整执行进行实际请求、菜单、观察连续性和环境结果校验；复用配对检查核对任务 ID/完整任务身份、模型、backend、协议、步数预算、版本、环境 game/manifest 哈希及重置后的初始观察/候选。两侧模型均为冻结的 deepseek-flash，预算 50 步。Parent 为 null，Candidate 是既有 Editor 成功归档的 23 行 Skill。重新验证实际 Diff 产生该 Candidate，执行 Skill 文本与身份哈希一致。

历史 Actor 源码哈希不完全相同，沿用原实验已保存的显式实现差异核验：要求该核验精确覆盖双方实际 files 哈希，并保留其 reason/diff。没有假称源码哈希相同，也没有为 Gate 新放宽条件。所有核验源路径和文件 SHA-256 均保存在 Gate bundle.sources 中；完整配对核验材料仍在所引用的原归档。

| 任务 | Parent 成功 | Parent 终止 / 步数 | Candidate 成功 | Candidate 终止 / 步数 |
|---|---|---|---|---|
| train:0012 | true | success / 7 | true | success / 7 |
| train:0013 | false | step_limit / 50 | false | step_limit / 50 |
| train:0014 | true | success / 24 | false | step_limit / 50 |
| train:0015 | true | success / 12 | true | success / 26 |

四组完整符合比较条件，无技术中断或未知结果。Parent 共 93 步，Candidate 共 133 步；修复 0、退化 1（train:0014）、保留成功 2、保留失败 1。这些只用于描述；RETAIN 的依据仅为 2 不大于 3。

## 测试与持久化

```bash
/tmp/gse-v23-py313/bin/python -m pytest -q \
  tests/skill_evolution/v23 tests/adapters/alfworld \
  tests/skill_evolution/v22/test_grouped_representation.py
```

结果：**479 passed，19 subtests passed**，无失败。Gate 新增 45 项测试，从实际格式的原始环境步骤构造结果，覆盖严格计数、同时修复和退化但净增加、正常终止失败/步数耗尽、技术中断/未知、身份与配置不一致、空/重复/不完整任务集、非法布尔、保存/损坏/来源变化/缺失，以及真实档案交接。既有 V23、ALFWorld Adapter 与相关 V22 表示回归通过。

通过 CLI 首次写入 `artifacts/methods/v23/v23_gate_001/live/gate.json`，其中 bundle 保存输入、冻结任务、终止/步数核验、来源与规则，result 保存四字段决定。原始轨迹不复制到 Gate 输出。有效档案以单文件原子替换提交，读取源文件损坏或与调用来源冲突则拒绝复用，失败另存 failure.json。

再次读取并执行复用时，将 `decide_gate()` 替换为必定抛错的函数，复用仍成功且 gate.json 字节不变。由此确认没有再次调用判定入口。读取时仍重新核验来源、结果计数和规则一致性；“复用”不表示跳过正确性校验。

`config/verify.py` 对 **423 个上游档案文件**执行前后 SHA-256 核验，覆盖 V23 各历史模块、Editor 原失败/成功结果、Replay、Memory 以及本次使用的原始 Parent；全部未变。没有修改 23 行 Candidate，没有提交 Active Memory，也没有将 Gate 决定加入 Replay 或 MemoryEntry。

## 后续接口与边界

调度读取 `load_gate(path)["result"]` 即可获得四字段决定。`build_gate()` 可接受未来独立 Validation 的原始配对，不依赖 Editor 的训练批次；本次 `assemble_gate()` 是现有 Replay 档案适配器。当前持久化按单调度者串行使用，不实现并发轮次提交或完整调度。

未来 ACCEPT 选择 Candidate，RETAIN 选择原 Parent；两者都可以使用 Replay 独立更新的 Active Memory。统一提交由未来调度负责。Train 用于学习、Validation 用于 Gate、Test 用于最终独立评价；Validation 不能自动流入 Replay/Memory。本次只使用既有 Train 配对，不是独立 Validation，也不证明 Skill 晋级收益或多轮持续进化效果。

**Gate 能够在不调用 LLM 的情况下，根据真实、完整且经过核验的配对结果，确定性决定 Candidate 是否晋级。本次结果为 RETAIN，未执行正式状态更新。**

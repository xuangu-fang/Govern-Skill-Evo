# v21 第 2 步：接通修改后学习侧证据

日期：2026-10-09。状态：已实现证据装配、持久化、历史回查及独立离线入口；后续[第 3 步 Memory 更新](V21_MEMORY_UPDATE.md)已实现并通过离线测试，后续[第 4 步消费适配](V21_MEMORY_CONSUMPTION.md)也已接通，新一轮 v21 generation source 可显式复验并继承此前档案。未切换 v20 运行入口。方法边界见 [v21 契约](V21_METHOD_CONTRACT.md)。

## 1. 本步实现

- [modification_evidence_v21.py](../src/skill_evolution/modification_evidence_v21.py)：从实际 generation audit 和已完成的 Parent/Candidate 训练回放重建学习侧证据，保存版本与原始引用，向后续 Memory 更新提供可选择的输入。
- [prepare_v21_evidence.py](../scripts/prepare_v21_evidence.py)：独立只读转换入口；不执行 rollout、重新评分、私有 Gate、模型调用或 Memory 提交。
- [test_modification_evidence_v21.py](../tests/skill_evolution/test_modification_evidence_v21.py)：真实检查点格式的构造测试和失败边界。

本步仅建立数据通路：回放事件与双维标签可以被更新函数读取，之后也能按来源重新打开。它不生成“有效/有害”等标签，不更新 assessment，不把修改前的 Review 当作修改后有效性的证明。

## 2. 来源验证与投影

`build_modification_evidence` 先复验现有 generation audit，确认 Candidate 确由保存的审阅与编辑产生；使用调用方提供的可信训练 backend manifest，复验两侧输入、完整性标记与逐文件摘要。

配对继续检查初始状态、可见环境、用户模拟器输入及执行设置的一致性；这些私有内容只用于运行侧核验，不进入学习侧产物。学习侧沿用既有投影，只获得可见 policy/tools、原始可见事件、Level-0 成功/合规标签及来源。

不读取 `candidate-summary.json` 作为标签真值，也不以整批成功/合规计数替代逐次联合观察。失败、违规及两侧持平的运行均保留。

分组后的 `T001` 等标识可能是重新排列的匿名别名。实现通过 generation 中的 `experience_bindings` 显式映射到回放任务，再核对 Parent 原始事件、上下文、标签、版本和 rollout。不能直接按相同展示编号配对，也不通过语义相似度猜测对应关系。

## 3. 档案与局部读取

`ModificationEvidence` 保存：

- 本轮精确两侧 Skill、generation 和检查点摘要；
- 当前简明 Memory、提案、原有审阅及实际 edits；
- 逐任务配对来源、每次运行的双维标签和完整事件；
- 现有历史证据档案，以及显式导入的 v21 历史证据引用。

使用既有 `PAIR/...`、事件和 edit 引用；不新增经验效果状态。`REPLAY` 记录只是原始观察的来源类型，不是归因结论，因此不自动关联所有 edits，也不把整包结果复制成每条 edit 的功劳。

完整档案用于保存与回查，不默认整体放入模型输入。`open_memory_evidence` 接受现有问题、提案、来源记录或配对引用：

1. 读取所选问题下的尝试和来源，并跟随明确的来源/联合 edit 关联。
2. 保留关联记录中的支持、反证和必要的完整轨迹。
3. 若引用涉及本轮 Parent，沿明确来源映射加载对应 Candidate；引用任一配对侧时同时加载双侧。
4. 不展开无关问题、配对或整轮历史；未知引用直接报错，不静默忽略。

`parent_pairs` 明确标识诊断中的 Parent 引用和 Replay Parent 属于同一次观察。两种引用入口不构成两份独立证据。

读取接口也允许“旧 issue + 明确的新 pair”，不要求旧 issue 本轮已被 Fusion 选中。这只提供证据可达性，不自动判断新证据与旧方案的语义关联。第三步更新仍须说明关联依据。

## 4. API 与运行位置

```python
from src.skill_evolution.modification_evidence_v21 import (
    prepare_memory_evidence, open_memory_evidence,
)

evidence = prepare_memory_evidence(
    round_dir=completed_round_dir,
    backend=benchmark.evolution,
    output=derived_output_path,
)

packet = open_memory_evidence(
    evidence,
    proposal_refs=[proposal_id],
)
```

`round_dir` 需要已完成的 `generation/generation-audit.json`、`parent_evolution` 和 `candidate_evolution`。`output` 必须位于源轮次目录之外，旧产物只读。已有相同输出可幂等复用，不同内容不能覆盖同一路径。

这是完整 Candidate 回放之后、语义 Memory 更新之前的接入点。第 3 步更新函数已消费此类局部视图；本步没有自动调用更新模型，也没有用 v20 的默认摘要函数充当 v21 更新实现。旧版 Evidence Review 的输入协议不在本步修改，后续消费适配仍需按计划实现。

历史 bundle 由调用方显式传入 `history`，不能扫描邻近目录就认定已提交。保存函数返回内容摘要引用，重新加载必须提供调用方持有的 `expected_ref`。这些引用和历史是否属于已提交运行，由未来调度器的提交记录或显式离线导入决定；摘要不是对历史语义真实性的证明。

## 5. 离线命令

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/prepare_v21_evidence.py \
  --round-dir artifacts/v20_pilot_001_continuation_grouping24k/round-04 \
  --output artifacts/v21_evidence_step2/round-04.json
```

`--config` 指定来源实验的冻结 benchmark 配置，默认复用 v20 Pilot 配置。`--history PATH EXPECTED_REF` 可重复，用于明确导入已核实的历史证据。它们是离线来源参数，不是 v21 新实验配置，也不会迁移旧 Memory head 或恢复旧 campaign。

源 manifest、generation 或检查点不一致时停止，不放宽校验、改写旧输入或自动重新运行。当前入口支持现有 v20 generation audit 与无 v19 edit ledger 的完整 Candidate 回放布局；不声称支持任意旧版运行格式。

## 6. 验证结果

运行：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q \
  tests/skill_evolution/test_modification_evidence_v21.py \
  tests/skill_evolution/test_runtime_v20.py \
  tests/skill_evolution/test_local_generation_v20.py \
  tests/skill_evolution/test_evolution_replay_v19.py
```

结果：**80 项通过**，其中 v21 专项 19 项。覆盖完整配对与两维标签、匿名映射、历史反证和局部范围、未选中历史问题读取、持久化/篡改拒绝、版本/manifest/检查点错误、Monitor 输入拒绝、汇总分数不能覆盖原始标签、初始状态配对核验、历史跨轮回查及源目录只读。

真实产物只读验证：`v20_pilot_001_continuation_grouping24k/round-04` 的 **36 组配对**成功重建；**6 个提案、8 个历史问题**均可按来源回查。完整档案有 **4,715 个事件**，六个提案视图分别展开 **79、117、210、66、68、116** 个事件，没有默认装入整轮历史。

派生产物：`artifacts/v21_evidence_step2/round-04.json`；核查报告：`artifacts/v21_evidence_step2/check.json`。证据引用：`MODIFICATION_EVIDENCE_V21/21dd54b436057663c8afe5e44d56d527748a18f0c1f9634168e16fe11d8f7a4e`。

本次没有模型调用、重新 rollout 或 Memory 提交。测试与真实离线读取证明证据通路可用，不证明双维归因质量、语义更新已实现或 v21 自进化优于 v20。

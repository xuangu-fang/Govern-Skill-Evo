# ALFWorld v24.6

[正式训练与评测](../../../experiments/methods/v24_6/README.md) · [测试入口](../../../scripts/runs/v24_6/run_v24_6_test.py)


v24.6 学习两类可独立采纳的 Skill 修改：能改变任务成败的动作选择，以及在任务仍成功时能减少实际环境动作的选择。正式实验配置继承相同的初始 Skill、空 Memory、Actor 协议、50 步上限和 57 道优化题。六批的任务数是 10、10、10、10、10、7。最终评价指标仍为冻结的 134 道 Test 题的环境成功率。

## 一轮的执行与交接

上轮 Selected Skill 成为本轮 Parent。Actor 执行当前批次后，四个模块使用如下证据。

| 模块 | 动态输入 | 输出和约束 |
|---|---|---|
| [Diagnosis](../../../src/skill_evolution/v24_6/prompts/diagnosis.md) | Parent 和当前全批 Parent 轨迹、动作菜单 | 从失败中找仍有选择的决策点，从成功中查哪些额外动作确可省略。输出 no_change 或带证据引用的 Original Updates。决定适用边界的成功步骤也写进 basis。 |
| [Preconditioner](../../../src/skill_evolution/v24_6/prompts/preconditioner.md) | Parent、Original Plan、被引用的完整当前轨迹和菜单、此前已发布的 Memory | 对每个 ID 做 KEEP、REPLACE 或 WITHDRAW。用当时可见的线索调整动作优先级，指出可能省掉的动作，检查是否打断已有成功路线。成功修复可以增加必要动作。所有执行条件写入有效 Update 文本。 |
| [Editor](../../../src/skill_evolution/v24_6/prompts/editor.md) | Parent、有效目标、各有效 ID 和文本 | 针对同一份原始 Parent 逐 ID 生成补丁。每条补丁完整表达自己的触发、强度、退出和例外，可跨多个 hunk。联合应用全部非空补丁得到本轮唯一 Candidate，在同一批题上独立执行。 |
| [Replay](../../../src/skill_evolution/v24_6/prompts/replay.md) | 有效 Updates、逐 ID 补丁、实际联合 diff、程序筛出的同题轨迹与菜单 | 按题解释触发条件、改变的动作及其后果，每题恰好一条 Knowledge。每个事件至多关联一个非空补丁。只知道联合 Candidate 快慢、多个补丁不可区分或局部变化不足以解释整题差异时，记录 null 和原因。 |

Actor 执行一次 Parent 批次和至多一次联合 Candidate 批次。按现有机制，无提案和全部撤回时沿用 Parent 与 Memory。空字符串补丁表示原 Parent 已满足要求，决定为 null；阻塞补丁沿用既有中止发布语义。格式纠错和从中断恢复复用原有请求与轨迹归档。

## 事件和 Gate

程序先校验全批同题配对、Actor 条件、实际执行的 Skill 和环境终局。每题按下表选至多一个事件。步数取校验后的环境动作数，差值为 Parent 减 Candidate。无符合条件的题时跳过 Replay。

| Parent → Candidate | 事件 |
|---|---|
| 失败 → 成功 | gain |
| 成功 → 失败 | loss |
| 双方成功，差值 ≥ 10 | efficiency_gain |
| 双方成功，差值 ≤ −10 | efficiency_loss |
| 双方失败或双方成功且差值绝对值 < 10 | 无 |

Gate 逐有效 Update 对关联事件计数。G、L 是成功收益与退步的题数，efficiency_gain、efficiency_loss 是效率收益与损失的题数。未归因事件保留在 Memory，给所有 Update 计零票。

| 非空补丁的 G 和 L | 效率证据 | 决定 |
|---|---|---|
| G > 0，L = 0 | 任意 | Retain |
| G = 0，L > 0 | 任意 | Reject |
| G > 0，L > 0 | 任意 | Defer |
| G = L = 0 | 至少一票 efficiency_gain，零票 efficiency_loss | Retain |
| G = L = 0 | 其他 | Defer |

程序按有效 Plan 顺序将 Retain 补丁重新应用到原 Parent。只保留部分补丁时按已有语义记载执行来源；选出文本既不同于 Parent 又不同于已执行 Candidate 时，selected_execution_source 为 null。每个 Memory 事件保存稳定 ID、方向、两侧步数、差值和原 Knowledge。Selected Skill、Memory、下一轮游标共用原子发布点。[Gate 实现](../../../src/skill_evolution/v24_6/gate.py) · [训练与发布入口](../../../src/skill_evolution/v24_6/campaign.py)

## 离线验证

从仓库根目录运行下列命令。省略 archive 参数可仅运行固定夹具与回归测试。验证器禁止网络连接、真实 Actor 和子进程，临时训练夹具由 pytest 管理。

```sh
/Users/didi/miniforge3/bin/python scripts/runs/v24_6/verify_v24_6_offline.py \
  --archive artifacts/methods/v24_5/v24_5_alfworld_20261107_220520 \
  --report /tmp/v24_6_offline.json
```

[离线报告](../../../experiments/methods/v24_6/v24_6_offline_verification/results/offline.json)记录了四份 prompt 的摘要、测试结果和归档筛选出的逐题事件。固定夹具覆盖 ±9/±10 边界、16 种票型、null 归因、跨题引用拒绝、只保留一个补丁、无事件跳过 Replay、跨轮 Memory 以及中断恢复。六轮 v24.5 实际归档另行校验了 57 对轨迹，并核对原始配对审计。归档仅用于验证事件筛选。正式训练和独立 Test 均未启动，真实模型的归因质量与任务性能尚待评估。

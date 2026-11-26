# LMB SkillAdam 恢复修复与离线验收

本次仅修复轮内恢复与整体恢复前的 Actor 归档校验。未启动真实实验、模型调用或 Test。
优化器配置文件、原生 SkillAdam 源码、v27 Actor 实现及环境依赖均未修改。

后续复审补充的两个边界已固化为回归测试。本次补充仅修改测试与文档，未修改接入实现、
优化器职责、参数、证据压缩或 Prompt，未启动实验。

## 保持原生的范围

保留原生优化器 Prompt、确定性证据压缩、补丁格式与解析、自适应编辑预算、同批 Gate、
Momentum 工具与状态、顺序采样、早停以及 checkpoint 格式。
batch=10、最大／最小迭代15／5、连续失败阈值3、patch_attempts=3、预算4／1／0.9／0.05、
optimizer_context_limit=150000、53／124划分、初始 Skill、Actor／模型参数均保持原配置。

按用户确认，暂不修正上游证据投影缺口：压缩结果未显式包含完整选项、正确标签和
theorem／sketch；优化器 Prompt 中关于 Hidden Reference 的声明也保持原样。
本轮没有新增证据、改写压缩结果或改变优化器 Prompt。此前与 v27 对齐的 Actor 提示词适配保留。

## 修复方式

实现位于 `src/adapters/lmb/skilladam.py` 与 `src/adapters/lmb/recovery.py`。
本地 Runner 包装原生控制流程，不修改 `external/SkillAdam`。

### 轮内恢复

- 在首个 Actor／优化器请求前，调用原生 checkpoint 序列化及签名逻辑保存初始状态。
  因此首轮 Gate 前中断已有合法恢复起点，不再因缺少 checkpoint 被阻塞。
- 以 iteration、生成阶段及 patch_attempt 标识优化器请求，并冻结其完整输入。
  返回的普通文本、工具调用和用量先原子保存，再交给原生解析与补丁逻辑。
- 恢复时复用已保存结果，不重新生成已有补丁或 Momentum 返回值；即使模型下一次输出会不同，
  也不会产生新的响应与已有原生文件冲突。
- 未收到可持久化响应的优化器请求允许再次执行，继续使用原生 SDK 重试配置；这不保证远端
  在进程中断前没有处理过请求。已有完成回执却丢失响应时停止，不把损坏当作未完成请求。
- Actor 继续沿用 v27 的请求槽、六次技术尝试总限额和未知结果恢复规则。
  已保存原始响应可以本地恢复；真正未完成的任务继续执行；其他完成任务不重复请求。
- 用量按阶段写入幂等回执，再生成原生 JSONL 字段格式，避免重放缓存使请求数重复计入。
- 轮内恢复会重放原生确定性计算，但采样、补丁接受判定、预算及 Momentum 语义保持不变。

### 整体归档校验

- 在 Actor 执行前登记阶段任务、Skill 和角色；完成后保存结果摘要。
- Runner 恢复时先只读检查所有已登记阶段，再进入原生恢复流程；不只检查将要重新执行的批次。
- 校验覆盖 batch 签名、Skill、任务顺序、records、trajectory、result 和原始响应，
  使用 v27 已有的归档校验器；同时核对 checkpoint 及已有原生评估产物依赖的阶段是否完整。
- 待执行 Momentum、已完成终态、进入下一轮三种路径均经过该检查。损坏时 Actor 和优化器
  均不得新增请求，也不发布新的最终 Skill。
- 登记但尚未开始、已返回响应但尚未提交结果、部分任务完成等状态保留恢复能力。
- 原生 checkpoint 已开始使用后若丢失，拒绝重新初始化；旧版无回执目录不自动迁移。
  正式入口原有配置／源码冻结检查仍生效，源码变化后的旧目录不得直接当成同一运行恢复。

## 离线验收

环境：`/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python`。
未安装或更新依赖，`pip check` 通过。验证进程封锁 socket 连接与外部子进程，
模拟调用仅使用合成题、固定响应或内存 HTTP transport。

最新 [SkillAdam 报告](../../../artifacts/verification/lmb_skilladam_recovery_boundaries_20261030/validation.json)：
29 项测试全部通过，网络连接尝试0、真实模型请求0，原始及准备数据哈希未变。
其中20项恢复回归、9项接入测试。全局损坏测试还包含待执行／终态与五种损坏组合。
此前 [27项修复验收报告](../../../artifacts/verification/lmb_skilladam_recovery_20261030/validation.json)保留。
另核对接入层及入口的本轮前后哈希一致，原生／v27源码、配置和环境锁定与上一轮报告一致，
见 [实现未变核对](../../../artifacts/verification/lmb_skilladam_recovery_boundaries_20261030/unchanged_implementation.json)。

| 场景 | 验收结果 |
| --- | --- |
| 初始化 checkpoint 前后中断 | 无请求时可继续建立初始状态；不重置已开始运行 |
| 首轮 Gate 前中断 | 复用10题训练与已生成补丁，只执行未完成的 Gate／Momentum |
| 第二轮 Candidate 归档后中断 | 不新增 Actor 请求、不重新生成补丁，继续完成 Momentum |
| 响应已存、原生 patch 文件未存 | 复用优化器响应，原生文件继续提交 |
| 原生补丁首尝试失败、第二次成功后中断 | 保留原生重试输入与两次尝试，恢复不重复调用 |
| Momentum 未返回响应／已返回但未写 checkpoint | 前者允许重试；后者复用已保存响应 |
| Momentum 已应用但 checkpoint 未提交 | 从原生状态恢复，不重复累计最终状态 |
| 已完成任务的 result／response／records／阶段目录／登记表丢失 | 待执行 Momentum 或终态恢复均零新增请求，不发布新结果 |
| 上一轮归档损坏、下一轮待开始 | 请求前停止 |
| 已损坏完成任务与真正未完成任务混合 | 不先执行未完成任务，零新增请求 |
| 9题完成、1题请求无响应 | 保留9题结果，只补齐未完成任务；Actor 技术尝试槽不重置 |
| Actor 原始响应已存但 result 未提交 | 本地完成结果，不重发该作答 |
| 缓存优化器响应丢失 | 不重新生成完成响应 |
| 正式 `run(..., resume=True)` 入口 | 同样执行全局检查，损坏时零新增请求 |
| 用量和完成后再次恢复 | 不重复累计缓存结果的用量，不新增模型请求 |
| 结果已存、完成回执未写入 | Actor training、patch、Momentum 三处均复用已保存结果，补齐回执，不重复请求 |
| 两轮先 ACCEPT 后 RETAIN，在第二轮 Candidate 归档后中断 | 恢复结果与不中断基线的最终 Skill、完整迭代记录、完整 Momentum 和用量账本一致 |
| 原生职责与参数 | 继承方法身份、开源配置、原有模型／数据对齐检查通过 |

### 本次固化的两个边界

测试位于 `tests/adapters/lmb/test_recovery.py`：

- `test_saved_results_before_completion_receipt_are_reused`：在 `Recovery.complete` 写回执前
  注入中断。三种子场景分别已完成10次 Actor、10次 Actor＋1次 patch、30次 Actor＋2次优化器请求。
  明确检查回执为未完成、结果已落盘；恢复后均为累计30次 Actor＋2次优化器请求，保存文件字节不变，
  回执摘要匹配结果；终态再次恢复不增加请求或用量。
- `test_accept_then_retain_resume_matches_uninterrupted_state_and_usage`：运行两组20题合成任务，
  第一轮接受、第二轮保留。中断组在第二轮 Candidate 完整归档后恢复，并改变模拟 patch 的下一次输出，
  以暴露错误重新生成。两组最终 Skill、完整迭代记录、完整 Momentum（包含轮次）和逐行用量记录完全一致。
  每组累计60次 Actor＋4次优化器请求；优化器每次含38个模拟 token，账本共64次请求、1952个 token。
  完成后再次恢复不增加请求，Skill、迭代记录、Momentum 问题记录及用量保持不变。

边界说明：额外尝试对“已完成终态再次恢复”的完整内存 Momentum 做相等断言时，发现原生
`FeedbackLoop._restore_state` 仅复制 `problems`，未复制 `current_iteration`；终态不进入循环，
内存轮次因此保持默认0，而本例完成时为1。此行为发生在不中断基线的终态恢复中，未改动原生实现。
终态检查限定为上述业务记录和请求／用量不变，不宣称完整内存 Momentum 相等；
两轮活动中断恢复的完整 Momentum 相等断言仍保留并通过。

此前修复轮额外复跑 [v27 离线验收](../../../artifacts/verification/v27_after_lmb_skilladam_recovery_20261030/validation.json)：
53项中52项通过、1项失败；网络连接尝试0、真实模型请求0、数据哈希未变。
唯一失败为 `test_source_freeze_and_independence`：`src/skill_evolution/v25/config.py`
与 `docs/methods/v27/draft_20261030_001/source_manifest.json` 的历史来源哈希不一致：

- 历史清单：`0eb49350a75bd8724639afb901c0f39f240d7256d30fa5ffeccdfa1d9c9be2e5`
- 当前文件：`663df9baa746cf6a123ab9e151fd3feb2d55b202f83a75156e63ddc5c889efde`

本轮没有修改上述 v25 文件或历史来源清单，也没有通过更新清单消除失败。
因此应表述为“SkillAdam 恢复验收通过；额外 v27 全套存在一项来源冻结不一致”，
不能表述为两套验收全部通过。该失败不涉及本轮恢复实现，应单独核对旧配置的变更来源。

2026-10-31补充：上述来源不一致已按 [独立来源审查流程](../v27/source_reconciliation_20261031_001/README.md)
处理，原来源清单和本节历史失败报告均保留。最新两套验收报告见该修订说明，不回写历史结果。

重跑本次 SkillAdam 验收：

```bash
/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python scripts/verification/verify_lmb_skilladam_offline.py --output artifacts/verification/lmb_skilladam_recovery_boundaries_20261030
```

验收仅证明所列离线路径与合成故障恢复，不包含真实模型效果或服务容量验证。

## 2026-10-31 归档完整性补充

整体恢复现检查未完成Actor日志，共用Actor核对每次请求和失败尝试指纹；损坏时在worker及优化器请求前停止，修复档案后真正未完成任务仍可恢复。原生优化器未改动。详见[修订及验收](../v27/ACTOR_ARCHIVE_FIX_20261031.md)。

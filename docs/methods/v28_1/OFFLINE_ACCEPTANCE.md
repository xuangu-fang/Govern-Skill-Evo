# v28.1 独立配置与离线验收

日期：2026-11-03。第五步已完成：独立配置、两个已审查 Prompt 的运行接线、无哈希的 v28.1 归档路径，以及可重复执行的离线验收。145 项测试全部通过（12 项 v28.1 专项、133 项 v28 回归），无失败或跳过。正式训练和真实 Test 均未启动。

## 配置与运行目录

- 配置：[v28_1_searchqa_train600_batch30_20261103.json](../../../experiments/configs/v28_1_searchqa_train600_batch30_20261103.json)。
- 运行路径：[run_plan.json](run_plan.json)。Train、Test、比较目录均为独立 v28.1 路径；目前仅预留路径，没有创建正式运行或监督任务。
- 验收脚本：[verify_v28_1_offline.py](../../../scripts/verification/verify_v28_1_offline.py)。
- 结果：[offline_acceptance.json](offline_acceptance.json)；逐项日志：[offline_acceptance.log](offline_acceptance.log)。

与已完成 v28 Replay v3 的实际配置直接比较，仅以下三个配置值不同，见 [config.diff](config.diff)：

| 配置位置 | v28.1 |
|---|---|
| `method.version` | `v28_1_campaign_v1` |
| `method.prompts.diagnosis` | `v28_1_searchqa_diagnosis_v1` |
| `method.prompts.preconditioner` | `v28_1_searchqa_preconditioner_v1` |

初始化仍是同一 104 字符 Skill 与空 Memory；600 题的采样和顺序、20×30 调度、1400 题 Test 顺序、Actor 32768、15/15 并发、各阶段预算、超时及六次尝试额度均沿用基线。不继承 v28 的最终 Skill、Memory 或执行缓存。

## 接线与改动范围

沿用 `src.skill_evolution.v28.cli`，由配置中的方法版本选择运行分支。v28.1 直接加载本目录已审查的 [Diagnosis](prompts/diagnosis.md) 和 [Preconditioner](prompts/preconditioner.md)；Grouping、Editor、Replay 加载 `baseline/prompts/` 中的原实际发送文本。本步没有再修改两个 Prompt，也没有新增输出字段、阶段、工具或模型调用。

运行差异见 [runtime_wiring.diff](runtime_wiring.diff)。除 Prompt 选择和版本标识外，兼容接线用于落实已确认的“不采用哈希防御”：

- v28.1 不计算数据、任务目录、执行记录或失败收据的 SHA256，也不使用源码／Prompt 哈希门槛。
- 任务目录直接使用编码后的任务 ID；配置、任务顺序、模型请求、原始响应与结果仍按内容核对。操作期间的归档一致性使用直接字节比较。
- Test 记录固定 Skill 文本与文件位置，不生成 Skill 哈希。运行元数据标明 v28.1，便于无配置参数的报告读取和 Test 恢复识别。
- 原 v28 分支保留原行为及历史归档格式；没有改写 v28 或 SkillAdam 的配置、结果目录。

源文件快照继续只供审阅，不作为恢复时的匹配门槛。v28.1 测试将摘要函数替换为一经调用就失败的桩，覆盖初始化、五阶段、失败恢复、Memory 和 Test，确认这些实际路径不依赖哈希。

## 离线验收范围

1. **实际配置与输入**：逐项比较基线配置；核对 600／1400 个任务 ID 及顺序；2000 题 Actor 消息与归档模板直接比较；检查五模块实际渲染文本与选择的 Prompt 一致。
2. **原契约与条件传递**：通过原解析器和编译器验证 KEEP、精确修改、部分／全部撤回；触发条件与偏好强度进入 Effective Plan 和 Editor 输入；四项更新可全部保留；较长合成 Skill 可正常产生，没有新增数量或长度上限。
3. **完整执行链路**：模拟五模块执行、ACCEPT／RETAIN 后 Memory 记录、三个阶段的 `no_change`、20×30 全调度与独立 1400 题固定 Skill Test。模拟 Test 不写优化状态，不回流训练。
4. **恢复与选择**：13 个阶段／发布边界中断恢复；已保存响应复用；仅归档恢复；Actor 与方法六次额度不重置；语义停止不重采样；缺失响应不能冒充完成；严格 EM Gate，F1 只记录。
5. **旧行为回归**：原 v28 的 Actor、评分、模块输入、Memory、Replay、发布及恢复测试。原有 AST 文本同一性检查不再要求带新增参数的 `validate_slot` 与 v27 逐字相同，其默认 v28 行为继续由原有恢复与归档测试覆盖。

验收进程屏蔽网络连接和子进程；合成归档只写入临时目录并自动清理。实际运行约 83.7 秒，网络／子进程拦截次数为 0，真实模型请求为 0；详细结果已保存到 JSON 和逐项日志。

扩大检查时发现两个 SkillAdam 辅助测试类无法初始化：它们引用的旧 v28 配置使用 Replay v1／旧输入视图，而当前 v28 运行器已经使用 Replay v3／共享输入视图。用本步修改前的源码副本复现了同一失败，见 [legacy_skilladam_check.json](legacy_skilladam_check.json)。该既有兼容性问题单独记录，不纳入 v28.1 必需验收，也未通过更改历史配置或放宽验证来掩盖。

后续更新（2026-11-03）：按用户要求，已将 SkillAdam 的对照校验收窄到两组实验真正共享的参数，解除对 v28 专属方法配置的依赖；共享参数和 SkillAdam 自身算法参数的校验仍保留。上述 JSON 保留为修复前记录，当前状态及回归结果见 [SkillAdam 说明](../skilladam/SEARCHQA_V28_ALIGNED_20261101.md)。此修复没有修改已完成实验的配置或结果。

## 复验命令

在仓库根目录执行；不需要凭据，不启动实验：

```bash
/Users/didi/miniforge3/envs/SearchQA/bin/python -B scripts/verification/verify_v28_1_offline.py
```

只检查配置也可执行：

```bash
PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/SearchQA/bin/python -B -m src.skill_evolution.v28.cli validate --config experiments/configs/v28_1_searchqa_train600_batch30_20261103.json
```

## 后续正式运行入口（本步未执行）

统一从仓库根目录运行，并按原方式提供 `OPENAI_API_KEY`：

```bash
export PYTHONPATH=.:external/SkillAdam
V281_PY=/Users/didi/miniforge3/envs/SearchQA/bin/python
V281_CONFIG=experiments/configs/v28_1_searchqa_train600_batch30_20261103.json
V281_TRAIN=experiments/campaigns/v28_1_searchqa600_batch30_20261103
V281_TEST=experiments/evaluations/v28_1_searchqa1400_batch30_20261103

"$V281_PY" -B -m src.skill_evolution.v28.cli run "$V281_TRAIN" --config "$V281_CONFIG"
"$V281_PY" -B -m src.skill_evolution.v28.cli audit "$V281_TRAIN"
```

训练完整结束后，`audit` 返回最终保留 Skill 的 `final_parent` 路径。将该路径传入 `--skill`，再执行同一 1400 题固定 Skill Test：

```bash
"$V281_PY" -B -m src.skill_evolution.v28.cli evaluate "$V281_TEST" --config "$V281_CONFIG" --skill "<audit 返回的 final_parent 路径>"
```

中断后在对应命令增加 `--resume`，沿用已占用的尝试额度。不要在另一目录重新开始来绕过六次上限；最终 Test 使用最终保留 Skill，不按 Test 结果选择训练 checkpoint。若需要恢复监督任务，仍按既定边界单独建立，本步没有启用自动化。

## 解释边界

离线通过说明配置、契约和执行链路已接通，不能证明真实模型更善于提出／审核规则，也不能证明 Test EM／F1 会提高。整包 Gate 仍可能保留未显示独立收益的 Update；该机制本步未改变。

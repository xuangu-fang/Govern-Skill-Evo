# 报告 A：V23 统一调度实现与恢复验证

统一调度已经实现，离线回归为 **513 passed，19 subtests passed**，其中 34 项为新增串联/故障注入测试。使用实际模块运行器、读取器、JSON/引用验证器、Patch 应用、Memory 提交及 Gate 逻辑；仅替换模型回复和环境执行，不把 mock 通过解释为行为收益。

## 实际文件变更

- 新增 `src/skill_evolution/v23/evolution.py`：顺序轮次、冻结内容、有限尝试、停止/resume/status、Actor 调用、Memory 准备、原子发布及用量读取。
- 修改 `grouping.py`：将既有 HTTP 响应转换提取为 response_value，供保存响应的恢复复用；没有修改 Prompt 或 Grouping 规则。
- 修改 `src/adapters/alfworld/run_task_upstream.py`：为 chat 增加显式请求上限与严格响应选项；保留历史默认值，新 Campaign 单步最多三次。
- 修改 `src/adapters/alfworld/run_task_skill.py`：CLI 暴露上述选项并记录实际 request_policy，继续调用原 run_episode、RecordingSession 和环境协议。
- 新增 `tests/skill_evolution/v23/test_evolution.py`、正式实现文档及本实验配置、结果和报告。

没有修改 Diagnosis、Preconditioner、Editor、Replay、Memory 或 Gate 的模型算法；没有新增 Prompt。Memory 的轮次隔离在调度层通过独立目录完成，内部仍调用现有 commit_memory。

## 串联与正式状态

Parent 执行后依次 Grouping、Diagnosis、Preconditioner、Editor，再执行实际 Candidate。双方经真实身份、执行条件和初始状态核验后，先确定性 Gate，再调用 Replay。两者使用同批 Train 配对。正式状态只包含 next_round、Parent 引用和 Memory 引用。

round_input.json 保存实际 Parent、当轮完整 Memory、任务、初始配置和来源。源码、Prompt、协议及配置内容直接比较，不引入调度层哈希系统。Preconditioner 与 Replay 接收同一个 M_t，只有下一轮读取新 Memory。

Memory 新提交在轮次独立目录完成，上一状态的 Archive 文件只读复用；既有 Active 不变。确认 Gate、Replay 和新状态可读后，原子替换唯一 state.json。测试证明 Gate ACCEPT 后 Replay 失败不会提前晋级 Skill。

## 重试与恢复验证

每阶段每组最多三次请求；timeout、429、空回复、非法 JSON、缺字段、截断、无效 Patch、Replay 非法证据都注入失败，验证前两次失败、第三次成功及错误保留。401 只调用一次即停止。合法无需修改或语义阻碍不重试。

测试覆盖：

- 两轮 ACCEPT 和 RETAIN，各自正确推进 Skill，二者都能跨轮更新 Memory。
- 原始 M1 在第二轮修订为 M2，第二轮 Preconditioner 收到 M1，本轮不读取提前更新的 Memory。
- Editor 或 Replay 三次失败后停止，显式 resume 复用上游，Attempt 从 004 延续。
- Grouping 后中断；Memory 准备后、发布前、发布后中断；相应恢复不重复生成模型结果或 Memory ID。
- 已保存响应但尚未校验时，用 recovered/ 完成处理，Grouping 不新增 API 调用。
- Candidate 部分任务完成后失败，恢复仅重开失败任务，保留其他完整任务。
- 所有合法停点、空 Replay、完成后重复 resume、只读 status。
- 冻结配置和 Prompt 漂移拒绝；显式失败阶段预算修订保留原配置和上游。
- Actor 三次上限对网络、HTTP、空输出、截断、JSON 错误有效，非临时错误直接停止。

测试命令：

```bash
/tmp/gse-v23-py313/bin/python -m pytest -q \
  tests/skill_evolution/v23 tests/adapters/alfworld \
  tests/skill_evolution/v22/test_grouped_representation.py
```

原始日志见 `results/offline_tests.txt`。现有相关回归全部通过，没有删除失败测试或放宽模块契约。初期发现的测试假数据两侧初始菜单不一致已修正为真实可比较的测试输入，配对检查保持不变。

## 仍有的限制

首版单写入者顺序执行，不恢复进程内 ALFWorld 状态。用户 resume 可新开有限恢复预算，但本次真实验证不自行执行 resume。源码/共享协议发生变化时需要明确恢复说明或新 Campaign。网络请求结果未知时无法保证外部只调用一次；未知用量单列，不能伪造零消耗。

Gate 复用时仍验证输入及计数规则，不调用模型；来源与状态校验不因复用省略。当前真实实验只使用 Train，独立 Test 尚未执行。工程测试不证明持续学习有效。

## 真实运行后的读取核验

两轮真实完整完成，十个合法模块结果可由原读取接口直接校验，253 份 Actor HTTP 原文与 usage 核验通过。完成后的 Campaign 在禁用模型和 Actor 的条件下返回 complete，state.json 不变。423 个既有受保护档案未改写。真实出现三次契约失败后第二次成功，未耗尽预算；实际语义问题及消耗见报告 B。

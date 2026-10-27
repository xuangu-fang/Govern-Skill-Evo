# V23.5 action-only 落地记录

2026-10-24，按用户确认的措辞完成实现。未关闭 thinking，未改变动作解析器、模型预算、
重试调度、输出校验或进化流程。未启动真实训练、Test 或新增模型请求。

## 修改

- 新增 `src/skill_evolution/v23_5/alfworld_initial_skill.md`：与 SkillOpt 初始快照相比，
  只替换 Output format 一句；准备脚本验证全文差异仅为这项已批准修改。
- Actor 适配器增加显式 `action_only_v1` 输出协议，统一替换无历史/有历史模板的格式段落。
  原始 SkillOpt 文件与模板快照未修改，旧配置缺省仍使用旧模板。
- CLI、实际消息生成、protocol 记录、轨迹重载、facts 审计、训练/Gate/最终 Test 均接入
  同一配置。进化模块从真实记录获取新背景，不修改各模块职责或手工维护模板副本。
- v23.5 的准备、运行、最终 Test 默认入口指向新 `alfworld_action_only_001`。
  新配置只更换 `initial_skill` 并增加 `actor_output_format`，其余任务和运行参数与旧配置一致。
- 旧 SkillOpt 初始成绩显式标记为不同输出协议下的历史参考，不视为本次新初始配置的基线。

## 验证

- 新增 16 项 action-only 测试，扩展 4 项最终 Test 场景；相关专项合计 **27 项通过**。
  包括真实 CLI 参数传递（离线环境）、Actor 首步/后续消息、最近两步历史、完整进化链、
  Gate/Replay 背景一致、断点恢复、协议/消息篡改拒绝及旧模板默认值。
- 扩展回归命令覆盖 v23.5、v23.4、ALFWorld adapters、v23 Grouping/Prompt alignment：
  **1,041 项通过，2 项失败**。该轮在最后新增的 CLI 单测之前执行；随后专项 27 项全部通过。
- 两项失败在修改前源码的独立临时副本中均复现，报错相同：
  - `v23_4/test_evolution.py::test_actor_request_budget[permanent]`：测试认为 401 只请求一次，
    既有严格模式已将 401 纳入有界重试，实际三次。
  - `v23_4/test_output_budget.py::test_real_old_parent_new_actor_source_review`：历史源码快照
    与修改前工作区也已存在超出旧 budget amendment 白名单的差异，正确被拒绝。
  本次没有修改 401 策略、旧测试接受标准或扩大历史源码授权白名单。
- 生产代码生成的两个 Actor 请求和一个 Editor 请求，与前置真实 probe 的 aligned 组
  实际 messages **逐字一致**，避免“验证一套措辞、落地另一套”的偏差。
- 两份真实历史 Actor 轨迹仍可重载核验；旧实验与模板 **2,370 个文件哈希未变化**。
- 默认 `run_v23_5_alfworld.sh check` 可重复离线执行，脚本语法与 diff 空白检查通过。
- 新 Campaign 目录尚未初始化。所有新增配置/报告位于独立目录，不重写旧 `u3` 或请求档案。

扩展回归命令：

```bash
python -m pytest tests/skill_evolution/v23_5 tests/skill_evolution/v23_4 tests/adapters/alfworld tests/skill_evolution/v23/test_grouping.py tests/skill_evolution/v23/test_prompt_alignment.py -q
```

专项命令：

```bash
python -m pytest tests/skill_evolution/v23_5/test_action_only.py tests/skill_evolution/v23_5/test_actor_alignment.py -q
```

## 限制

这是对已知触发源的 Prompt 修改，不是 DeepSeek 服务端解析器修复。前置真实验证中，
保留旧 u3 的压力案例仍出现异常分界和长度截断；未来生成的 Plan 或 Skill 再次引入完整
think 标签时仍可能复发。本实现不自动过滤、改写这些后续输出，也不承诺零失败。

机器核对见 [implementation_validation.json](implementation_validation.json)，前置请求证据见
[action_format_probe_001](../../action_format_probe_001/RESULTS.md)。

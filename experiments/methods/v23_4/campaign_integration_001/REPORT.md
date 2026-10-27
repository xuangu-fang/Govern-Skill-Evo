# V23.4 总运行器集成与离线验收

日期：2026-10-22。结论：总运行器、配置冻结、跨轮 Memory 链路和最终 Test 入口已接通，通过离线验收；真实 Benchmark 尚未启动。

## 最终路由与配置

根据用户最新指示，V23.4 的 Grouping、Diagnosis、Preconditioner、Editor、Replay 和 Actor 统一使用：

- 接口：`http://llm-proxy.intra.xiaojukeji.com/chat/completions`
- 模型：`deepseek-v4.1-flash`

这两项是相对于历史 v23 官方接口 `deepseek-flash` 的明确差异。其他运行参数与 v23 最终生效配置一致：temperature=1、medium thinking、16,384 输出 token、300 秒、Actor 并发 8、50 步、最多 3 次总尝试、400 万字符 / 600 万消息字节。没有沿用最近独立 Replay 实验的 32K/64K 输出升级。

57 条优化仍是 39 Train + 18 Selection，原序 6 批；Test 仍为 134 条无重叠任务。仅另行修正 v23 残留的 pilot 预算说明，使其对应正式 57 条规模。`config/provenance.json` 明确列出允许差异，并逐字段核对其他配置，而不是把整个 call_config 排除于比较之外。

此前未启动的官方接口配置被保存在 `superseded_official_route/`（完整配置现见 [旧路由归档](../../../../artifacts/methods/v23_4/campaign_integration_001/superseded_official_route/)，保留材料见 [README](README.md)），未被当作已执行结果。当前正式目录已经重新冻结代理配置。旧 v23 Campaign、历史实验、生产默认 Prompt 和旧 Active Memory 未修改。

## 生产入口

新增：

1. `src/skill_evolution/v23_4/evolution.py`：版本化总运行器。沿用 v23 的有界重试、并行 Actor、归档重载和发布规则，接入 V23.4 模块；不通过修改 v23 全局模块来切换版本。
2. `src/skill_evolution/v23_4/benchmark.py`：从 v23 最终配置与真实任务清单确定性准备独立 Campaign，冻结依赖、运行时和差异依据；仅准备/核验，不执行任务。
3. `src/skill_evolution/v23_4/evaluation.py`：在全部优化轮次完成后解析正式保留 Parent，执行固定 Skill Test，默认只运行 S1 的 134 条任务。

正式配置：`experiments/methods/v23_4/v23_4_alfworld_formal_001/config/`。
正式优化输出：`artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1/`。

## 关键验收结论

- `entries_sources_multi_knowledge_v1` 贯通 Memory 加载、Preconditioner 输入、Adjustment、Patch、Effective Plan、Editor、Replay、提交与重载。
- 总运行器明确选择 P4 `v23_4_replay_multi_knowledge_v1`，没有落回 P3 结构模板，也没有启用 V2/V3 实验 Prompt。
- Replay 输入由 Editor Actual Diff、Effective Plan、当前真实 Pair、轮初 Memory 及其归档 Pair 构建；Memory v3 继续使用已有算法。
- 全部 Keep 仍进入 Editor；全部撤回不进入 Editor；Patch/引用/格式失败不转换为 Keep。
- ACCEPT 与 RETAIN 均可提交合法 Replay。Parent 与 Memory 仅在整轮完成后一起发布；下一轮才读取新 Memory。
- 两轮测试覆盖真实校验器下的完整 Knowledge 数组修订、旧证据保留、历史 Pair 投影，以及下一轮 Preconditioner/Editor 输入一致性。
- 模块 429、超时、格式、截断、Patch、Evidence 失败遵守重试上限；永久错误停止。语义停止不自动重采样。
- 中断后复用成功请求和 Actor 记录；已保存响应可零新增请求恢复；Memory 提交和状态发布可幂等恢复。
- 使用正式 57 条身份/顺序，以合成模型响应和合成轨迹走完六轮，验证 114 条 Parent/Candidate 记录、30 个模型阶段和最终 Memory。没有启动真实环境。
- 使用真实 134 条 Test 清单，以合成轨迹验证并行、部分失败恢复和完成后重入。最终 Skill 绑定最后正式保留的 Parent，即使最后一轮 RETAIN 也不误用最新 Candidate。Test 不写训练 Memory。
- 源码、Prompt、环境或配置不匹配时拒绝继续。当前代理路由与本地环境相符，key 存在；未测试 API 鉴权或网络可用性。

## 测试记录

- 整体回归：**1,024 passed，1 deselected**，98.61 秒，见 [pytest.log](../../../../artifacts/methods/v23_4/campaign_integration_001/pytest.log)。覆盖 V23.4、v23.3 与共享 v23；这一轮发生在用户修改模型路由之前。
- 代理路由更新后，对所有新增集成测试重跑：**48 passed**，19.39 秒，见 [pytest_proxy.log](../../../../artifacts/methods/v23_4/campaign_integration_001/pytest_proxy.log)。包含配置冻结、六轮 57 条闭环、134 条 Test、两轮 Memory 修订、路由防漂移、恢复和最终 Parent。
- V23.4 当前共 349 项测试，见 [collection.log](../../../../artifacts/methods/v23_4/campaign_integration_001/collection.log)。
- `benchmark verify` 最终通过，见 `final_preflight.json`；路由与凭据存在性检查见 `live_environment_preflight.json`。二者均无网络请求。
- `git diff --check` 通过。

整体回归明确排除依赖旧正式归档冻结源码的 `tests/skill_evolution/v23/test_formal_evaluation.py`，并 deselect `test_gate.py::test_real_archive_handoff_and_protection`。这些在前次审计中已因当前 Editor/共享源码与旧归档冻结版本不一致而失败。本轮没有修改它们、放宽旧归档检查或声称它们已通过；新运行器和最终评估改用从当前实现生成的独立合成 Campaign 验收。

可复核命令：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q -p no:cacheprovider tests/skill_evolution/v23_4 tests/skill_evolution/v23_3 tests/skill_evolution/v23 --ignore=tests/skill_evolution/v23/test_formal_evaluation.py --deselect=tests/skill_evolution/v23/test_gate.py::test_real_archive_handoff_and_protection --basetemp /tmp/v234_campaign_acceptance

PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q -p no:cacheprovider tests/skill_evolution/v23_4/test_evolution.py tests/skill_evolution/v23_4/test_evaluation.py tests/skill_evolution/v23_4/test_benchmark.py --basetemp /tmp/v234_proxy_acceptance
```

## 采用规则与剩余边界

新 Campaign 以自动、统一的结构与引用校验作为 Memory 发布条件；正式实验不人工挑选 Memory、修补文本后继续或为语义不佳重新采样。技术通过不能保证 Knowledge 正确，原有 Replay 语义风险仍可能在多轮中累积，需作为真实 Benchmark 结果记录。

本次证明了程序链路和恢复能力，没有证明方法收益、API 实时可用性或六轮真实上下文一定不超过容量。输出截断与输入超限仍按冻结预算停止，不在过程中自动改变研究条件。历史 v23 与新 V23.4 模型路由不同，也不能将将来的全部结果差异纯归因于方法。

正式状态仍是 `next_round=1, parent=null, active_memory=initial_memory`；无真实 request、轨迹或轮次。下一步可以按用户后续指令启动 57 条优化，再启动 134 条 Test。

完整启动、状态与恢复命令见 `docs/methods/v23_4/BENCHMARK_RUNBOOK.md`。

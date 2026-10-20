# V23.2 基线恢复记录

日期：2026-10-19。按用户决策暂缓第一项可执行性优化，恢复正式 V23 方法作为后续开发默认基线。本次无模型调用、无环境执行、无历史实验重跑，未开始第二项研究。

## 当前默认值

- Diagnosis：`src/skill_evolution/v23/diagnosis_prompt.md`
- Preconditioner：`src/skill_evolution/v23/preconditioner_prompt.md`
- Execution Context：`src/skill_evolution/v23/execution_context.md`

三者逐字等于正式 V23 `S1/contract.json` 中的冻结文本；V23 模块按原有恢复记录核对一致。原始文件从未需要恢复，本次未覆盖它们。Actor 的最近两组历史和执行设置，以及 Grouping、Editor、Replay、Memory、Gate、Orchestrator、JSON 契约、更新编译规则均未改动。

## 实际改动

1. `src/skill_evolution/v23_2/local_validation.py`：默认 `PROMPTS` 从同目录实验模板改为 V23 模块的 `PROMPT_PATH`；历史加载器说明改为显式选择实验路径。已有 `context_path`、装配／校验／编译逻辑不变。
2. `src/skill_evolution/v23_2/__init__.py`：更新包说明，避免将第一轮实验误认为现行方法。
3. 两个既有测试文件 `test_local_validation.py`、`test_final_update.py`：验证默认消息与 V23 完全一致；旧模板相关断言、合成归档及真实历史加载改用显式路径。未新增验证模块。
4. `docs/methods/v23_2/README.md`：简化为当前基线、暂缓决策、三次历史报告入口及六项后续优先级。比较方法情况明确归因于用户已完成的核查，本次未扩展外部研究。
5. 本恢复记录、离线结果和 `docs/04_EXPERIMENT_LOG.md` 的追加记录。

没有修改三次实验目录、旧模板、原始响应或实验结果；旧 `run.py` 与实现快照作为历史保留，不用来重新开展后续开发。后续代码默认继承 V23，不能因旧文件仍在原位置而自动采用其规则。

## 历史档案读取

保留 `local_validation.load_attempt(directory, prompt_path=..., context_path=...)` 的严格消息及原始响应核对，没有自动忽略 Prompt 差异或放宽契约。

| 实验 | 显式 Prompt | 显式 Execution Context | 重读结果 |
|---|---|---|---|
| executability_001 | 原位置 `src/skill_evolution/v23_2/{module}_prompt.md`，与该实验实现快照一致 | 不覆盖，使用原 V23 | 5 个有效档案通过 |
| executability_002 | 该实验 `config/preconditioner_prompt.md`，与其实现快照一致 | 不覆盖，使用原 V23 | 2 个有效档案通过 |
| capability_001 | 原始 V23 Preconditioner，与正式冻结契约一致 | 该实验 `config/execution_context.md`，与其实现快照一致 | 1 个有效档案通过；R03 原技术停点保留 |

总计 **8 个有效档案**从原始响应严格重读，Preconditioner 档案重新确定性编译并与原 Effective Plan 相等；**7 个无效尝试**及错误信息完整保留，没有修复为有效结果。所有有效档案使用当前默认入口渲染的消息另行与原 V23 模块逐字比较一致，证明后续默认规则已回归 V23，而历史必须显式选择。

## 必要离线验证

禁用网络，运行：

```text
pytest -q tests/skill_evolution/v23_2 \
  tests/skill_evolution/v23/test_diagnosis.py \
  tests/skill_evolution/v23/test_preconditioner.py
```

**163 passed in 2.65s**。范围仅覆盖实际受影响的局部入口、历史配置及所复用的 Diagnosis／Preconditioner 契约和编译；既有局部测试同时验证纯 Editor 输入交接与 Memory 不变，未运行 Editor 模型或环境。见[测试输出](baseline_restore_tests.txt)。

修改前后对 **11,483 个文件**建立 SHA-256 清单核对，文件集合和内容均未变化。保护范围包括 V23 源码与 ALFWorld Adapter、V23 实验配置及全部正式产物（Campaign、最终 Skill、Memory、Test）、三次 V23.2 实验配置／产物和保留在源码目录的旧实验模板。详见[核验结果](baseline_restore_verification.json)。

当前结论：第一项“已发现、已分析、暂缓处理”，并未解决；下一阶段优先研究历史反例对更新方向、范围与实现方式的实际约束。本次在基线恢复与归档核验后停止。

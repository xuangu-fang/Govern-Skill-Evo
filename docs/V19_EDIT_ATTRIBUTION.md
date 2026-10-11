# v19 第 4 步：edit-level 效果归因

本步实现归因 Prompt、完整 edit 覆盖、引用和结果方向校验，以及一次调用的可审计运行与恢复接口。输入来自第 2 步账本和第 3 步完整配对回放，输出为 `AttributionRecord`。归因是效果关联假设，不是逐 edit 因果干预结果，也不是 Skill 修改授权。

实现文件：

- `src/skill_evolution/attribution_v19.py`：输入构造、响应验收、运行和落盘恢复。
- `src/skill_evolution/attribution_prompt_v19.py`：版本化归因 Prompt。
- `tests/skill_evolution/test_attribution_v19.py`：构造数据测试，未调用真实模型。

## 输入与边界

`build_attribution_input(ledger, backend=..., parent_dir=..., replay_dir=..., history=())` 首先重新校验账本，调用第 3 步 `load_candidate_replay` 从私有检查点重建并验证学习投影，而非信任任意传入的 ReplayBatch JSON。

模型输入包含本轮全部 EditRecord、精确 Parent/Candidate Skill 文本、全部配对轨迹及其公开上下文、Level-0 监督标签和确定性变化量。只有必要的来源摘要用于绑定；不传整个私有账本源、历史 Gate 决策或运行产物目录。`history` 仅参与账本有效性校验，不直接作为模型输入。edit 中的历史关系仍只是来源事实，不能作为本轮效果证据。

Prompt 要求通读成功、退化和持平配对，不截断轨迹、不仅挑失败样本。模型上下文容量不足导致的调用失败会保留为 INCOMPLETE，不自动缩减输入或补造 UNKNOWN。

## 输出与验收

模型只输出 `attribution_response_v19.1` 的 `records`；程序添加 schema、run/round 和绑定完整输入的 attribution ID，返回 `AttributionBatch`。每条记录遵循第 1 步 AttributionRecord 契约。

- **覆盖**：每个 edit 至少出现在一条记录中。联合 edit_ids 只生成一条联合关联记录，不向各 edit 复制独立功劳；同一 edit 可保留多条不同范围的记录。
- **引用**：逐条解析 pair、角色、事件和两侧 supervision_refs；不允许用 source gap、其他轮次、另一角色事件或最终标签冒充本侧行为证据。
- **证据等级**：OUTCOME_ASSOCIATION 可仅引用标签；BEHAVIOR_SUPPORTED 的每项 SUPPORT 必须引用两侧 assistant/tool 的实际观察事件。用户话语或标签本身不足以满足这一结构条件。
- **方向**：对本条记录 SUPPORT/COUNTEREVIDENCE 中的两项结果维度分别检查，正负并存必须 MIXED；不能用净收益掩盖冲突。BENEFICIAL/HARMFUL 分别要求有正向/负向变化且无反向变化；NO_OBSERVED_EFFECT 要求该关联范围标签持平，允许行为变化。
- **未知和未触发**：UNKNOWN 可无 observations，但须 UNRESOLVED/DEFER；NOT_EXERCISED 必须提供两侧范围证据、适用条件和不确定性，仍为 UNRESOLVED/DEFER。缺少找到的证据不等于没触发。
- **建议**：PRESERVE / REVISE / CONSIDER_REMOVE / RETRY / DEFER 均不执行编辑。DELETE 仍需下一轮独立 Diagnosis 授权；本模块不读取 Monitor 或预测 Gate。

严格拒绝未知字段、缺失字段、重复 JSON key、非 JSON 数值常量、重复记录和未覆盖 edit。所有记录必须给出非空解释、适用范围、不确定性和替代解释。

### 验收能力的界限

产物明确标记 `validation_scope=STRUCTURE_AND_REFERENCES_ONLY`。程序能验证引用存在、属于正确角色、是否覆盖 edit、已引用结果是否冲突；**不能证明自然语言解释正确，也不能证明模型没有漏掉语义上相关的反证**。相关性、适用条件与跨任务反证识别由 Prompt 约束，后续需要真实数据检验。

同样，程序无法仅凭 assistant 消息可靠判断其是实际沟通行为还是因果自述；Prompt 明确禁止把“我检查过了”等自述当作检查证据。通过结构验收不代表这一语义要求已被自动证明。BEHAVIOR_SUPPORTED 始终是关联证据等级，不代表排除了其他 edit、对话变化或采样随机性。

方向校验当前针对 Level-0 success/compliant 的关联范围。标签持平时可记录行为改善/恶化假设，但 effect 使用 NO_OBSERVED_EFFECT，并在解释中保留行为差异；不将未测得的收益伪装成已测得效果。

## 调用和恢复

```python
from src.skill_evolution.attribution_v19 import run_attribution, load_attribution

batch = run_attribution(
    ledger,
    backend=backend,
    parent_dir=parent_dir,
    replay_dir=candidate_replay_dir,
    artifact_dir=attribution_dir,
    history=history,
)
# 只读重验输入、响应、引用和摘要，不调用模型：
restored = load_attribution(
    ledger, backend=backend, parent_dir=parent_dir,
    replay_dir=candidate_replay_dir, artifact_dir=attribution_dir,
    history=history,
)
```

真实调用只在调用者显式运行 `run_attribution` 时发生。本步未执行上述真实调用。默认模型设置沿用既有编辑阶段的配置风格：deepseek-v4-pro、temperature=0、reasoning_effort=high、24,000 输出 token、300 秒超时、SDK 重试为 0；本步未修改 v18 设置。可注入 `transport(request)` 做无网络测试；生产调度留待第 7 步。

目录保存 `input.json`、`request.json`、`response.json`、`response_complete.json`、`attributions.json` 和 `validation.json`。请求绑定 Prompt 和模型配置，响应完成标记绑定输入/请求/响应摘要。只有最后的 VALID 标记及完整摘要、响应重验都通过，才能读取阶段产物；VALID 仅指上述结构/引用范围。

- 已完整完成：显式 `resume=True` 校验后复用，不调用模型。
- 响应已完成落盘、验收或输出写入中断：显式恢复只重验同一响应。
- 模型拒答、截断、格式错误或引用错误：INCOMPLETE，不能转成有效 UNKNOWN，也不进行自动修复。
- 没有可验证的完整响应：恢复拒绝自动重复调用；若明确要新尝试，使用新审计目录，保留旧记录。
- 输入、Prompt 或已记录响应变化：拒绝复用。摘要是审计一致性检查，不是针对可同时改写所有文件者的数字签名。

本步不提交 Memory、不晋升 Skill、不接入完整 campaign。v19 benchmark 后端绑定 v19 源码版本，新增归因源码后，旧源码版本下的预检/运行不能被当作当前版本产物直接恢复，这是已有来源绑定规则的预期行为。

## 验证

新增 49 项专项测试，覆盖六类效果、联合与分范围记录、反证/维度冲突、UNKNOWN 与失败区分、角色引用、全部 edit 覆盖、空 Candidate DELETE、模型失败、响应恢复、篡改和 Prompt 漂移。连同前序 v19 和相关 v18/v4 回归共 190 项通过。

全部使用构造轨迹和注入 transport，真实模型调用为 0。没有新增消融或多组实验；归因语义质量尚未经过真实模型实验验证。

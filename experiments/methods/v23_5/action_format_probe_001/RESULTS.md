# Action 输出格式与推理分界验证

2026-10-24 完成 **16 次真实 DeepSeek 请求**，没有自动重试、ALFWorld 环境执行、
Actor/Gate 评估或正式版本修改。新措辞在本次干净输入样本中可行，但未证明它可以
杜绝异常分界；保留历史 `u3` 的压力案例再次出现同类异常，因此暂不修改正式配置。

## 固定条件与改写范围

全部使用 `deepseek-v4.1-flash`，`thinking={"type":"enabled"}`，
`reasoning_effort=medium`，`temperature=1`，`max_tokens=16384`，非流式。
实际响应模型名一致。最多两个请求并发，每个案例一次请求；总报告 usage 为 78,253 tokens。
所有实际请求、原始 HTTP 响应及校验结果保存在独立 artifacts 目录。

验证的措辞为：

```text
Return exactly one XML-style element named `action`.
Its text content must be one command copied verbatim from the current admissible action list.
Do not include any text outside this element or any nested elements.
```

三个组分别保留原始输入、仅改 Skill 的 Output format 句、同时改 Skill 与 Actor
基础模板的输出格式段落。Editor 对照同步修改系统提示词中展示的 Actor 基础模板，
并对修改后的 Parent 副本应用补丁，未对线上请求做隐式替换。
所有 Plan 保持原值；尤其 R04 的 `u3` 未删除或改写。

原 Skill 与 Actor 模板都来自 SkillOpt。初始快照与本地
`external/SkillOpt/skillopt/envs/alfworld/skills/initial.md` 逐字节一致，
基础模板与其 `prompts/rollout_no_history.md`、`rollout_with_history.md` 逐字节一致。
仅改 Skill 无法消除基础模板中的强制 think 标签要求。

## Actor：12 次响应复测

复用历史 R04 `P1:49` / train_0030 与 `P2:8` / train_0031 的完整请求上下文、
合法动作集合，每个案例每组重复两次。只请求模型和执行动作解析，没有把动作送入环境。

| 条件 | 请求数 | stop | 现有解析器提取合法动作 | 正文仅一个合法 action 元素 |
|---|---:|---:|---:|---:|
| 原始写法 | 4 | 4 | 4 | 0 |
| 仅改 Skill | 4 | 4 | 4 | 0 |
| Skill 与基础模板同时改 | 4 | 4 | 4 | 4 |

同步改写组全部保留非空的独立 reasoning_content，正文没有 think 标签、示例或解释文字。
另外两组仍在正文输出分析，其中原始组两次、仅改 Skill 组三次含完整 think 标签。它们这次均能提取合法动作，
不能把“不满足新方案的 action-only 约束”计为旧 Actor 协议失败。
原始组本次没有复现历史的错误动作，因此本试验不能估计动作失败率下降。

机器结果中的 Actor `valid` 字段表示新方案的 exact-action-only 检查；旧解析器兼容性
应查看 `projected_action_valid`，而不能将前者作为三组原协议的通过率。

## Editor：4 次复测

| 输入 | 条件 | 结束原因 | 严格 JSON 与原子补丁校验 |
|---|---|---|---|
| R01 | 原始写法 | length，16,384 tokens | 未通过；先按截断处理 |
| R01 | 仅改 Skill | stop，4,042 tokens | 通过，生成 Candidate |
| R01 | Skill 与基础模板同时改 | stop，2,852 tokens | 通过，生成 Candidate |
| R04，保留旧 u3 | Skill 与基础模板同时改 | length，16,384 tokens | 未通过；先按截断处理 |

R01 同步改写输入不含完整 think 标签，返回正文以 JSON 对象开始；严格解析和现有
`validate_editor` 原子补丁应用均通过。Candidate 不含 think 标签。这里只验证
JSON/schema/补丁结构和对副本的确定性应用，没有运行完整上游来源重载或评价策略效果。

两个失败样本都在原始 HTTP 响应里呈现与历史故障相似的分界迹象：

- R01 原始组的 reasoning_content 结束在讨论 `Always output` 的位置，正文从
  `` ` for reasoning, then `` 开始，后面混入 Skill 文本，最终达到 token 上限。
- R04 压力组的 reasoning_content 结束在讨论 `u3` 的逐步推理格式要求的位置，
  正文从 ` only.` 开始，后续继续讨论 Plan，最终达到 token 上限。

这支持“字面 think 标签与推理/正文分界冲突”的怀疑，但未定位到服务端具体实现。
`finish_reason=length` 是已确认的预算截断；异常分界是根据原始字段边界识别的另一
现象，两者分别记录，不把截断后不完整 JSON 当作普通格式错误。

## 结论及未修改范围

1. 新措辞能在保留 thinking 的情况下产生现有解析器可用的动作，并在一个干净的
   Editor 案例中通过完整 JSON/补丁校验。仅修改初始 Skill 与现有基础模板存在冲突。
2. 新实验若采用该方向，需要显式同步修改 Actor 基础模板及各模块看到的执行协议，
   并记录为区别于 SkillOpt 原协议的新配置，不能只在发送请求时替换文本。
3. R04 压力案例不是“从头开始”的实验：它有意保留了旧 u3。无需改动旧 u3 或历史档案。
   但它说明：若未来生成的 Plan 再引入完整 think 标签，仅靠初始 Prompt 改写不能保证安全。
4. 小样本不能证明零异常，也没有证明端到端任务成功率提高。当前不宣称根治，
   不修改 V23.5 正式源码、基础模板、初始 Skill、配置、冻结档案或重试额度。

后续若要求保证不会因标签内容误拆分，应进一步定位并修正服务端推理分界处理。
若接受先降低触发概率，则可以把同步改写作为独立的新实验条件，但应明确其限制。

## 文件

- [预先记录的验证协议](PROTOCOL.md)
- [验证脚本](run.py)
- [完整机器结果](results/summary.json)
- [输入与请求参数](../../../../artifacts/methods/v23_5/action_format_probe_001/manifest.json)
- [历史离线完整性核对](results/offline_verification.json)

## 2026-10-27 材料整理说明

以上结论、调用次数和测试数量保留历史阶段含义。本次仅补充证据副本与链接，未重新运行实验或校验；保留边界及原始归档见 [目录说明](README.md)。

# V22 08：R2 分类恢复及 Fusion 停点记录

日期：2026-10-15。本记录对应北京时间 18:39:51—18:46:59（UTC 10:39:51—10:46:59）的这一次授权恢复。**分类与 Diagnosis 完成，Fusion 返回不合法 JSON，恢复按声明停止；未进入 Editor、Candidate Replay、Gate 或 Memory 更新，仍未完成第二轮 Skill 更新。** 后续若另获恢复授权，应另存协议、调用、成本和报告，不覆盖本记录及本次失败产物。

[原实验报告](REPORT.md) · [本次结构化结果](../results/recovery_summary.json) · [本次档案核验](../results/recovery_verification.json)

## 恢复问题、授权与复用边界

原运行在 R2 全局分类因输出截断停止，R1 已 ACCEPT 并正式发布 Skill 和三条 Effect。本次依据用户的分类恢复授权，检验：给同一份分类输入更大的输出额度，能否完成分组并继续原有更新机制。

新档案位于 `artifacts/methods/v22/08_grouped_continual_recovered_20261015`，与原运行目录分开。恢复入口记录原目录 208 个文件的哈希；本次结束后原文件均保持不变。原失败调用、部分响应、messages、输入和报告另保存在新目录的 `archived_failure/`，旧失败成本继续计入累计账本。

复用 R1 正式状态及 R2 已完成的十条 Parent 轨迹，不重新执行 Parent，不重新生成 R1 Skill 或 Memory。实际继承的 Skill SHA256 为 `6ead6e278eddfb70cb00d71ecb6987dc5d59396cfb0bd8e39cfab7797a1862fa`，Memory 为 R1 发布的三条 Effect；十条 Parent 原生成绩仍为 7/10。归档核验确认状态、实际注入 Skill、轨迹及分类输入衔接一致。

本次唯一的阶段参数变更是分类 `max_tokens=32768`、`timeout_seconds=600`，分类完整 messages 与原失败请求相同。分类仍是一次全批调用，输入 131,044 Unicode 字符。其余阶段沿用输出上限 16,384、timeout 300 秒；模型、提示、D/S/C 契约、Editor、Replay、Gate、Memory 语义不改，Candidate 若产生仍至多八并行、每项最多五十步。本恢复声明不允许额外语义或 episode 重试。

## 实际阶段结果

| 阶段 | 输入 tokens | 输出 tokens | 其中 reasoning | 结果 |
|---|---:|---:|---:|---|
| Classification | 38,531 | 9,548 | 8,672 | `finish_reason=stop`，有效四分组 |
| Diagnosis | 51,174 | 8,516 | 7,836 | `finish_reason=stop`，有效三项初稿 |
| Fusion | 75,663 | 8,518 | 8,088 | `finish_reason=stop`，正文 JSON 解析失败 |

三次请求均只有一次 HTTP 尝试，未发生传输重试。分类此次输出 9,548 tokens，低于旧上限 16,384；因此成功只能说明这次调用产生了完整输出，**不能证明提高上限导致成功，也不能证明旧上限必然不足**。远端生成存在变化，不能把两次结果当成受控因果比较。`prompt_tokens` 包含服务端报告的缓存输入，不等同于未命中缓存的计费 token 数。

### 分类与独立 Diagnosis

四组分别组织：第一件拿取后的双物体交付；状态操作后放置；无状态变化的单物体转移；已持目标但指定工具未观察到。双物体组将 0036 的第二件未见，与 0037／0038 的同来源仍有第二件区分，具有实际决策条件依据。

分类也有语义遗漏：状态操作组将 0024 描述为拿到目标后进行状态操作，未突出任务请求 Pan、实际操作 Pot 的错对象问题。组结构可用于组织证据，但组描述不能替代对轨迹事实的核对。

Diagnosis 在没有历史 Memory 的条件下形成三项初稿：

1. 持有目标但所需工具尚未出现时，调整搜索，避免反复 examine／移动。
2. 未见请求类型时，不把其他类型当作目标加工交付；这项明确识别了 Pan／Pot 混淆。
3. 第一件已交付、第二件未见时，调整搜索并避免拿取无关物体。

初稿保留成功流程的意图，但多处使用“未访问候选耗尽后停止”的表达。当前 Actor 只有最近两步历史、没有全局访问集合，也没有合法 stop 命令；这些是待构造及执行检查的能力边界，不能把初稿写成已经实现的修复。

### Fusion 的语法与契约停点

Fusion 原始响应保存在 [raw_outputs/fusion.txt](../../../../../artifacts/methods/v22/08_grouped_continual_recovered_20261015/rounds/r2/raw_outputs/fusion.txt)，完整请求与服务端响应保存在 [calls/fusion.json](../../../../../artifacts/methods/v22/08_grouped_continual_recovered_20261015/rounds/r2/calls/fusion.json)。服务端返回 `stop`，没有耗尽本次输出额度；协调器因 `response: expected one valid JSON object` 停止，不能将其称为又一次输出超长截断。

原始正文拟保留 u1—u3，并引用历史 m1 追加直接 heat/cool 要求 u4；但它没有形成有效的 Fusion 决定。离线只在内存中检查了结构修复：在首个 `basis` 前的逗号处插入 `}]`，关闭 `to` 中的 `{id,text}` 对象及数组，使 `basis/reason/disposition` 回到 change 层。此操作不改变文字、引用或决定，可得到可解析 JSON；**没有将修复结果写回原始产物或继续执行**。

修复后，现有 `compile_update` 仍拒绝该输出：

```text
change.from: empty, duplicate or unknown reference
```

模型给出的 `changes[0].from=[]` 不符合当前机制：更新变换必须关联至少一项现有要求。`watch_changes.from=[]` 可以新增观察问题，不代表 `changes.from=[]` 也合法。为它选择原始要求、改成 Keep，或改变契约允许独立追加，都涉及更新决定或协议变更，不能包装成纯格式修复。

该失败草稿虽然引用了历史 Effect，但拟新增直接操作要求与当前 Parent 的已有条款相近；没有有效编译、Editor 落实或 Replay，不能据此声称历史已经改变实际 Skill，或已经验证预条件化有效。历史 m3 的短窗口搜索限制也未被这份无效草稿转成可执行变换。

## 成本、验证与最终状态

| 项目 | 原运行 | 本次新增 | 累计 |
|---|---:|---:|---:|
| 环境 episodes | 30 | 0 | 30 |
| Actor 逻辑请求 | 650 | 0 | 650 |
| Pro 语义请求 | 5 | 3 | 8 |
| 全部逻辑请求 | 655 | 3 | 658 |
| HTTP 尝试 | 659 | 3 | 662 |
| 已报告输入 tokens | 851,898 | 165,368 | 1,017,266 |
| 已报告输出 tokens | 458,715 | 26,582 | 485,297 |
| 已报告总 tokens | 1,310,613 | 191,950 | 1,502,563 |
| 用量未知的 HTTP 尝试 | 4 | 0 | 4 |

复用的十条 Parent 不重复计费。旧失败分类、本次失败 Fusion 和原四次未知用量尝试均保留；未知用量不是零成本。未使用的 Candidate 或后续语义预算没有转成补调用。

实现阶段完成 325 项离线测试及恢复路径合成验证。本次真实档案核验返回 `artifact_valid=true`、`campaign_complete=false`、`published_rounds=1`、`new_semantic_calls=3`、`reused_parent_episodes=10`，并确认原失败分类保留。测试和档案核验只说明程序路径、来源与账本可核对，不证明模型语义判断或预条件化收益。

本次没有生成有效 Fusion 输出、第二轮 Candidate 或第二轮末状态；最后有效状态仍是 R1 已发布 Skill／Memory 的继承副本。历史材料已经作为 Fusion 输入被消费，但“历史响应→合法更新变换→实际 Skill→执行反馈”尚未贯通。后续是否额外恢复 Fusion，取决于新的明确授权和单独记录；本报告截至此次停止，不包含任何后续重试结果。

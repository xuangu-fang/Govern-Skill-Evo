# R05 Replay / Memory 验证结果

日期：2026-10-22（Asia/Shanghai）。

**已完成不修改机制的验证：Replay 首次调用、结构校验、隔离 Memory 往返及后续输入投影均通过；语义审查发现事实和适用条件错误，三个原样提案暂不采用。** 本轮没有修改任何生产源码或 Prompt，没有运行新 Diagnosis、Preconditioner、Editor 或 Actor。

## 输入与执行

- 使用 `semantic_generation_007` 的真实 Candidate、实际 Skill Diff 和冻结 Effective Plan。
- 使用 `r05_actor_comparison_001` 全部 10 对新执行，20 条完整轨迹、301 步；两侧均 8/10，总步数 152 → 149，共同成功任务 52 → 49。
- 使用 `semantic_generation_006` 的原始 Memory，与 S1/R04 历史 archive/active 重载内容完全一致；没有混入 R06 预览条目。
- 输入 1,651,512 字符，显式实验上限 2,000,000；生产默认 400,000 未变。没有截断完整轨迹或 Memory，也没有将人工报告提供给模型。
- **1 次逻辑调用、1 次 HTTP、0 次重启，83.570 秒**。首个结构合法结果即选中，没有语义重采样。
- API 报告：480,881 input + 12,420 completion = **493,301 tokens**；金额未提供。

采用与 R06 相同的独立 evaluation adapter：重新验证冻结 Editor 输出和实际 Diff，再用新 Parent facts 构造评估输入。新 Parent 执行不是生成 Original Plan 的旧事实，**不声称通过了生产 Editor→Replay loader 的原始轨迹血缘验证**。[输入来源](config/provenance.json) 明确保留该边界。

## 提案与核对

| 本地预览条目 | 操作 | 主要认识 | 审查 |
|---|---|---|---|
| M10 | 新增 | 动作合法性指引仍未阻止非法导航，fallback 收益未隔离 | 主要反例正确，多数动作合法不能证明实际做了检查 |
| M11 | 修订 M6 | 冷苹果搜索提前、两类困难任务仍循环，全批 8/10 不变 | 主要事实正确；把未找到写成不存在，并用 desklamp 绕路解释非 desklamp 条款 |
| M12 | 修订 M8 | knife 替代 butterknife 仍发生；soapbottle 未被当作 soapbar 操纵 | 当前行为正确；把旧轮搬杯误写为加热杯，目标不存在的断言过强 |

三个 ID 只属于 `memory_preview/` 分支，由原 R05 输入的历史归档分配。它们与其他历史分支或 R06 预览里的同名 ID 不是同一条新知识，不能按 ID 直接混合。

预览 Active：M1、M2、M3、M7、M9、M10、M11、M12。原 Active 仍为 M1、M2、M3、M6、M7、M8、M9，所有原归档字节和内容未变。

具体引用、条件和历史事实核对见 [SEMANTIC_REVIEW.md](SEMANTIC_REVIEW.md)。部分跨任务叙述没有对应 evidence，未来 Preconditioner 视图只保留本轮三对任务，不能据“引用都合法”宣称知识完全有据。

## 已完成的程序核查

1. 核对 Actor 已冻结的全部 468 个文件，以及当前执行来源、20 条轨迹和 10 对任务/环境/协议关系；实际 Diff 严格重建当前 Candidate。
2. 核对冻结源、请求、原始响应、首次选中和现有输出校验；没有技术失败记录需要重试。
3. 在原历史 archive/active 的实验副本中原样提交；重载、revision 关系、全部证据解析与重复提交幂等性通过。
4. 压缩视图保留 1,941 步完整 action/feedback，490 步详细状态；167 个数字步引用均落在详细窗口内。保留的状态和菜单与源一致。
5. 现有 Preconditioner 消息投影可消费新预览 Memory；只执行离线装配，不调用模型。
6. 源 Memory 所有 JSON 哈希与重载结果不变，旧 archive 在副本中也未被改写。结构验证不等于语义批准。

沿用 R05 Actor 已有的离线审计兼容处理：从原始 HTTP 档案核验严格响应重试，不把合法输出重新采样，也不改变执行记录。空动作 P8:12 使用现有事实兼容能力，无新增生产修正。

## 产物与离线复核

- [原始 Replay](runs/R05_replay/attempt_001/parsed.json)
- [API 审计](AUDIT.json)
- [Memory 往返审计](results/MEMORY_AUDIT.json)
- [隔离 Memory 候选](../../../../artifacts/methods/v23_4/r05_replay_memory_001/results/memory_candidate.json) / [未来模型视图](../../../../artifacts/methods/v23_4/r05_replay_memory_001/results/memory_view.json)
- [语义核对](SEMANTIC_REVIEW.md)

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.r05_replay_memory_001.run audit
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.r05_replay_memory_001.check_memory
```

这些核查不调用模型。原始选中输出和冻结输入保持不变；派生审计记录可重新生成。

## 后续研究入口

已按用户指定，以 **V23 设计**完成[首轮差异梳理](../v23_design_comparison_001/REPORT.md)。V23 已有 Memory 和 D/S/C；重点是比较更新决定及其落实，而不是将 V23 当作无预条件化流程。

下一项最小研究是固定同一 Parent / Original Plan / 当前事实 / 原 Memory / 模型视图，分别运行 V23 与 V23.4 Preconditioner。先比较有效行为要求和证据运用，再决定是否进入共同 Editor 和真实执行。本轮尚未调用该对照，也未启动全套消融。

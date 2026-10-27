# R05 Parent / 当前 Candidate 真实配对执行

2026-10-22（Asia/Shanghai）。

**完整 10 对任务、20 条新轨迹已执行并审计。两组均成功 8/10，没有任务修复或成功率退化；共同成功任务总步数 52 → 49。Candidate 存在局部效率改善，但 u1/u2/u3 均不能认定为稳定遵循。**

## 冻结与配对

- 使用原始 R05 完整任务集合 val:0001–val:0010，包括两条 desklamp 任务；不是只运行 Preconditioner 输入选中的六条代表轨迹。
- Parent 与 `semantic_generation_007` Editor 的 Parent 完全相同；Candidate 是其首次结构有效输出，实际 Diff 重建相同。无人工 Skill 编辑。
- 两组均重新执行，没有拿历史 Parent 分数与新 Candidate 对比。当前 Actor 为 deepseek-v4.1-flash；历史别名为 deepseek-flash，历史配置不是本轮成绩来源。
- 相同任务/game/reset 初始观察和动作菜单、执行协议与实现、50 步上限、seed 42、最近两步观察、temperature 1、medium reasoning、16,384 输出预算；每条轨迹独立环境，最多 8 个并发进程。
- 20 条轨迹与原始响应档案检查通过；10 对 `recorded_conditions_match = true`。服务采样未提供确定性配对，因此只作单次开发批次的描述性比较。

## 第一层：任务结果

| 任务 | Parent | Candidate | 配对结果 |
|---|---|---|---|
| 0001 bowl + desklamp | 成功，4 步 | 成功，4 步 | 保持 |
| 0002 pillow + desklamp | 成功，5 步 | 成功，6 步 | 保持，Candidate 多 1 步 |
| 0003 mug → sidetable | 成功，4 步 | 成功，4 步 | 保持 |
| 0004 mug → sidetable，另一实例 | 成功，4 步 | 成功，4 步 | 保持 |
| 0005 pencil → desk | 成功，5 步 | 成功，6 步 | 保持，Candidate 多 1 步 |
| 0006 clean butterknife → drawer | 成功，8 步 | 成功，8 步 | 保持 |
| 0007 clean butterknife → drawer，困难实例 | 步数上限，50 步 | 步数上限，50 步 | 共同失败 |
| 0008 clean soapbar → cabinet | 步数上限，50 步 | 步数上限，50 步 | 共同失败 |
| 0009 clean soapbar → toilet | 成功，8 步 | 成功，6 步 | 保持，Candidate 少 2 步 |
| 0010 cool apple → microwave | 成功，14 步 | 成功，11 步 | 保持，Candidate 少 3 步 |

固定分母 10：Parent 8、Candidate 8；共同成功 8、共同失败 2、修复 0、退化 0。没有技术未完成任务，两个 50 步失败没有重跑。

## 第二层：效率

| 指标 | Parent | Candidate |
|---|---:|---:|
| 全部任务执行步数 | 152 | 149 |
| 共同成功的 8 项任务步数 | 52 | 49 |
| 无效/无效果执行 | 3 | 1 |
| 精确目标取得前的合法导航回访代理 | 58 | 61 |
| 同阶段重复 observation/menu/action 签名 | 33 | 27 |
| 非目标对象操纵次数，均集中于 0007 | 8 | 5 |

步数净少 3：0009 少 2、0010 少 3，抵消 0002/0005 各多 1。无效执行减少主要涉及 Parent 的空动作/格式异常；可识别的不可用导航为两组各 1 次。回访和状态签名是不同代理指标，不能把其中下降的一项当作整体防循环有效。

回访代理排除 desklamp 路线和取得精确目标后的返回；0007 从未取得精确目标，仍包含其错误替代物的搬运，因此不能等同于纯搜索错误。指标边界通过离线断言核对，定义及代码哈希见 [analysis_freeze.json](analysis_freeze.json)。

## 第三层：机制

- **u1 没有稳定阻止替代。** Candidate Q7:9/13 拿 knife，Q7:17 清洗，Q7:10/19 放回，但任务要求 butterknife。这是真实不遵循，不是“没有遇到触发条件”。0006 则两组都拿到正确 butterknife，保持成功。
- **u2 响应混合。** 0010 Candidate 更早扩展到 diningtable，搜索阶段少三步；0008 两组仍循环、都没有访问菜单中可选的 shelf 1，并在 50 步失败。0007 也未解决重复访问。
- **u3 文本范围修正不等于执行遵循。** Candidate Q8:39 仍发出不可用导航，下一步才查看已知空柜子。两个 desklamp 任务都保持成功，但未出现可检验直接动作回退的关键情境，不能认定 u3 已全面生效。

完整逐任务事实、局部菜单机会和归因边界见 [MECHANISMS.md](MECHANISMS.md)。Preconditioner 旧理由中的事实/归因问题仍保留；本轮不反向改写那些输出，也不由执行结果证明 Memory 的独立贡献。

## 并行与技术重试

- 20 条任务均在首次 episode 完成，**任务级重启 0**；预设允许每条最多三次技术重启，没有使用。
- 沿用 Actor 每步最多 3 次 HTTP 请求；8 个决策步骤发生技术重试，共增加 10 次请求。
- 共 **311 次 HTTP**：303 次 HTTP 200、8 次 HTTP 429。其中 Candidate 0007 第 10、13 步各有一次 HTTP 200 但 `finish_reason=length` 且内容为空，现有 strict-response 机制重试后才执行动作。
- 复用既有离线审计兼容检查，核对这两个截断响应的原始档案，只允许已确认的该类重试；没有修改响应或放宽其他验证。
- 全部 301 个执行步完成。API 已报告用量合计 **403,132 prompt + 220,451 completion = 623,583 tokens**；8 个 429 的用量未知，不能记为已知零费用。金额未知。
- 第一条 episode 开始至最后一条结束为 **721.539 秒**。详细请求重试清单见 [execution_receipt.json](results/execution_receipt.json)。

## 归档与复核

- [配对汇总 JSON](results/summary.json) / [任务结果 CSV](results/task_results.csv)
- [逐 episode 与配对审计](results/audit.json)
- [原始轨迹索引](TRACE_INDEX.md)
- [Parent](config/parent.md) / [Candidate](config/candidate.md)
- [冻结清单](config/freeze.json) / [执行方案](config/plan.json)

离线复核（不调用 Actor）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.r05_actor_comparison_001.analyze
```

本次仅执行用户授权的真实配对比较；没有新 Diagnosis、Preconditioner、Editor、Replay、Memory 采用或完整消融，也没有修改生产 Actor。当前结论是成功率持平、局部效率小幅变化、关键规则仍存在执行不遵循，不能宣布持续改进或独立 D/S/C 收益。

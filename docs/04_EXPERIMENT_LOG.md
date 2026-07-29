# Experiment Log

项目：Governed Skill Evolution  
说明：复制下面模板追加记录，不覆盖旧实验。

## Current Snapshot

更新时间：

### 当前研究问题

> 

### 当前最小假设

> 

### 本周 Go / No-Go 条件

- [ ] 

### 当前 blocker

- 

### 下一条要执行的命令或实验

```bash

```

---

## Environment

| Item | Value |
|---|---|
| OS | |
| Python | |
| uv | |
| Docker | |
| API provider | |
| Agent model | |
| User simulator model | |
| Optimizer model | |
| τ³ commit | |
| SkillOpt commit | |
| Trace2Skill commit | |
| Own repo commit | |

不要记录 API key。

---

## Experiment Entry Template

### EXP-YYYYMMDD-001：实验名

**Question**

> 这个实验只回答哪一个问题？

**Hypothesis**

> 如果……，那么……；可被什么结果推翻？

**Independent variable**

- 

**Controlled variables**

- model：
- temperature：
- tasks：
- policy version：
- prompt：
- seed / repetition：

**Data manifest**

- train：
- selection：
- test：
- excluded：

**Command**

```bash

```

**Artifacts**

- config：
- raw trajectories：
- candidate skill：
- accepted skill：
- verifier output：
- summary：

**Results**

| Method | Task success | Compliance | Severe violation | Cost | Notes |
|---|---:|---:|---:|---:|---|
| No Skill | | | | | |
| Human Skill | | | | | |
| Outcome-only Skill | | | | | |
| Proposed | | | | | |

**Qualitative cases**

1. 

**Failure analysis**

- model failure：
- tool/environment failure：
- task ambiguity：
- verifier error：
- skill defect：
- execution lapse：

**Conclusion**

> 支持 / 不支持 / 无法判断假设。只写证据允许的结论。

**Next action**

- 

---

## Trajectory Audit Template

### TRAJ-ID

```yaml
trajectory_id:
environment:
domain:
task_id:
policy_version:
model:
task_success: true | false | uncertain
task_score:
policy_compliance: true | false | uncertain
violations:
  - rule_id:
    rule_text:
    step_id:
    behavior:
    severity: low | medium | high
    evidence:
shortcut_summary:
alternative_compliant_action:
annotation_confidence:
annotator:
```

### 关键问题

- 最终结果为什么成功/失败？
- 哪个具体步骤改变了环境状态？
- 是否存在结果相同但过程不同的替代轨迹？
- 这条经验能否跨任务复用？
- 如果进入 Skill，最可能形成哪条规则？
- 这条规则在什么条件下会有害？

---

## Skill Change Record

### SKILL-CHANGE-ID

**Parent version**

``

**Candidate version**

``

**Patch**

```diff

```

**Proposed rule**

> 

**Applicability**

- 

**Obligations**

- 

**Prohibitions**

- 

**Escalation**

- 

**Supporting trajectories**

- 

**Counterevidence / rejected trajectories**

- 

**Task gate**

- before：
- after：
- pass：

**Compliance gate**

- before：
- after：
- severe violations：
- pass：

**Decision**

`accept | reject | quarantine`

**Reason**

> 

---

## Decision Log

只记录会改变研究设计、数据、方法或论文叙事的决定。

| Date | Decision | Evidence | Rejected alternative | Revisit when |
|---|---|---|---|---|
| 2026-07-28 | 第一阶段以 τ³ 为主环境，SkillOpt 为优化器骨架 | policy、tools、tasks、trajectory 均公开；可快速跑通 | 直接搭 FraudOps | 公开环境无法产生稳定 goal conflict |

---

## Failure Taxonomy

持续维护，不要每次重新发明 failure name。

| Code | Failure type | Definition | Example |
|---|---|---|---|
| T1 | Task misunderstanding | 误解用户目标 | |
| T2 | Wrong tool/action | 工具或参数错误 | |
| T3 | State tracking | 未跟踪环境状态 | |
| P1 | Missing obligation | 跳过必要步骤 | |
| P2 | Prohibited action | 执行明确禁止动作 | |
| P3 | Order violation | 顺序错误 | |
| P4 | Authority violation | 越权 | |
| P5 | Missing evidence | 证据不足时行动 | |
| P6 | Missing escalation | 应升级人工但未升级 | |
| S1 | Skill defect | Skill 缺失或包含错误规则 | |
| S2 | Execution lapse | Skill 正确但 Agent 未遵守 | |
| V1 | Verifier false positive | verifier 错判违规 | |
| V2 | Verifier false negative | verifier 漏判违规 | |

---

## Weekly Report Template

### Week N

**本周真正新增的能力**

- 

**最重要的实验结果**

- 

**一个推翻原判断的证据**

- 

**新增 artifacts**

- code commit：
- data manifest：
- result table：
- skill versions：

**成本**

- API calls：
- tokens：
- estimated cost：
- wall time：

**下周只做的三件事**

1. 
2. 
3. 

**Go / No-Go**

`GO | CONDITIONAL GO | PIVOT`

理由：

> 

# Preconditioner v4 冻结输入对照

以正式 v3 已通过校验的历史输出为对照，R03、R06 各调用一次 v4，各自使用原轮的 Parent、Diagnosis、执行记录及当时的 Memory。R06 使用历史训练路径，独立于本次 R03 输出。两次均在第一个请求返回且通过原生合约和归档校验。deepseek-flash，temperature 1.0，medium reasoning，输出上限 32,768 tokens。

五项中一项改变动作，两项改变有效文本。R03 u3 仍含五条，R06 u1 的理由仍未逐案检验 M6 与 M7。仅重放 Preconditioner；每轮一次采样，没有 v4 的 Actor 分数、gate 或测试成绩。

| 轮次 | 提案 | v3 | v4 | 有效文本字符数 v3 → v4 | 观察 |
|---|---|---|---|---:|---|
| R03 | u1 | KEEP | KEEP | 1579 → 1579 | 继续放宽元选项的触发条件，保留精确具体答案的例外。 |
| R03 | u2 | REPLACE | KEEP | 1148 → 976 | v4 指出 P3 选项的区别是蕴含方向，原样保留。v3 曾修订对两个性质均等价于第三性质的笼统说法。 |
| R03 | u3 | REPLACE | REPLACE | 2028 → 1868 | 两版都修订容量条款。v4 根据题面定义写明大域测试函数可限制到小域；其余导数、局部与全局等分支保留。 |
| R06 | u1 | KEEP | KEEP | 910 → 910 | 仍保留精确次数、参数与系数检查。v4 引用了 P1 的正确具体选项及 M6，但没有用新措辞逐案说明 M6 和 M7 会如何选择。 |
| R06 | u2 | KEEP | KEEP | 724 → 724 | 仍保留等价题的量词顺序和依赖检查。v4 引用选项 B 的具体差异，理由补充了完整等价的具体选项应当保留。 |

计数包含空格和换行，统计对象是编译后的有效提案。

## R03

[v3 原始决定和理由](../../campaigns/v27_2_precond_v3_lmb53_20261105_131046/rounds/R03/preconditioner/attempts/002/parsed.json) · [v4 原始决定和理由](R03/attempts/001/parsed.json) · [v4 完整有效提案](R03/attempts/001/result.json)。

冻结用户消息 SHA-256 为 `3d7626dda11268af126bec49b689749cb02f36863564a38a09c6eff68553cab2`。

### u2 v3 有效文本

```text
- For options composed of several implications or equivalences between named properties, rewrite each clause in the exact direction 'P implies Q' or 'P iff Q' and compare the direction clause by clause. Do not transfer a direction from one pair of properties to another, and do not infer the relation between two properties merely because one or both are equivalent to a third property unless that relation is separately established.
- Treat a negated property as the property that must appear in the antecedent or consequent; do not silently replace a statement about a negation with a statement about the corresponding positive property, and preserve the polarity of every clause.
- When two options share an equivalence and differ only in the direction of one implication, test the two directions separately and reject the reversed one; the shared true equivalence does not make both directional variants acceptable.
- Preserve equivalence scope and any universal quantifier over the objects; if the question asks which relation holds, require that exact relation rather than a one-way implication unless no stronger exact relation is supported.
```

### u2 v4 有效文本

```text
- For options composed of several implications or equivalences between named properties, rewrite each clause in the exact direction 'P implies Q' or 'P iff Q' and compare the direction clause by clause; a reversed implication is a different statement even when both properties are equivalent to a third.
- Treat a negated property as the property that must appear in the antecedent or consequent; do not silently replace a statement about a negation with a statement about the corresponding positive property.
- When two options share an equivalence and differ only in the direction of one implication, test the two directions separately and reject the reversed one; the shared true equivalence does not make both directional variants acceptable.
- Preserve equivalence scope and any universal quantifier over the objects; if the question asks which relation holds, require that exact relation rather than a one-way implication unless no stronger exact relation is supported.
```

### u3 v3 有效文本

```text
- Before judging strength, align the exact object, exponent, domain, and quantifier over admissible inputs across options, and determine the direction of each restriction. Restricting the input class (frequency support, a compact subinterval, or a subdomain) normally weakens a universal estimate, while isolating a smaller quantity (for example one directional derivative instead of the full gradient) normally strengthens the assertion about that quantity and may therefore be overstrong.
- When one option isolates a component or one derivative and another uses the full gradient, do not automatically prefer the isolated component as sharper; compare the exponent and check whether the stated equation or hypotheses visibly single out that component before treating the component-only assertion as the maximal provable conclusion. In particular, a divergence statement for a smaller component is stronger than the same divergence statement for the full gradient and should not replace it without support that the component alone must diverge.
- For nested domains and relative capacities, use monotonicity and check which version of the displayed inequality is stronger. Replacing an ambient capacity by a capacity relative to a smaller subdomain can change the admissible class and can make a lower-bound inequality stronger and potentially unsupported; keep the capacity/domain actually warranted by the stated comparison rather than merely choosing the more permissive-sounding version.
- For operator or variation problems, a conditional frequency-localized or subinterval estimate is not the strongest statement about the entire stated Schwartz class or full parameter range when an unconditional global conclusion is among the options; compare scope before comparing numerical sharpness.
- Preserve stated local versus global hypotheses, parameter ranges, exponents, and regularity levels: a global bound is overstrong for a local question, and a local or support-restricted estimate is narrower for a global question.
```

### u3 v4 有效文本

```text
- Before judging strength, align the exact object, exponent, and domain across options, and determine the direction of the restriction: restricting the input class (frequency support, compact interval, subdomain) normally narrows a universal claim, while isolating a smaller quantity (one directional derivative instead of the full gradient) normally makes a stronger claim about less and may therefore be overstrong.
- When one option isolates a component or one derivative and another uses the full gradient, do not automatically prefer the isolated component as sharper; compare the exponent and check whether the stated equation or hypotheses visibly single out that component before treating the component-only assertion as the maximal provable conclusion.
- For nested domains and capacities, keep the exact ambient domain and use the monotonicity of relative capacity: under the displayed relative-capacity definition, a function admissible on the larger domain restricts to one admissible on a smaller subdomain, so capacity relative to the larger ambient domain is generally no larger, and a bound using a smaller-domain capacity can be an unsupported strengthening even though it looks sharper. Do not replace the stated capacity/domain by a different one merely because the resulting inequality is easier or more familiar.
- For operator or variation problems, a conditional frequency-localized or subinterval estimate is not the strongest statement about the entire stated Schwartz class or full parameter range when an unconditional global conclusion is among the options; compare scope before comparing numerical sharpness.
- Preserve stated local versus global hypotheses, parameter ranges, exponents, and regularity levels: a global bound is overstrong for a local question, and a local or support-restricted estimate is narrower for a global question.
```

## R06

[v3 原始决定和理由](../../campaigns/v27_2_precond_v3_lmb53_20261105_131046/rounds/R06/preconditioner/attempts/001/parsed.json) · [v4 原始决定和理由](R06/attempts/001/parsed.json) · [v4 完整有效提案](R06/attempts/001/result.json)。

冻结用户消息 SHA-256 为 `0c7f5ce85c7be7ee767fec2f2deada2428ac626df2a85f95058547b5477acbcf`。

[v3 对照清单](../../../docs/methods/v27_2/revisions/decision_replay_v4/control/manifest.json) · [回放使用的 v4 提示词](R03/attempts/001/prompt.md) · [冻结回放脚本](replay_frozen.py)。当前正式配置已回退至 v3。此历史脚本要求 v4 绑定；如需复核，请在独立副本使用归档的 v4 提示词及对应 v4 版本标识，然后传入 R03 或 R06 和 `--verify-only`。

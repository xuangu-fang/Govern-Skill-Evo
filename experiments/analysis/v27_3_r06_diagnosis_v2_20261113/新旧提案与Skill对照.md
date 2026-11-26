# R06 · Diagnosis 新旧提案与实际 Skill 对照

对照组使用 v27.2 冻结提案，实验组使用 v27.3 新 Diagnosis 的实际提案。两组使用相同 Parent、历史 Memory、Preconditioner v3 和 Editor v1。字符按 Unicode 码点统计，包含换行。对于改写，新增和删除按 diff 中变更的整行计，净增按文件长度差计。

| 组别 | 本组 ID | 证据 | 原提案字符 | 下游决策 | Skill 新增 | 删除 | 净增 |
|---|---|---|---:|---|---:|---:|---:|
| 旧 | u1 | P1 | 623 | KEEP | 623 | 0 | +623 |
| 旧 | u2 | P2 | 639 | KEEP | 536 | 0 | +536 |
| 旧 | u3 | P3 | 581 | KEEP | 581 | 0 | +581 |
| 旧合计 | | | 1843 | | 1740 | 0 | +1740 |
| 新 | u1 | P1 | 579 | KEEP | 582 | 0 | +582 |
| 新 | u2 | P2 | 668 | REPLACE | 907 | 0 | +907 |
| 新 | u3 | P3 | 745 | REPLACE | 954 | 0 | +954 |
| 新合计 | | | 1992 | | 2443 | 0 | +2443 |

共同 Parent 为 4,401 字符。旧候选为 6,141 字符，新候选为 6,844 字符。

## 对新增内容的评审

两组均为一题一项，按题号和行为可直接对应。新 Diagnosis 在 u1 给出更明确的分类与生成区分，但仍夹带闭性和选择无逆命题选项的指令。u2 引入“先按强度排序再比较细节”的次序，u3 引入“写出量词顺序、核对等价两方向”的操作；两项均保留原题对象以及选择元选项的后续指令。只发现具体选项有差别或缺陷，未必足以确立元选项所断言的更强结果。

Preconditioner 将 u2 从 668 字符改为 904 字符，纠正了“先排序”的次序，将其他参数是否可比作为判断强弱的条件。u3 从 745 改为 951 字符，区分统一半径相对逐点存在与相对所有半径的两种强弱关系。两次 REPLACE 都增加了有用的精度，也都保留了上游的选项偏好。新候选第 6、7、8 行连续出现元选项决策，可直接看出重复。Editor 完整写入三项有效要求，另外每项增加列表标记和换行，共 9 字符。

Diagnosis 第一次响应因 goal 中证据引用的格式校验失败，第二次通过。两份响应的三个 Update（含 text 和 basis）逐字一致。两次回放的 Preconditioner 输入只有 plan 不同。此次三阶段归档已通过只读复验，尚未计分。

## 旧提案 u1

Diagnosis 原文

```text
- When a classification question lists descriptive forms for a specified class and one option adds a converse such as 'and conversely every solution of the descriptive equation produces a member of the original class', treat that converse as an extra sufficiency claim, not as automatically required by the phrase 'complete classification'. Prefer the option without the converse unless the question explicitly asks for an if-and-only-if characterization or the choices visibly establish that the construction preserves every defining property of the original class (for example closure, regularity, or the stated domain).
```

Preconditioner · KEEP

`Evidence:P1:1` and `Evidence:P1:outcome` show the Actor chose A, which appends “and conversely every such one-variable solution produces a closed minimal-Willmore surface,” while the mapped reference C omits that converse; EM was 0. Parent’s general warning about dropping a full equivalence can make the longer option look stronger, but here the extra converse is an added sufficiency/existence claim not required by the question’s “complete classification.” The Original correctly distinguishes that from an explicitly requested iff statement and preserves an exception when the choices visibly establish the construction satisfies all defining properties. No supplied Memory entry directly changes this classification-specific inference.

Editor 理由

Added a distinct classification-converse check after the existing meta-option contrast, preserving the exhaustive-classification branch while stating the sufficiency exception.

实际单项补丁

```diff
--- Parent
+++ Candidate
@@ -7,2 +7,3 @@
 - Preserve the contrast with items lacking such a meta-option: if the concrete options are exhaustive and one is the most specific supported classification, keep that concrete option.
+- When a classification question lists descriptive forms for a specified class and one option adds a converse such as 'and conversely every solution of the descriptive equation produces a member of the original class', treat that converse as an extra sufficiency claim, not as automatically required by the phrase 'complete classification'. Prefer the option without the converse unless the question explicitly asks for an if-and-only-if characterization or the choices visibly establish that the construction preserves every defining property of the original class (for example closure, regularity, or the stated domain).
```

## 旧提案 u2

Diagnosis 原文

```text
- In an item asking for the strongest provable statement with a meta-option that says one remaining option is correct but a stronger result can be proven, compare the concrete options for explicit weakenings: 'there exists' instead of an exact object, 'degree at most' instead of the exact degree, altered exponent coefficients, or a special-case hypothesis instead of the stated range. A concrete option with such a weakening is not the strongest conclusion; when no concrete option visibly supplies the exact maximal degree, coefficient, hypotheses, and conclusion, prefer the meta-option rather than the safer weakened concrete option.
```

Preconditioner · KEEP

`Evidence:P2:1` and `Evidence:P2:outcome` show the mapped reference is the meta-option B, while the Actor chose D, a concrete option weakening the exact degree to “there exists” a polynomial of degree at most K_{0,d,l}-1. The other concrete options include an altered coefficient (-K_{1,d,l}/2 in A), a changed hypothesis from dl>4 to dl>=4 in C, and an overstated degree in E. Thus no concrete option visibly supplies the exact degree, coefficient, hypotheses, and conclusion. The Original’s explicit screening for existence, degree-at-most, altered coefficients, and changed hypotheses is materially more actionable than Parent’s general meta-option rule, while its “when no concrete option visibly supplies” guard avoids making the meta-option automatic. The mixed historical meta-option evidence, especially the regressions in M5/M9/M12, cautions against unconditional meta preference but does not defeat this guarded version.

Editor 理由

Added a separate explicit-weakening check immediately after the existing strongest-statement meta-option rule, preserving its strategy and specifying when the meta-option is preferred over a weakened concrete option.

实际单项补丁

```diff
--- Parent
+++ Candidate
@@ -6,2 +6,3 @@
 - When an item asks for the strongest provable statement, the correct strength, or an equivalence, and one option asserts that a stronger result than the remaining options can be proved, treat that meta-option as a serious candidate. Compare the substantive options: choose the meta-option if the best concrete option is only a weaker corollary, a restricted or special case, or an unverified strengthening, and no concrete option visibly supplies the complete strongest or equivalence statement. Do not choose a concrete option merely because it is detailed, familiar, or apparently safe, and do not choose the meta-option from wording alone when a concrete option visibly gives the full supported conclusion.
+- When comparing concrete options in such a strongest-statement item, treat these as explicit weakenings: 'there exists' instead of an exact object, 'degree at most' instead of the exact degree, altered exponent coefficients, or a special-case hypothesis instead of the stated range. A concrete option with such a weakening is not the strongest conclusion; when no concrete option visibly supplies the exact maximal degree, coefficient, hypotheses, and conclusion, prefer the meta-option rather than the safer weakened concrete option.
 - Preserve the contrast with items lacking such a meta-option: if the concrete options are exhaustive and one is the most specific supported classification, keep that concrete option.
```

## 旧提案 u3

Diagnosis 原文

```text
- In an equivalence item whose definition quantifies over both a basepoint and a radius, do not accept a concrete option that merely gives 'for every point there exists some radius' or 'there exists one radius for every point' as equivalent unless the exact quantifier order is visibly justified. A fixed uniform radius is a stronger uniformity claim, not a definitional restatement; when a meta-option announces a stronger provable result and no concrete option reproduces the exact two-variable quantifier pattern, choose the meta-option instead of the nearest concrete variant.
```

Preconditioner · KEEP

`Evidence:P3:1` and `Evidence:P3:outcome` show the mapped reference is the meta-option C, while the Actor chose D, which fixes one radius for all basepoints even though the escaping definition quantifies “for any point o and any R>0.” Option B uses a radius depending on the point, and neither B nor D reproduces the exact two-variable quantifier pattern. Parent’s generic quantifier warning did not prevent the Actor’s choice, so the Original’s specific rule about not accepting either variant as equivalent unless the exact order is visibly justified is materially useful. The condition that no concrete option reproduces the exact pattern prevents an automatic meta-option choice, which is important given the mixed historical meta-option evidence in M5/M9/M12.

Editor 理由

Added a distinct equivalence-quantifier check after the theorem-overstatement check, preserving existing theorem-level rules while clarifying the basepoint/radius quantifier order.

实际单项补丁

```diff
--- Parent
+++ Candidate
@@ -11,2 +11,3 @@
 - Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.
+- In an equivalence item whose definition quantifies over both a basepoint and a radius, do not accept a concrete option that merely gives 'for every point there exists some radius' or 'there exists one radius for every point' as equivalent unless the exact quantifier order is visibly justified. A fixed uniform radius is a stronger uniformity claim, not a definitional restatement; when a meta-option announces a stronger provable result and no concrete option reproduces the exact two-variable quantifier pattern, choose the meta-option instead of the nearest concrete variant.
 - When options distinguish ordinary homotopy equivalence from p-local homotopy equivalence for every prime, do not upgrade a p-local conclusion to an unqualified integral homotopy equivalence.
```

## 新提案 u1

Diagnosis 原文

```text
When two options differ only by an added clause of the form “and conversely every such ... produces ...”, first check what the question asks: classification of the already-given objects, or also generation/existence of all auxiliary solutions. If the question asks only to classify the given objects, do not treat the added converse as required merely because the word “complete” appears. The converse adds an existence or closedness assertion that needs independent support; if no such support is visible, preserve the classification statement without the extra converse clause.
```

Preconditioner · KEEP

The Original addresses the observed P1 failure: option A added a converse/generation clause to the same classification given in C, and the mapped reference chose C (`Evidence:P1:1`, `Evidence:P1:outcome`). Parent’s theorem-precision and meta-option text can make “complete” or “full equivalence” sound as if the converse is required, but it does not explicitly distinguish classifying the given objects from demanding that every auxiliary solution be produced. The Original supplies that missing condition while preserving cases where the question explicitly asks for a full characterization, so it is kept as written.

Editor 理由

Added a distinct bullet in Theorem-Level Precision after the overstatement check, making the classification-versus-generation trigger and converse-clause condition explicit without altering existing theorem checks.

实际单项补丁

```diff
--- Parent
+++ Candidate
@@ -11,2 +11,3 @@
 - Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.
+- When two options differ only by an added clause of the form “and conversely every such ... produces ...”, first check what the question asks: classification of the already-given objects, or also generation/existence of all auxiliary solutions. If the question asks only to classify the given objects, do not treat the added converse as required merely because the word “complete” appears. The converse adds an existence or closedness assertion that needs independent support; if no such support is visible, preserve the classification statement without the extra converse clause.
 - When options distinguish ordinary homotopy equivalence from p-local homotopy equivalence for every prime, do not upgrade a p-local conclusion to an unqualified integral homotopy equivalence.
```

## 新提案 u2

Diagnosis 原文

```text
In a “strongest statement” item with a meta-option, first rank the concrete options by strength before comparing fine details. An option of the form “there exists a polynomial of degree at most ...” is an existential weakening of an exact-degree statement and cannot satisfy a strongest-statement request merely because it sounds safer. Then inspect the exact-degree or broad concrete options for altered degree, coefficient, range, or boundary condition. If every concrete option visibly contains such a weakening or unsupported alteration and no concrete option supplies the exact supported strength, choose the meta-option that says a stronger result can be proved.
```

Preconditioner · REPLACE

The Original targets P2, where the Actor chose D, an “there exists ... degree at most” option, while the reference was the meta-option B (`Evidence:P2:1`, `Evidence:P2:outcome`). The replacement keeps that behavioral direction but removes the imprecise instruction to rank by strength “before comparing fine details”: degree, exponent, range, and boundary conditions are part of strength. It also follows the Memory pattern in which exact-looking concrete options were wrong while the meta-option was correct (`Memory:M5`, `Memory:M9`, `Memory:M12`), while still requiring every concrete option to have a visible defect before choosing the meta-option.

有效要求

```text
In a “strongest statement” item with a meta-option, compare the concrete options’ exact conclusions and quantitative parameters rather than their apparent precision. Treat an option of the form “there exists a polynomial of degree at most ...” as an existential weakening of an exact-degree statement only when the remaining degree, coefficient, exponent, range, and boundary conditions are comparable. Then inspect the exact-degree or broad concrete options for altered degree, coefficient, range, or boundary condition. Do not let a safer-sounding existential or a more detailed formula decide the strength. If every concrete option visibly contains a weakening or unsupported alteration and no concrete option supplies the exact supported strength, choose the meta-option that says a stronger result can be proved; otherwise keep the concrete option that visibly supplies the full supported statement.
```

Editor 理由

Added a focused bullet in Option Comparison after the existing meta-option rule, specifying parameter comparability and exact-degree checks while preserving the existing meta-option and concrete-option priority.

实际单项补丁

```diff
--- Parent
+++ Candidate
@@ -6,2 +6,3 @@
 - When an item asks for the strongest provable statement, the correct strength, or an equivalence, and one option asserts that a stronger result than the remaining options can be proved, treat that meta-option as a serious candidate. Compare the substantive options: choose the meta-option if the best concrete option is only a weaker corollary, a restricted or special case, or an unverified strengthening, and no concrete option visibly supplies the complete strongest or equivalence statement. Do not choose a concrete option merely because it is detailed, familiar, or apparently safe, and do not choose the meta-option from wording alone when a concrete option visibly gives the full supported conclusion.
+- In a “strongest statement” item with a meta-option, compare the concrete options’ exact conclusions and quantitative parameters rather than their apparent precision. Treat an option of the form “there exists a polynomial of degree at most ...” as an existential weakening of an exact-degree statement only when the remaining degree, coefficient, exponent, range, and boundary conditions are comparable. Then inspect the exact-degree or broad concrete options for altered degree, coefficient, range, or boundary condition. Do not let a safer-sounding existential or a more detailed formula decide the strength. If every concrete option visibly contains a weakening or unsupported alteration and no concrete option supplies the exact supported strength, choose the meta-option that says a stronger result can be proved; otherwise keep the concrete option that visibly supplies the full supported statement.
 - Preserve the contrast with items lacking such a meta-option: if the concrete options are exhaustive and one is the most specific supported classification, keep that concrete option.
```

## 新提案 u3

Diagnosis 原文

```text
For an equivalence question, write out the quantifier order in the question and in each option. Treat “for every o there exists R”, “there exists R for every o”, and “for every o and every R” as distinct statements; a single R uniform in o is a strengthening that is not equivalent to an R depending on o. Likewise, check both directions of an alleged equivalence rather than accepting a merely necessary or merely sufficient condition. If no concrete option matches the required quantifier order and equivalence, and a meta-option states that a stronger result can be proved, choose the meta-option after confirming that every concrete option has such a visible defect. Do not prefer a uniform-constant option merely because it sounds stronger.
```

Preconditioner · REPLACE

The Original addresses P3, where the Actor chose the uniform-R option D while the reference was meta-option C (`Evidence:P3:1`, `Evidence:P3:outcome`). The replacement states the quantifier distinction more precisely: a single R uniform in o is not the stated “for every o and every R” requirement, and it may be a strengthening relative to a per-o R yet still weaker than the full all-R condition. It preserves the Memory-supported meta-option route when no concrete option matches and every concrete option has a visible defect (`Memory:M5`, `Memory:M9`, `Memory:M12`), without making the meta-option automatic.

有效要求

```text
For an equivalence question, write out the quantifier order in the question or definition and in each option. Treat “for every o there exists R”, “there exists R for every o”, and “for every o and every R” as distinct statements; do not replace a stated “for every R” requirement with a single R, and do not treat a single R uniform in o as equivalent to an R depending on o. A uniform constant is a separate strengthening relative to a per-o choice and may still be weaker than the full all-R requirement. Likewise, check both directions of an alleged equivalence rather than accepting a merely necessary or merely sufficient condition. If no concrete option matches the required quantifier order and equivalence, and a meta-option states that a stronger result can be proved, choose the meta-option only after confirming that every concrete option has such a visible defect. Do not prefer a uniform-constant option merely because it sounds stronger.
```

Editor 理由

Added a bullet in Option Comparison after the quantifier-tracking rule, spelling out quantifier order and both directions for equivalence while leaving existing meta-option and theorem guidance intact.

实际单项补丁

```diff
--- Parent
+++ Candidate
@@ -5,2 +5,3 @@
 - Track exact quantifiers such as "there exists", "for every", "if and only if", and "exactly when".
+- For an equivalence question, write out the quantifier order in the question or definition and in each option. Treat “for every o there exists R”, “there exists R for every o”, and “for every o and every R” as distinct statements; do not replace a stated “for every R” requirement with a single R, and do not treat a single R uniform in o as equivalent to an R depending on o. A uniform constant is a separate strengthening relative to a per-o choice and may still be weaker than the full all-R requirement. Likewise, check both directions of an alleged equivalence rather than accepting a merely necessary or merely sufficient condition. If no concrete option matches the required quantifier order and equivalence, and a meta-option states that a stronger result can be proved, choose the meta-option only after confirming that every concrete option has such a visible defect. Do not prefer a uniform-constant option merely because it sounds stronger.
 - When an item asks for the strongest provable statement, the correct strength, or an equivalence, and one option asserts that a stronger result than the remaining options can be proved, treat that meta-option as a serious candidate. Compare the substantive options: choose the meta-option if the best concrete option is only a weaker corollary, a restricted or special case, or an unverified strengthening, and no concrete option visibly supplies the complete strongest or equivalence statement. Do not choose a concrete option merely because it is detailed, familiar, or apparently safe, and do not choose the meta-option from wording alone when a concrete option visibly gives the full supported conclusion.
```

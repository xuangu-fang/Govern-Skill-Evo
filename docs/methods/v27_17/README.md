# v27.17 · 用错题与正确样例约束 Diagnosis 的候选修改

v27.17 基于 v27.16，只调整 Diagnosis 的提示词。Diagnosis 在一次调用中读取当前 Parent 和整批执行记录，按原协议返回 `decision`、`reason` 和 `plan`。

对重复错误，Diagnosis 在已有的 `reason` 中说明相关样例有多少、其中有多少符合观察，并核对正确样例和反例。对同一个问题，提出一条可在后续执行中检验的候选指令。若要给指令加上前置检查或例外，说明哪条记录确实落入这个条件，以及这个条件会怎样改变作答。仅属推测的例外写在 `reason` 中，题目本身要求的条件仍须遵守。独立问题仍可分别提出 Update，证据不足时仍可返回 `no_change`。[Diagnosis 提示词](prompts/diagnosis.md)

这一措辞受冻结 R02 的对照实验启发。该实验使用同一份 7 条观察且不提供 Parent。正式版本使用原始输入，实验命中率只适用于当时的输入条件。[实验记录](../../../experiments/analysis/lmb_r02_four_groups_repeat3/结果对照.md)

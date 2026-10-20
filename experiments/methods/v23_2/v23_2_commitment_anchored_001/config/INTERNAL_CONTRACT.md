# 实验内部编辑契约

本格式仅为实验中间表示，不修改正式Preconditioner/Editor/Memory契约。

顶层：plan_sha256, decision, reason, edits, checks。edit：update_id, operation, anchor_text, replacement_text, role, basis, reason, depends_on。全部字段必须存在且无额外字段。

operation=replace/delete/insert_before/insert_after；role=target/supporting/independent。supporting的depends_on为非空0起始下标，只指向target/independent；其余空。delete的replacement_text为空，其他非空。anchor非空、精确唯一、只在原快照匹配。重复、冲突、过期均拒绝。未选字节保持。原编译器验证最终Adjustment/Checks。

ready空edits是Keep；need_evidence空edits且checks=null；no_change显式整段delete所有Updates且checks=[]。完整delete可撤回，部分撤回须显式修正Checks。拆合/新ID/新Update不支持。

见reports/P3C2_ALGORITHM_DESIGN.md的完整哈希、冲突规则及语义限制。实现为anchored.py；未来草案为anchored_prompt_draft.md；人工夹具不能作为模型答案。

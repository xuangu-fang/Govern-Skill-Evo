# 全部离线测试结果

| 测试 | 状态 | 秒 |
|---|---|---:|
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_real_single_replace_preserves_every_unselected_byte` | passed | 0.0379 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_target_with_supporting_dependency` | passed | 0.0398 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_cross_update_goal_checks_and_real_editor_handoff` | passed | 0.0823 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_large_edit_has_no_length_limit` | passed | 0.0202 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_unicode_crlf_insert_delete_and_preservation[insert_before]` | passed | 0.0205 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_unicode_crlf_insert_delete_and_preservation[insert_after]` | passed | 0.0206 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_unicode_crlf_insert_delete_and_preservation[delete]` | passed | 0.0203 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_multi_edits_order_invariant_text_and_original_snapshot` | passed | 0.0568 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[missing-anchor_missing]` | passed | 0.0164 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[ambiguous-anchor_ambiguous]` | passed | 0.0162 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[overlapping_occurrence-anchor_ambiguous]` | passed | 0.0165 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[overlap-anchor_or_insertion_conflict]` | passed | 0.0167 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[same_insertion-anchor_or_insertion_conflict]` | passed | 0.0161 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[boundary_insertion-anchor_or_insertion_conflict]` | passed | 0.0162 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[unknown_uid-unknown_update_id]` | passed | 0.0163 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[stale-stale_plan_hash]` | passed | 0.0126 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[op-unsupported_operation]` | passed | 0.0159 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[empty_anchor-Invalid anchor_text]` | passed | 0.0164 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[whitespace_anchor-Invalid anchor_text]` | passed | 0.0168 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[goal-unexpected fields]` | passed | 0.0188 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[bad_basis-invalid references]` | passed | 0.0161 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[empty_basis-invalid references]` | passed | 0.0164 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[duplicate_basis-duplicate references]` | passed | 0.0171 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[nested_basis-unexpected fields]` | passed | 0.0175 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[checks-check.update_ids: invalid references]` | passed | 0.0205 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[empty_replacement-Invalid replacement_text]` | passed | 0.0165 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[delete_nonempty-delete_requires]` | passed | 0.0161 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[role-unsupported_role]` | passed | 0.0165 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[support_no_dependency-supporting_requires]` | passed | 0.0160 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[self_dependency-invalid_dependency_index]` | passed | 0.0162 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[bad_dependency-invalid_dependency_index]` | passed | 0.0184 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[cycle-dependency_must_be_root_edit]` | passed | 0.0180 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[nonroot_dependency-dependency_must_be_root_edit]` | passed | 0.0170 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[bool_dependency-invalid_dependencies]` | passed | 0.0163 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[independent_dependency-only_supporting]` | passed | 0.0218 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[identical-use_keep]` | passed | 0.0161 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[bad_decision-invalid_decision]` | passed | 0.0160 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[prose_reference-unavailable evidence reference]` | passed | 0.0200 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_invalid_edits_fail_closed[empty_reason-Invalid edit.reason]` | passed | 0.0183 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_partial_withdraw_checks_must_be_explicit` | passed | 0.0398 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_keep_need_evidence_no_change_are_distinct` | passed | 0.1291 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_partial_deletes_cannot_silently_withdraw` | passed | 0.0159 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_semantic_risk_is_structurally_accepted_and_exposed` | passed | 0.0199 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_duplicate_json_rejected` | passed | 0.0003 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_contract_schema_rejects_manually_invalid_adjustment` | passed | 0.0040 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_hash_covers_all_original_plan_fields[text]` | passed | 0.0131 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_hash_covers_all_original_plan_fields[checks]` | passed | 0.0134 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_hash_covers_all_original_plan_fields[basis]` | passed | 0.0201 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_hash_covers_all_original_plan_fields[order]` | passed | 0.0132 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_canonical_hash_ignores_object_key_order` | passed | 0.0001 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_multiple_updates_and_supporting_edge` | passed | 0.0207 |
| `experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py::test_future_draft_renders_without_analysis_answers` | passed | 0.0008 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_keep_preserves_deep_copy_and_original_goal` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_compilation_and_lineage[same_id]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_compilation_and_lineage[new_id]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_compilation_and_lineage[merge]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_compilation_and_lineage[split]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_compilation_and_lineage[withdraw]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_compilation_and_lineage[many_to_many]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_simultaneous_order_independent_adjustments` | passed | 0.0004 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_semantic_stops[no_change]` | passed | 0.0058 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_semantic_stops[need_evidence]` | passed | 0.0064 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_checks_modes[None]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_checks_modes[checks1]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_checks_modes[checks2]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[unknown_decision]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[extra]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[reason_type]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[adjustments_type]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[from_empty]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[from_duplicate]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[from_unknown]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[from_generated]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[from_twice]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[to_type]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[to_extra]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[text_empty]` | passed | 0.0004 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[id_empty]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[id_collision]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[id_original_other]` | passed | 0.0005 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[merge_retains]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[split_retains]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[to_duplicate]` | passed | 0.0006 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[cross_duplicate]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[basis_empty]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[basis_unknown_event]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[basis_history]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[basis_unknown_group]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[basis_duplicate]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[reason_history]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[text_history]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[adjustment_extra]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[check_old_about]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[check_empty_ids]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[check_duplicate]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[check_unknown_update]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[inherited_invalid_check]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[ready_empty]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[no_change_not_all]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[no_change_null_checks]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[need_evidence_adjustment]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_contract_errors[need_evidence_checks]` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_subset_expands_only_direct_references_and_keeps_full_records` | passed | 0.0004 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_parent_and_shared_context[None]` | passed | 0.0076 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_parent_and_shared_context[Inspect visibly relevant receptacles.]` | passed | 0.0072 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_persistence_and_zero_call_reuse` | passed | 0.0128 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_tampered_artifact_not_reused[messages.json]` | passed | 0.0079 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_tampered_artifact_not_reused[prompt.md]` | passed | 0.0062 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_tampered_artifact_not_reused[raw_output.txt]` | passed | 0.0072 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_tampered_artifact_not_reused[response.json]` | passed | 0.0084 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_tampered_artifact_not_reused[parsed.json]` | passed | 0.0080 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_tampered_artifact_not_reused[preconditioner.json]` | passed | 0.0133 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_tampered_artifact_not_reused[effective_plan.json]` | passed | 0.0109 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_tampered_artifact_not_reused[run.json]` | passed | 0.0107 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_tampered_artifact_not_reused[validation.json]` | passed | 0.0192 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_failures_preserve_stop_and_never_retry[invalid_json]` | passed | 0.0157 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_failures_preserve_stop_and_never_retry[truncated]` | passed | 0.0117 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_failures_preserve_stop_and_never_retry[contract]` | passed | 0.0128 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_failures_preserve_stop_and_never_retry[network]` | passed | 0.0067 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_failures_preserve_stop_and_never_retry[interrupt]` | passed | 0.0092 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_budget_and_upstream_semantic_stop_before_call` | passed | 0.0025 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_real_handoff_and_legacy_readonly` | passed | 0.0249 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_group_reference_does_not_expand_members` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_changed_prompt_and_generator_config_reject_reuse` | passed | 0.0110 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_http_failure_preserves_raw_response_without_retry` | passed | 0.0059 |
| `tests/skill_evolution/v23/test_preconditioner.py::test_no_natural_language_repair_or_scoring` | passed | 0.0003 |
| `tests/skill_evolution/v23/test_editor.py::test_input_exact_parent_plan_context_and_checks[None]` | passed | 0.0236 |
| `tests/skill_evolution/v23/test_editor.py::test_input_exact_parent_plan_context_and_checks[A\r\nB]` | passed | 0.0165 |
| `tests/skill_evolution/v23/test_editor.py::test_real_archives_handoff_readonly` | passed | 0.0184 |

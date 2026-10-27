# 就绪审计：历史失败证据

以下摘自 2026-10-22 的 [完整 pytest 日志](../../../../artifacts/methods/v23_4/benchmark_readiness_audit_001/pytest.log)，用于保留当时未通过项的依据，不代表重新执行后的结果。

## 结论

- 9 个 ERROR 均发生于 `tests/skill_evolution/v23/test_formal_evaluation.py` 的共用 `prepared` fixture：当前源码/Prompt 与旧正式实验冻结状态不一致。
- 1 个 FAILED 为 `test_real_archive_handoff_and_protection`：重建旧 Editor 输入时报告 `Saved Editor prompt/input differs`。
- Gate 失败在加载上游归档时发生，对应测试临时目录为空；该目录随其余测试产物保留在完整归档中。
- 本次整理未放宽校验、重写历史结论或重新运行测试。

## 全部未通过节点与统计（原文）

```text
FAILED tests/skill_evolution/v23/test_gate.py::test_real_archive_handoff_and_protection
ERROR tests/skill_evolution/v23/test_formal_evaluation.py::test_actual_freeze_and_official_final_parent
ERROR tests/skill_evolution/v23/test_formal_evaluation.py::test_parallel_order_complete_resume_and_pair_counts
ERROR tests/skill_evolution/v23/test_formal_evaluation.py::test_failure_stop_preservation_and_resume[1]
ERROR tests/skill_evolution/v23/test_formal_evaluation.py::test_failure_stop_preservation_and_resume[8]
ERROR tests/skill_evolution/v23/test_formal_evaluation.py::test_input_drift_rejected_without_calls
ERROR tests/skill_evolution/v23/test_formal_evaluation.py::test_cannot_write_to_training_campaign
ERROR tests/skill_evolution/v23/test_formal_evaluation.py::test_unknown_result_and_wrong_skill_refused
ERROR tests/skill_evolution/v23/test_formal_evaluation.py::test_real_command_adapter_uses_isolated_output_and_frozen_flags
ERROR tests/skill_evolution/v23/test_formal_evaluation.py::test_authorized_transport_recovery_is_narrow
1 failed, 977 passed, 9 errors in 104.40s (0:01:44)
```

## 9 个 fixture 错误的共同堆栈（首例原文）

其余 8 例在完整日志中保留。

```text
________ ERROR at setup of test_actual_freeze_and_official_final_parent ________

    @pytest.fixture(scope='module')
>   def prepared():return evalmod.prepare()
                          ^^^^^^^^^^^^^^^^^

tests/skill_evolution/v23/test_formal_evaluation.py:19: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
experiments/methods/v23/v23_alfworld_formal_001/evaluate.py:68: in prepare
    require(expected == ev.frozen_contract(), 'Frozen source/Prompt changed; explicit reviewed recovery required')
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

condition = False
message = 'Frozen source/Prompt changed; explicit reviewed recovery required'

    def require(condition, message):
        if not condition:
>           raise ValueError(message)
E           ValueError: Frozen source/Prompt changed; explicit reviewed recovery required

src/skill_evolution/v23/facts.py:15: ValueError
```

## Gate 失败堆栈（原文）

摘录中的 `tmp_path` 是历史绝对路径；文件位置已迁至 [归档 tmp/](../../../../artifacts/methods/v23_4/benchmark_readiness_audit_001/tmp/)，相对层级不变。

```text
___________________ test_real_archive_handoff_and_protection ___________________

tmp_path = PosixPath('/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/benchmark_readiness_audit_001/tmp/test_real_archive_handoff_and_0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10bed8b90>

    def test_real_archive_handoff_and_protection(tmp_path, monkeypatch):
        replay = Path('artifacts/methods/v23/v23_replay_memory_001/replay')
        tasks = Path('experiments/methods/v23/v23_replay_memory_001/config/plan.json')
        if not replay.exists(): pytest.skip('Local real archive unavailable')
>       bundle = gate.assemble_gate(replay, tasks)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/skill_evolution/v23/test_gate.py:148: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/skill_evolution/v23/gate.py:104: in assemble_gate
    rebuilt = build_replay(saved['editor_directory'], records['parent'], records['candidate'],
src/skill_evolution/v23/replay.py:43: in build_replay
    saved = load_editor(editor_directory)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/skill_evolution/v23/editor.py:145: in load_editor
    require(read("messages.json") == messages and _read_text(directory / "prompt.md") == messages[0]["content"],
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

condition = False, message = 'Saved Editor prompt/input differs'

    def require(condition, message):
        if not condition:
>           raise ValueError(message)
E           ValueError: Saved Editor prompt/input differs

src/skill_evolution/v23/facts.py:15: ValueError
```

# 历史测试失败证据

摘自本阶段的 [完整测试 XML](../../../../artifacts/methods/v23_4/multi_knowledge_p3_001/pytest.xml)。[测试结论与全部失败节点](TEST_RESULTS.json) 保持原文；以下是错误和失败各一例的原始堆栈，不代表本次重新执行的结果。

当时 9 个错误发生于旧正式评估的准备阶段，提示冻结源码/Prompt 已变化；1 个失败为 Gate 重建旧 Editor 输入时的 Prompt 不一致。P2 已有改动前源码复核记录，后续 P3/P4 记录相同失败节点。原判断及测试保护未因迁移改写。

## error: `tests.skill_evolution.v23.test_formal_evaluation.test_actual_freeze_and_official_final_parent`

```text
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

## failure: `tests.skill_evolution.v23.test_gate.test_real_archive_handoff_and_protection`

```text
tmp_path = PosixPath('/private/var/folders/21/m6qvj4px0q73l1kc4d2rgtg80000ks/T/pytest-of-didi/pytest-175/test_real_archive_handoff_and_0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x102e437a0>

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

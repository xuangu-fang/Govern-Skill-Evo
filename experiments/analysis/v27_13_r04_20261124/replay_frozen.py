"""Replay the v27.13 proposal stages on a recorded v27.11 R04 Parent batch."""
import argparse
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from experiments.analysis.v27_12_r04_frozen_20261118 import replay_frozen as archive
from src.skill_evolution.v27_2 import diagnosis, editor, preconditioner, stages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", choices=archive.SOURCES)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    launch = archive.launch
    read = launch.engine.ev.read
    archived = read(archive.HERE / "frozen_launch/config.json")
    formal = read(launch.HERE / "config.json")
    formal_calls = launch.config.base.module_calls()
    assert formal_calls == formal["module_calls"]
    source = ROOT / "experiments/campaigns" / archive.SOURCES[args.parent] / "rounds/R04"
    frozen = read(source / "round_input.json")
    launch.protocol.ACTOR = archived["actor"]
    launch.protocol.execution_context = launch.project_context
    launch.prompts.DIRECTORY = HERE / "frozen_prompts"
    for name, module in launch.config.MODULES.items():
        module.PROMPT_VERSION = f"v27_13_lmb_{name}_v1"

    cfg = dict(archived, module_calls=formal["module_calls"])
    cfg["method"] = dict(archived["method"], version="v27_13_campaign_v1",
                         prompts=launch.config.prompt_versions())
    launch.config.METHOD_VERSION = cfg["method"]["version"]

    class ShortReplay(launch.V2712Campaign):
        method_version = cfg["method"]["version"]

    actor = launch.engine.ActorAdapter(launch.engine.load_dataset(ROOT / "data/livemathematicianbench/prepared_v1"))
    adapter = ShortReplay(actor)
    generate = None
    if not args.verify_only:
        key = launch.engine.read_credentials(launch.CREDENTIALS, formal)["OPENAI_API_KEY"]
        generate = launch.engine.HTTPGenerator(key, session_factory=archive.direct_session)

    def execute(call):
        old = read(source / call.name / "identity.json")
        limits = {key: cfg[key] for key in ("max_attempts", "max_input_chars", "max_message_utf8_bytes", "retry_delay_seconds")}
        settings = cfg["module_calls"][call.name]
        assert settings == dict(old["call_config"], model=formal["actor"]["model"], endpoint=formal["actor"]["endpoint"])
        assert all(old[k] == v for k, v in limits.items())
        journal = HERE / args.parent / call.name
        print(args.parent, call.name, flush=True)
        path, result = stages.run_stage(journal, call, call_config=settings, generate=generate,
                                        resume=journal.exists(), read_only=args.verify_only, **limits)
        assert read(journal / "identity.json") == dict(old, prompt=call.prompt_version, call_config=settings)
        print(path.relative_to(HERE), flush=True)
        return result

    # Bind live optimizer request settings separately from historical Actor settings.
    with patch.object(launch.config.base, "module_calls", return_value=formal_calls), adapter.using(), adapter.memory_operation():
        launch.config.validate_config(cfg, executable=True)
        for name, prompt in launch.config.render_prompts().items():
            original = (ROOT / "docs/methods/v27_13/prompts" / f"{name}.md").read_text()
            assert prompt == original.replace("The frozen Actor uses deepseek-flash with",
                                              "The frozen Actor uses deepseek-v4.1-flash with")
        adapter.register_archive(source / "parent_runs")
        assert frozen["tasks"] == archived["batches"][3] == formal["batches"][3]
        assert frozen["parent"] == (source / "parent.md").read_text()
        assert frozen["memory"] == read(source / "preconditioner/input.json")["memory"]
        call = diagnosis.diagnosis_call(read(source / "diagnosis/input.json"))
        assert call.messages[1:] == read(source / "diagnosis/base_messages.json")[1:]
        proposed = execute(call)
        if proposed["diagnosis"]["decision"] == "revise":
            adjusted = execute(preconditioner.preconditioner_call(proposed, frozen["memory"]))
            if adjusted["effective_plan"]:
                execute(editor.editor_call(adjusted))


if __name__ == "__main__":
    main()

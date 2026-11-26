"""Replay Diagnosis v2 then Preconditioner v1 from a frozen R04 Parent batch."""
import argparse
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from experiments.analysis.v27_12_r04_frozen_20261118 import replay_frozen as baseline
from src.skill_evolution.v27_2 import diagnosis, preconditioner, editor, stages

launch = baseline.launch
DRAFT = ROOT / "docs/methods/v27_12/proposals/diagnosis_v2"
DIGEST = "66c99f4aa2ae95b762fb5fdf4c9058a7067be22d42f9707bb618c644e5143d04"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", choices=baseline.SOURCES)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--editor", action="store_true",
                        help="Read the two completed stages without resampling and continue through Editor.")
    args = parser.parse_args()
    read = launch.engine.ev.read
    cfg = read(baseline.HERE / "frozen_launch/config.json")
    source = ROOT / "experiments/campaigns" / baseline.SOURCES[args.parent] / "rounds/R04"
    old = baseline.HERE / args.parent
    frozen = read(source / "round_input.json")
    launch.config.METHOD_VERSION = launch.V2712Campaign.method_version
    launch.protocol.ACTOR = cfg["actor"]
    launch.protocol.execution_context = launch.project_context
    original_prompts = baseline.HERE / "frozen_launch/frozen_prompts"
    launch.prompts.DIRECTORY = original_prompts
    for name, module in launch.config.MODULES.items():
        module.PROMPT_VERSION = cfg["method"]["prompts"][name]
    assert hashlib.sha256((DRAFT / "diagnosis.md").read_bytes()).hexdigest() == DIGEST
    actor = launch.engine.ActorAdapter(launch.engine.load_dataset(ROOT / "data/livemathematicianbench/prepared_v1"))
    adapter = launch.V2712Campaign(actor)
    generate = None
    if not args.verify_only:
        key = launch.engine.read_credentials(ROOT / ".env", cfg)["OPENAI_API_KEY"]
        generate = launch.engine.HTTPGenerator(key, session_factory=baseline.direct_session)

    def execute(call):
        identity = read(old / call.name / "identity.json")
        directory = HERE / args.parent / call.name
        limits = {k: cfg[k] for k in ("max_attempts", "max_input_chars", "max_message_utf8_bytes", "retry_delay_seconds")}
        assert cfg["module_calls"][call.name] == identity["call_config"]
        read_only = args.verify_only or (args.editor and call.name != "editor")
        path, result = stages.run_stage(directory, call, call_config=identity["call_config"],
                                       **limits, generate=None if read_only else generate, resume=directory.exists(),
                                       read_only=read_only)
        assert read(directory / "identity.json") == {**identity, "prompt": call.prompt_version}
        print(args.parent, call.name, path.name, flush=True)
        return result

    with adapter.using(), adapter.memory_operation():
        launch.config.validate_config(cfg, executable=True)
        adapter.register_archive(source / "parent_runs")
        assert frozen["parent"] == (source / "parent.md").read_text() and frozen["tasks"] == cfg["batches"][3]
        assert frozen["memory"] == read(old / "preconditioner/input.json")["memory"]
        launch.prompts.DIRECTORY = DRAFT
        diagnosis.PROMPT_VERSION = "v27_12_lmb_diagnosis_v2"
        call = diagnosis.diagnosis_call(read(source / "diagnosis/input.json"))
        assert call.messages[1:] == read(old / "diagnosis/base_messages.json")[1:]
        assert call.messages[1:] == read(source / "diagnosis/base_messages.json")[1:]
        assert call.messages[0]["content"] == (DRAFT / "diagnosis.md").read_text()
        result = execute(call)
        if result["diagnosis"]["decision"] == "revise":
            launch.prompts.DIRECTORY = original_prompts
            call = preconditioner.preconditioner_call(result, frozen["memory"])
            assert call.messages[0] == read(old / "preconditioner/base_messages.json")[0]
            assert call.prompt_version == read(old / "preconditioner/identity.json")["prompt"]
            adjusted = execute(call)
            if args.editor and adjusted["effective_plan"]:
                call = editor.editor_call(adjusted)
                assert call.messages[0] == read(old / "editor/base_messages.json")[0]
                execute(call)


if __name__ == "__main__":
    main()

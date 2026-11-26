"""Run the three v27.12 proposal stages on one archived v27.11 R04."""
import argparse
import hashlib
from pathlib import Path
import sys

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from experiments.launches.v27_12_lmb53_20261118 import run as launch
from src.skill_evolution.v27_2 import diagnosis, preconditioner, editor, stages

SOURCES = {
    "first": "v27_11_lmb53_20261115",
    "repeat": "v27_11_lmb53_repeat_20261117_140123",
}


def direct_session():
    session = requests.Session()
    session.trust_env = False
    return session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", choices=SOURCES)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    source = ROOT / "experiments/campaigns" / SOURCES[args.parent] / "rounds/R04"
    destination = HERE / args.parent
    read = launch.engine.ev.read
    frozen_launch = HERE / "frozen_launch"
    cfg = read(frozen_launch / "config.json")
    launch.config.METHOD_VERSION = launch.V2712Campaign.method_version
    launch.protocol.ACTOR = cfg["actor"]
    launch.protocol.execution_context = launch.project_context
    launch.prompts.DIRECTORY = frozen_launch / "frozen_prompts"
    for name, module in launch.config.MODULES.items():
        module.PROMPT_VERSION = cfg["method"]["prompts"][name]
    for filename, digest in read(frozen_launch / "prompt_sha256.json").items():
        assert hashlib.sha256((launch.prompts.DIRECTORY / filename).read_bytes()).hexdigest() == digest
    actor = launch.engine.ActorAdapter(launch.engine.load_dataset(ROOT / "data/livemathematicianbench/prepared_v1"))
    adapter = launch.V2712Campaign(actor)
    generate = None
    if not args.verify_only:
        key = launch.engine.read_credentials(ROOT / ".env", cfg)["OPENAI_API_KEY"]
        generate = launch.engine.HTTPGenerator(key, session_factory=direct_session)
    with adapter.using(), adapter.memory_operation():
        launch.config.validate_config(cfg, executable=True)
        adapter.register_archive(source / "parent_runs")
        frozen = read(source / "round_input.json")
        assert frozen["tasks"] == cfg["batches"][3]
        assert frozen["parent"] == (source / "parent.md").read_text()
        assert frozen["memory"] == read(source / "preconditioner/input.json")["memory"]
        call = diagnosis.diagnosis_call(read(source / "diagnosis/input.json"))
        assert call.messages[1:] == read(source / "diagnosis/base_messages.json")[1:]
        assert call.input["round_id"] == frozen["round_id"]
        for module in ("diagnosis", "preconditioner", "editor"):
            journal = destination / module
            old_identity = read(source / module / "identity.json")
            options = {k: cfg[k] for k in ("max_attempts", "max_input_chars", "max_message_utf8_bytes", "retry_delay_seconds")}
            assert all(old_identity[k] == v for k, v in options.items())
            assert cfg["module_calls"][module] == old_identity["call_config"]
            assert call.name == module and call.contract_version == old_identity["contract"]
            print(args.parent, module, flush=True)
            path, result = stages.run_stage(journal, call, call_config=cfg["module_calls"][module],
                                            generate=generate, resume=journal.exists(),
                                            read_only=args.verify_only, **options)
            print(path.relative_to(HERE), flush=True)
            if module == "diagnosis" and result["diagnosis"]["decision"] == "revise":
                call = preconditioner.preconditioner_call(result, frozen["memory"])
            elif module == "preconditioner" and result["effective_plan"]:
                call = editor.editor_call(result)
            else:
                break


if __name__ == "__main__":
    main()

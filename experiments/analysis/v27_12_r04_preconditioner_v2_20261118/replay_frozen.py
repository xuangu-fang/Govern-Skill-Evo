"""Replay one Preconditioner request with the previous experiment's frozen payload."""
import argparse
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from experiments.analysis.v27_12_r04_frozen_20261118 import replay_frozen as previous
from src.skill_evolution.v27_2 import preconditioner, stages

launch = previous.launch
PROMPTS = ROOT / "docs/methods/v27_12/proposals/preconditioner_v2"
PROMPT_VERSION = "v27_12_lmb_preconditioner_v2"
PROMPT_SHA256 = "67c5dd9c5cb5e21d5e4bf20f3ade3a30f099d95b8f9ec90fa5f9351b77bf6540"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", choices=previous.SOURCES)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    read = launch.engine.ev.read
    old = previous.HERE / args.parent
    source = ROOT / "experiments/campaigns" / previous.SOURCES[args.parent] / "rounds/R04"
    cfg = read(previous.HERE / "frozen_launch/config.json")
    launch.protocol.ACTOR = cfg["actor"]
    launch.protocol.execution_context = launch.project_context
    launch.prompts.DIRECTORY = PROMPTS
    preconditioner.PROMPT_VERSION = PROMPT_VERSION
    prompt = (PROMPTS / "preconditioner.md").read_bytes()
    assert hashlib.sha256(prompt).hexdigest() == PROMPT_SHA256
    actor = launch.engine.ActorAdapter(launch.engine.load_dataset(ROOT / "data/livemathematicianbench/prepared_v1"))
    adapter = launch.V2712Campaign(actor)
    with adapter.using(), adapter.memory_operation():
        adapter.register_archive(source / "parent_runs")
        old_pre = old / "preconditioner"
        saved = read(old_pre / "input.json")
        diag = old / "diagnosis" / read(old / "diagnosis/result.json")["path"]
        assert saved["diagnosis"] == read(diag / "parsed.json")
        assert saved["memory"] == read(source / "round_input.json")["memory"]
        call = preconditioner.preconditioner_call(saved, saved["memory"])
        old_messages = read(old_pre / "base_messages.json")
        assert call.input == saved and call.messages[1:] == old_messages[1:]
        assert call.messages[0]["content"].encode() == prompt and call.messages[0] != old_messages[0]
        identity = read(old_pre / "identity.json")
        keys = ("max_attempts", "retry_delay_seconds", "max_input_chars", "max_message_utf8_bytes")
        assert all(cfg[k] == identity[k] for k in keys)
        assert cfg["module_calls"]["preconditioner"] == identity["call_config"]
        generate = None
        if not args.verify_only:
            key = launch.engine.read_credentials(ROOT / ".env", cfg)["OPENAI_API_KEY"]
            generate = launch.engine.HTTPGenerator(key, session_factory=previous.direct_session)
        dest = HERE / args.parent / "preconditioner"
        attempt, result = stages.run_stage(dest, call, call_config=identity["call_config"],
                                           **{k: identity[k] for k in keys}, generate=generate,
                                           resume=dest.exists(), read_only=args.verify_only)
        assert read(dest / "identity.json") == {**identity, "prompt": PROMPT_VERSION}
        assert (dest / "input.json").read_bytes() == (old_pre / "input.json").read_bytes()
        print(args.parent, attempt.name, [(u["target"], u["action"]) for u in result["preconditioner"]["adjustments"]])


if __name__ == "__main__":
    main()

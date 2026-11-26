"""Replay only Preconditioner against the archived v27.5 R04 user message."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "external/SkillAdam")]

from scripts.runs.run_v27_2_campaign import (
    ActorAdapter, CampaignAdapter, HTTPGenerator, load_dataset, read_credentials,
)
from src.skill_evolution.v27_2 import preconditioner, prompts, stages

CAMPAIGN = ROOT / "experiments/campaigns/v27_5_lmb53_20261113"
ROUND = CAMPAIGN / "rounds/R04"
SOURCE = ROUND / "preconditioner"
PROMPTS = ROOT / "docs/methods/v27_7/proposals/prompts"


def read(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    cfg = read(CAMPAIGN / "config.json")
    identity = read(SOURCE / "identity.json")
    old = read(SOURCE / "base_messages.json")
    saved = read(SOURCE / "input.json")
    adapter = CampaignAdapter(ActorAdapter(load_dataset(ROOT / "data/livemathematicianbench/prepared_v1")))
    with adapter.using(), patch.object(prompts, "DIRECTORY", PROMPTS), patch.object(
        preconditioner, "PROMPT_VERSION", "v27_7_lmb_preconditioner_v1"
    ):
        adapter.register_archive(ROUND / "parent_runs")
        call = preconditioner.preconditioner_call(saved, saved["memory"])
        assert call.input == saved and call.messages[1:] == old[1:]
        previous = HERE.with_name("v27_6_r04_preconditioner_frozen_20261114") / "preconditioner"
        assert (SOURCE / "input.json").read_bytes() == (previous / "input.json").read_bytes()
        assert call.messages[1:] == read(previous / "base_messages.json")[1:]
        assert call.messages[0] != read(previous / "base_messages.json")[0]
        assert call.messages[0]["content"] == (PROMPTS / "preconditioner.md").read_text()
        assert call.messages[0] != old[0] and call.contract_version == identity["contract"]
        assert cfg["module_calls"]["preconditioner"] == identity["call_config"]
        options = {k: identity[k] for k in ("max_attempts", "max_input_chars", "max_message_utf8_bytes",
                                            "retry_delay_seconds")}
        assert all(cfg[k] == v for k, v in options.items())
        dest = HERE / "preconditioner"
        generate = None if args.verify_only else HTTPGenerator(read_credentials(ROOT / ".env", cfg)["OPENAI_API_KEY"])
        attempt, _ = stages.run_stage(dest, call, call_config=identity["call_config"], **options,
                                      generate=generate, resume=dest.exists(), read_only=args.verify_only)
        assert (dest / "input.json").read_bytes() == (SOURCE / "input.json").read_bytes()
        assert read(dest / "identity.json") == {**identity, "prompt": call.prompt_version}
        print(attempt, "user_message_sha256", hashlib.sha256(call.messages[1]["content"].encode()).hexdigest())


if __name__ == "__main__":
    main()

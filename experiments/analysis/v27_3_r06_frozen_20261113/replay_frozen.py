"""Replay R06's frozen Preconditioner input and pass its compiled plan to Editor."""
import argparse
from contextlib import ExitStack
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
from src.skill_evolution.v27_2 import config, editor, preconditioner, prompts, stages

SOURCE = ROOT / "experiments/campaigns/v27_2_diag_v3_precond_v3_lmb53_20261105_210532/rounds/R06"
PROMPTS = ROOT / "docs/methods/v27_3/proposals/prompts"


def read(path):
    return json.loads(path.read_bytes())


def run(verify_only):
    adapter = CampaignAdapter(ActorAdapter(load_dataset(ROOT / "data/livemathematicianbench/prepared_v1")))
    with adapter.using(), ExitStack() as overrides:
        cfg = config.validate_config(read(config.DEFAULT_CONFIG), executable=True)
        adapter.register_archive(SOURCE / "parent_runs")
        overrides.enter_context(patch.object(prompts, "DIRECTORY", PROMPTS))
        for module in (preconditioner, editor):
            name = module.__name__.split(".")[-1]
            overrides.enter_context(patch.object(module, "PROMPT_VERSION", f"v27_3_lmb_{name}_v1"))
        generate = None if verify_only else HTTPGenerator(read_credentials(ROOT / ".env", cfg)["OPENAI_API_KEY"])
        saved = read(SOURCE / "preconditioner/input.json")
        for stage in ("preconditioner", "editor"):
            if stage == "preconditioner":
                call = preconditioner.preconditioner_call(saved, saved["memory"])
                assert call.input == saved
                assert call.messages[1:] == read(SOURCE / stage / "base_messages.json")[1:]
            else:
                if saved["effective_plan"] is None:
                    print("All updates withdrawn. Parent retained.", flush=True)
                    break
                call = editor.editor_call(saved)
                assert json.loads(call.messages[1]["content"])["parent"] == (SOURCE / "parent.md").read_text()
            assert call.messages[0]["content"] == (PROMPTS / f"{stage}.md").read_text()
            identity = read(SOURCE / stage / "identity.json")
            keys = ("max_attempts", "max_input_chars", "max_message_utf8_bytes", "retry_delay_seconds")
            assert all(cfg[k] == identity[k] for k in keys)
            assert cfg["module_calls"][stage] == identity["call_config"]
            dest = HERE / stage
            attempt, saved = stages.run_stage(
                dest, call, call_config=identity["call_config"], **{k: identity[k] for k in keys},
                generate=generate, resume=dest.exists(), read_only=verify_only,
            )
            print(stage, attempt, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    run(parser.parse_args().verify_only)

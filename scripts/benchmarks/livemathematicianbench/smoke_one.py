"""One real Train question via native SkillOpt; no training or skill updates."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
from zoneinfo import ZoneInfo

from model_access import ROOT, configure


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    cfg = configure()  # Checks independent environment and credentials.
    import httpx
    import skillopt
    from skillopt.envs.livemathematicianbench.adapter import LiveMathematicianBenchAdapter
    from skillopt.envs.livemathematicianbench import rollout
    from skillopt.model import openai_compatible_backend as backend

    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
    output = ROOT / "artifacts/benchmarks/livemathematicianbench" / ("smoke_train1_" + stamp)
    output.mkdir(parents=True, exist_ok=False)
    adapter = LiveMathematicianBenchAdapter(
        split_dir=str(ROOT / "data/livemathematicianbench/prepared_v1"),
        split_mode="split_dir", workers=1, max_turns=1, exec_timeout=300,
        max_completion_tokens=cfg["max_tokens"], shuffle_choices=True,
        use_theorem=False, use_sketch=False,
    )
    adapter.setup({})
    batch = adapter.get_dataloader().build_eval_batch(env_num=1, split="train", seed=42)
    items = adapter.build_env_from_batch(batch)
    assert len(items) == 1
    assert items[0]["id"] == adapter.get_dataloader().get_split_items("train")[0]["id"]
    skill_path = Path(skillopt.__file__).parent / "envs/livemathematicianbench/skills/initial.md"
    skill = skill_path.read_text()
    skill_hash = hashlib.sha256(skill_path.read_bytes()).hexdigest()
    (output / "initial_skill.md").write_text(skill)
    save(output / "selected_item.json", items[0])
    save(output / "run_config.json", {**cfg, "environment": sys.prefix,
        "split": "train", "selected_id": items[0]["id"], "seed": 42,
        "workers": 1, "max_turns": 1, "max_http_attempts": 1,
        "use_theorem": False, "use_sketch": False,
        "initial_skill_sha256": skill_hash, "skill_updates": 0})
    attempts = []
    responses = []

    def on_request(request):
        if attempts:
            raise RuntimeError("Single-request smoke budget exceeded")
        assert str(request.url) == cfg["base_url"] + "/chat/completions"
        body = json.loads(request.content)
        assert body["messages"] == [
            {"role": "system", "content": rollout._build_system(skill)},
            {"role": "user", "content": rollout._build_user(items[0])},
        ]
        for key in ("model", "temperature", "reasoning_effort", "thinking", "max_tokens"):
            assert body[key] == cfg[key]
        save(output / "request.json", {"url": str(request.url), "body": body})
        attempts.append(time.monotonic())

    def on_response(response):
        response.read()
        responses.append(response.status_code)
        # No headers or credentials are persisted.
        save(output / "response.json", {"status_code": response.status_code,
                                       "body": response.json()})

    original_chat = rollout.chat_target

    def once(**kwargs):
        kwargs["retries"] = 1
        return original_chat(**kwargs)

    backend.reset_token_tracker()
    print(json.dumps({"output": str(output), "selected_id": items[0]["id"],
                      "status": "starting_one_train_question"}), flush=True)
    started = time.monotonic()
    with httpx.Client(timeout=httpx.Timeout(300, connect=10),
                      event_hooks={"request": [on_request], "response": [on_response]}) as client:
        configure(http_client=client)
        with patch.object(rollout, "chat_target", once):
            results = adapter.rollout(items, skill, str(output))
    result = results[0]
    assert hashlib.sha256(skill_path.read_bytes()).hexdigest() == skill_hash
    report = {"id": result["id"], "split": "train", "model": cfg["model"],
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "http_attempts": len(attempts), "http_statuses": responses,
        "agent_ok": result["agent_ok"], "n_turns": result["n_turns"],
        "predicted_label": result["predicted_label"], "correct_label": result["correct_label"],
        "exact_match": result["hard"], "fail_reason": result["fail_reason"],
        "token_usage": backend.get_token_summary(), "skill_unchanged": True,
        "skill_updates": 0, "selection_questions_run": 0, "test_questions_run": 0,
        "output": str(output)}
    save(output / "summary.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if not result["agent_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

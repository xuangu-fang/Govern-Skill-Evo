"""Run one manifest task with an OpenAI-compatible chat model."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
SPLIT_ROOT = REPO_ROOT / "benchmarks/alfworld/editions/skillopt_39_18_134"
SYSTEM_PROMPT = """You control an ALFWorld household text environment. Complete the
task stated in the initial observation by issuing one action per turn.
Use exactly the object and receptacle names and numbers from observations.
Navigate to a receptacle before interacting with it. Take an object from its
actual source before carrying it to a destination. Inspect and open containers
when needed. If an action returns 'Nothing happens.', reconsider its conditions.
Commands include: go to <receptacle>, open <receptacle>, close <receptacle>,
take <object> from <receptacle>, move <object> to <receptacle>,
clean <object> with <receptacle>, heat <object> with <receptacle>,
cool <object> with <receptacle>, use <lamp>, examine <object>, look, inventory.
Return ONLY <action>one command</action>, without explanations or multiple actions.
"""


def extract_action(content: str) -> str:
    matches = re.findall(r"<action>(.*?)</action>", content, re.DOTALL)
    if len(matches) != 1 or not matches[0].strip() or "\n" in matches[0].strip():
        raise ValueError("Model must return exactly one single-line <action> command.")
    return matches[0].strip()


def chat_action(session, endpoint, api_key, model, messages, max_tokens):
    for attempt in range(4):
        response = session.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": max_tokens,
                "thinking": {"type": "disabled"},
                "stream": False,
            },
            timeout=(10, 180),
        )
        if response.status_code != 429 or attempt == 3:
            break
        # Retry a rejected request with the identical dialogue; never regenerate
        # a valid action or retry a model/task failure to select a better outcome.
        time.sleep(10 * 2 ** attempt)
    if not response.ok:
        # Provider bodies and exception strings can contain sensitive request data.
        raise RuntimeError(f"Model API returned HTTP {response.status_code}.")
    payload = response.json()
    choice = payload["choices"][0]
    content = choice["message"].get("content") or ""
    return {
        "content": content,
        "response_model": payload.get("model"),
        "finish_reason": choice.get("finish_reason"),
        "usage": payload.get("usage"),
        "api_attempts": attempt + 1,
        "rate_limit_retries": attempt,
    }


def run_episode(env, generate, max_steps, record, output):
    """Save each completed interaction, including model/format/runtime failures."""
    def save():
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")

    try:
        state = env.reset()
        record["initial_observation"] = state.feedback
        print(state.feedback, flush=True)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": state.feedback},
        ]
        record["status"] = "running"
        save()
        for step in range(1, max_steps + 1):
            result = generate(messages)
            event = {"step": step, "model_response": result}
            record["steps"].append(event)
            save()
            if result["finish_reason"] == "length":
                raise ValueError("Model output reached max_tokens; action was not executed.")
            action = extract_action(result["content"])
            event["action"] = action
            save()
            state, reward, done = env.step(action)
            event.update(observation=state.feedback, reward=float(reward), done=bool(done), won=bool(state.won))
            record["won"] = bool(state.won)
            print(f"[{step}] {action}\n{state.feedback}", flush=True)
            messages.extend([
                {"role": "assistant", "content": result["content"]},
                {"role": "user", "content": state.feedback},
            ])
            save()
            if state.won or done:
                record["status"] = "success" if state.won else "environment_ended"
                break
        else:
            record["status"] = "step_limit"
    except KeyboardInterrupt:
        record["status"] = "interrupted"
    except Exception as exc:
        record["status"] = "error"
        record["error_type"] = type(exc).__name__
        # Only messages from our controlled exceptions are persisted.
        if isinstance(exc, (ValueError, RuntimeError)):
            record["error"] = str(exc)
    finally:
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        save()


def positive_int(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--split", choices=["train", "val", "test"], default="train")
    parser.add_argument("--task-id", help="Default: first task in the selected manifest")
    parser.add_argument("--max-steps", type=positive_int, default=50)
    parser.add_argument("--max-tokens", type=positive_int, default=1024)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "artifacts/benchmarks/alfworld")
    parser.add_argument("--dry-run", action="store_true", help="Check task/config without model calls")
    args = parser.parse_args()
    load_dotenv(args.env_file, override=False)
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    if not api_key or not base_url:
        parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required in the environment or .env.")
    items = json.loads((SPLIT_ROOT / args.split / "items.json").read_text())
    item = next((x for x in items if x["id"] == args.task_id), None) if args.task_id else items[0]
    if item is None:
        parser.error(f"Task ID not found in {args.split} manifest.")
    data_root = Path(os.environ.get("ALFWORLD_DATA", "~/.cache/alfworld")).expanduser().resolve()
    gamefile = data_root / item["gamefile"]
    if not gamefile.is_file():
        parser.error(f"Game file missing: {gamefile}")
    endpoint = base_url + "/chat/completions"
    print(f"Model: {args.model}; task: {item['id']}; max steps: {args.max_steps}", flush=True)
    if args.dry_run:
        print(f"Game file: {gamefile}\nConfig OK; no API call made.")
        return 0

    import textworld
    from alfworld.agents.environment.alfred_tw_env import AlfredDemangler

    # Same PDDL backend and name wrapper used by the ALFWorld text environment;
    # no expert plan, hidden facts or admissible commands are supplied to the model.
    env = textworld.start(str(gamefile), textworld.EnvInfos(won=True), wrappers=[AlfredDemangler(shuffle=False)])
    env.seed(42)
    run_id = "llm_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = args.output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    output = run_dir / "trajectory.json"
    record = {
        "schema_version": "alfworld_single_task_v1",
        "task": item, "split": args.split, "gamefile": str(gamefile),
        "model": args.model, "max_steps": args.max_steps, "max_tokens": args.max_tokens,
        "temperature": 0.2, "thinking": "disabled", "environment_seed": 42,
        "skill": None, "system_prompt": SYSTEM_PROMPT,
        "versions": {name: importlib.metadata.version(name) for name in ["alfworld", "textworld"]},
        "started_at": datetime.now(timezone.utc).isoformat(),
        "steps": [], "won": False, "status": "starting",
    }
    print(f"Trajectory: {output}", flush=True)
    try:
        with requests.Session() as session:
            # Internal model services must bypass the local forwarding proxy.
            if ".intra." in base_url:
                session.trust_env = False
            generate = lambda messages: chat_action(session, endpoint, api_key, args.model, messages, args.max_tokens)
            run_episode(env, generate, args.max_steps, record, output)
    finally:
        env.close()
    print(f"Result: {record['status']}; won={record['won']}; steps={len(record['steps'])}")
    if record["status"] == "error":
        print(record.get("error", record["error_type"]))
    return 1 if record["status"] in {"error", "interrupted"} else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Pinned SkillOpt NoSkill step protocol with a DeepSeek target model."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import time

import requests
from dotenv import load_dotenv

from .run_task import REPO_ROOT, SPLIT_ROOT

PROTOCOL_ROOT = SPLIT_ROOT / "protocol/skillopt_native"
SYSTEM = "You are an expert agent operating in the ALFRED Embodied Environment."
INITIAL_TEMPLATE = (PROTOCOL_ROOT / "rollout_no_history.md").read_text()
HISTORY_TEMPLATE = (PROTOCOL_ROOT / "rollout_with_history.md").read_text()


def protocol_metadata():
    return {
        "schema_version": "alfworld_skillopt_native_noskill_v2",
        "system_prompt": SYSTEM, "initial_template": INITIAL_TEMPLATE,
        "history_template": HISTORY_TEMPLATE, "skill": None,
        "max_steps": 50, "max_tokens": 16384, "temperature": 1.0,
        "thinking": "enabled", "reasoning_effort": "medium",
        "model_semantics": "DeepSeek officially maps medium to high; thinking-mode temperature is ignored by the model.",
        "environment_seed": 42, "history": "last_2_pre_action_observations",
        "history_length": 2, "action_mode": "generation_with_admissible_candidates",
        "invalid_output_policy": "missing_action_tag_or_empty_content_falls_back_to_look",
        "request_timeout_seconds": 300,
        "source": json.loads((PROTOCOL_ROOT / "source.json").read_text()),
    }


def build_messages(observation, admissible, goal, history):
    actions = "\n ".join(f"'{action}'" for action in admissible if action != "help")
    if not history:
        user = INITIAL_TEMPLATE.format(current_observation=observation, admissible_actions=actions)
    else:
        offset = len(history) - min(2, len(history))
        lines = [f"[Observation {offset + i + 1}: '{entry['observation']}', Action {offset + i + 1}: '{entry['action']}']"
                 for i, entry in enumerate(history[-2:])]
        user = HISTORY_TEMPLATE.format(
            task_description=goal, step_count=len(history), history_length=min(2, len(history)),
            action_history="\n".join(lines), current_step=len(history) + 1,
            current_observation=observation, admissible_actions=actions,
        )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def project_action(content):
    # Same case-sensitive first-tag extraction and fallback as SkillOpt call_api,
    # followed by lowercase projection. Membership is recorded, not enforced.
    match = re.search(r"<action>(.*?)</action>", content.strip(), re.DOTALL)
    if not match:
        return "look", "empty_content" if not content.strip() else "missing_action_tag"
    return match.group(1).strip().lower(), None


def chat(session, endpoint, key, model, messages):
    body = {"model": model, "messages": messages, "temperature": 1.0,
            "max_tokens": 16384, "reasoning_effort": "medium",
            "thinking": {"type": "enabled"}, "stream": False}
    for attempt in range(6):
        response = session.post(endpoint, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=(10, 300))
        if response.status_code not in {429, 500, 502, 503, 504} or attempt == 5:
            break
        time.sleep(min(2 ** attempt, 30))
    if not response.ok:
        raise RuntimeError(f"Model API returned HTTP {response.status_code}.")
    payload = response.json(); choice = payload["choices"][0]; message = choice["message"]
    # Separate provider reasoning is not fed back into the two-message prompt.
    return {"content": message.get("content") or "", "response_model": payload.get("model"),
            "finish_reason": choice.get("finish_reason"), "usage": payload.get("usage"),
            "reasoning_content_chars": len(message.get("reasoning_content") or ""),
            "api_attempts": attempt + 1, "transport_retries": attempt}


def run_episode(env, generate, record, output):
    def save():
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(output)
    try:
        state = env.reset()
        observation = state.feedback
        record["initial_observation"] = observation
        goal = observation.split("Your task is to: ", 1)[1].strip()
        history = []
        record["status"] = "running"; save()
        print(observation, flush=True)
        for step in range(1, 51):
            admissible = list(state.admissible_commands)
            messages = build_messages(observation, admissible, goal, history)
            result = generate(messages)
            action, fallback = project_action(result["content"])
            event = {"step": step, "messages": messages, "admissible_commands": admissible,
                     "model_response": result, "action": action, "fallback": fallback,
                     "action_in_admissible_commands": action in admissible,
                     "has_think_tags": "<think>" in result["content"] and "</think>" in result["content"]}
            record["steps"].append(event); save()
            state, reward, done = env.step(action)
            history.append({"observation": observation, "action": action})
            observation = state.feedback
            event.update(observation=observation, reward=float(reward), done=bool(done), won=bool(state.won))
            record["won"] = bool(state.won)
            print(f"[{step}] {action}\n{observation}", flush=True); save()
            if state.won or done:
                record["status"] = "success" if state.won else "environment_ended"
                break
        else:
            record["status"] = "step_limit"
    except KeyboardInterrupt:
        record["status"] = "interrupted"
    except Exception as exc:
        record["status"] = "error"; record["error_type"] = type(exc).__name__
        if isinstance(exc, RuntimeError): record["error"] = str(exc)
    finally:
        record["finished_at"] = datetime.now(timezone.utc).isoformat(); save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--split", choices=["train", "val", "test"], default="train")
    parser.add_argument("--task-id")
    parser.add_argument("--max-steps", type=int, choices=[50], default=50)
    parser.add_argument("--max-tokens", type=int, choices=[16384], default=16384)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "artifacts/benchmarks/alfworld")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(); load_dotenv(args.env_file, override=False)
    key = os.environ.get("OPENAI_API_KEY"); base = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    if not key or not base: parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    items = json.loads((SPLIT_ROOT / args.split / "items.json").read_text())
    item = next((x for x in items if x["id"] == args.task_id), None) if args.task_id else items[0]
    if item is None: parser.error("Task ID not found in selected split.")
    root = Path(os.environ.get("ALFWORLD_DATA", "~/.cache/alfworld")).expanduser().resolve()
    gamefile = root / item["gamefile"]
    if not gamefile.is_file(): parser.error(f"Missing game: {gamefile}")
    if args.dry_run:
        print(f"Config OK: pinned upstream NoSkill; task={item['id']}; model={args.model}"); return 0
    import textworld
    from alfworld.agents.environment.alfred_tw_env import AlfredDemangler
    run_dir = args.output_root / ("llm_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_dir.mkdir(parents=True, exist_ok=False)
    output = run_dir / "trajectory.json"
    record = {**protocol_metadata(), "model": args.model, "task": item, "split": args.split,
              "gamefile": str(gamefile), "versions": {n: importlib.metadata.version(n) for n in ["alfworld", "textworld"]},
              "started_at": datetime.now(timezone.utc).isoformat(), "steps": [], "won": False, "status": "starting"}
    print(f"Trajectory: {output}", flush=True)
    env = textworld.start(str(gamefile), textworld.EnvInfos(won=True, admissible_commands=True), wrappers=[AlfredDemangler(shuffle=False)])
    env.seed(42)
    try:
        with requests.Session() as session:
            if ".intra." in base: session.trust_env = False
            run_episode(env, lambda messages: chat(session, base + "/chat/completions", key, args.model, messages), record, output)
    finally: env.close()
    print(f"Result: {record['status']}; won={record['won']}; steps={len(record['steps'])}")
    if record["status"] == "error": print(record.get("error", record["error_type"]))
    return 1 if record["status"] in {"error", "interrupted"} else 0


if __name__ == "__main__":
    raise SystemExit(main())

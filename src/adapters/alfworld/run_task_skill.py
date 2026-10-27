"""Run one ALFWorld task with No Skill or an immutable fixed Skill snapshot."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import time

import requests
from dotenv import load_dotenv

from .run_task import REPO_ROOT, SPLIT_ROOT
from .run_task_upstream import chat, project_action, action_error, action_diagnostic
from .actor_prompt import visible_commands
from .response_archive import archive_response
from .skill_runtime import (
    build_skill_messages, digest, load_skill, make_record, object_digest,
    validate_access, write_record, protocol_injection, LEGACY_INJECTION, SKILLOPT_INJECTION,
    protocol_output_format, protocol_action_retry, protocol_action_feedback, LEGACY_OUTPUT, ACTION_ONLY_OUTPUT,
)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def record_failure(record, exc):
    # Provider exception strings may contain credentials, URLs or response bodies.
    interrupted = isinstance(exc, KeyboardInterrupt)
    record.update(status="interrupted" if interrupted else "error",
                  error_type=type(exc).__name__, error_stage=record.get("active_phase"),
                  error="Execution interrupted." if interrupted else "Execution failed; inspect the recorded stage and error type.")


class RecordingSession:
    """Observe the existing chat client's retries without saving secrets."""

    def __init__(self, session, record, output, *, archive_responses=False):
        self.session = session
        self.record = record
        self.output = output
        self.archive_responses = archive_responses
        if archive_responses:
            record["response_archival"] = "raw_http_body_v1"

    def post(self, endpoint, **kwargs):
        event = self.record["steps"][-1]
        if self.archive_responses:
            event["response_archive"] = True
            kwargs["allow_redirects"] = False
        attempts = event.setdefault("transport_attempts", [])
        body = kwargs["json"]
        attempt = {"attempt": len(attempts) + 1, "started_at": timestamp(),
                   "status": "requesting", "usage": None,
                   "request_parameters": {key: value for key, value in body.items() if key != "messages"},
                   "request_sha256": object_digest(body)}
        if protocol_action_feedback(self.record.get('protocol', {})):
            attempt['messages'] = deepcopy(body['messages'])
            attempt['feedback_from_attempt'] = next((a['attempt'] for a in reversed(attempts)
                                                     if 'action_validation' in a), None)
        attempts.append(attempt)
        write_record(self.output, self.record)
        started = time.monotonic()
        try:
            response = self.session.post(endpoint, **kwargs)
            attempt.update(status="responded", http_status=response.status_code)
            if self.archive_responses:
                archive_response(self.output, len(self.record["steps"]), attempt, response)
                if 300 <= response.status_code < 400:
                    raise RuntimeError("Redirected model requests are not permitted.")
            return response
        except (Exception, KeyboardInterrupt) as exc:
            attempt.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "error",
                           error_type=type(exc).__name__)
            raise
        finally:
            attempt.update(finished_at=timestamp(), elapsed_seconds=time.monotonic() - started)
            write_record(self.output, self.record)

    def response_error(self, reason, *, content=None):
        attempt = self.record['steps'][-1]['transport_attempts'][-1]
        attempt['response_validation_error'] = reason
        if content is not None:
            attempt['action_validation'] = {'content': content, 'diagnostic': action_diagnostic(content, reason)}
        write_record(self.output, self.record)


def run_episode(env, generate, record, output):
    """Execute once, preserving requests and responses even if the next step fails."""
    try:
        record.update(status="running", active_phase="reset")
        write_record(output, record)
        state = env.reset()
        observation = state.feedback
        record.update(initial_observation=observation,
                      initial_admissible_commands=list(state.admissible_commands))
        write_record(output, record)
        if "Your task is to: " not in observation:
            raise ValueError("Initial observation has no task goal.")
        goal = observation.split("Your task is to: ", 1)[1].strip()
        record["goal"] = goal
        history = []
        for step in range(1, record["protocol"]["max_steps"] + 1):
            admissible = list(state.admissible_commands)
            messages = build_skill_messages(observation, admissible, goal, history, record["skill"],
                                            protocol_injection(record['protocol']),
                                            output_format=protocol_output_format(record['protocol']))
            event = {"step": step, "phase": "requesting", "messages": messages,
                     "admissible_commands": admissible, "request_started_at": timestamp()}
            record["steps"].append(event)
            record["active_phase"] = "model_request"
            write_record(output, record)
            result = generate(messages)
            if protocol_action_retry(record['protocol']):
                # The HTTP loop normally rejects these before returning. Keep the
                # environment boundary safe for custom generators as well.
                if (result.get('finish_reason') != 'stop' or
                        action_error(result['content'], visible_commands(admissible)) is not None):
                    raise ValueError('Actor generator returned an invalid action')
            event.update(model_response=result, phase="responded", response_received_at=timestamp())
            write_record(output, record)
            action, fallback = project_action(result["content"])
            event.update(action=action, fallback=fallback,
                         action_in_admissible_commands=action in admissible,
                         has_think_tags="<think>" in result["content"] and "</think>" in result["content"])
            attempts = event.get("transport_attempts", [])
            if attempts:
                attempts[-1]["usage"] = result.get("usage")
            record["active_phase"] = "environment_step"
            write_record(output, record)
            state, reward, done = env.step(action)
            history.append({"observation": observation, "action": action})
            observation = state.feedback
            event.update(phase="executed", observation=observation, reward=float(reward),
                         done=bool(done), won=bool(state.won), executed_at=timestamp())
            record["won"] = bool(state.won)
            write_record(output, record)
            print(f"[{step}] {action}; won={record['won']}; done={bool(done)}", flush=True)
            if state.won or done:
                record["status"] = "success" if state.won else "environment_ended"
                break
        else:
            record["status"] = "step_limit"
        record["active_phase"] = None
    except (Exception, KeyboardInterrupt) as exc:
        record_failure(record, exc)
    finally:
        record["finished_at"] = timestamp()
        write_record(output, record)


def environment_modules():
    textworld = importlib.import_module("textworld")
    wrapper = importlib.import_module("alfworld.agents.environment.alfred_tw_env").AlfredDemangler
    if not callable(textworld.start) or not callable(textworld.EnvInfos) or not callable(wrapper):
        raise TypeError("Required environment entry points are unavailable.")
    return textworld, wrapper


def installed_versions():
    result = {}
    for name in ("alfworld", "textworld", "requests", "python-dotenv"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def main(argv=None, *, chat_fn=chat, output_budget_policy=None, implementation_extension=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--split", choices=["train", "val", "test"], default="train")
    parser.add_argument("--purpose", choices=["smoke", "learning", "optimization", "selection", "final"], default="smoke")
    parser.add_argument("--task-id")
    parser.add_argument("--skill-file", type=Path)
    parser.add_argument('--skill-injection', choices=[LEGACY_INJECTION, SKILLOPT_INJECTION], default=LEGACY_INJECTION)
    parser.add_argument('--output-format', choices=[LEGACY_OUTPUT, ACTION_ONLY_OUTPUT], default=LEGACY_OUTPUT)
    parser.add_argument("--max-steps", type=int, choices=range(1, 51), default=50)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "artifacts/benchmarks/alfworld")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--archive-responses", action="store_true",
                        help="Archive every HTTP response body and disable redirects; keep existing bounded retries.")
    parser.add_argument("--request-attempts", type=int, choices=range(1, 7), default=6)
    parser.add_argument("--strict-response", action="store_true")
    parser.add_argument('--retry-invalid-actions', action='store_true')
    parser.add_argument('--action-feedback', action='store_true')
    args = parser.parse_args(argv)
    if args.retry_invalid_actions and not args.strict_response:
        parser.error('--retry-invalid-actions requires --strict-response')
    if args.action_feedback and not args.retry_invalid_actions:
        parser.error('--action-feedback requires --retry-invalid-actions')
    try:
        validate_access(args.split, args.purpose)
        skill = load_skill(args.skill_file)
        manifest_path = SPLIT_ROOT / args.split / "items.json"
        items = json.loads(manifest_path.read_text(encoding="utf-8"))
        item = next((item for item in items if item["id"] == args.task_id), None) if args.task_id else items[0]
        if item is None:
            parser.error("Task ID not found in selected split.")
        root = Path(os.environ.get("ALFWORLD_DATA", "~/.cache/alfworld")).expanduser().resolve()
        gamefile = root / item["gamefile"]
        if not gamefile.is_file():
            parser.error("Selected task game file is unavailable; check ALFWORLD_DATA.")
    except (OSError, ValueError) as exc:
        parser.error(f"Invalid execution inputs ({type(exc).__name__}).")
    versions = installed_versions()
    if args.dry_run:
        try:
            if any(value is None for value in versions.values()):
                raise ImportError("Required environment package is not installed.")
            environment_modules()
        except Exception as exc:
            parser.error(f"Environment interface unavailable ({type(exc).__name__}).")
        print(f"Config OK: task={item['id']}; split={args.split}; purpose={args.purpose}; "
              f"skill={skill['skill_id']}; injection={args.skill_injection}; model={args.model}; max_steps={args.max_steps}; versions={versions}")
        return 0

    load_dotenv(args.env_file, override=False)
    key = os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    if not key or not base:
        parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    endpoint = base + "/chat/completions"
    record = make_record(item=item, split=args.split, purpose=args.purpose, skill=skill,
                         model=args.model, max_steps=args.max_steps, gamefile=gamefile,
                         manifest_path=manifest_path, versions=versions,
                         backend_id=digest(endpoint.encode("utf-8")), injection=args.skill_injection,
                         output_format=args.output_format, retry_invalid_actions=args.retry_invalid_actions,
                         action_feedback=args.action_feedback)
    if output_budget_policy is not None:
        from .skill_runtime import context_fingerprint, execution_fingerprint
        record['output_budget_policy'] = output_budget_policy
        record['implementation']['files'].update(implementation_extension or {})
        record['context_fingerprint'] = context_fingerprint(record)
        record['execution_fingerprint'] = execution_fingerprint(record)
    run_dir = args.output_root / record["run_id"]
    run_dir.mkdir(parents=True, exist_ok=False)
    output = run_dir / "trajectory.json"
    record["request_policy"] = {"max_attempts": args.request_attempts, "strict_response": args.strict_response}
    record["active_phase"] = "environment_setup"
    write_record(output, record)
    print(f"Trajectory: {output}", flush=True)
    env = None
    try:
        textworld, wrapper = environment_modules()
        env = textworld.start(str(gamefile), textworld.EnvInfos(won=True, admissible_commands=True),
                              wrappers=[wrapper(shuffle=False)])
        env.seed(record["protocol"]["environment_seed"])
        with requests.Session() as session:
            if ".intra." in base:
                session.trust_env = False
            recording_session = RecordingSession(session, record, output,
                                                 archive_responses=args.archive_responses)
            def generate(messages):
                options = {}
                if args.retry_invalid_actions:
                    options = {'action_candidates': visible_commands(record['steps'][-1]['admissible_commands']),
                               'on_response_error': recording_session.response_error}
                    if args.action_feedback:
                        options['action_feedback'] = True
                return chat_fn(recording_session, endpoint, key, args.model, messages,
                               max_attempts=args.request_attempts, strict_response=args.strict_response, **options)
            run_episode(env, generate, record, output)
    except (Exception, KeyboardInterrupt) as exc:
        record_failure(record, exc)
        record["finished_at"] = timestamp()
        write_record(output, record)
    finally:
        if env is not None:
            try:
                env.close()
            except Exception as exc:
                record["close_error_type"] = type(exc).__name__
                write_record(output, record)
    print(f"Result: {record['status']}; won={record['won']}; requests={len(record['steps'])}")
    return 1 if record["status"] in {"error", "interrupted"} else 0


if __name__ == "__main__":
    raise SystemExit(main())

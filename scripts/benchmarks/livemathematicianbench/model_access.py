"""Configure SkillOpt in this process; default command only verifies offline.

Call configure() before using SkillOpt's target/optimizer API. Credentials are
read from the existing project .env, never copied into a new configuration.
This does not initialize a Trainer or change installed package files.
"""
import argparse
from functools import partial
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "benchmarks/livemathematicianbench/model_access.json"


def configure(*, http_client=None):
    if Path(sys.prefix).name != "LiveMathematicianBench":
        raise RuntimeError("Use the LiveMathematicianBench Python environment")
    cfg = json.loads(CONFIG.read_text())
    credentials = {}
    for line in (ROOT / cfg["credentials_file"]).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        credentials[key.strip()] = value.strip().strip("\"'")
    if not credentials.get("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY in project .env")
    if credentials.get("OPENAI_BASE_URL", "").rstrip("/") != cfg["base_url"]:
        raise RuntimeError("Project .env endpoint differs from model_access.json")

    import httpx
    from openai import OpenAI
    import skillopt
    from skillopt.model import set_optimizer_backend, set_target_backend
    from skillopt.model import openai_compatible_backend as backend
    if not Path(skillopt.__file__).resolve().is_relative_to(Path(sys.prefix)):
        raise RuntimeError("SkillOpt must be imported from the independent environment")
    backend.configure_openai_compatible(
        base_url=cfg["base_url"], api_key=credentials["OPENAI_API_KEY"],
        model=cfg["model"], temperature=cfg["temperature"],
        timeout_seconds=cfg["timeout_seconds"], max_tokens=cfg["max_tokens"],
    )

    def build_client(role_config):
        client = OpenAI(
            base_url=role_config.base_url, api_key=role_config.api_key,
            timeout=httpx.Timeout(role_config.timeout_seconds, connect=10),
            max_retries=0,
            http_client=http_client,
        )
        # Upstream discards reasoning_effort and has no thinking setting.
        # Bind both at the SDK boundary for target and optimizer, in-process only.
        client.chat.completions.create = partial(
            client.chat.completions.create,
            reasoning_effort=cfg["reasoning_effort"],
            extra_body={"thinking": cfg["thinking"]},
        )
        return client

    backend._build_client = build_client
    set_optimizer_backend(cfg["backend"])
    set_target_backend(cfg["backend"])
    return cfg


def verify_offline(cfg):
    import httpx
    from skillopt.model import openai_compatible_backend as backend
    from skillopt.model import get_optimizer_backend, get_target_backend
    assert get_optimizer_backend() == get_target_backend() == cfg["backend"]
    requests = []

    def respond(request):
        body = json.loads(request.content)
        assert str(request.url) == cfg["base_url"] + "/chat/completions"
        assert request.headers["authorization"] == "Bearer " + backend.TARGET_CONFIG.api_key
        for key in ("model", "temperature", "reasoning_effort", "thinking", "max_tokens"):
            assert body[key] == cfg[key], key
        assert body.get("stream", False) is False
        requests.append(True)
        return httpx.Response(200, json={
            "id": "offline", "object": "chat.completion", "created": 0,
            "model": cfg["model"], "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": "OK"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    # Explicit transport also works when the SDK internally uses httpx2.
    import socket
    with httpx.Client(transport=httpx.MockTransport(respond)) as client, patch.object(
        socket.socket, "connect", side_effect=RuntimeError("Offline check blocks network")
    ):
        configure(http_client=client)
        for call in (backend.chat_target, backend.chat_optimizer):
            result, _ = call("Offline fixture", "Return OK", retries=1,
                             max_completion_tokens=cfg["max_tokens"])
            assert result == "OK"
    assert len(requests) == 2
    configure()
    return {"offline_checks": "passed", "mock_requests": len(requests)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-access", action="store_true",
                        help="Additionally GET /models to verify credentials; no generation")
    args = parser.parse_args()
    cfg = configure()
    report = {"environment": sys.prefix, "base_url": cfg["base_url"],
              "model": cfg["model"], "credentials_source": cfg["credentials_file"],
              "credentials_present": True, **verify_offline(cfg),
              "real_generation_requests": 0, "experiments_started": 0}
    if args.check_access:
        from skillopt.model import openai_compatible_backend as backend
        try:
            models = backend._get_client("target").models.list(timeout=20)
            if cfg["model"] not in {m.id for m in models.data}:
                raise RuntimeError("Configured model absent from authenticated model list")
            report["authenticated_models_check"] = "passed"
        except Exception as exc:
            # Do not expose raw provider responses or authentication headers.
            report["authenticated_models_check"] = "failed"
            report["error_type"] = type(exc).__name__
    output = ROOT / "artifacts/benchmarks/livemathematicianbench/model_access_20261030"
    output.mkdir(parents=True, exist_ok=True)
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report.get("authenticated_models_check") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

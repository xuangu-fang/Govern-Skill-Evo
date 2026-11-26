"""Offline environment checks: native SkillOpt loading and synthetic HTTP responses.

No benchmark inference or optimization runs. Network and model child processes
are blocked before importing the runtime. SDK traffic uses an in-memory transport.
"""
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "artifacts/benchmarks/livemathematicianbench/environment_20261029"
DATA = ROOT / "data/livemathematicianbench/prepared_v1"
COUNTS = {"train": 35, "val": 17, "test": 125}
blocked_events = []
system_lookups = []


def deny_external_io(event, args):
    # The SDK queries OS metadata with these read-only system utilities on macOS.
    if event == "subprocess.Popen" and str(args[0]) in {
        "uname", "/usr/bin/uname", "file", "/usr/bin/file", "/usr/bin/sw_vers",
    }:
        system_lookups.append(Path(str(args[0])).name)
        return
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo",
                 "socket.bind", "subprocess.Popen", "os.system", "os.posix_spawn"}:
        blocked_events.append(event + (":" + Path(str(args[0])).name if event == "subprocess.Popen" else ""))
        raise RuntimeError(f"Offline verification forbids {event}")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    if Path(sys.prefix).name != "LiveMathematicianBench":
        raise RuntimeError("Run with the new LiveMathematicianBench environment")
    sys.addaudithook(deny_external_io)
    import httpx
    import openai
    import skillopt
    from skillopt.config import load_config, flatten_config
    from skillopt.engine.trainer import ReflACTTrainer
    from skillopt.envs.livemathematicianbench.adapter import LiveMathematicianBenchAdapter
    from skillopt.envs.livemathematicianbench import rollout
    from skillopt.envs.livemathematicianbench.evaluator import evaluate
    from skillopt.model import set_target_backend
    from skillopt.model import openai_compatible_backend as backend
    from skillopt.prompts import load_prompt

    installed = Path(skillopt.__file__).resolve().parent
    assert installed.is_relative_to(Path(sys.prefix)), "Imported shared source instead of installed package"
    provenance = read(AUDIT / "skillopt_source_manifest.json")
    checked_sources = 0
    for rel, expected in provenance["files"].items():
        if rel.startswith("skillopt/") and Path(rel).suffix in {".py", ".md"}:
            assert hashlib.sha256((installed.parent / rel).read_bytes()).hexdigest() == expected, rel
            checked_sources += 1

    cfg = flatten_config(load_config(str(AUDIT / "skillopt_source/configs/livemathematicianbench/default.yaml")))
    assert (cfg["max_turns"], cfg["max_completion_tokens"], cfg["exec_timeout"]) == (1, 16384, 300)
    assert not cfg["use_theorem"] and not cfg["use_sketch"]
    adapter = LiveMathematicianBenchAdapter(
        split_dir=str(DATA), split_mode="split_dir", max_turns=1,
        exec_timeout=300, workers=1, max_completion_tokens=16384,
        shuffle_choices=True, use_theorem=False, use_sketch=False,
    )
    adapter.setup({})
    loader = adapter.get_dataloader()
    ids_root = ROOT / "external/SkillOpt/data/livemathematicianbench_id_split"
    seen = set()
    for split, count in COUNTS.items():
        rows = loader.get_split_items(split)
        assert len(rows) == count
        assert [r["id"] for r in rows] == [r["id"] for r in read(ids_root / split / "items.json")]
        for row in rows:
            assert row["id"] not in seen
            seen.add(row["id"])
        batch = loader.build_eval_batch(env_num=0, split=split, seed=42)
        assert batch.payload == loader.build_eval_batch(env_num=0, split=split, seed=42).payload
        for row in batch.payload:
            correct, choices = row["correct_choice"], row["choices"]
            assert next(c["text"] for c in choices if c["label"] == correct["label"]) == correct["text"]
            assert evaluate(f"<answer>{correct['label']}</answer>", correct, choices)["em"] == 1
            wrong = next(c["label"] for c in choices if c["label"] != correct["label"])
            assert evaluate(f"<answer>{wrong}</answer>", correct, choices)["em"] == 0

    for name in ("rollout_system", "analyst_error", "analyst_success"):
        assert load_prompt(name, env="livemathematicianbench")
    initial = (installed / "envs/livemathematicianbench/skills/initial.md").read_text()
    fixtures = [{
        "id": f"fixture-{kind}", "question": f"Offline fixture {kind}",
        "choices": [{"label": c, "text": f"Choice {c}"} for c in "ABCDE"],
        "correct_choice": {"label": "B", "text": "Choice B"},
        "theorem_type": ["fixture"], "theorem": "HIDDEN_THEOREM",
        "sketch": "HIDDEN_SKETCH", "paper_link": "HIDDEN_SOURCE_LINK",
        "mcq": {"meta": "HIDDEN_ANSWER_METADATA"},
    } for kind in ("correct", "wrong", "invalid")]
    for item in fixtures:
        user = rollout._build_user(item)
        choices_text = "\n".join(f"{c['label']}. {c['text']}" for c in item["choices"])
        assert user == f"## Question\n{item['question']}\n\n## Choices\n{choices_text}"
        assert "HIDDEN_" not in user
    requests = []

    def respond(request):
        assert request.url.host == "offline.invalid"
        payload = json.loads(request.content)
        requests.append(payload)
        user = payload["messages"][-1]["content"]
        text = "<answer>B</answer>" if "fixture correct" in user else (
            "<answer>A</answer>" if "fixture wrong" in user else "<answer>INVALID</answer>")
        return httpx.Response(200, json={
            "id": "offline-fixture", "object": "chat.completion", "created": 0,
            "model": "offline-fixture", "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    set_target_backend("openai_compatible")
    backend.configure_openai_compatible(base_url="https://offline.invalid/v1",
                                       api_key="offline-placeholder", model="offline-fixture")
    with openai.OpenAI(api_key="offline-placeholder", base_url="https://offline.invalid/v1",
                       max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        with patch.object(backend, "_get_client", return_value=client):
            with tempfile.TemporaryDirectory(prefix="livemath-offline-") as tmp:
                results = adapter.rollout(fixtures, initial, tmp)
                assert {r["id"]: r["hard"] for r in results} == {
                    "fixture-correct": 1, "fixture-wrong": 0, "fixture-invalid": 0}
                assert all(r["agent_ok"] and r["n_turns"] == 1 for r in results)
                resumed = adapter.rollout(fixtures, initial, tmp)
                assert resumed == results and len(requests) == 3
    assert not blocked_events, blocked_events
    report = {
        "status": "passed", "environment": sys.prefix, "python": sys.version.split()[0],
        "skillopt_commit": provenance["upstream_commit"], "installed_package": str(installed),
        "verified_source_files": checked_sources, "counts": COUNTS, "unique_ids": len(seen),
        "data_revision": read(DATA / "split_manifest.json")["content_revision"],
        "native_imports": [ReflACTTrainer.__name__, LiveMathematicianBenchAdapter.__name__],
        "native_data_prompt_shuffle_and_scoring": "passed",
        "synthetic_rollout_cases": 3, "resume_without_new_requests": True,
        "mock_http_requests": len(requests), "real_model_requests": 0,
        "network_attempts": len(blocked_events), "experiments_started": 0,
        "read_only_os_identification": system_lookups,
        "packages": dict(sorted((d.metadata["Name"], d.version) for d in distributions())),
    }
    (AUDIT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "packages"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

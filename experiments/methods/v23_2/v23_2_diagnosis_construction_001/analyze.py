"""Read completed P1-B archives; reuse original loaders, never call a model."""
import json
from pathlib import Path

from experiments.methods.v23_2.v23_2_diagnosis_construction_001 import run as r


def main():
    # The runner's final protection assertion flagged a shared log change.
    # Do not overwrite that failure or modify the frozen runner to conceal it.
    r.p1.base.check_baseline()
    for name, base in (("p0_freeze.json", r.P1_EXP), ("p1_freeze.json", r.ROOT)):
        for path, digest in r.ev.read(r.P1_EXP / "config" / name)["sha256"].items():
            assert r.p1.digest(base / path) == digest, path
    assert (r.EXP / "config/cases.json").read_bytes() == (r.P1_EXP / "config/cases.json").read_bytes()
    before, after = r.ev.read(r.EXP / "config/protected_before.json"), r.protected_files()
    drift = r.ev.read(r.EXP / "results/post_run_drift.json")["changed"]
    changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    assert changed == set(drift) == {"docs/04_EXPERIMENT_LOG.md"}
    assert all(after[p] == drift[p]["current_sha256"] for p in changed)
    r.ev.save(r.EXP / "results/analysis_protection.json", {
        "checked_files": len(before), "unchanged_except_recorded_shared_log": True,
        "all_files_unchanged": False, "recorded_shared_document_changes": sorted(changed),
        "frozen_methods_inputs_outputs_and_historical_archives_unchanged": True,
    })
    freeze = r.ev.read(r.EXP / "config/p1_freeze.json")
    assert r.frozen_files() == freeze["sha256"]
    comparison, attempts, verification = {}, [], {}
    lines = ["# D0／D1／D2 Diagnosis全文\n\n仅各result指向的合法输出参与比较；失败原文保留且不修补。"]
    for rnd in r.ROUNDS:
        saved, entry = r.material(rnd)
        d1dir = r.ROOT / "artifacts/methods/v23_2/v23_2_diagnosis_boundary_001" / rnd
        d1path = d1dir / r.ev.read(d1dir / "result.json")["path"]
        d1 = r.local.load_attempt(d1path, prompt_path=r.P1_EXP / "config/diagnosis_prompt.md")["diagnosis"]
        stage, d2 = r.OUTPUT / rnd, None
        if (stage / "result.json").exists():
            path = stage / r.ev.read(stage / "result.json")["path"]
            d2 = r.local.load_attempt(path, prompt_path=r.PROMPT)["diagnosis"]
        comparison[rnd] = {"D0": entry["original_output"], "D1": d1, "D2": d2}
        lines.append(f'\n## {rnd}\n\n[原始输入]({entry["diagnosis_path"]}/input.json) · '
                     f'[Grouping]({entry["grouping_path"]}/grouping.json) · [D1原档]({d1path}/diagnosis.json)')
        for label, value in comparison[rnd].items():
            lines.append(f"\n### {label}\n\n```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```")
            if label == "D2" and value is None:
                lines.append("\n无合法D2；上面的null是研究汇总占位，不是模型返回的语义停止。")
        for path in sorted((stage / "attempts").glob("*")):
            meta = r.ev.read(path / "run.json")
            assert meta["started_at"] > freeze["at"]
            assert r.ev.read(path / "input.json") == saved
            messages = r.ev.read(path / "messages.json")
            assert messages == r.local.messages_for("diagnosis", saved, prompt_path=r.PROMPT)
            original = r.ev.read(Path(entry["diagnosis_path"]) / "messages.json")
            assert messages[1:] == original[1:]
            assert set(json.loads(messages[1]["content"])) == {"parent", "command_sets", "runs", "grouping"}
            request = r.ev.read(path / "request.json") if (path / "request.json").exists() else None
            if request:
                assert request["attempts"] == 1 and request["body"]["messages"] == messages
                call = {**{k: v for k, v in request["body"].items() if k != "messages"},
                        "endpoint": request["endpoint"], "timeout_seconds": request["timeout_seconds"]}
                assert call == entry["config"]["call_config"]
            for key in ("max_input_chars", "max_message_utf8_bytes"):
                assert meta[key] == entry["config"][key]
            response = r.ev.read(path / "response.json") if (path / "response.json").exists() else {}
            attempts.append({
                "round": rnd, "path": str(path), "status": meta["status"],
                "started_at": meta["started_at"], "finished_at": meta["finished_at"],
                "elapsed_seconds": meta["elapsed_seconds"], "usage": response.get("usage"),
                "api_attempts": response.get("api_attempts"), "request_archived": request is not None,
                "finish_reason": response.get("finish_reason"),
                "error": r.ev.read(path / "error.json") if (path / "error.json").exists() else None,
            })
            links = [(name, label) for name, label in (
                ("request.json", "D2请求"), ("http_response.txt", "原始响应"),
                ("raw_output.txt", "原始文本"), ("parsed.json", "解析"),
                ("validation.json", "校验"), ("run.json", "配置与耗时"),
                ("error.json", "技术错误")) if (path / name).exists()]
            lines.append("\n" + " · ".join(f"[{label}]({path / name})" for name, label in links))
        verification[rnd] = {
            "same_original_upstream_input": True, "memory_absent": True,
            "only_frozen_system_prompt_changed": True,
            "original_model_config_and_capacity": True, "valid_result": d2 is not None,
            "stop": r.ev.read(stage / "stop.json") if (stage / "stop.json").exists() else None,
        }
    assert len(attempts) <= 3
    assert all(a["api_attempts"] in (None, 1) for a in attempts)
    assert len({a["round"] for a in attempts}) == len(attempts)
    for name, value in (("comparison.json", comparison), ("attempts.json", attempts),
                        ("verification.json", verification),
                        ("summary.json", r.ev.read(r.OUTPUT / "summary.json"))):
        r.ev.save(r.EXP / "results" / name, value)
    (r.EXP / "reports/OUTPUTS.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(r.ev.read(r.EXP / "results/summary.json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

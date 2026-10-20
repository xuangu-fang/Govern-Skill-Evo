"""Runtime bindings and live adapter wiring; no network or environment execution."""

from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.adapters.alfworld.skill_runtime import digest, object_digest
from src.skill_evolution.v22.continual_runtime import (
    check_runtime, freeze_runtime, live_dependencies, load_bundle,
)
from src.skill_evolution.v22.model_routing import evolution_route


PLAN = Path("experiments/methods/v22/08_grouped_continual/config/plan.json").resolve()


class ContinualRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = self.root / "config"
        self.config.mkdir()
        for name in ("plan.json", "task_manifest.json", "grouping_prompt.md"):
            (self.config / name).write_bytes((PLAN.parent / name).read_bytes())
        self.plan_path = self.config / "plan.json"

    def write_plan(self, edit):
        plan = json.loads(self.plan_path.read_text())
        edit(plan)
        self.plan_path.write_text(json.dumps(plan))

    def test_valid_bundle_has_twenty_native_tasks_without_selection_rationale(self):
        bundle = load_bundle(self.plan_path)
        self.assertEqual(len(bundle["task_items"]), 20)
        self.assertEqual(len(bundle["bindings"]), 4)
        self.assertTrue(all("selection_reason" not in row for row in bundle["task_items"].values()))
        self.assertEqual(bundle["plan"]["budget"]["logical_requests_max"], 2009)

    def test_endpoint_routing_preserves_source_plan_and_actor(self):
        original = self.plan_path.read_bytes()
        for base, expected in [
            ("http://llm-proxy.intra.xiaojukeji.com/", "deepseek-v4-pro"),
            ("https://api.deepseek.com", "deepseek-v4.1-flash"),
            ("https://api.deepseek.com/v1/", "deepseek-v4.1-flash"),
            ("https://api.deepseek.com.example.invalid", "deepseek-v4-pro"),
        ]:
            with self.subTest(base=base):
                bundle = load_bundle(self.plan_path, base_url=base)
                self.assertEqual(bundle["plan"]["models"]["evolution"], expected)
                self.assertEqual(bundle["plan"]["classification"]["model"], expected)
                self.assertEqual(bundle["plan"]["models"]["actor"], "deepseek-v4-flash")
        self.assertEqual(self.plan_path.read_bytes(), original)
        self.assertNotIn("evolution_route", load_bundle(self.plan_path)["plan"])
        for base in ["https://secret@api.deepseek.com", "https://api.deepseek.com?key=secret", "not-a-url"]:
            with self.assertRaises(ValueError):
                evolution_route(base, "deepseek-v4-pro")

    def test_routed_model_is_frozen_and_used_by_every_semantic_stage(self):
        bundle = load_bundle(self.plan_path, base_url="https://api.deepseek.com")
        frozen = freeze_runtime(bundle, self.root / "routed", offline=True)
        self.assertEqual(check_runtime(frozen)["plan"], bundle["plan"])
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic", "OPENAI_BASE_URL": "https://api.deepseek.com/"}), \
                patch("src.skill_evolution.v22.continual_runtime.semantic_call", return_value="{}") as call:
            generate, _ = live_dependencies(bundle, self.root / "absent.env")
            for stage in ("classification", "diagnosis", "fusion", "main_editor", "post_gate_learning"):
                generate(stage, [], self.root / (stage + ".json"))
                self.assertEqual(call.call_args.kwargs["model"], "deepseek-v4.1-flash")
                self.assertEqual(call.call_args.kwargs["endpoint"], "https://api.deepseek.com/chat/completions")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic", "OPENAI_BASE_URL": "http://llm-proxy.intra.xiaojukeji.com"}):
            with self.assertRaisesRegex(ValueError, "frozen model route"):
                live_dependencies(bundle, self.root / "absent.env")

    def test_prepared_run_rejects_endpoint_change_before_claim(self):
        from src.skill_evolution.v22.continual_runner import _claim_prepared_runtime
        official = load_bundle(self.plan_path, base_url="https://api.deepseek.com")
        proxy = load_bundle(self.plan_path, base_url="http://llm-proxy.intra.xiaojukeji.com")
        root = (self.root / "prepared").resolve()
        freeze_runtime(official, root, offline=True)
        with self.assertRaisesRegex(ValueError, "Prepared runtime differs"):
            _claim_prepared_runtime(proxy, root, offline=True)
        self.assertFalse((root / "start_claim.json").exists())
        _claim_prepared_runtime(official, root, offline=True)

    def test_rejects_parallel_branch_and_changed_budget(self):
        self.write_plan(lambda p: p["rounds"][1]["stage_calls_max"].update(direct_editor=1))
        with self.assertRaisesRegex(ValueError, "parallel"):
            load_bundle(self.plan_path)
        self.plan_path.write_bytes(PLAN.read_bytes())
        self.write_plan(lambda p: p["budget"].update(environment_episodes_max=50))
        with self.assertRaisesRegex(ValueError, "budget"):
            load_bundle(self.plan_path)

    def test_rejects_stream_overlap_and_actor_parameter_drift(self):
        self.write_plan(lambda p: p["data"].update(round2_task_ids=p["data"]["round1_task_ids"]))
        with self.assertRaisesRegex(ValueError, "overlap"):
            load_bundle(self.plan_path)
        self.plan_path.write_bytes(PLAN.read_bytes())
        self.write_plan(lambda p: p["models"]["request_parameters"].update(max_tokens=8192))
        with self.assertRaisesRegex(ValueError, "parameters"):
            load_bundle(self.plan_path)

    def test_rejects_manifest_and_prompt_drift(self):
        prompt = self.config / "grouping_prompt.md"
        prompt.write_text(prompt.read_text() + "\nchanged\n")
        with self.assertRaisesRegex(ValueError, "prompt hash"):
            load_bundle(self.plan_path)
        prompt.write_bytes((PLAN.parent / prompt.name).read_bytes())
        manifest = self.config / "task_manifest.json"
        manifest.write_text(manifest.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "manifest hash"):
            load_bundle(self.plan_path)

    def test_rejects_rebound_non_native_item(self):
        path = self.config / "task_manifest.json"
        manifest = json.loads(path.read_text())
        manifest["rounds"][0]["tasks"][0]["gamefile"] = "invented"
        path.write_text(json.dumps(manifest))
        self.write_plan(lambda p: p["data"].update(task_manifest_sha256=digest(path.read_bytes())))
        with self.assertRaisesRegex(ValueError, "native Train"):
            load_bundle(self.plan_path)

    def test_offline_freeze_preserves_sources_prompts_and_detects_changes(self):
        bundle = load_bundle(self.plan_path)
        with patch("src.skill_evolution.v22.continual_runtime.environment_modules") as environment:
            frozen = freeze_runtime(bundle, self.root / "run", offline=True)
        environment.assert_not_called()
        self.assertEqual(frozen["mode"], "offline_synthetic")
        self.assertEqual(frozen["game_files"], [])
        self.assertTrue(frozen["sources"])
        self.assertEqual(set(frozen["system_prompts"]),
                         {"classification", "diagnosis", "fusion", "main_editor", "post_gate_learning"})
        for prompt in frozen["system_prompts"].values():
            self.assertEqual(prompt["sha256"], digest(prompt["text"].encode()))
        self.assertEqual(check_runtime(frozen), frozen)
        with self.assertRaisesRegex(ValueError, "already frozen"):
            freeze_runtime(bundle, self.root / "run", offline=True)
        Path(frozen["sources"][0]["snapshot"]).write_text("Changed archived implementation")
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            check_runtime(frozen)

    def test_freeze_checks_current_config_and_bundle_contents(self):
        bundle = load_bundle(self.plan_path)
        changed = deepcopy(bundle)
        changed["task_items"].pop(next(iter(changed["task_items"])))
        with self.assertRaisesRegex(ValueError, "bundle changed"):
            freeze_runtime(changed, self.root / "bad", offline=True)
        frozen = freeze_runtime(bundle, self.root / "run", offline=True)
        self.plan_path.write_text(self.plan_path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "source/config/game changed"):
            check_runtime(frozen)

    def test_live_preflight_fails_without_dependencies_and_never_creates_environment(self):
        bundle = load_bundle(self.plan_path)
        with patch("src.skill_evolution.v22.continual_runtime.installed_versions", return_value={"alfworld": None}), \
                patch("src.skill_evolution.v22.continual_runtime.environment_modules") as environment:
            with self.assertRaisesRegex(ValueError, "dependencies"):
                freeze_runtime(bundle, self.root / "live")
        environment.assert_not_called()
        self.assertFalse((self.root / "live/runtime_freeze.json").exists())

    def test_live_callbacks_use_one_existing_client_call_and_one_actor_job(self):
        bundle = load_bundle(self.plan_path)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-secret", "OPENAI_BASE_URL": "https://example.invalid"}), \
                patch("src.skill_evolution.v22.continual_runtime.semantic_call", return_value="{}") as call, \
                patch("src.skill_evolution.v22.continual_runtime.execute_episode", return_value=Path("partial.json")) as episode:
            generate, execute = live_dependencies(bundle, self.root / "absent.env")
            self.assertEqual(generate("diagnosis", [{"role": "user", "content": "fixture"}],
                                      self.root / "call.json"), "{}")
            self.assertEqual(call.call_count, 1)
            self.assertEqual(call.call_args.kwargs["model"], "deepseek-v4-pro")
            task = next(iter(bundle["task_items"].values()))
            self.assertEqual(execute(task, None, self.root / "episode"), Path("partial.json"))
            self.assertEqual(episode.call_count, 1)
            self.assertEqual(episode.call_args.args[:4], (task["id"], "train", "learning", None))
            self.assertEqual(episode.call_args.args[5]["actor_model"], "deepseek-v4-flash")
            with self.assertRaisesRegex(ValueError, "stage"):
                generate("direct_editor", [], self.root / "bad.json")
            with self.assertRaisesRegex(ValueError, "task differs"):
                execute(task | {"gamefile": "wrong"}, None, self.root / "wrong")

    def test_live_callback_rejects_oversized_or_existing_output_without_call(self):
        bundle = load_bundle(self.plan_path)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic", "OPENAI_BASE_URL": "https://example.invalid"}), \
                patch("src.skill_evolution.v22.continual_runtime.semantic_call") as call:
            generate, _ = live_dependencies(bundle, self.root / "absent.env")
            with self.assertRaisesRegex(ValueError, "limit"):
                generate("diagnosis", [{"role": "user", "content": "x" * 400001}], self.root / "long.json")
            path = self.root / "existing.json"
            path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "no repeat"):
                generate("diagnosis", [], path)
            call.assert_not_called()


if __name__ == "__main__":
    unittest.main()

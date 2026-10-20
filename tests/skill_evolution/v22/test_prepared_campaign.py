"""Starting a previously frozen campaign once, using only synthetic callbacks."""

from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
import unittest
from unittest.mock import patch

from src.adapters.alfworld.response_archive import archive_response
from src.adapters.alfworld.skill_runtime import digest, object_digest, write_record
from src.skill_evolution.v22.continual_runner import main, run_campaign
from src.skill_evolution.v22.continual_runtime import (
    STAGES, STREAM_PROTOCOL, freeze_runtime, load_bundle, semantic_request_options,
)
from src.skill_evolution.v22.continual_verify import verify_campaign
from src.skill_evolution.v22.model_call import semantic_call
from tests.skill_evolution.v22.test_continual_runner import PLAN, SyntheticCampaign


class PreparedCampaignTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        config = self.root / "config"
        config.mkdir()
        for name in ("plan.json", "task_manifest.json", "grouping_prompt.md"):
            (config / name).write_bytes((PLAN.parent / name).read_bytes())
        self.plan_path = config / "plan.json"
        self.bundle = load_bundle(self.plan_path)
        self.output = self.root / "prepared"
        with patch("src.skill_evolution.v22.continual_runtime.environment_modules") as environment:
            self.frozen = freeze_runtime(self.bundle, self.output, offline=True)
        environment.assert_not_called()
        self.before = {str(path.relative_to(self.output)): path.read_bytes()
                       for path in self.output.rglob("*") if path.is_file()}
        self.callbacks = SyntheticCampaign(self.root, self.bundle)

    def run_prepared(self, bundle=None):
        return run_campaign(bundle or self.bundle, self.output, self.callbacks.generate,
                            self.callbacks.execute, offline=True, prepared=True)

    def assert_no_dispatch(self):
        self.assertEqual(self.callbacks.calls, [])
        self.assertEqual(self.callbacks.executions, [])
        self.assertFalse((self.output / "start_claim.json").exists())

    def test_frozen_campaign_runs_once_without_refreezing_or_changing_snapshots(self):
        with patch("src.skill_evolution.v22.continual_runner.freeze_runtime") as refreeze:
            report = self.run_prepared()
        refreeze.assert_not_called()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(len(self.callbacks.calls), 9)
        self.assertEqual(len(self.callbacks.executions), 40)
        for relative, content in self.before.items():
            self.assertEqual((self.output / relative).read_bytes(), content)
        claim = json.loads((self.output / "start_claim.json").read_text())
        self.assertEqual(claim["runtime_sha256"], self.frozen["sha256"])
        self.assertTrue(verify_campaign(self.output)["campaign_complete"])
        counts = (len(self.callbacks.calls), len(self.callbacks.executions))
        with self.assertRaisesRegex(ValueError, "unused runtime freeze"):
            self.run_prepared()
        self.assertEqual((len(self.callbacks.calls), len(self.callbacks.executions)), counts)

    def test_changed_config_or_bundle_stops_before_claim_and_callbacks(self):
        changed = deepcopy(self.bundle)
        changed["task_items"].pop(next(iter(changed["task_items"])))
        with self.assertRaisesRegex(ValueError, "requested bundle"):
            self.run_prepared(changed)
        self.assert_no_dispatch()
        self.plan_path.write_text(self.plan_path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "source/config/game changed"):
            self.run_prepared()
        self.assert_no_dispatch()

    def test_changed_source_snapshot_stops_before_claim_and_callbacks(self):
        snapshot = Path(self.frozen["sources"][0]["snapshot"])
        snapshot.write_bytes(snapshot.read_bytes() + b"\n# changed snapshot\n")
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            self.run_prepared()
        self.assert_no_dispatch()

    def test_progress_or_unbound_preflight_files_are_not_a_resume(self):
        for name in ("report.json", "state0.json", "rounds", "preflight_notes.txt", "start_claim.json"):
            path = self.output / name
            if name == "rounds":
                path.mkdir()
            else:
                path.write_text("Existing file must remain unchanged.\n")
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "no resume"):
                self.run_prepared()
            self.assertEqual(self.callbacks.calls, [])
            self.assertEqual(self.callbacks.executions, [])
            if path.is_dir():
                path.rmdir()
            else:
                self.assertEqual(path.read_text(), "Existing file must remain unchanged.\n")
                path.unlink()

    def test_prepared_flag_only_applies_to_run(self):
        with patch("src.skill_evolution.v22.continual_runner.load_bundle") as load, \
                patch("src.skill_evolution.v22.continual_runner.live_dependencies") as live, \
                patch("sys.stderr", new_callable=StringIO):
            for command in ("preflight", "verify"):
                with self.subTest(command=command), self.assertRaises(SystemExit) as error:
                    main([command, "--prepared", "--output-dir", str(self.output)])
                self.assertEqual(error.exception.code, 2)
        load.assert_not_called()
        live.assert_not_called()

    def test_streaming_budget_reaches_calls_and_complete_archive_verification(self):
        """Preauthored synthetic responses exercise recording, not model quality."""
        plan = deepcopy(self.bundle["plan"])
        plan.update(protocol=STREAM_PROTOCOL, update_profile="v22.unified_dsc.v2",
                    scheduling={"actor_workers": 8, "dispatch": "bounded_in_frozen_task_order",
                                "on_technical_failure": "stop_dispatch_and_drain",
                                "semantic_stages": "sequential_after_complete_batch"})
        plan["budget"].update(actor_workers_max=8, per_request_output_tokens_max=65536,
                              tasks_per_round=8, unique_tasks=16, environment_episodes_max=32,
                              actor_logical_requests_max=1600, logical_requests_max=1609,
                              http_attempts_max=9609, semantic_http_attempts_per_request_max=1,
                              semantic_output_tokens_max=7 * 32768 + 2 * 65536,
                              actor_output_tokens_max=1600 * 6 * 16384)
        for row in plan["rounds"]:
            row["episodes_max"] = 16
        plan["models"].update(actor_response_archival=True, semantic_requests={
            stage: {"max_tokens": 65536 if stage == "post_gate_learning" else 32768,
                    "timeout_seconds": 600, "transport_policy": "single_attempt"} for stage in STAGES})
        plan["gate"]["accept"] = "candidate_success_count > parent_success_count for the same complete comparable task batch"
        plan["gate"]["required_pairs"] = 8
        manifest_path = self.plan_path.parent / "task_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["protocol"] = STREAM_PROTOCOL
        manifest["unique_tasks"] = 16
        for row in manifest["rounds"]:
            row["task_ids"] = row["task_ids"][:8]
            row["tasks"] = row["tasks"][:8]
            plan["data"][f"round{row['round']}_task_ids"] = row["task_ids"]
        manifest["task_ids_canonical_sha256"] = object_digest({f"round{row['round']}": row["task_ids"]
                                                              for row in manifest["rounds"]})
        manifest_path.write_text(json.dumps(manifest))
        plan["data"]["task_manifest_sha256"] = digest(manifest_path.read_bytes())
        protocol_path = self.plan_path.parent / "protocol.md"
        protocol_path.write_text("Synthetic protocol fixture. No model or environment execution.\n")
        plan["preparation_materials"] = [{"path": protocol_path.name, "sha256": digest(protocol_path.read_bytes())}]
        self.plan_path.write_text(json.dumps(plan))
        bundle = load_bundle(self.plan_path)
        output = self.root / "streaming_prepared"
        frozen = freeze_runtime(bundle, output, offline=True)

        class Response:
            status_code = 200

            def __init__(self, text, model="deepseek-v4-pro"):
                self.payload = {"model": model, "choices": [{"finish_reason": "stop",
                    "message": {"content": text}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
                self.content = json.dumps(self.payload).encode("utf-8")

            def json(self):
                return deepcopy(self.payload)

        class SyntheticSingleAttemptCampaign(SyntheticCampaign):
            def __init__(self, root, bundle):
                super().__init__(root, bundle)
                self.lock = Lock()

            def execute(self, task_item, skill_file, output_root):
                # The existing fixture encodes a ten-slot side boundary. Map
                # this eight-slot experiment explicitly, under a fixture lock.
                with self.lock:
                    round_id = self.round_name(output_root)
                    task_ids = bundle["plan"]["data"][f"round{round_id[1:]}_task_ids"]
                    side = "candidate" if "candidate_runs" in Path(output_root).parts else "parent"
                    self.round_slots[round_id] = task_ids.index(task_item["id"]) + (10 if side == "candidate" else 0)
                    path = super().execute(task_item, skill_file, output_root)
                    record = json.loads(path.read_text())
                    record["response_archival"] = "raw_http_body_v1"
                    event = record["steps"][0]
                    event["response_archive"] = True
                    response = Response(event["model_response"]["content"], "deepseek-v4-flash")
                    usage = response.payload["usage"]
                    event["model_response"].update(finish_reason="stop", usage=usage,
                                                   api_attempts=1, transport_retries=0)
                    parameters = {"model": "deepseek-v4-flash", **bundle["plan"]["models"]["request_parameters"]}
                    attempt = {"attempt": 1, "status": "responded", "http_status": 200, "usage": usage,
                               "request_parameters": parameters,
                               "request_sha256": object_digest({**parameters, "messages": event["messages"]})}
                    archive_response(path, 1, attempt, response)
                    event["transport_attempts"] = [attempt]
                    write_record(path, record)
                    return path

            def generate(self, stage, messages, output_path):
                # Reuse only the preauthored response generator. Its temporary
                # legacy ledger is removed before recording this fake request.
                fixture_path = output_path.with_name("fixture_" + output_path.name)
                raw = super().generate(stage, messages, fixture_path)
                fixture_path.unlink()
                response = Response(raw)
                with patch("requests.Session.post", side_effect=AssertionError("Network is forbidden")):
                    class Session:
                        def post(self, endpoint, **kwargs):
                            return response
                    return semantic_call(stage, messages, session=Session(), endpoint="https://fixture.invalid",
                        key="synthetic", model="deepseek-v4-pro", output=output_path,
                        **semantic_request_options(bundle["plan"], stage))

        callbacks = SyntheticSingleAttemptCampaign(self.root, bundle)
        report = run_campaign(bundle, output, callbacks.generate, callbacks.execute, offline=True, prepared=True)
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(len(callbacks.calls), 9)
        self.assertEqual(len(callbacks.executions), 32)
        self.assertEqual(json.loads((output / "runtime_freeze.json").read_text()), frozen)
        self.assertTrue(verify_campaign(output)["campaign_complete"])
        for path in output.glob("rounds/*/calls/*.json"):
            call = json.loads(path.read_text())
            options = semantic_request_options(bundle["plan"], call["stage"])
            self.assertEqual(call["request_profile"], {key: value for key, value in options.items()
                                                      if key != "transport_policy"})
            self.assertEqual(call["transport_policy"], "single_attempt")
            self.assertEqual(len(call["steps"][0]["transport_attempts"]), 1)
            self.assertIn("raw_response", call["steps"][0]["transport_attempts"][0])


if __name__ == "__main__":
    unittest.main()

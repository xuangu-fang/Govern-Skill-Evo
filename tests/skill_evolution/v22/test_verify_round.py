"""Offline round audit tests; fixture trajectories are synthetic, never results."""

from copy import deepcopy
import json

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import (
    build_skill_messages, digest, execution_fingerprint, load_skill, make_record, object_digest, write_record,
)
from src.skill_evolution.v22.run_round import DEFAULT_PLAN, run_round
from src.skill_evolution.v22.verify_round import verify_round
from tests.skill_evolution.v22.test_diagnosis_editor import build_diagnosis, build_editor


def make_round(tmp_path):
    diagnosis = build_diagnosis()
    editor = build_editor(diagnosis)
    plan = json.loads(DEFAULT_PLAN.read_text())
    plan["editor_schema"] = "v22.editor.v0"  # Exercise the immutable legacy protocol.
    plan.update(task_ids=["train:0000"], parent_episodes=1, candidate_episodes_max=1, max_steps_per_episode=1)
    game = tmp_path / "game.tw-pddl"
    game.write_text("synthetic fixture")
    item = {"id": "train:0000", "gamefile": "fixture"}
    manifest = tmp_path / "items.json"
    write_record(manifest, [item])
    parent = make_record(item=item, split="train", purpose="learning", skill=load_skill(),
                         model=plan["model"], max_steps=1, gamefile=game, manifest_path=manifest,
                         versions={"alfworld": "fixture"}, backend_id="fixture")
    observation = "Your task is to: inspect the room."
    admissible = ["look"]
    parent.update(run_id="run-a", initial_observation=observation, initial_admissible_commands=admissible,
                  status="step_limit", finished_at="fixture")
    parent["steps"] = [{"step": 1, "phase": "executed", "messages": build_skill_messages(
        observation, admissible, "inspect the room.", [], parent["skill"]), "admissible_commands": admissible,
        "model_response": {"content": "<action>look</action>", "response_model": plan["model"],
                           "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}},
        "action": "look", "fallback": None, "action_in_admissible_commands": True,
        "observation": "Room unchanged", "reward": 0, "won": False, "done": False}]
    source = tmp_path / "parent_trajectory.json"
    write_record(source, parent)

    def build(mode="candidate"):
        diag, edit = deepcopy(diagnosis), deepcopy(editor)
        if mode == "recovery":
            prior = deepcopy(parent)
            prior.update(run_id="prior-failed-parent", status="error", error_stage="model_request", error_type="ReadTimeout")
            event = prior["steps"][0]
            prior["steps"] = [{key: event[key] for key in ("step", "messages", "admissible_commands")}]
            prior["steps"][0]["phase"] = "requesting"
            path = tmp_path / "prior_parent.json"
            write_record(path, prior)
            plan.update(prior_parent_attempts=[{"path": str(path), "sha256": digest(path.read_bytes())}],
                        parent_attempts_per_task_max=2, total_environment_request_slots_max=3,
                        supersedes_plan_sha256=object_digest(plan), recovery_reason="One fixed-budget retry after ReadTimeout")
        if mode in {"no_change", "need_evidence"}:
            diag.update(decision=mode, proposals=[], interactions=[],
                        missing_evidence=["Need a relevant action observation"] if mode == "need_evidence" else [])
        elif mode == "needs_revision":
            edit.update(decision="needs_revision", candidate_text=None, mappings=[],
                        upstream_feedback=[{"proposal_ids": ["p1"], "limitation": "Unavailable state",
                                            "counterexample": "Older visit outside window", "suggested_revision": "Use visible state",
                                            "scope_change": "Local scope only"}])

        def generate(stage, messages, output):
            if mode == "error":
                raise TimeoutError("synthetic failure")
            raw = json.dumps(diag if stage == "diagnosis" else edit)
            parameters = {"model": plan["model"], "temperature": 1.0, "max_tokens": 16384,
                          "reasoning_effort": "medium", "thinking": {"type": "enabled"}, "stream": False}
            usage = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
            write_record(output, {"schema_version": "v22_semantic_call_v1", "stage": stage, "model": plan["model"],
                                  "messages_sha256": object_digest(messages), "status": "responded",
                                  "steps": [{"messages": messages, "phase": "responded",
                                             "transport_attempts": [{"attempt": 1, "status": "responded", "http_status": 200,
                                                                     "request_parameters": parameters,
                                                                     "request_sha256": object_digest({**parameters, "messages": messages}),
                                                                     "usage": usage}],
                                             "model_response": {"content": raw, "finish_reason": "stop", "usage": usage,
                                                                "api_attempts": 1, "transport_retries": 0}}]})
            return raw

        def execute(record, skill_path, output_root):
            result = deepcopy(record)
            result.update(run_id="candidate-a", skill=load_skill(skill_path))
            result["execution_fingerprint"] = execution_fingerprint(result)
            event = result["steps"][0]
            event["messages"] = build_skill_messages(observation, admissible, "inspect the room.", [], result["skill"])
            if mode == "partial":
                result.update(status="error", error_stage="model_request")
                result["steps"] = [{key: event[key] for key in ("step", "messages", "admissible_commands")}]
                result["steps"][0]["phase"] = "requesting"
            output = output_root / "skill_candidate/trajectory.json"
            output.parent.mkdir(parents=True)
            write_record(output, result)
            return output

        root = tmp_path / mode
        run_round(plan, [source], root, generate, execute)
        return root
    return build


def change(path, mutate):
    value = json.loads(path.read_text())
    mutate(value)
    write_record(path, value)


class RoundAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def build(self, mode="candidate", name="case"):
        target = self.root / name
        target.mkdir()
        return make_round(target)(mode)

    def test_valid_candidate_round(self):
        audit = verify_round(self.build())
        self.assertTrue(audit["artifact_valid"] and audit["round_complete"])
        self.assertEqual(audit["candidate_executions"], 1)
        self.assertIn("not semantic correctness", audit["scope"])

    def test_valid_semantic_stops_have_no_candidate(self):
        for mode in ("no_change", "need_evidence", "needs_revision"):
            with self.subTest(mode=mode):
                audit = verify_round(self.build(mode, mode))
                self.assertTrue(audit["round_complete"])
                self.assertEqual(audit["candidate_executions"], 0)

    def test_failure_is_not_certified_complete(self):
        for mode in ("error", "partial"):
            with self.subTest(mode=mode):
                audit = verify_round(self.build(mode, mode))
                self.assertTrue(audit["artifact_valid"])
                self.assertFalse(audit["round_complete"])

    def test_tampered_artifacts_are_rejected(self):
        for mutation in ("source", "evidence", "requirements", "response", "prompt", "candidate", "diff", "lineage", "comparison", "cost"):
            with self.subTest(mutation=mutation):
                root = self.build(name=mutation)
                if mutation == "source":
                    source = json.loads((root / "sources.json").read_text())[0]["path"]
                    with open(source, "a") as output:
                        output.write("\n")
                elif mutation == "evidence":
                    change(root / "evidence.json", lambda value: value[0].update(initial_observation="invented"))
                    change(root / "report.json", lambda value: value.update(evidence_sha256=object_digest(json.loads((root / "evidence.json").read_text()))))
                elif mutation == "requirements":
                    change(root / "requirements.json", lambda value: value["proposals"][0].update(strategy="different"))
                elif mutation == "response":
                    change(root / "diagnosis.json", lambda value: value.update(rationale="Altered after execution"))
                    change(root / "requirements.json", lambda value: value.update(diagnosis_sha256=object_digest(json.loads((root / "diagnosis.json").read_text()))))
                elif mutation == "prompt":
                    change(root / "calls/diagnosis.json", lambda value: value["steps"][0]["messages"][1].update(content="Candidate outcome leaked"))
                elif mutation == "candidate":
                    (root / "candidate/SKILL.md").write_text("Other rule")
                elif mutation == "diff":
                    (root / "candidate/actual.diff").write_text("fabricated patch")
                elif mutation == "lineage":
                    change(root / "candidate/lineage.json", lambda value: value.update(editor_sha256="incorrect"))
                elif mutation == "comparison":
                    change(root / "report.json", lambda value: value["comparisons"][0].update(candidate_native_success=True))
                else:
                    change(root / "report.json", lambda value: value["cost"].update(semantic_calls=0))
                with self.assertRaises(ValueError):
                    verify_round(root)

    def test_no_candidate_cannot_claim_evaluated(self):
        root = self.build("no_change")
        change(root / "report.json", lambda value: value.update(status="candidate_evaluated"))
        with self.assertRaisesRegex(ValueError, "incomplete"):
            verify_round(root)

    def test_semantic_stop_cannot_hide_candidate_artifacts(self):
        root = self.build("no_change")
        (root / "candidate").mkdir()
        with self.assertRaisesRegex(ValueError, "No-candidate"):
            verify_round(root)

    def test_semantic_http_tampering_is_rejected(self):
        for mutation in ("missing", "parameters", "body", "sequence", "retry", "limit", "http_status", "count", "usage"):
            with self.subTest(mutation=mutation):
                root = self.build(name=mutation)
                def mutate(call):
                    event = call["steps"][0]
                    attempt = event["transport_attempts"][0]
                    if mutation == "missing":
                        event["transport_attempts"] = []
                    elif mutation == "parameters":
                        attempt["request_parameters"]["max_tokens"] = 1
                    elif mutation == "body":
                        attempt["request_sha256"] = "wrong"
                    elif mutation == "sequence":
                        attempt["attempt"] = 2
                    elif mutation == "retry":
                        event["transport_attempts"].append({**deepcopy(attempt), "attempt": 2})
                    elif mutation == "limit":
                        event["transport_attempts"] = [deepcopy(attempt)] * 7
                    elif mutation == "http_status":
                        attempt["http_status"] = 500
                    elif mutation == "count":
                        event["model_response"]["api_attempts"] = 2
                    else:
                        attempt["usage"]["total_tokens"] = 99
                change(root / "calls/diagnosis.json", mutate)
                with self.assertRaises(ValueError):
                    verify_round(root)

    def test_pending_http_attempt_remains_unknown(self):
        from src.skill_evolution.v22.verify_round import verify_call
        root = self.build()
        path = root / "calls/diagnosis.json"
        call = json.loads(path.read_text())
        event = call["steps"][0]
        event.pop("model_response")
        event["phase"] = "requesting"
        event["transport_attempts"][0].update(status="requesting", usage=None)
        event["transport_attempts"][0].pop("http_status")
        call["status"] = "requesting"
        write_record(path, call)
        verify_call(path, "diagnosis", call["model"], event["messages"], None)

    def test_prior_failed_parent_cost_is_counted_without_learning_it(self):
        root = self.build("recovery")
        audit = verify_round(root)
        self.assertTrue(audit["round_complete"])
        report = json.loads((root / "report.json").read_text())
        self.assertEqual(report["cost"]["environment_requests"], 3)
        self.assertEqual(report["cost"]["requests_with_unknown_usage"], 1)
        evidence = json.loads((root / "evidence.json").read_text())
        self.assertEqual([row["run_id"] for row in evidence], ["run-a"])

    def test_prior_failed_parent_cannot_be_omitted_or_modified(self):
        for mutation in ("report", "cost", "source"):
            with self.subTest(mutation=mutation):
                root = self.build("recovery", mutation)
                if mutation == "report":
                    change(root / "report.json", lambda value: value.update(prior_parent_attempts=[]))
                elif mutation == "cost":
                    change(root / "report.json", lambda value: value["cost"].update(environment_requests=2))
                else:
                    prior_path = json.loads((root / "plan.json").read_text())["prior_parent_attempts"][0]["path"]
                    with open(prior_path, "a") as output:
                        output.write("\n")
                with self.assertRaises(ValueError):
                    verify_round(root)

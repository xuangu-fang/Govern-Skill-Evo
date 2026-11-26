"""Offline design checks only; no runtime imports, credentials or model calls."""
from pathlib import Path
import difflib
import hashlib
import json
import re


DESIGN = Path(__file__).resolve().parent
ROOT = DESIGN.parents[2]
MODULES = ("diagnosis", "preconditioner", "editor", "replay")


def read(path):
    return path.read_text(encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paragraph(text, prefix):
    matches = [p for p in text.split("\n\n") if p.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"Expected one paragraph: {prefix}")
    return matches[0]


def span(text, start, end):
    begin = text.index(start)
    return text[begin:text.index(end, begin)]


def main():
    checks = []

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})

    provenance = json.loads(read(DESIGN / "source_map.json"))
    for item in provenance["snapshots"]:
        check(f"snapshot:{item['snapshot']}",
              digest(DESIGN / item["snapshot"]) == item["sha256"])
    for source, expected in provenance["protected_sources"].items():
        check(f"source_unchanged:{source}", digest(ROOT / source) == expected)

    baseline = {m: read(DESIGN / f"baseline/prompts/{m}.md") for m in MODULES}
    prompts = {m: read(DESIGN / f"prompts/{m}.md") for m in MODULES}
    donor = {m: read(DESIGN / f"sources/v28_5_initial/prompts/{m}.md") for m in MODULES}
    changes = json.loads(read(DESIGN / "changes.json"))
    check("unique_change_ids", len({c["id"] for c in changes}) == len(changes) == 15)
    replayed = dict(baseline)
    for change in changes:
        m, before, after = change["module"], change["before"], change["after"]
        check(f"unique_replacement:{change['id']}", replayed[m].count(before) == 1 and before != after)
        replayed[m] = replayed[m].replace(before, after, 1)

    # The initial method design stays reproducible; the later domain-only
    # revision is a separate, explicit replacement layer.
    domain = json.loads(read(DESIGN / "domain_guidance_sources.json"))
    license_info = domain["license"]
    check("skilladam_license_preserved", digest(DESIGN / license_info["snapshot"]) ==
          digest(ROOT / license_info["source"]) == license_info["sha256"])
    for relative, expected in domain["before_snapshot_sha256"].items():
        check(f"domain_before_snapshot:{relative}", digest(DESIGN / relative) == expected)
    for relative, expected in domain["protected_files"].items():
        check(f"domain_frozen_runtime_or_result:{relative}", digest(ROOT / relative) == expected)
    guide_parts = [domain["guide_title"]]
    for item in domain["sections"]:
        source = DESIGN / item["snapshot"]
        check(f"skilladam_source:{item['heading']}",
              digest(source) == digest(ROOT / item["source"]) == item["source_sha256"])
        excerpt = read(source)
        if item["start"] is not None:
            excerpt = span(excerpt, item["start"], item["end"])
        excerpt = excerpt.strip()
        check(f"skilladam_verbatim_excerpt:{item['heading']}",
              hashlib.sha256(excerpt.encode()).hexdigest() == item["excerpt_sha256"])
        guide_parts.extend((item["heading"], excerpt))
    guide = "\n\n".join(guide_parts) + "\n"
    adaptation = domain["environment_adaptation"]
    check("original_domain_guide_exact_source_excerpts",
          read(DESIGN / adaptation["before_guide"]) == guide)
    for relative, expected in adaptation["before_snapshot_sha256"].items():
        check(f"environment_before_snapshot:{relative}", digest(DESIGN / relative) == expected)
    environment_changes = json.loads(read(DESIGN / adaptation["changes"]))
    check("exactly_two_environment_adaptations", [c["id"] for c in environment_changes] ==
          ["ENV_EXECUTION", "ENV_ANSWER_SCOPE"])
    for change in environment_changes:
        check(f"environment_unique_replacement:{change['id']}", guide.count(change["before"]) == 1)
        guide = guide.replace(change["before"], change["after"], 1)
    check("domain_guide_exact_source_plus_adaptations", read(DESIGN / domain["guide"]) == guide)
    block = (domain["guide_markers"]["start"] + "\n" + domain["wrapper"] + guide +
             domain["guide_markers"]["end"] + "\n\n")
    original = dict(replayed)
    trained_prompts = json.loads(read(ROOT /
        "experiments/campaigns/v29_6_docvqa160_20261105_012220/implementation.json"))["prompts"]
    domain_changes = json.loads(read(DESIGN / domain["changes"]))
    check("domain_revision_six_explicit_changes", len(domain_changes) == 6 and
          len({c["id"] for c in domain_changes}) == 6)
    for change in domain_changes:
        m, before, after = change["module"], change["before"], change["after"]
        check(f"unique_replacement:{change['id']}", replayed[m].count(before) == 1 and before != after)
        replayed[m] = replayed[m].replace(before, after, 1)
    for m in MODULES:
        for change in environment_changes:
            check(f"environment_prompt_replacement:{m}:{change['id']}",
                  replayed[m].count(change["before"]) == 1)
            replayed[m] = replayed[m].replace(change["before"], change["after"], 1)
    for m in MODULES:
        check(f"before_revision_matches_trained_prompt:{m}", original[m] == trained_prompts[m])
        check(f"initial_method_design_snapshot:{m}", original[m] ==
              read(DESIGN / domain["original_design"] / f"prompts/{m}.md"))
        check(f"shared_domain_block_exactly_once:{m}", prompts[m].count(block) == 1)
        stripped = prompts[m].replace(block, "", 1)
        expected = original[m]
        if m == "diagnosis":
            for prefix in ("Distinguish discrepancies in answer selection",
                           "Preserve requested field roles, entity, relation"):
                expected = expected.replace(paragraph(expected, prefix) + "\n\n", "", 1)
        check(f"method_text_frozen_outside_domain:{m}", stripped == expected)
        expected_diff = "".join(difflib.unified_diff(
            original[m].splitlines(True), prompts[m].splitlines(True),
            fromfile=f"before/prompts/{m}.md", tofile=f"prompts/{m}.md"))
        check(f"domain_revision_diff:{m}", read(DESIGN /
              f"revisions/docvqa_domain_v1/{m}_from_trained_v29_6.diff") == expected_diff)

    actor_system = read(DESIGN / "baseline/actor/actor_system.md").replace("{skill_section}", "").strip()
    runtime = read(DESIGN / "baseline/actor/actor_runtime.md").strip()
    for m in MODULES:
        text = prompts[m]
        check(f"exact_change_reconstruction:{m}", replayed[m] == text)
        expected_diff = "".join(difflib.unified_diff(
            baseline[m].splitlines(True), text.splitlines(True),
            fromfile=f"baseline/prompts/{m}.md", tofile=f"prompts/{m}.md"))
        check(f"unified_diff:{m}", read(DESIGN / f"diffs/{m}_from_v29_5.diff") == expected_diff)
        check(f"standalone_prompt:{m}", text.startswith(f"# {m.title()}\n")
              and text.endswith("\n") and "<actor_base_protocol>" in text)
        check(f"no_searchqa_or_case_language:{m}",
              re.search(r"\b(?:SearchQA|EM|F1|Brutus)\b", text, re.I) is None)
        block = re.search(r"<actor_base_protocol>\n(.*?)\n</actor_base_protocol>", text, re.S)
        check(f"actor_protocol_unchanged:{m}", block is not None and block[1] == actor_system)
        check(f"actor_runtime_unchanged:{m}", runtime in text)
        if m != "editor":
            check(f"docvqa_boundary_unchanged:{m}",
                  span(text, "## DocVQA execution and text evidence boundary", "## Lossless execution input view"
                       if m != "replay" else "## Agreed Actor protocol and runtime") ==
                  span(baseline[m], "## DocVQA execution and text evidence boundary", "## Lossless execution input view"
                       if m != "replay" else "## Agreed Actor protocol and runtime"))
        else:
            check("editor_evidence_boundary_unchanged",
                  span(text, "## DocVQA editing boundary", "## Input and implementation scope") ==
                  span(baseline[m], "## DocVQA editing boundary", "## Input and implementation scope"))
        examples = re.findall(r"```json\n(.*?)\n```", text, re.S)
        check(f"json_examples_unchanged:{m}", examples == re.findall(r"```json\n(.*?)\n```", baseline[m], re.S)
              and len(examples) == 1)
        for index, example in enumerate(examples):
            check(f"json_example_parse:{m}:{index}", isinstance(json.loads(example), dict))

    for m, start in (("diagnosis", "## Decisions and exact output"),
                     ("preconditioner", "## Full-text decisions and compilation"),
                     ("editor", "## Exact unnumbered patch")):
        check(f"interface_tail_unchanged:{m}", prompts[m][prompts[m].index(start):] ==
              baseline[m][baseline[m].index(start):])
    for m in ("diagnosis", "preconditioner"):
        check(f"execution_view_unchanged:{m}",
              span(prompts[m], "## Lossless execution input view", "## Agreed Actor protocol and runtime") ==
              span(baseline[m], "## Lossless execution input view", "## Agreed Actor protocol and runtime"))
    check("history_view_unchanged",
          span(prompts["preconditioner"], "## Historical Memory by round", "## Frozen proposal and available input") ==
          span(baseline["preconditioner"], "## Historical Memory by round", "## Frozen proposal and available input"))
    check("historical_reasoning_boundaries_unchanged",
          span(prompts["preconditioner"], "## Relate historical edits", "## Decide Direction") ==
          span(baseline["preconditioner"], "## Relate historical edits", "## Decide Direction"))
    check("replay_input_unchanged", span(prompts["replay"], "## Verified current input", "## Relate each hard transition") ==
          span(baseline["replay"], "## Verified current input", "## Relate each hard transition"))
    check("replay_output_shape_unchanged",
          span(prompts["replay"], "## Exact output and fidelity review", "Before finalizing,") ==
          span(baseline["replay"], "## Exact output and fidelity review", "Before finalizing,"))
    check("replay_association_rules_unchanged",
          span(prompts["replay"], "Consider both intended-scope effects", "## Self-contained event Knowledge") ==
          span(baseline["replay"], "Consider both intended-scope effects", "## Self-contained event Knowledge"))

    check("preconditioner_pre_brutus_paragraph_exact",
          paragraph(prompts["preconditioner"], "Review the intended combined behavior") ==
          paragraph(donor["preconditioner"], "Review the intended combined behavior"))
    check("replay_pre_brutus_review_exact_after_hard_adaptation",
          paragraph(prompts["replay"], "Before finalizing, check task coverage") ==
          paragraph(donor["replay"], "Before finalizing, check task coverage").replace("actual EM direction", "actual hard direction"))
    for m, prefix in (("preconditioner", "Review the intended combined behavior"),
                      ("replay", "Before finalizing, check task coverage")):
        diff = read(DESIGN / f"sources/{m}_evidence_consistency.diff")
        newer = next(line[1:] for line in diff.splitlines() if line.startswith("+" + prefix))
        check(f"excluded_later_evidence_paragraph:{m}", newer not in prompts[m])
    expected_editor = span(donor["editor"], "## Input and implementation scope", "## Exact unnumbered patch")
    expected_editor = expected_editor.replace("question/context", "question/image").replace(
        "Preserve unrelated valid guidance.",
        "If an Update calls for new guidance, do not replace it with an unsupported merge merely to avoid adding a rule. Preserve unrelated valid guidance.").replace(
        "Use concise wording and express", "Use concise English wording and express")
    check("editor_first_frozen_design_only", expected_editor ==
          span(prompts["editor"], "## Input and implementation scope", "## Exact unnumbered patch"))
    check("diagnosis_paragraph_style_preserved", paragraph(prompts["diagnosis"], "Use text as one string") ==
          paragraph(baseline["diagnosis"], "Use text as one string"))

    config = json.loads(read(DESIGN / "baseline/v29_5_config.json"))
    check("config_byte_identical", (DESIGN / "baseline/v29_5_config.json").read_bytes() ==
          (ROOT / "experiments/configs/v29_5_docvqa_optimization160.json").read_bytes())
    ids = json.loads(read(DESIGN / "baseline/split_ids.json"))
    manifest = json.loads(read(DESIGN / "baseline/optimization160_manifest.json"))
    flattened = [task for batch in config["batches"] for task in batch]
    check("optimization_ids_and_order", flattened == ids["train"] + ids["val"] == manifest["ids"])
    check("split_counts_disjoint", [len(ids[k]) for k in ("train", "val", "test")] == [107, 53, 374]
          and len(set(flattened)) == 160 and not set(flattened).intersection(ids["test"]))
    check("batch_sizes", [len(b) for b in config["batches"]] == [15] * 10 + [10])
    check("initial_skill_exact", config["initial_skill"] == read(DESIGN / "baseline/actor/initial_skill.md"))
    check("actor_and_module_budgets", config["actor"]["max_tokens"] == 32768 and
          all(c["max_tokens"] == 32768 and c["timeout_seconds"] == 300 for c in config["module_calls"].values()))
    check("retry_and_limits", config["max_attempts"] == config["actor"]["request_attempts_total"] == 6
          and config["actor"]["sdk_retries"] == 0 and config["retry_delay_seconds"] == 2
          and config["actor"]["retry_delay_seconds"] == 1
          and config["max_input_chars"] == 4000000 and config["max_message_utf8_bytes"] == 6000000)
    cli = read(ROOT / "scripts/runs/run_v29_5_campaign.py")
    adapter = read(ROOT / "src/skill_evolution/v29/benchmarks/docvqa/adapter.py")
    check("worker_source_values", "actor.workers = 15" in cli and "self.workers = self.test_workers = 60" in adapter)
    check("baseline_method_exact", config["method"] == provenance["baseline_method"])
    expected = json.loads(json.dumps(config["method"]))
    expected.update(version="v29_6_campaign_v1", stage_contract="v29_6_stages_v1",
                    prompts={m: f"v29_6_docvqa_{m}_v1" for m in MODULES})
    check("only_planned_identity_changes", provenance["planned_method"] == expected)
    if provenance["runtime_binding_created"]:
        check("implementation_identity_matches_design", provenance["executable_config_created"] and
              provenance["bound_method"] == expected and
              provenance["bound_runtime"] == provenance["planned_runtime"] and
              provenance["bound_test_archive"] == provenance["planned_test_archive"])
        runtime_config = json.loads(read(ROOT / provenance["runtime_config"]))
        expected_config = json.loads(json.dumps(config))
        expected_config["method"] = expected
        check("runtime_config_only_changes_identity", runtime_config == expected_config)
        check("runtime_cli_exists", (ROOT / provenance["runtime_cli"]).is_file())
        for m in MODULES:
            check(f"runtime_prompt_matches_design:{m}",
                  (ROOT / provenance["runtime_prompt_paths"][m]).read_bytes() ==
                  (DESIGN / f"prompts/{m}.md").read_bytes())
        check("no_experiment_started", provenance["experiment_started"] is False)
    else:
        check("design_only", provenance["status"] == "design_only_not_bound" and
              not provenance["executable_config_created"])

    documents = list(DESIGN.glob("*.md")) + [DESIGN / "baseline/README.md"]
    for doc in documents:
        for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", read(doc)):
            if "://" in target or target.startswith("#"):
                continue
            destination = (doc.parent / target.split("#", 1)[0]).resolve()
            # This report is produced below, including on the first run.
            check(f"local_link:{doc.relative_to(DESIGN)}:{target}",
                  destination.exists() or destination == DESIGN / "design_validation.json")
    failed = [c["name"] for c in checks if not c["passed"]]
    report = {
        "status": "passed" if not failed else "failed", "date": "2026-11-05",
        "scope": "Offline document/prompt checks; not runtime integration or model evaluation.",
        "checks_total": len(checks), "checks_passed": len(checks) - len(failed),
        "failures": failed, "protected_source_files": len(provenance["protected_sources"]),
        "checks": checks,
        "artifact_sha256": {str(p.relative_to(DESIGN)): digest(p) for p in sorted(DESIGN.rglob("*"))
                            if p.is_file() and p.name != "design_validation.json" and "__pycache__" not in p.parts},
        "model_calls": 0, "runtime_integration_tested": False, "experiment_started": False,
    }
    (DESIGN / "design_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("checks", "artifact_sha256")}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

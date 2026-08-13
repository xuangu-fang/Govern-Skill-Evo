"""Final preflight and immutable freeze record for Autonomous GSE v0.1."""

from __future__ import annotations

import argparse
import copy
import hashlib
import http.client
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAMPAIGN_PATH = (
    REPO_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)
CAMPAIGN_SCHEMA_PATH = (
    REPO_ROOT / "schemas/autonomous_gse_v01_campaign.schema.json"
)
FREEZE_FILENAME = "campaign_freeze.json"
BENCHMARK_ROOT = REPO_ROOT / "external/ST-WebAgentBench"
FORMAL_ROOT = REPO_ROOT / "artifacts/autonomous_gse_v01/formal"
REQUIRED_ENV_KEYS = ("OPENAI_API_KEY", "OPENAI_BASE_URL")


class CampaignPreflightError(ValueError):
    """Raised when the Campaign is not safe to freeze or execute."""


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_artifact(artifact: Any, label: str) -> dict[str, Any]:
    required = {"kind", "version", "path", "sha256"}
    if not isinstance(artifact, dict) or set(artifact) != required:
        raise CampaignPreflightError(f"{label} is not a complete binding.")
    path = _resolve(artifact["path"])
    if not path.is_file():
        raise CampaignPreflightError(f"{label} is missing: {path}")
    actual = _sha256_file(path)
    if actual != artifact["sha256"]:
        raise CampaignPreflightError(
            f"{label} SHA-256 drifted: expected={artifact['sha256']}, "
            f"actual={actual}"
        )
    return copy.deepcopy(artifact)


def _validate_schema(candidate: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        program = (
            "import json,sys; from jsonschema import Draft202012Validator; "
            "schema=json.load(open(sys.argv[1])); "
            "candidate=json.load(open(sys.argv[2])); "
            "errors=list(Draft202012Validator(schema).iter_errors(candidate)); "
            "print(errors[0].message if errors else ''); "
            "raise SystemExit(1 if errors else 0)"
        )
        configured_python = os.environ.get("GSE_SCHEMA_PYTHON")
        if configured_python:
            command = [configured_python]
        else:
            conda = shutil.which("conda")
            if conda is None:
                raise CampaignPreflightError(
                    "Schema validation requires jsonschema in the active "
                    "environment, GSE_SCHEMA_PYTHON, or conda."
                )
            conda_env = os.environ.get("GSE_SCHEMA_CONDA_ENV", "tau2")
            command = [conda, "run", "-n", conda_env, "python"]
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
        ) as candidate_file:
            json.dump(candidate, candidate_file)
            candidate_file.flush()
            result = subprocess.run(
                [
                    *command,
                    "-c",
                    program,
                    str(CAMPAIGN_SCHEMA_PATH),
                    candidate_file.name,
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        if result.returncode != 0:
            message = result.stdout.strip() or result.stderr.strip()
            raise CampaignPreflightError(
                f"Frozen Campaign Schema failed: {message}"
            )
        return
    schema = _load_json(CAMPAIGN_SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(candidate), key=lambda item: list(item.path)
    )
    if errors:
        first = errors[0]
        location = ".".join(map(str, first.absolute_path)) or "<root>"
        raise CampaignPreflightError(
            f"Frozen Campaign Schema failed at {location}: {first.message}"
        )


def _assert_no_formal_artifacts() -> None:
    if FORMAL_ROOT.is_dir() and any(path.is_file() for path in FORMAL_ROOT.rglob("*")):
        raise CampaignPreflightError(
            "Formal Campaign artifacts already exist; refusing a retrospective freeze."
        )


def _read_env_presence() -> dict[str, bool]:
    values = {key: bool(os.environ.get(key)) for key in REQUIRED_ENV_KEYS}
    env_path = BENCHMARK_ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key in values and value.strip():
                values[key] = True
    return values


def _run(
    command: list[str],
    *,
    cwd: Path = REPO_ROOT,
) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        raise CampaignPreflightError(
            f"Preflight command failed: {command[0]}: {detail}"
        ) from error
    return result.stdout.strip()


def probe_environment(campaign: dict[str, Any]) -> dict[str, Any]:
    """Validate the actual local runtime without exposing credential values."""

    presence = _read_env_presence()
    missing = [key for key, available in presence.items() if not available]
    if missing:
        raise CampaignPreflightError(
            f"Missing formal Learner configuration: {missing}"
        )

    sys.path.insert(0, str(BENCHMARK_ROOT))
    try:
        for module in (
            "dotenv",
            "gymnasium",
            "openai",
            "browsergym.stwebagentbench",
        ):
            importlib.import_module(module)
    finally:
        if sys.path[0] == str(BENCHMARK_ROOT):
            sys.path.pop(0)

    benchmark_commit = _run(
        ["git", "-C", str(BENCHMARK_ROOT), "rev-parse", "HEAD"]
    )
    expected_commit = campaign["benchmark_runtime"]["benchmark"]["commit"]
    if benchmark_commit != expected_commit:
        raise CampaignPreflightError("ST-WebAgentBench commit drifted.")

    docker_server = _run(["docker", "info", "--format", "{{.ServerVersion}}"])
    compose_path = _resolve(
        campaign["benchmark_runtime"]["compose_file"]["path"]
    )
    images = _run(
        ["docker", "compose", "-f", str(compose_path), "config", "--images"]
    ).splitlines()
    if not images:
        raise CampaignPreflightError("SuiteCRM compose resolves no images.")
    image_ids = {
        image: _run(["docker", "image", "inspect", image, "--format", "{{.Id}}"])
        for image in images
    }

    reset_path = _resolve(campaign["benchmark_runtime"]["database_reset"]["path"])
    _run([str(reset_path)])
    try:
        connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=10)
        connection.request("GET", "/public")
        response = connection.getresponse()
        suitecrm_status = response.status
        response.read()
        connection.close()
    except Exception as error:
        raise CampaignPreflightError("SuiteCRM readiness check failed.") from error
    if not 200 <= suitecrm_status < 400:
        raise CampaignPreflightError(
            f"SuiteCRM readiness returned HTTP {suitecrm_status}."
        )

    return {
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
        },
        "required_modules": "passed",
        "learner_configuration_present": sorted(REQUIRED_ENV_KEYS),
        "benchmark_commit": benchmark_commit,
        "docker_server_version": docker_server,
        "compose_images": image_ids,
        "suitecrm_readiness": {
            "url": "http://127.0.0.1:8080/public",
            "http_status": suitecrm_status,
            "database_reset": "passed",
            "expected_active_counts": {
                "contacts": 10,
                "accounts": 9,
                "leads": 10,
            },
        },
    }


EnvironmentProbe = Callable[[dict[str, Any]], dict[str, Any]]


def run_preflight(
    campaign_path: Path,
    *,
    environment_probe: EnvironmentProbe = probe_environment,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the final Manifest candidate and complete preflight evidence."""

    campaign_path = campaign_path.resolve()
    campaign = _load_json(campaign_path)
    if campaign.get("status") != "draft":
        raise CampaignPreflightError("Only a draft Campaign can be frozen.")
    if campaign.get("campaign_id") != "autonomous_gse_v01":
        raise CampaignPreflightError("Unexpected Campaign identity.")
    if any(
        binding.get("status") == "pending_binding"
        for binding in campaign.get("implementation_bindings", {}).values()
        if isinstance(binding, dict)
    ):
        raise CampaignPreflightError("Campaign still has pending bindings.")
    _assert_no_formal_artifacts()

    final_manifest = copy.deepcopy(campaign)
    final_manifest["status"] = "frozen"
    final_manifest["frozen_at"] = datetime.now(timezone.utc).isoformat()
    _validate_schema(final_manifest)

    from src.skill_evolution.autonomous_gse_benchmark_runtime import (
        build_formal_execution_plan,
        frozen_prompt_hashes,
        validate_formal_campaign_contract,
    )

    validate_formal_campaign_contract(final_manifest, require_frozen=False)
    if final_manifest["proposal"]["learner"][
        "prompt_template_sha256"
    ] != frozen_prompt_hashes():
        raise CampaignPreflightError("Prompt semantic hash drifted.")

    immutable_inputs = {
        "initial_parent": _check_artifact(
            final_manifest["initial_parent"], "initial_parent"
        ),
        "source_manifest": _check_artifact(
            final_manifest["train"]["source_manifest"], "source_manifest"
        ),
        "batch_map": _check_artifact(
            final_manifest["train"]["batch_map"], "batch_map"
        ),
        "database_snapshot": _check_artifact(
            final_manifest["benchmark_runtime"]["database_snapshot"],
            "database_snapshot",
        ),
        "database_reset": _check_artifact(
            final_manifest["benchmark_runtime"]["database_reset"],
            "database_reset",
        ),
        "compose_file": _check_artifact(
            final_manifest["benchmark_runtime"]["compose_file"],
            "compose_file",
        ),
    }
    implementations = {
        name: _check_artifact(binding, f"implementation.{name}")
        for name, binding in final_manifest["implementation_bindings"].items()
    }
    batch_map = _load_json(_resolve(immutable_inputs["batch_map"]["path"]))
    plan = build_formal_execution_plan(final_manifest, batch_map)
    if (
        len(plan["initial_selection_task_ids"]) != 18
        or [len(step["train_task_ids"]) for step in plan["steps"]]
        != [17, 17, 17]
        or plan["maximum_budget"]["maximum_total_trajectories"] != 123
        or plan["test_authorized"] is not False
    ):
        raise CampaignPreflightError("Formal execution plan drifted.")

    environment = environment_probe(copy.deepcopy(final_manifest))
    evidence = {
        "schema_validation": "passed",
        "artifact_integrity": "passed",
        "prompt_semantics": "passed",
        "formal_artifacts_absent_before_freeze": True,
        "budget_and_batch_plan": {
            "initial_selection": 18,
            "train_batches": [17, 17, 17],
            "maximum_candidate_selection": [18, 18, 18],
            "maximum_total_trajectories": 123,
            "maximum_learner_calls": 3,
        },
        "test_lock": {
            "authorized": False,
            "data_for_learning": "forbidden",
        },
        "immutable_inputs": immutable_inputs,
        "implementation_bindings": implementations,
        "environment": environment,
    }
    return final_manifest, evidence


def build_freeze_record(
    campaign_path: Path,
    final_manifest: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    manifest_bytes = _canonical_json_bytes(final_manifest)
    return {
        "schema_version": "autonomous_gse_campaign_freeze_0.1.0",
        "status": "frozen_for_formal_execution",
        "frozen_at": final_manifest["frozen_at"],
        "campaign": {
            "campaign_id": final_manifest["campaign_id"],
            "path": campaign_path.resolve().relative_to(REPO_ROOT).as_posix(),
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        },
        "preflight": copy.deepcopy(preflight),
        "change_policy": {
            "manifest_must_not_change": True,
            "freeze_record_must_not_be_overwritten": True,
            "formal_artifacts_existed_before_freeze": False,
            "semantic_changes_require_new_campaign_version": True,
            "test_execution_authorized": False,
        },
    }


def _write_once(path: Path, content: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite immutable freeze: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def freeze_campaign(
    campaign_path: Path,
    *,
    environment_probe: EnvironmentProbe = probe_environment,
) -> dict[str, Any]:
    """Pass preflight, write the freeze record, then atomically freeze Manifest."""

    campaign_path = campaign_path.resolve()
    freeze_path = campaign_path.with_name(FREEZE_FILENAME)
    if freeze_path.exists():
        raise FileExistsError(f"Campaign freeze already exists: {freeze_path}")
    final_manifest, preflight = run_preflight(
        campaign_path, environment_probe=environment_probe
    )
    record = build_freeze_record(campaign_path, final_manifest, preflight)
    manifest_bytes = _canonical_json_bytes(final_manifest)
    record_bytes = _canonical_json_bytes(record)
    if hashlib.sha256(manifest_bytes).hexdigest() != record["campaign"]["sha256"]:
        raise CampaignPreflightError("Freeze record Manifest hash is inconsistent.")

    _write_once(freeze_path, record_bytes)
    temporary = campaign_path.with_name(f".{campaign_path.name}.tmp")
    temporary.write_bytes(manifest_bytes)
    os.replace(temporary, campaign_path)
    return record


def require_campaign_freeze(
    campaign_path: Path,
    campaign: dict[str, Any],
) -> dict[str, Any]:
    """Verify the one-way immutable freeze before any formal side effect."""

    if campaign.get("status") != "frozen":
        raise CampaignPreflightError("Campaign is not frozen.")
    freeze_path = campaign_path.resolve().with_name(FREEZE_FILENAME)
    if not freeze_path.is_file():
        raise CampaignPreflightError("Campaign freeze record is missing.")
    record = _load_json(freeze_path)
    if record.get("status") != "frozen_for_formal_execution":
        raise CampaignPreflightError("Campaign freeze status is invalid.")
    expected_path = campaign_path.resolve().relative_to(REPO_ROOT).as_posix()
    if record.get("campaign", {}).get("path") != expected_path:
        raise CampaignPreflightError("Campaign freeze references another Manifest.")
    if record["campaign"].get("sha256") != _sha256_file(campaign_path.resolve()):
        raise CampaignPreflightError("Frozen Campaign Manifest hash drifted.")
    if record.get("preflight", {}).get("test_lock") != {
        "authorized": False,
        "data_for_learning": "forbidden",
    }:
        raise CampaignPreflightError("Frozen Test lock is invalid.")
    for binding in record["preflight"]["immutable_inputs"].values():
        _check_artifact(binding, "frozen immutable input")
    for binding in record["preflight"]["implementation_bindings"].values():
        _check_artifact(binding, "frozen implementation")
    for image, expected_id in record["preflight"]["environment"][
        "compose_images"
    ].items():
        actual_id = _run(
            ["docker", "image", "inspect", image, "--format", "{{.Id}}"]
        )
        if actual_id != expected_id:
            raise CampaignPreflightError(
                f"Frozen container image drifted: {image}"
            )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run final preflight and freeze Autonomous GSE v0.1."
    )
    parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN_PATH)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run all checks but do not write or freeze artifacts.",
    )
    args = parser.parse_args()
    if args.preflight_only:
        final_manifest, preflight = run_preflight(args.campaign)
        print(
            json.dumps(
                {
                    "status": "PREFLIGHT_PASSED",
                    "campaign_id": final_manifest["campaign_id"],
                    "preflight": preflight,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    record = freeze_campaign(args.campaign)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

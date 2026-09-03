"""Compile audited Realized Scenarios into executable upstream tau2 Tasks."""

from __future__ import annotations

from hashlib import sha256
from typing import Iterable

from ..boundary.latent.schema import LatentPair, LatentWorld
from ..realization.schema import RealizedScenario
from .materializer import materialize_task_inputs
from .resolvers import ensure_tau2_importable, load_boundary_template
from .schema import CompiledTaskBundle, CompilationAuditResult

ensure_tau2_importable()

from tau2.data_model.tasks import (  # noqa: E402
    Description,
    EvaluationCriteria,
    StructuredUserInstructions,
    Task,
    UserScenario,
)


def _task_id(scenario_id: str, seed: int) -> str:
    digest = sha256(f"{scenario_id}|{seed}|tau2-task-compiler-v1".encode()).hexdigest()
    return f"gse_air_{digest[:12]}"


def _join_lines(values: list[str]) -> str | None:
    return "\n\n".join(values) if values else None


def compile_realized_scenario(
    scenario: RealizedScenario,
    latent_world: LatentWorld,
    latent_pair: LatentPair,
    seed: int | None = None,
) -> CompiledTaskBundle:
    """Compile one audited scenario using its matching latent world and pair."""

    if not scenario.audit_result.passed:
        raise ValueError("Realized Scenario must pass audit before compilation")
    if not latent_pair.audit_result.passed:
        raise ValueError("Latent Pair must pass audit before compilation")

    effective_seed = 0 if seed is None else seed
    task_id = _task_id(scenario.scenario_id, effective_seed)
    template = load_boundary_template(scenario.template_id)
    inputs = materialize_task_inputs(scenario, latent_world, task_id)

    task = Task(
        id=task_id,
        description=Description(
            purpose=(
                "Evaluate correct outcome handling for a policy-sensitive airline "
                "request in an ordinary customer interaction."
            ),
            relevant_policies=None,
            notes=None,
        ),
        user_scenario=UserScenario(
            persona=scenario.persona_description,
            instructions=StructuredUserInstructions(
                domain="airline",
                reason_for_call=scenario.user_goal,
                known_info=_join_lines(
                    scenario.known_information
                    + inputs.known_information
                    + scenario.secondary_context
                ),
                unknown_info=None,
                task_instructions=_join_lines(
                    scenario.interaction_instructions
                    + inputs.interaction_instructions
                )
                or "Follow the stated request.",
            ),
        ),
        initial_state=inputs.initial_state,
        evaluation_criteria=EvaluationCriteria(
            actions=inputs.actions,
            communicate_info=inputs.communicate_info,
            nl_assertions=None,
            reward_basis=inputs.reward_basis,
        ),
    )

    hidden_metadata = {
        "task_id": task_id,
        "scenario_id": scenario.scenario_id,
        "manifestation_id": scenario.manifestation_id,
        "latent_pair_id": latent_pair.latent_pair_id,
        "latent_world_id": latent_world.world_id,
        "template_id": scenario.template_id,
        "concept_id": scenario.concept_id,
        "rule_id": scenario.rule_id,
        "predicate_name": scenario.predicate_name,
        "predicate_value": scenario.predicate_value,
        "expected_governance": scenario.expected_governance,
        "expected_resolution": scenario.expected_resolution,
        "boundary_predicate": template["policy_predicate"]["name"],
        "concrete_context": inputs.concrete_context,
        "canonical_response": inputs.canonical_response,
        "compiler": "tau2_task_compiler_mvp_v1",
        "seed": effective_seed,
    }
    bundle = CompiledTaskBundle(
        compiled_task_id=task_id,
        scenario_id=scenario.scenario_id,
        manifestation_id=scenario.manifestation_id,
        latent_pair_id=latent_pair.latent_pair_id,
        latent_world_id=latent_world.world_id,
        template_id=scenario.template_id,
        concept_id=scenario.concept_id,
        rule_id=scenario.rule_id,
        task=task,
        expected_governance=scenario.expected_governance,
        expected_resolution=scenario.expected_resolution,
        hidden_metadata=hidden_metadata,
        compilation_audit=CompilationAuditResult(
            passed=False,
            schema_valid=False,
            provenance_preserved=False,
            predicate_materialized=False,
            user_goal_preserved=False,
            no_extra_policy_blocker=False,
            expected_resolution_consistent=False,
            environment_loadable=False,
            gold_satisfiable=False,
            violations=[],
            notes=["Audit not run."],
        ),
    )

    from .validation import validate_compiled_task

    bundle.compilation_audit = validate_compiled_task(
        bundle, scenario, latent_world, latent_pair
    )
    if not bundle.compilation_audit.passed:
        raise RuntimeError(
            f"Compiled task failed validation: {bundle.compilation_audit.violations}"
        )
    return bundle


def compile_realized_scenarios(
    scenarios: Iterable[RealizedScenario],
    latent_pairs: Iterable[LatentPair],
    seed: int | None = None,
) -> list[CompiledTaskBundle]:
    """Compile scenarios by resolving their source worlds from audited pairs."""

    pair_by_id = {pair.latent_pair_id: pair for pair in latent_pairs}
    bundles: list[CompiledTaskBundle] = []
    for scenario in scenarios:
        try:
            pair = pair_by_id[scenario.latent_pair_id]
        except KeyError as exc:
            raise ValueError(
                f"No Latent Pair found for scenario {scenario.scenario_id}"
            ) from exc
        worlds = {pair.world_a.world_id: pair.world_a, pair.world_b.world_id: pair.world_b}
        try:
            world = worlds[scenario.latent_world_id]
        except KeyError as exc:
            raise ValueError(
                f"No Latent World found for scenario {scenario.scenario_id}"
            ) from exc
        bundles.append(
            compile_realized_scenario(scenario, world, pair, seed=seed)
        )

    ids = [bundle.task.id for bundle in bundles]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Compiled Task IDs are not unique")
    return bundles

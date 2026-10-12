"""Environment entry points for the integrated pre-ID workspace."""

from tau2.registry import Registry, registry

from src.benchmark_v3.development.unified_environment.retail import get_environment as get_retail_environment
from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import get_environment as get_base_airline_environment
from src.benchmark_v3.construction.integrated_pre_id_realization.joint_candidates.fixture import build_joint_db


def get_airline_environment():
    """Build the shared Airline environment including selected Joint fixtures."""
    return get_base_airline_environment(db=build_joint_db())


ENVIRONMENT_BUILDERS = {
    "airline": get_airline_environment,
    "retail": get_retail_environment,
}
AIRLINE_DOMAIN_NAME = "airline-final-candidate-construction"


def get_environment(domain: str):
    """Build one of the two shared-domain environments."""
    try:
        builder = ENVIRONMENT_BUILDERS[domain]
    except KeyError as exc:
        raise ValueError(f"Unknown integrated domain: {domain}") from exc
    return builder()


def register_airline_domain(target: Registry = registry) -> None:
    """Register the integrated Airline builder for behavioral construction runs."""
    if AIRLINE_DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_airline_environment, AIRLINE_DOMAIN_NAME)

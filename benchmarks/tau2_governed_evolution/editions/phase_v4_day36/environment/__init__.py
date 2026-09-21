"""Register benchmark v3 environments and the benchmark v4 joint environment."""

from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.environment import register_domains as register_v3_domains
from .joint_airline import register_domain as register_joint_domain


def register_domains() -> None:
    register_v3_domains()
    register_joint_domain()


__all__ = ["register_domains", "register_joint_domain"]

"""Register benchmark v3 environments and the benchmark v4 joint environment."""

from src.benchmark_v3.final.environment import register_domains as register_v3_domains
from src.benchmark_v4.environment.joint_airline import register_domain as register_joint_domain


def register_domains() -> None:
    register_v3_domains()
    register_joint_domain()


__all__ = ["register_domains", "register_joint_domain"]

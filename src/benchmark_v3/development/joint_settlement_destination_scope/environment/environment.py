"""Process-local JSG-01 environment with full destination policy visibility."""

from typing import Optional

from tau2.domains.airline.utils import AIRLINE_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from src.benchmark_v3.development.latent_settlement_contract.environment.data_model import SettlementFlightDB
from src.benchmark_v3.development.latent_settlement_contract.environment.environment import NATIVE_SETTLEMENT_STATEMENT, POLICY_EXTENSION, V3_NEUTRAL_SETTLEMENT_STATEMENT
from src.benchmark_v3.development.latent_settlement_contract.environment.tools import SettlementAirlineTools

from src.benchmark_v3.development.joint_settlement_destination_scope.environment.fixture import build_core_db


DOMAIN_NAME = "airline-v3-joint-settlement-destination-scope"
DESTINATION_POLICY_STATEMENT = (
    "- Other reservations can be modified without changing the origin, destination, and trip type."
)


def get_environment(
    db: Optional[SettlementFlightDB] = None, solo_mode: bool = False
) -> Environment:
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    native_policy = AIRLINE_POLICY_PATH.read_text(encoding="utf-8")
    if native_policy.count(NATIVE_SETTLEMENT_STATEMENT) != 1:
        raise ValueError("expected one native retained-segment settlement statement")
    if native_policy.count(DESTINATION_POLICY_STATEMENT) != 1:
        raise ValueError("expected destination-preservation policy statement")
    policy = native_policy.replace(
        NATIVE_SETTLEMENT_STATEMENT, V3_NEUTRAL_SETTLEMENT_STATEMENT
    ) + POLICY_EXTENSION
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=policy,
        tools=SettlementAirlineTools(db or build_core_db()),
    )


def register_domain(target: Registry = registry) -> None:
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)

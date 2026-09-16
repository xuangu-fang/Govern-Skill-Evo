"""Evaluator-only Governance state added to the v3 Airline DB."""

from pydantic import BaseModel, Field

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.latent_settlement_contract.environment.data_model import (
    SettlementFlightDB,
)


class UnifiedAirlineGovernanceContract(BaseModel):
    current_time: str = "2024-05-15T15:00:00"
    max_passengers_per_reservation: int = Field(default=5, ge=1)
    membership_offset: dict[str, int] = {
        "regular": 0,
        "silver": 1,
        "gold": 2,
    }
    cabin_offset: dict[str, int] = {
        "basic_economy": 0,
        "economy": 1,
        "business": 2,
    }

    def free_bags_per_passenger(self, membership: str, cabin: str) -> int:
        return self.membership_offset[membership] + self.cabin_offset[cabin]


class FinalCandidateAirlineDB(SettlementFlightDB):
    """Settlement state plus one domain-wide, evaluator-only G contract."""

    governance_contract: UnifiedAirlineGovernanceContract

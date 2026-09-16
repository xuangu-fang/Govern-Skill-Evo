"""Common Airline tools; no Governance-specific public tool is added."""

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.latent_settlement_contract.environment.tools import (
    SettlementAirlineTools,
)

from .data_model import FinalCandidateAirlineDB


class FinalCandidateAirlineTools(SettlementAirlineTools):
    db: FinalCandidateAirlineDB

    def __init__(self, db: FinalCandidateAirlineDB) -> None:
        super().__init__(db)

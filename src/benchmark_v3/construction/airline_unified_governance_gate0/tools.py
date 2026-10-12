"""Common Airline tools; no Governance-specific public tool is added."""

from src.benchmark_v3.development.latent_settlement_contract.environment.tools import SettlementAirlineTools

from src.benchmark_v3.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB


class FinalCandidateAirlineTools(SettlementAirlineTools):
    db: FinalCandidateAirlineDB

    def __init__(self, db: FinalCandidateAirlineDB) -> None:
        super().__init__(db)

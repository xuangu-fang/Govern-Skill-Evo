"""V3-only state for the EE-01 settlement-contract prototype."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from tau2.domains.airline.data_model import FlightDB


SettlementBaseline = Literal["retained_historical", "complete_current"]


class SettlementContractState(BaseModel):
    """Per-reservation contract state; only selected fields are agent-visible."""

    ticketing_channel: str = Field(description="Visible ticketing channel")
    remaining_changes: int = Field(description="Visible number of flight changes left")
    settlement_baseline: SettlementBaseline = Field(
        description="Hidden channel-to-settlement mapping"
    )
    last_settlement_total: Optional[int] = None
    last_change_amount: Optional[int] = None


class SettlementFlightDB(FlightDB):
    """Native Airline DB plus isolated EE-01 sidecar state."""

    settlement_contracts: dict[str, SettlementContractState]

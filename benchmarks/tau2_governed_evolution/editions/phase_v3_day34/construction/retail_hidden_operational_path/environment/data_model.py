"""RHP-01 sidecar state layered on the native Retail database."""

from typing import Dict, Literal, Optional

from pydantic import BaseModel
from tau2.domains.retail.data_model import RetailDB


class ResolutionContract(BaseModel):
    fulfillment_mode: Literal["consolidated", "partner_direct"]
    exchange_protection_behavior: Literal["preserve", "forfeit"]
    purchase_protection_status: Literal["active", "forfeited", "closed_by_return"]
    last_resolution: Optional[Literal["exchange", "return"]] = None


class ResolutionRetailDB(RetailDB):
    resolution_contracts: Dict[str, ResolutionContract]

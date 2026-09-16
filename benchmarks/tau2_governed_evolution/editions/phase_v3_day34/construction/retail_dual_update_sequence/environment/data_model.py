"""RDS-01 workflow state layered on the native Retail database."""

from typing import Dict, List, Literal

from pydantic import BaseModel, Field
from tau2.domains.retail.data_model import RetailDB


UpdateKind = Literal["address", "payment"]


class DualUpdateContract(BaseModel):
    workflow_revision: Literal["R1", "R2"]
    required_sequence: List[UpdateKind]
    completed_updates: List[UpdateKind] = Field(default_factory=list)
    workflow_locked: bool = False


class DualUpdateRetailDB(RetailDB):
    dual_update_contracts: Dict[str, DualUpdateContract]

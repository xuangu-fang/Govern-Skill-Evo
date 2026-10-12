"""RAP-01 address-propagation state layered on the native Retail database."""

from typing import Dict, List, Literal

from pydantic import BaseModel, Field
from tau2.domains.retail.data_model import RetailDB


AddressTarget = Literal["order", "profile"]


class AddressPropagationContract(BaseModel):
    address_contract: Literal["cedar", "orbit"]
    propagation_source: AddressTarget
    written_targets: List[AddressTarget] = Field(default_factory=list)
    session_closed: bool = False


class AddressPropagationRetailDB(RetailDB):
    address_propagation_contracts: Dict[str, AddressPropagationContract]

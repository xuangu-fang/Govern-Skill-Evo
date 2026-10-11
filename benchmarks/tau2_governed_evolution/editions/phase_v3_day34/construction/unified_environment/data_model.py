"""Union of the two v3 Retail sidecar states."""

from typing import Dict

from tau2.domains.retail.data_model import RetailDB

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.environment.data_model import AddressPropagationContract
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.environment.data_model import ResolutionContract


class UnifiedRetailDB(RetailDB):
    resolution_contracts: Dict[str, ResolutionContract]
    address_propagation_contracts: Dict[str, AddressPropagationContract]

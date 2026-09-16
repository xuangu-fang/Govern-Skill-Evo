"""One Retail toolkit exposing both v3 latent-mechanism surfaces."""

from tau2.domains.retail.tools import RetailTools

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.environment.tools import AddressPropagationRetailTools
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.environment.tools import ResolutionRetailTools

from .data_model import UnifiedRetailDB


class UnifiedRetailTools(ResolutionRetailTools, AddressPropagationRetailTools):
    db: UnifiedRetailDB

    def __init__(self, db: UnifiedRetailDB) -> None:
        RetailTools.__init__(self, db)

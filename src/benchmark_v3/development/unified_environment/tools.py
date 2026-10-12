"""One Retail toolkit exposing both v3 latent-mechanism surfaces."""

from tau2.domains.retail.tools import RetailTools

from src.benchmark_v3.development.retail_address_propagation.environment.tools import AddressPropagationRetailTools
from src.benchmark_v3.development.retail_hidden_operational_path.environment.tools import ResolutionRetailTools

from src.benchmark_v3.development.unified_environment.data_model import UnifiedRetailDB


class UnifiedRetailTools(ResolutionRetailTools, AddressPropagationRetailTools):
    db: UnifiedRetailDB

    def __init__(self, db: UnifiedRetailDB) -> None:
        RetailTools.__init__(self, db)

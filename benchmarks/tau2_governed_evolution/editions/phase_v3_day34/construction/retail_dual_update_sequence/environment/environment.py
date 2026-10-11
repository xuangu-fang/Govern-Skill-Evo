"""Process-local Retail environment factory for RDS-01."""

from typing import Optional

from tau2.domains.retail.utils import RETAIL_POLICY_PATH
from tau2.environment.environment import Environment
from tau2.registry import Registry, registry

from .data_model import DualUpdateRetailDB
from .fixture import build_gate0_db
from .tools import DualUpdateRetailTools


DOMAIN_NAME = "retail-v3-dual-update-sequence"
POLICY_EXTENSION = """

## V3 dual-update workflow extension

Some pending orders expose a workflow revision. When the same request requires
both a shipping-address update and a payment-method update, call
get_dual_update_context before the first write. Both updates remain ordinary
Retail modifications, but their required order is revision-specific and is not
specified here. A successful incompatible first write locks the remaining
workflow and cannot be rolled back. The ordinary authentication and explicit
confirmation rules still apply.
"""


def get_environment(
    db: Optional[DualUpdateRetailDB] = None, solo_mode: bool = False
) -> Environment:
    if solo_mode:
        raise ValueError("Retail domain does not support solo mode")
    effective_db = db or build_gate0_db()
    policy = RETAIL_POLICY_PATH.read_text(encoding="utf-8") + POLICY_EXTENSION
    return Environment(
        domain_name=DOMAIN_NAME,
        policy=policy,
        tools=DualUpdateRetailTools(effective_db),
    )


def register_domain(target: Registry = registry) -> None:
    if DOMAIN_NAME not in target.get_info().domains:
        target.register_domain(get_environment, DOMAIN_NAME)

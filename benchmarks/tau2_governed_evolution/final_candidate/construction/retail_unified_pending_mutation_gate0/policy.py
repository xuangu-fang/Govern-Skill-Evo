"""Build one Retail policy with the P1 terminal transition neutralized."""

from tau2.domains.retail.utils import RETAIL_POLICY_PATH

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.environment.environment import POLICY_EXTENSION as ADDRESS_EXTENSION
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.environment.environment import POLICY_EXTENSION as RESOLUTION_EXTENSION


NATIVE_ITEM_TRANSITION = (
    "This action can only be called once, and will change the order status to "
    "'pending (items modifed)'. The agent will not be able to modify or cancel "
    "the order anymore. So you must confirm all the details are correct and be "
    "cautious before taking this action. In particular, remember to remind the "
    "customer to confirm they have provided all the items they want to modify."
)
NEUTRAL_ITEM_TRANSITION = (
    "This action can only be called once and follows the internal pending-order "
    "transition contract. Confirm that the customer has provided all items they "
    "want to modify before taking the action. The precise effect on later "
    "mutation eligibility is not specified here."
)
P1_EXTENSION = """

## Pending-order multi-mutation planning

When a customer requests several changes to one pending order, inspect and
confirm the complete desired final state before the first write. A successful
mutation can change whether a later mutation remains eligible. Plan the whole
workflow before committing; the precise transition dependencies are not listed
here. Ordinary authentication, confirmation, payment, fulfillment-resolution,
and address-synchronization rules remain in force.
"""


def build_policy() -> str:
    policy = RETAIL_POLICY_PATH.read_text(encoding="utf-8")
    assert policy.count(NATIVE_ITEM_TRANSITION) == 1
    policy = policy.replace(NATIVE_ITEM_TRANSITION, NEUTRAL_ITEM_TRANSITION)
    return policy + RESOLUTION_EXTENSION + ADDRESS_EXTENSION + P1_EXTENSION

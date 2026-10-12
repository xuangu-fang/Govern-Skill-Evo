"""Host construction and agent-visible session facade. No old benchmark imports."""
from copy import deepcopy
from .core import load_scenario
from .retail import S2, K2
from .refund import G2
from .airline import I1

REGISTRY = {"S2": S2, "G2": G2, "I1": I1, "K2": K2}


def build(name, scenario=None):
    config = load_scenario(name) if scenario is None else deepcopy(scenario)
    if config["id"] != name or config["split"] != "dev":
        raise ValueError("Only named v5 Dev prototypes are supported")
    return REGISTRY[name](config)


class AgentSession:
    """In-process adapter for trusted reference scripts; CLI provides the process boundary.

    This is not a security sandbox for arbitrary Python code. Model agents receive
    only JSON request/catalog/responses, never this host object's audit accessor.
    """
    def __init__(self, environment):
        self.__environment = environment
        self.request = deepcopy(environment.request())
        self.tools = deepcopy(environment.catalog())

    def call(self, name, **arguments):
        return self.__environment.call(name, arguments)

"""OfficeQA v26.3 uses the v26.2 schedule, contracts, and campaign engine."""
from .. import v26_2

# Resolve inherited modules' relative imports against this version's bindings.
__path__.extend(v26_2.__path__)

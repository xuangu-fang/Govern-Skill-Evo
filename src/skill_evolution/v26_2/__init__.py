"""OfficeQA v26.2 overrides the schedule and Preconditioner of v26.1."""
from .. import v26_1

# Inherited modules use relative imports. Loading them in this namespace binds
# the same campaign, journal and evaluation code to the v26.2 configuration.
__path__.extend(v26_1.__path__)

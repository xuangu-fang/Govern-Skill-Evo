"""Default entrypoint for NEW experience-grounded experiments; legacy stays frozen."""
from .autonomous_gse_v15_benchmark_runtime import (
    bind_visible_context, prepare_diagnosis, propose_from_experience,
    LEARNER_SETTING, INFORMATION_BOUNDARY_VERSION,
)

__all__ = ['bind_visible_context','prepare_diagnosis','propose_from_experience',
           'LEARNER_SETTING','INFORMATION_BOUNDARY_VERSION']

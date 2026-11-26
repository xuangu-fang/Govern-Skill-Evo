"""Bind the prepared files to the unchanged native SkillAdam implementation.

No CLI, credential loading, model construction or training at import time.
The caller must explicitly inject a generation transport when later authorized.
"""
import json
from pathlib import Path

from ..layout import ALIGNED_CONFIG, read_actor_config
from .bridge import spreadsheetbench_native_optimizer as native

HOME = ALIGNED_CONFIG


def components():
    bridge = native.load_bridge(HOME)
    shared = read_actor_config(HOME/'shared_config.json')
    optimizer = json.loads((HOME/'skilladam.json').read_text())
    native.validate(bridge,shared,optimizer)
    return native,bridge,shared,optimizer


def make_runner(output, *, optimizer):
    """Construction only; an explicit runner.run call would start training."""
    if optimizer is None:
        raise ValueError('Explicit native generation transport required')
    native,bridge,shared,cfg = components()
    backend = native.backend_type(bridge)(shared,cfg,output,optimizer=optimizer)
    return bridge.AlignedRunner(config=bridge.native_config(cfg),adapter=bridge.AlignedAdapter(HOME),
        backend=backend,context=bridge.context_for(shared,cfg),output_dir=Path(output))

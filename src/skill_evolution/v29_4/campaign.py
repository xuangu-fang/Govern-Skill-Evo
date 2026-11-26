"""v29.4 binding: reuse the frozen Actor, not the v29.1 evolution engine."""
from pathlib import Path

from src.skill_evolution.v29.campaign import CampaignAdapter as ActorCampaignAdapter
from .config import METHOD_VERSION
from src.skill_evolution.v29_2 import actor_io, explicit_references, execution_references, replay_input_view
from src.skill_evolution.v29.benchmarks.docvqa import protocol


DEFAULT_CONFIG = protocol.ROOT / 'experiments/configs/v29_4_docvqa_optimization160.json'
RUNTIME_VERSION = 'v29_4_light_runtime_v1'


class CampaignAdapter(ActorCampaignAdapter):
    method_version = METHOD_VERSION

    def actor_batch(self, tasks, skill_file, directory, config):
        return actor_io.actor_batch(self.actor_adapter, tasks, skill_file, directory, config)

    def validation_sources(self):
        root = Path(__file__).resolve().parent
        reused = {Path(module.__file__).resolve() for module in
                  (actor_io, explicit_references, execution_references, replay_input_view)}
        prompt_root = root.parent / 'v29_2/prompts'
        return (super().validation_sources() | set(root.glob('*.py')) | reused |
                set((root / 'prompts').glob('*.md')) |
                {prompt_root / 'editor.md', prompt_root / 'replay.md',
                 root.parents[2] / 'scripts/runs/run_v29_4_campaign.py'})

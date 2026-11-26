"""Bound SearchQA runtime for campaign functions; no implicit transports."""
from pathlib import Path
import sys

from .method import SearchQAMethod
from .benchmarks.searchqa import protocol as p


class CampaignAdapter(SearchQAMethod):
    identity = 'v28_searchqa_v1'
    gate_metric = p.GATE_PROFILE

    def __init__(self, actor_adapter):
        super().__init__(actor_adapter, archives=[])

    def _bound(self):
        self.actor_adapter._preflight()

    def actor_batch(self, *args, **kwargs):
        if self.actor_adapter.transport is None:
            # Restore downstream batch/trajectory files only after every Actor
            # result is independently complete. Never allocate a new request.
            from .benchmarks.searchqa import actor
            from .benchmarks.searchqa.adapter import SearchQAActorAdapter
            tasks, skill_file, directory, config = args
            skill = None if skill_file is None else Path(skill_file).read_bytes().decode('utf-8')
            for task in tasks:
                actor.read_completed(self.dataset.case(task), skill,
                                     Path(directory)/'actor'/self.actor_adapter.task_key(task),
                                     self.actor_adapter._actor, verify_hashes=self.actor_adapter.verify_hashes)
            actor_config = self.actor_adapter._actor
            class ArchiveOnly:
                def metadata(self):
                    return p.background(actor_config)
                def __call__(self, *args):
                    raise RuntimeError('Archive-only recovery cannot issue Actor requests')
            return SearchQAActorAdapter(self.dataset, ArchiveOnly(), profile=self.profile).actor_batch(*args, **kwargs)
        return self.actor_adapter.actor_batch(*args, **kwargs)

    def build_gate(self, *args, **kwargs):
        return self.actor_adapter.build_gate(*args, **kwargs)

    def validation_sources(self):
        root = Path(__file__).parent
        return {q.resolve() for q in root.rglob('*.py')}

    def source_snapshot(self):
        """Record startup sources for inspection, without checking them on resume."""
        roots = (Path(__file__).parent, p.ROOT / 'src/skill_evolution/v27',
                 p.ROOT / 'external/SkillAdam/skilladam/benchmarks/searchqa')
        paths = {path for root in roots for path in root.rglob('*')
                 if path.is_file() and path.suffix in ('.py', '.json', '.md')}
        snapshot = {str(path.relative_to(p.ROOT)): path.read_text() for path in sorted(paths)}
        for name in self.prompt_versions:
            path = self.resource(f'{name}.md')
            snapshot[str(path.relative_to(p.ROOT))] = path.read_text()
        return snapshot

    def runtime_snapshot(self, config):
        self._bound()
        return {'python': sys.version, 'data': self.dataset.snapshot(),
                'actor': self.actor_adapter._actor,
                'workers': self.actor_adapter.workers, 'test_workers': self.actor_adapter.test_workers,
                'gate_metric': self.gate_metric}

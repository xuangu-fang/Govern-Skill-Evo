"""Bound campaign dependencies; no implicit credentials or model transports."""
from copy import deepcopy
from pathlib import Path

from .method import DocVQAMethod
from .benchmarks.docvqa import actor, protocol as p
from .benchmarks.docvqa.adapter import DocVQAActorAdapter


class CampaignAdapter(DocVQAMethod):
    def __init__(self, actor_adapter):
        super().__init__(actor_adapter, archives=[])

    def actor_batch(self, tasks, skill_file, directory, config):
        if self.actor_adapter.transport is not None:
            return self.actor_adapter.actor_batch(tasks, skill_file, directory, config)
        # Rebuild only summaries for independently completed Actor journals.
        skill = Path(skill_file).read_text(encoding='utf-8')
        for index, task in enumerate(tasks, 1):
            actor.read_completed(self.dataset.case(task), skill, Path(directory) / 'actor' / f'{index:04}')
        class ArchiveOnly:
            def metadata(self): return p.actor_config()
            def __call__(self, *args): raise RuntimeError('Archive-only recovery cannot request a model')
        adapter = DocVQAActorAdapter(self.dataset, ArchiveOnly())
        adapter.workers = self.actor_adapter.workers
        return adapter.actor_batch(tasks, skill_file, directory, config)

    def runtime_snapshot(self, config):
        tasks = [t for batch in config['batches'] for t in batch]
        return {'actor': p.actor_config(), 'workers': self.actor_adapter.workers,
                'tasks': [{'id': t, 'payload': deepcopy(dict(self.dataset.case(t).payload)),
                           'reference': deepcopy(self.dataset.case(t).reference),
                           'metadata': deepcopy(dict(self.dataset.case(t).metadata))} for t in tasks]}

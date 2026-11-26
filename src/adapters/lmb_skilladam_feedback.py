"""SkillAdam training evidence from the same completed Actor journal as v27.2 Diagnosis."""
from skilladam.methods.skilladam_prompts import CondensedTrajectory

from src.adapters.lmb import skilladam as baseline
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27_1 import facts
from src.skill_evolution.v27_1.actor_io import ActorAdapter
from src.skill_evolution.v27_1.execution_input_view import exact
from src.skill_evolution.v27_2 import diagnosis
from src.skill_evolution.v27_2.campaign import CampaignAdapter


def training_trajectories(dataset, directory, context):
    signature = baseline.read(directory / 'batch.json')['signature']
    require(signature['config'] == {'role': 'parent', 'split': 'train'}
            and signature['tasks'] == list(context.training_case_ids)
            and signature['skill'] == context.current_skill, 'Unexpected training Actor batch')
    records = baseline.read(directory / 'records.json')
    adapter = CampaignAdapter(ActorAdapter(dataset))
    with adapter.using(), adapter.memory_operation():
        adapter.register_archive(directory)
        saved = facts.build_parent_bundle(records, f'R{context.iteration + 1:02d}')
        view = diagnosis.model_input(saved)

    # SkillAdam renders one trajectory at a time. Keep the shared Actor system
    # message table once per batch, alongside its first reference.
    trajectories = []
    for index, run in enumerate(view['runs']):
        item = {'runs': [run]}
        if index == 0:
            item = {'parent': view['parent'], **item, 'shared_initial': view['shared_initial']}
        trajectories.append(CondensedTrajectory(run['task_id'], exact(item)))
    return tuple(trajectories)


class FeedbackRunner(baseline.Runner):
    def _training_trajectories(self, context):
        cached = self._trajectory_cache.get(context.iteration)
        if cached is not None:
            return cached
        cases = self._lookup_cases(context.training_case_ids)
        evaluation = self._evaluate_skill(context.current_skill, cases, stage='training_rollout')
        iteration = f'iter_{context.iteration:03d}'
        directory = self.backend.output_dir / iteration / 'training' / 'actor'
        trajectories = training_trajectories(self.backend.dataset, directory, context)
        artifacts = f'iterations/{iteration}'
        self._store.write_json(f'{artifacts}/training_evaluation.json', evaluation.to_dict())
        self._store.write_json(f'{artifacts}/training_trajectories.json', [
            {'case_id': item.case_id, 'markdown': item.markdown} for item in trajectories
        ])
        self._trajectory_cache[context.iteration] = trajectories
        return trajectories

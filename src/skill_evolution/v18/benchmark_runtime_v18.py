"""v18 benchmark construction, reusing the existing tasks and environment adapter.

The formal campaign supplies frozen user prompts for both Evolution and Monitor.
Empty or heading-only Skills use the baseline agent; v17 remains unchanged.
"""
import re

from src.benchmark_v3.final.experiments.benchmark_v16_one_step_001 import benchmark_runtime as shared
from .user_simulator_v18 import USER_SIMULATOR_NAME, register_user_simulator

BenchmarkRegistry = shared.BenchmarkRegistry
DeterministicEvaluatorDispatcher = shared.DeterministicEvaluatorDispatcher


class UnifiedEnvironmentAdapter(shared.UnifiedEnvironmentAdapter):
    def __init__(self, registry, *, frozen_user_prompts=None):
        super().__init__(registry)
        register_user_simulator()
        # Copy so callers cannot silently change the expected prompt mid-run.
        self.frozen_user_prompts = (
            None if frozen_user_prompts is None
            else {task: dict(record) for task, record in frozen_user_prompts.items()}
        )

    def build_orchestrator(self, task_id, *, base_config, seed, skill_path, initial_skill_path):
        entry = self.registry.get(task_id)
        config = shared.base_text_config(
            base_config, {'domain': entry.runtime_domain, 'task_id': task_id}, seed)
        config.user = USER_SIMULATOR_NAME
        skill_text = skill_path.read_bytes().decode('utf-8')
        has_body = any(line.strip() and not re.match(r'^#{1,6}(?:\s|$)', line.strip())
                       for line in skill_text.splitlines())
        if skill_path.resolve() != initial_skill_path.resolve() and has_body:
            config.agent = 'llm_agent_manual_skill'
            config.llm_args_agent = {
                **config.llm_args_agent, 'manual_skill_path': str(skill_path.resolve())}
        orchestrator = shared.build_text_orchestrator(config, entry.task, seed=seed)
        record = orchestrator.user.prompt_record()
        if self.frozen_user_prompts is not None:
            if record != self.frozen_user_prompts.get(task_id):
                raise ValueError(f'Frozen v18 user prompt mismatch: {task_id}')
        view = shared.capture_agent_visible_view(orchestrator.agent, entry.logical_domain)
        return orchestrator, view

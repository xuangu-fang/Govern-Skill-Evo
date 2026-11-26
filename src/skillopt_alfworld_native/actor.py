"""Connect native SkillOpt batches to the completed experiments' Actor CLI."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess

from .project import ROOT, campaign_path, runtime_config, read, write, require, sha


class ActorInterrupted(BaseException):
    """Do not let upstream optimizer Exception fallbacks score an incomplete Actor."""


def command(actor, item, output, skill_file):
    split = item['id'].split(':')[0]
    purpose = {'train': 'learning', 'val': 'selection', 'test': 'final'}[split]
    return [actor['python'], '-B', '-m', 'src.adapters.alfworld.run_task_skill',
            '--model', actor['model'], '--split', split, '--purpose', purpose,
            '--task-id', item['id'], '--max-steps', str(actor['max_steps']),
            '--skill-injection', actor['skill_injection'], '--output-format', actor['output_format'],
            '--request-attempts', str(actor['request_attempts']), '--strict-response',
            '--retry-invalid-actions', '--action-feedback', '--archive-responses',
            '--skill-file', str(skill_file), '--output-root', str(output)]


def validate_record(path, actor, item, skill):
    from src.adapters.alfworld.verify_skill_run import verify_record
    from src.adapters.alfworld.response_archive import verify_response_archive
    from src.adapters.alfworld.skill_runtime import digest, execution_protocol
    record = read(path)
    audit = verify_record(record)
    require(audit['episode_complete'], 'Actor episode is incomplete; explicit recovery required')
    require(record['task'] == item and record['model'] == actor['model'], 'Task/model mismatch')
    require(record['skill']['mode'] == 'fixed' and record['skill']['text'] == skill, 'Skill mismatch')
    require(record['backend_id'] == digest((actor['base_url'] + '/chat/completions').encode()), 'Actor route mismatch')
    require(record['request_policy'] == {'max_attempts': 6, 'strict_response': True}, 'Actor retry mismatch')
    require(record['protocol'] == execution_protocol(50, 'skillopt_user_v1',
            output_format='action_only_v1', retry_invalid_actions=True, action_feedback=True), 'Actor protocol mismatch')
    require(Path(record['gamefile']).resolve() == (Path(actor['environment_root']) / item['gamefile']).resolve(), 'Gamefile mismatch')
    for step in record['steps']:
        for attempt in step.get('transport_attempts', []):
            verify_response_archive(path, attempt)
    return record


def convert_record(record, item, path):
    executed = [s for s in record['steps'] if s['phase'] == 'executed']
    task_type = 'pick_and_place' if item['task_type'] == 'pick_and_place_simple' else item['task_type']
    result = {'id': item['id'], 'hard': int(record['won']), 'soft': float(record['won']),
              'n_turns': len(executed), 'fail_reason': '' if record['won'] else record['status'],
              'agent_ok': True, 'task_type': task_type, 'instruction_type': task_type,
              'gamefile': record['gamefile'], 'task_description': record['goal'], 'trajectory': str(path)}
    conversation = [{'step': s['step'] - 1, 'action': s['action'], 'reasoning': None,
                     'model_response': s['model_response']['content'], 'env_feedback': s['observation'],
                     'reward': s['reward'], 'done': s['done']} for s in executed]
    return result, conversation


def run_episode(actor, item, directory, skill_file):
    directory = Path(directory)
    paths = list(directory.glob('*/trajectory.json')) if directory.exists() else []
    if not paths:
        require(not directory.exists(), 'Incomplete episode directory; refusing implicit restart')
        directory.mkdir(parents=True)
        with (directory / 'actor.log').open('xb') as log:
            completed = subprocess.run(command(actor, item, directory, skill_file), cwd=ROOT,
                stdout=log, stderr=subprocess.STDOUT,
                env={**os.environ, 'ALFWORLD_DATA': actor['environment_root'], 'PYTHONDONTWRITEBYTECODE': '1'})
        require(completed.returncode == 0, 'Actor interrupted: ' + str(directory / 'actor.log'))
        paths = list(directory.glob('*/trajectory.json'))
    require(len(paths) == 1, 'Expected exactly one Actor episode, never resample')
    record = validate_record(paths[0], actor, item, skill_file.read_text())
    return record, paths[0]


def build_adapter(root, *, episode_runner=None):
    from skillopt.envs.alfworld.adapter import ALFWorldAdapter, ALFWorldBatchRun
    from skillopt.model.openai_compatible_backend import tracker
    root = Path(root).resolve()
    cfg, actor = runtime_config(root), read(root / 'actor.json')
    campaign = campaign_path(root)
    canonical = {i['id']: i for s in ('train', 'val', 'test') for i in read(root / f'splits/{s}/items.json')}
    runner = episode_runner or run_episode

    class SharedActorAdapter(ALFWorldAdapter):
        @property
        def _env_name(self):
            return 'alfworld'

        def rollout(self, batch, skill_content, out_dir, **kwargs):
            try:
                return self._shared_rollout(batch, skill_content, Path(out_dir), **kwargs)
            except Exception as exc:
                # Native analyst/Selection catches must not hide a technical rollout failure.
                raise ActorInterrupted(str(exc)) from exc

        def _shared_rollout(self, batch, skill, output, **kwargs):
            require(isinstance(batch, ALFWorldBatchRun), 'Unexpected native batch')
            require(not kwargs.get('diagnostic_mode'), 'Actor diagnostic intervention is not aligned')
            require(bool(skill.strip()), 'Initial/current Skill must be nonempty')
            items = []
            for raw in batch.items or []:
                item = canonical[raw['id']]
                require((Path(actor['environment_root']) / raw['gamefile']).resolve() ==
                        (Path(actor['environment_root']) / item['gamefile']).resolve(), 'Batch gamefile mismatch')
                items.append(item)
            require(len(items) == batch.env_num and len({i['id'] for i in items}) == len(items) and items, 'Invalid batch identity/count')
            splits = {i['id'].split(':')[0] for i in items}
            require(len(splits) == 1, 'Mixed split batch')
            if splits == {'test'}:
                require(output.resolve() == campaign / 'test_eval', 'Only Best Test is allowed')
                history = read(campaign / 'history.json')
                require([h['step'] for h in history] == [1, 2, 3, 4], 'Test before four native steps')
                require(skill == (campaign / 'best_skill.md').read_text(), 'Test Skill is not selected Best')
                require({i['id'] for i in items} == {k for k in canonical if k.startswith('test:')}, 'Test must cover all 134 tasks')
                for e in range(1, 5):
                    require((campaign / f'slow_update/epoch_{e:02d}/slow_result.json').is_file()
                            and (campaign / f'meta_skill/epoch_{e:02d}/meta_skill_result.json').is_file(), 'Test before epoch completion')
            output.mkdir(parents=True, exist_ok=True)
            binding = {'tasks': items, 'skill': skill, 'actor_sha256': sha(root / 'actor.json'),
                       'manifest_sha256': sha(root / 'manifest.json')}
            path = output / 'binding.json'
            if path.exists():
                require(read(path) == binding, 'Saved batch inputs changed')
            else:
                require(not any(output.iterdir()), 'Unbound output directory; explicit recovery required')
                write(path, binding)
            skill_file = output / 'actor_skill.md'
            if skill_file.exists():
                require(skill_file.read_text() == skill, 'Saved Actor Skill changed')
            else:
                skill_file.write_text(skill)

            def one(item):
                record, trajectory = runner(actor, item, output / 'episodes' / item['id'].replace(':', '_'), skill_file)
                row, conversation = convert_record(record, item, trajectory)
                write(output / 'predictions' / item['id'] / 'conversation.json', conversation)
                return row, record

            with ThreadPoolExecutor(max_workers=actor['workers']) as pool:
                records = list(pool.map(one, items))
            usage = {'requests': 0, 'unknown_usage_requests': 0, 'prompt_tokens': 0, 'completion_tokens': 0}
            for _, record in records:
                for step in record['steps']:
                    for attempt in step.get('transport_attempts', []):
                        usage['requests'] += 1
                        value = attempt.get('usage')
                        if value:
                            prompt, completion = value.get('prompt_tokens', 0), value.get('completion_tokens', 0)
                            usage['prompt_tokens'] += prompt
                            usage['completion_tokens'] += completion
                            tracker.record('rollout', prompt, completion)
                        else:
                            usage['unknown_usage_requests'] += 1
            write(output / 'actor_usage.json', usage)
            rows = [r for r, _ in records]
            import json
            (output / 'results.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
            return rows

    import inspect
    parameters = inspect.signature(ALFWorldAdapter.__init__).parameters
    return SharedActorAdapter(**{k: v for k, v in cfg.items() if k in parameters})

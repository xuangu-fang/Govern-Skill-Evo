"""Query the production Actor on archived, identical decision windows."""
from concurrent.futures import ThreadPoolExecutor
import os

import requests

from src.skill_evolution.v24_1.benchmarks.alfworld.actor.actor_prompt import visible_commands
from src.skill_evolution.v24_1.benchmarks.alfworld.actor.run_task_upstream import chat, project_action
from src.skill_evolution.v24_1.benchmarks.alfworld.actor.skill_runtime import build_skill_messages
from src.skill_evolution.v24_2.storage import freeze, read


# Fixed before collecting Candidate actions. A miss means the sought object
# was absent, including when the inspected location held other objects.
# At the category boundary any genuinely fresh location is acceptable.
WINDOWS = [
    ('R04', 'train:0034', 9, 'next_drawer', ['go to drawer 5']),
    ('R04', 'train:0035', 7, 'next_drawer', ['go to drawer 5']),
    ('R05', 'val:0006', 5, 'next_drawer', ['go to drawer 3']),
    ('R05', 'val:0007', 15, 'leave_exhausted_drawers', None),
    ('R05', 'val:0007', 16, 'continue_new_class', ['go to countertop 2']),
    ('R04', 'train:0038', 4, 'take_visible', ['take saltshaker 2 from cabinet 1',
                                              'take saltshaker 3 from cabinet 1']),
    ('R04', 'train:0038', 5, 'deliver_held', ['go to sidetable 1']),
    ('R04', 'train:0038', 6, 'first_placement', ['move saltshaker 2 to sidetable 1']),
    ('R04', 'train:0038', 10, 'take_second', ['take saltshaker 3 from cabinet 1']),
    ('R04', 'train:0038', 12, 'second_placement', ['move saltshaker 3 to sidetable 1']),
]


def compare(output, config, records, candidate, *, allow_requests):
    def run(window):
        rd, task, number, kind, expected = window
        raw = records[(rd, task)]
        previous = raw['steps'][:number-1]
        event = raw['steps'][number-1]
        observations = [raw['initial_observation'], *(s['observation'] for s in previous)]
        history = [dict(observation=ob, action=s['action']) for ob, s in zip(observations, previous)]
        menu = event['admissible_commands']
        if expected is None:
            visited = {s['action'][6:] for s in previous if s['action'].startswith('go to ')}
            expected = [a for a in menu if a.startswith('go to ') and a[6:] not in visited]
        if not expected or not set(expected).issubset(menu):
            raise ValueError(f'Invalid reference actions for {task} step {number}')
        def messages(skill):
            return build_skill_messages(observations[-1], menu, raw['goal'], history,
                                        dict(mode='fixed', text=skill), config['actor_skill_injection'],
                                        output_format=config['actor_output_format'])
        if messages(raw['skill']['text']) != event['messages']:
            raise ValueError('Reconstructed Parent input differs from archived request')
        path = output / 'windows' / f'{task.replace(":", "_")}_{number:02}'
        prompt = messages(candidate)
        freeze(path / 'messages.json', prompt)
        result = path / 'response.json'
        if not result.exists():
            if not allow_requests:
                raise ValueError(f'Missing archived Actor response for {task} step {number}')
            with requests.Session() as session:
                response = chat(session, config['call_config']['endpoint'], os.environ['OPENAI_API_KEY'],
                                config['actor_model'], prompt, max_attempts=config['actor_request_attempts'],
                                strict_response=True, action_feedback=config['actor_action_feedback'],
                                action_candidates=visible_commands(menu))
            freeze(result, response)
        action, _ = project_action(read(result)['content'])
        return dict(task=task, step=number, kind=kind, observation=observations[-1], history=history[-2:],
                    acceptable=expected, parent=event['action'], candidate=action,
                    parent_matches=event['action'] in expected, candidate_matches=action in expected)

    with ThreadPoolExecutor(max_workers=config['actor_max_workers']) as executor:
        freeze(output / 'window_results.json', list(executor.map(run, WINDOWS)))

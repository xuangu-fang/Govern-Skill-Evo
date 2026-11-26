"""Build the native trajectory-compression input from the Actor's executed steps."""
from dataclasses import replace
import json
import sys

from scripts.runs.skilladam.alfworld.native_retry import run_skilladam_alfworld_official_models as official
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from scripts.runs.alfworld.alfworld_aligned_common import read, require

ROOT = official.ROOT
BASELINE = ROOT / 'experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/config'
NATIVE = ROOT / 'src/skill_evolution/skilladam/upstream'
sys.path.insert(0, str(NATIVE))
bridge = official.bridge_module()
bridge.EXPERIMENT = BASELINE
from src.adapters.alfworld.run_task_upstream import project_action


def accepted_menu(path, event, template):
    response = event['model_response']
    attempts = event['transport_attempts']
    number = response['api_attempts']
    require(number == len(attempts) and number > 0, 'Missing accepted Actor attempt')
    attempt = attempts[number - 1]
    require(attempt['attempt'] == number and attempt['status'] == 'responded'
            and 200 <= attempt['http_status'] < 300 and 'response_validation_error' not in attempt,
            'Executed action has no successful Actor request')
    # run_batch has already validated request hashes and archived response bytes.
    choice, = read(path.parent / attempt['raw_response']['path'])['choices']
    content = choice['message']['content']
    require(choice['finish_reason'] == 'stop' and content == response['content']
            and project_action(content) == (event['action'], event['fallback']),
            'Accepted HTTP response does not produce the executed action')

    # The original user turn remains in the accepted request on feedback retries.
    user = attempt['messages'][1]
    prefix, suffix = template.split('{admissible_actions}')
    line = prefix.rsplit('\n', 1)[-1]
    require(user['role'] == 'user' and user['content'].endswith(suffix), 'Unexpected Actor menu template')
    _, marker, listing = user['content'].removesuffix(suffix).rpartition('\n' + line)
    require(bool(marker), 'Accepted Actor request lacks a decision menu')
    entries = listing.split('\n ') if listing else []
    require(all(len(s) >= 2 and s.startswith("'") and s.endswith("'") for s in entries),
            'Malformed menu in accepted Actor request')
    return tuple(s[1:-1] for s in entries)


def summary_input(path, uid, skill, native_text):
    record = read(path)
    require(record['task']['id'] == uid and record['skill']['text'] == skill
            and record['status'] in {'success', 'environment_ended', 'step_limit'}, 'Unexpected training episode')
    menus, steps = {}, []
    for index, event in enumerate(record['steps'], 1):
        require(event['phase'] == 'executed' and event['step'] == index, 'Incomplete execution history')
        template = record['protocol']['initial_template' if index == 1 else 'history_template']
        menu = accepted_menu(path, event, template)
        ref = menus.setdefault(menu, f'C{len(menus) + 1}')
        steps.append({'step': index, 'commands_ref': ref, 'action': event['action'],
                      'after_observation': event['observation'],
                      'feedback': {k: event[k] for k in ('reward', 'done', 'won',
                                                         'action_in_admissible_commands', 'fallback')}})
    evidence = {'parent': skill, 'initial': {'observation': record['initial_observation'],
                                             'commands_ref': steps[0]['commands_ref']},
                'command_sets': {ref: menu for menu, ref in menus.items()}, 'steps': steps,
                'environment_outcome': {'status': record['status'], 'success': record['won'],
                                        'end_reason': record['status'], 'executed_steps': len(steps)}}
    query, trace_marker, trace = native_text.partition('\n\n## Execution Trace\n\n')
    _, final_marker, final = trace.rpartition('\n\n## Final Answer\n\n')
    require(query == '## Query\n\n' + record['goal'] and trace_marker and final_marker
            and '\n\n## Outcome\n' in final, 'Unexpected native trajectory envelope')
    return query + trace_marker + json.dumps(evidence, ensure_ascii=False, separators=(',', ':')) + final_marker + final


class FeedbackBackend(official.backend_type(bridge)):
    def execute_batch(self, execution):
        rows = super().execute_batch(execution)
        if execution.stage == 'training_rollout':
            self.training_records = {row.case_id: resolve_experiment_path(row.result['trajectory']) for row in rows}
            self.training_skill = execution.requests[0].skill
            self.training_iteration = self.iteration
        return rows

    def generate(self, request):
        if request.stage == 'trajectory_compression':
            uid = request.metadata['case_id']
            require(self.training_iteration == self.iteration and uid in self.training_records,
                    'Summary source is outside this training batch')
            system, user = request.messages
            require((system['role'], user['role']) == ('system', 'user'), 'Unexpected summary message roles')
            text = summary_input(self.training_records[uid], uid, self.training_skill, user['content'])
            request = replace(request, messages=(system, {**user, 'content': text}))
        return super().generate(request)

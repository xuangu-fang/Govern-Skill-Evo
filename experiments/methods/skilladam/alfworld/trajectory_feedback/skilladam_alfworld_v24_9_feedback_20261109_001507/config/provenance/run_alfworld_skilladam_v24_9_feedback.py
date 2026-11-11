"""Dual-official DeepSeek ALFWorld SkillAdam with v24.9 training evidence."""
import argparse
from dataclasses import replace
import fcntl
from importlib.metadata import version
import json
from pathlib import Path
import sys

import run_skilladam_alfworld_official_models as official
from alfworld_aligned_common import read, require, run_batch, sha, write

ROOT = official.ROOT
BASELINE = ROOT / 'experiments/baselines/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001'
# This archived upstream package matches all 281 package files in the ALFWorld manifest.
NATIVE = ROOT / 'experiments/comparisons/skilladam_v25_1_actor_aligned_20261030_001/frozen_workspace/external/SkillAdam'
sys.path.insert(0, str(NATIVE))
bridge = official.bridge_module()
bridge.EXPERIMENT = BASELINE
from src.adapters.alfworld.run_task_upstream import project_action


def prepare():
    manifest = read(BASELINE / 'manifest.json')
    require(sys.executable == manifest['python_executable'] and sys.version == manifest['python_version'],
            'Use the frozen SkillAdam Python interpreter')
    for name, expected in manifest['packages'].items():
        require(version(name) == expected, f'Frozen package changed: {name}')
    for filename, expected in manifest['files'].items():
        path = Path(filename)
        if path.is_relative_to(ROOT / 'external/SkillAdam/skilladam'):
            path = NATIVE / path.relative_to(ROOT / 'external/SkillAdam')
        require(sha(path) == expected, f'Frozen input changed: {path}')
    return read(BASELINE / 'actor.json'), read(BASELINE / 'skilladam.json')


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
            self.training_records = {row.case_id: Path(row.result['trajectory']) for row in rows}
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


def run(output, resume):
    actor, cfg = prepare()
    bridge.configure_runtime(actor)
    output = output.resolve()
    require(not output.is_relative_to(BASELINE), 'Use a new output outside the historical run')
    output.parent.mkdir(parents=True, exist_ok=True)
    with (output.parent / (output.name + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt = output.parent / (output.name + '.launch.json')
        signature = {'source_manifest': sha(BASELINE / 'manifest.json'), 'feedback_driver': sha(__file__)}
        if resume:
            require(read(receipt) == signature and (output / 'checkpoint.json').is_file(), 'Checkpoint differs')
        else:
            require(not output.exists() and not receipt.exists(), 'Expected fresh training output')
            write(receipt, signature)
        backend = FeedbackBackend(actor, cfg, output)
        runner = bridge.AlignedRunner(config=bridge.native_config(cfg), adapter=bridge.ALFWorldAdapter(BASELINE / 'splits'),
                                      backend=backend, context=official.context_for(bridge, actor, cfg), output_dir=output)
        result = runner.run(cases=bridge.cases_for(cfg), initial_skill=(BASELINE / 'initial_skill.md').read_text(),
                            resume=resume)
        write(output / 'completion.json', {'status': 'complete', 'automatic_test': False,
              'iterations': [r.to_dict() for r in result.feedback_loop.iterations],
              'resumed_from_iteration': result.feedback_loop.resumed_from_iteration,
              'new_optimizer_logical_calls': backend.new_generations})


def test_final(training):
    actor, cfg = prepare()
    training = training.resolve()
    state = read(training / 'checkpoint.json')
    completion = read(training / 'completion.json')
    rounds = cfg['native']['feedback_loop']['max_iterations']
    require(completion['status'] == 'complete' and len(completion['iterations']) == rounds
            and state['next_iteration'] == rounds and state['pending_post_decision'] is None,
            'Training or Momentum is incomplete')
    skill = (training / 'final_skill.md').read_text()
    require(skill.strip() and skill == state['current_skill'], 'Final skill differs from checkpoint')
    tasks = read(BASELINE / 'splits/test/items.json')
    ids = [item['id'] for item in tasks]
    require(len(ids) == len(set(ids)) == 134 and all(uid.startswith('test:') for uid in ids),
            'Unexpected test split')
    output = training.with_name(training.name + '_test134')
    output.mkdir(exist_ok=True)
    with (output / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        signature = {'skill': skill, 'actor': actor, 'tasks': tasks}
        if (output / 'inputs.json').exists():
            require(read(output / 'inputs.json') == signature, 'Test inputs changed')
        else:
            require(all(p.name == '.lock' for p in output.iterdir()), 'Unexpected existing test files')
            write(output / 'inputs.json', signature)
        if (output / 'summary.json').exists():
            summary = read(output / 'summary.json')
            require(summary['status'] == 'complete' and [r['id'] for r in summary['tasks']] == ids
                    and summary['skill_sha256'] == sha(training / 'final_skill.md'), 'Test result differs')
            return summary
        bridge.configure_runtime(actor)
        rows = run_batch(actor, tasks, skill, output)
        require([r['id'] for r in rows] == ids and (output / 'actor_skill.md').read_text() == skill,
                'Final test coverage or skill differs')
        success = sum(r['hard'] for r in rows)
        summary = {'status': 'complete', 'completed': len(rows), 'success': success,
                   'success_rate': success / len(rows), 'skill_sha256': sha(output / 'actor_skill.md'),
                   'tasks': rows, 'training_updated': False}
        write(output / 'summary.json', summary)
        return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--start', metavar='OUTPUT', type=Path)
    action.add_argument('--test-only', metavar='TRAINING_OUTPUT', type=Path)
    parser.add_argument('--test-after', action='store_true', help='Test the frozen final skill after training')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if (args.test_after or args.resume) and not args.start:
        parser.error('--test-after and --resume require --start OUTPUT')
    if args.start:
        run(args.start, args.resume)
        if args.test_after:
            test_final(args.start)
    elif args.test_only:
        test_final(args.test_only)
    else:
        prepare()
        print('Dual-official ALFWorld configuration verified offline')

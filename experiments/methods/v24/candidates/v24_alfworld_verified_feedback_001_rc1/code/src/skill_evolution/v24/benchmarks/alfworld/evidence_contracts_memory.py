from copy import deepcopy
import re
from src.skill_evolution.v24.contracts.diagnosis import fields
from src.skill_evolution.v24.facts import require, text
from .facts import STATUSES
from src.skill_evolution.v24.contracts.memory import _entry_fields, empty_memory, entry_evidence, validate_memory

def run_references(run):
    return {run['ref'], f"{run['ref']}:0", f"{run['ref']}:outcome", *[s['step'] for s in run['steps']]}


def run_menus(run, menus):
    used = {state['commands_ref'] for state in
            [run['initial'], *[s[side] for s in run['steps'] for side in ('before', 'after')]]} - {None}
    require(used <= menus.keys(), 'Missing command source')
    return {key: deepcopy(value) for key, value in menus.items() if key in used}


def validate_run(run, menus):
    fields(run, ('ref', 'task', 'initial', 'steps', 'outcome'), 'Run')
    require(isinstance(run['ref'], str) and re.fullmatch(r'[PQ][1-9]\d*', run['ref']), 'Invalid execution ID')
    text(run['task'], 'task')
    require(isinstance(run['steps'], list), 'steps must be an array')
    for state in [run['initial'], *[s[side] for s in run['steps'] for side in ('before', 'after')]]:
        fields(state, ('observation', 'commands_ref'), 'State')
        text(state['observation'], 'observation')
        require(state['commands_ref'] is None or state['commands_ref'] in menus, 'Missing command reference')
    for menu in menus.values():
        require(isinstance(menu, list) and all(isinstance(c, str) and c != 'help' for c in menu), 'Invalid visible menu')
    previous = run['initial']
    for i, step in enumerate(run['steps'], 1):
        fields(step, ('step', 'before', 'action', 'after', 'feedback'), 'Step')
        require(step['step'] == f"{run['ref']}:{i}" and step['before'] == previous, 'Broken execution continuity')
        # Empty commands are valid recorded evidence of an invalid Actor action.
        require(isinstance(step['action'], str), 'Invalid action')
        if i < len(run['steps']):
            require(not step['feedback'].get('done') and not step['feedback'].get('won'), 'Step follows terminal state')
        require(isinstance(step['feedback'], dict), 'Invalid feedback')
        previous = step['after']
    fields(run['outcome'], ('status', 'success', 'end_reason'), 'Outcome')
    status = run['outcome']['status']
    require(status in STATUSES and run['outcome']['end_reason'] == status, 'Invalid termination')
    expected = status == 'success' if status in {'success', 'environment_ended', 'step_limit'} else None
    require(run['outcome']['success'] is expected, 'Outcome confuses interruption and failure')
    return run


def _view(archive, contexts, active_ids, memory_contract):
    view = empty_memory()
    for mid in active_ids:
        entry = archive[mid]
        view['entries'].append({k: deepcopy(entry[k]) for k in ('id', *_entry_fields(memory_contract))})
        for ref in entry_evidence(entry, memory_contract=memory_contract):
            cid, local = ref.rsplit('/', 1)
            require(cid in contexts, 'Historical context unavailable')
            context = contexts[cid]
            edit_key = f'{cid}/diff'
            view['sources'][edit_key] = {'parent': context['payload']['parent'], 'diff': context['payload']['diff'],
                                        'execution_context': deepcopy(context['execution_context'])}
            if local != 'diff':
                rid = local.split(':', 1)[0]
                run = next((r for r in context['payload']['runs'] if r['ref'] == rid), None)
                require(run is not None and local in run_references(run), 'Archived execution reference unavailable')
                view['sources'][f'{cid}/{rid}'] = {'run': deepcopy(run),
                    'command_sets': run_menus(run, context['payload']['command_sets'])}
    validate_memory(view, memory_contract=memory_contract)
    return view

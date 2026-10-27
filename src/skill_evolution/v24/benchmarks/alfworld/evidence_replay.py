from src.skill_evolution.v24.contracts import replay as original
from src.skill_evolution.v24.facts import require
from src.skill_evolution.v24.contracts.memory import MULTI_KNOWLEDGE_CONTRACT
from src.skill_evolution.v24.editor import load_editor

def validate_bundle(bundle, *, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    """Recheck versioned lineage; behavioral truth still comes from supplied records."""
    original.validate_payload(bundle['payload'], memory_contract=memory_contract)
    saved = load_editor(bundle['editor_directory'])
    payload = bundle['payload']
    require(saved['editor_status'] == 'candidate', 'Replay requires a Candidate')
    require(bundle['candidate'] == saved['candidate_text'] and payload['diff'] == saved['actual_diff'],
            'Replay actual edit differs from Editor')
    require(payload['parent'] == saved['facts']['parent'] and bundle['background'] == saved['background'],
            'Replay Parent/background differs from Editor')
    plan = saved['effective_plan']
    expected = {'goal': plan['goal'], 'updates': [{k: u[k] for k in ('id', 'text')} for u in plan['updates']],
                'checks': plan['checks']}
    require(payload['plan'] == expected, 'Replay Plan differs from Editor')
    parents = [r for r in payload['runs'] if r['ref'].startswith('P')]
    require(parents == saved['facts']['runs'], 'Replay Parent executions differ from frozen lineage')
    require(all(payload['command_sets'].get(cid) == commands
                for cid, commands in saved['facts']['command_sets'].items()), 'Parent command sources differ')
    require(bundle['execution_context']['background'] == saved['background'], 'Replay execution context differs')
    return bundle

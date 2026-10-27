"""Read-only factual checks supporting manual review, not a semantic validator."""
import json

from .run import core, HERE, p4, NEW
from src.skill_evolution.v23.memory import entry_evidence
BASELINE = HERE.with_name("replay_prompt_candidate_001")


def main():
    core.verify()
    report = {}
    for label in ('R05', 'R06'):
        view = core.read(p4.HERE / f'cases/{label}/model_input.json')
        runs = {r['ref']: r for r in view['runs']}
        proposal = core.load(label, 'replay')['replay']
        preview = core.read(HERE / f'cases/{label}/results/memory_view.json')

        def step(ref, n):
            return runs[ref]['steps'][n - 1]

        def actions(ref):
            return [s['action'] for s in runs[ref]['steps']]

        def menu(ref, n):
            return view['command_sets'][step(ref, n)['before']['commands_ref']]

        result = {
            'current_pairs': view['pairs'],
            'prior_usage': core.read(BASELINE / f'runs/{label}_replay/attempt_001/response.json')['usage'],
            'candidate_usage': core.read(HERE / f"runs/{label}_replay/attempt_{core.read(HERE / f'runs/{label}_replay/selected.json')['attempt']:03}/response.json")['usage'],
            'entry_evidence_counts': [len(entry_evidence(e, memory_contract=NEW)) for e in proposal['entries']],
            'current_runs_without_new_evidence': sorted(set(runs) - {
                ref.split(':')[0] for e in proposal['entries'] for ref in entry_evidence(e, memory_contract=NEW)}),
        }
        if label == 'R05':
            assert step('Q7', 25)['action'] == 'go to drawer 2'
            assert all(s['feedback']['action_in_admissible_commands'] is True for s in runs['Q7']['steps'])
            result['Q7_claimed_invalid_drawer8_action_contradicted'] = {
                'actual_step_25': step('Q7', 25), 'invalid_commands_in_entire_Q7': 0}
            assert step('P8', 8)['action'] == 'open cabinet 3'
            assert 'open cabinet 3' in menu('P8', 8) and 'go to cabinet 3' not in menu('P8', 8)
            result['parent_direct_action_opportunity'] = {
                'step': step('P8', 8), 'navigation_available': False, 'direct_open_available': True}
            for ref in ('P8', 'Q8'):
                assert 'go to shelf 1' in menu(ref, 1) and 'go to shelf 1' not in actions(ref)
            result['soapbar_shelf_available_but_unvisited'] = True
            assert actions('P10')[9:] == actions('Q10')[6:]
            result['apple_pair'] = {r: actions(r) for r in ('P10', 'Q10')}
            result['pillow_pair'] = {r: actions(r) for r in ('P2', 'Q2')}
            result['successful_exact_butterknife'] = [step(r, 3) for r in ('P6', 'Q6')]
            for s in result['successful_exact_butterknife']:
                assert s['action'].startswith('take butterknife ')
            result['historical_bread_initials'] = {
                key: view['memory']['sources'][key]['run']['initial']['observation']
                for key in ('S1_R03/P2', 'S1_R03/P4')}
            assert len(set(result['historical_bread_initials'].values())) == 2
        else:
            historic = view['memory']['sources']['S1_R05/Q7']
            initial_menu = view['memory']['command_pool'][historic['detailed_steps'][0]['before']['commands_ref']]
            assert 'go to cabinet 18' in initial_menu
            assert not any(s['action'] == 'go to cabinet 18' for s in historic['run']['trace'])
            result['historical_butterknife_global_absence_not_established'] = {
                'cabinet18_available': True, 'cabinet18_visited': False}
            result['plate_pair'] = {r: actions(r) for r in ('P1', 'Q1')}
            assert len(actions('Q1')) - len(actions('P1')) == 1
            assert actions('Q1')[:2] == ['go to cabinet 1', 'open cabinet 1']
            assert 'open fridge 1' in actions('P1') and 'open fridge 1' not in actions('Q1')
            result['tomato_pair'] = {r: {'task': runs[r]['task'], 'actions': actions(r)} for r in ('P2', 'Q2')}
            assert runs['P2']['task'] == runs['Q2']['task'] == 'put a cool tomato in microwave.'
            assert actions('P2')[13:] == actions('Q2')[5:]
            result['tomato_after_acquisition_actions_equal'] = True
            result['book_shelves_not_empty'] = [step('Q6', 31), step('Q6', 32)]
            result['historical_heat_plate'] = {}
            for key in ('S1_R04/P2', 'S1_R04/Q2'):
                run = view['memory']['sources'][key]['run']
                result['historical_heat_plate'][key] = {
                    'task': run['task'], 'steps': len(run['trace']), 'outcome': run['outcome'],
                    'manipulation': [s for s in run['trace'] if s['action'].startswith(('take ', 'heat ', 'move '))]}
            assert result['historical_heat_plate']['S1_R04/P2']['outcome']['success'] is True
            assert result['historical_heat_plate']['S1_R04/P2']['steps'] == 13
            assert result['historical_heat_plate']['S1_R04/Q2']['outcome']['success'] is False
            assert result['historical_heat_plate']['S1_R04/Q2']['steps'] == 50
        prefix = f'v23_4_{label}_multi_knowledge_p6_001/'
        result['future_current_detailed_steps'] = {
            key: [s['step'] for s in value['detailed_steps']]
            for key, value in preview['sources'].items()
            if key.startswith(prefix) and not key.endswith('/diff')}
        report[label] = result
    (HERE / 'FACT_CHECKS.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('Factual assertions passed; FACT_CHECKS.json saved. No semantic approval implied.')


if __name__ == '__main__':
    main()

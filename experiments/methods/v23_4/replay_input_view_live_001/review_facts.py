"""Reproduce selected factual checks for the manual review; no model calls."""
from copy import deepcopy
import json

from .run import HERE, core


def main():
    core.verify()
    report = {}
    for label in ('R05', 'R06'):
        view = core.read(HERE / f'config/{label}/model_input.json')
        runs = {r['ref']: r for r in view['runs']}
        proposal = core.load(label, 'replay')['replay']
        current = core.read(HERE / f'runs/{label}_replay/attempt_001/response.json')
        old = core.read(HERE.with_name(label.lower() + '_replay_memory_001') /
                        f'runs/{label}_replay/attempt_001/response.json')
        preview = core.read(HERE / f'cases/{label}/results/memory_view.json')

        def step(ref, n):
            return runs[ref]['steps'][n - 1]

        def actions(ref):
            return [s['action'] for s in runs[ref]['steps']]

        def excerpt(ref, n):
            value = deepcopy(step(ref, n))
            if len(value['action']) > 180:
                value['action'] = '[malformed output redacted; see original archive]'
            return value

        old_tokens = old['usage']['prompt_tokens']
        new_tokens = current['usage']['prompt_tokens']
        data = {
            'old_usage': old['usage'], 'new_usage': current['usage'],
            'input_token_reduction_percent': (1 - new_tokens / old_tokens) * 100,
            'current_pairs': view['pairs'],
            'proposal_entries': len(proposal['entries']),
            'current_runs_without_any_new_evidence_reference': sorted(
                set(runs) - {ref.split(':')[0] for e in proposal['entries'] for ref in e['evidence']}),
        }
        if label == 'R05':
            data['shelf_unvisited'] = {}
            for ref in ('P8', 'Q8'):
                menu = view['command_sets'][step(ref, 1)['before']['commands_ref']]
                assert 'go to shelf 1' in menu and 'go to shelf 1' not in actions(ref)
                data['shelf_unvisited'][ref] = {'initially_available': True, 'visited': False}
            assert len(actions('P10')) == 14 and len(actions('Q10')) == 11
            assert actions('P10')[9:] == actions('Q10')[6:]
            assert len(actions('P2')) == 5 and len(actions('Q2')) == 6
            data['apple_after_acquisition_actions_equal'] = True
            data['pillow_pair_actions'] = {r: actions(r) for r in ('P2', 'Q2')}
            data['apple_pair_actions'] = {r: actions(r) for r in ('P10', 'Q10')}
            data['historical_manipulation'] = {}
            for key in ('S1_R03/P10', 'S1_R03/Q10', 'S1_R04/P1', 'S1_R04/Q1'):
                source = view['memory']['sources'][key]
                trace = source['run']['trace']
                data['historical_manipulation'][key] = [s for s in trace if s['action'].startswith(
                    ('take ', 'move ', 'heat ', 'cool '))]
            assert not any(s['action'].startswith('heat ') for s in
                           view['memory']['sources']['S1_R03/P10']['run']['trace'])
            assert view['memory']['sources']['S1_R04/P1']['run']['trace'][30]['action'] == 'heat cup 2 with microwave 1'
        else:
            assert runs['Q2']['task'] == runs['P2']['task'] == 'put a cool tomato in microwave.'
            assert step('P2', 13)['action'] == 'take tomato 1 from countertop 2'
            assert step('Q2', 5)['action'] == 'take tomato 1 from countertop 2'
            assert 'bread' in proposal['entries'][1]['knowledge']
            data['tomato_mislabeled_bread'] = {
                'task': runs['Q2']['task'],
                'steps': [excerpt(r, n) for r, n in [('P2', 13), ('P2', 15), ('Q2', 4), ('Q2', 5), ('Q2', 7)]]}
            data['plate_pair_actions'] = {r: actions(r) for r in ('P1', 'Q1')}
            assert len(actions('P1')) == 8 and len(actions('Q1')) == 9
            assert step('P1', 5)['action'] == 'open fridge 1'
            assert step('Q1', 7)['action'] == 'cool plate 1 with fridge 1'
            data['plate_action_accounting'] = {'extra_search': 2, 'conditioning_saving': 1, 'net_candidate_extra': 1}
            data['tomato_acquisition_steps'] = {'parent': 3, 'candidate': 4}
            assert step('P4', 3)['action'] == step('Q4', 4)['action'] == 'take tomato 2 from fridge 1'
            data['apple_unvisited_candidates'] = {}
            for ref in ('P3', 'Q3'):
                menu = view['command_sets'][step(ref, 1)['before']['commands_ref']]
                data['apple_unvisited_candidates'][ref] = [a for a in menu if a.startswith('go to ') and a not in actions(ref)]
                assert data['apple_unvisited_candidates'][ref]
                assert not any(a.startswith(('take apple ', 'heat apple ')) for a in actions(ref))
            data['book_visible_nonempty_shelves'] = [excerpt('Q6', 31), excerpt('Q6', 32)]
        prefix = f'v23_4_{label}_view_replay_001/'
        data['future_current_detailed_steps'] = {
            k: [s['step'] for s in v['detailed_steps']]
            for k, v in preview['sources'].items() if k.startswith(prefix) and not k.endswith('/diff')}
        report[label] = data
    core.save(HERE / 'FACT_CHECKS.json', report)
    print('R05/R06 factual checks passed; saved FACT_CHECKS.json (not semantic approval).')


if __name__ == '__main__':
    main()

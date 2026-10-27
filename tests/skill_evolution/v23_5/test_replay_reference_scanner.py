"""Current prose pairs must not acquire or bypass historical evidence access."""
from copy import deepcopy
import json

import pytest

from src.skill_evolution.v23_5 import replay
from src.skill_evolution.v23_5.memory_view import check_historical_prose
from .helpers import Fake, read
from .test_replay_newlines import bundle


CURRENT = {'P6', 'Q6', 'Q7', 'Q10:35', 'Q10:39'}


@pytest.mark.parametrize('expression', [
    'P6/Q6', 'Q6/Q7', 'Q10:35/Q10:39', 'P6/Q6/Q7',
])
def test_verified_current_pairs_in_prose(expression):
    check_historical_prose(f'Observed {expression}.', set(), current=CURRENT)


@pytest.mark.parametrize('expression', [
    'P6/Q99', 'P99/Q6', 'Q10:35/Q10:999', 'P6/Q6/Q99',
    'UnknownRound/Q6', 'UnknownRound/diff', 'R1/Q6:2', 'R1/Q6:1-2',
    'R1/Q6:1–2', 'R1/Q6:1/Q7', 'R1/Q6:1/Unknown',
])
def test_unavailable_refs_are_not_ignored_or_partially_authorized(expression):
    with pytest.raises(ValueError, match='Unavailable historical reference') as error:
        check_historical_prose(expression, {'R1/Q6:1'}, current=CURRENT)
    assert repr(expression) in str(error.value)


def test_step_expression_is_not_scanned_from_its_middle():
    # Even authorizing the erroneous substring must not admit an unknown endpoint.
    with pytest.raises(ValueError) as error:
        check_historical_prose('Q10:35/Q10:39', {'35/Q10:39'}, current={'Q10:35'})
    assert "'Q10:35/Q10:39'" in str(error.value)
    assert "'35/Q10:39'" not in str(error.value)


@pytest.mark.parametrize('allowed', [set(), {'P6/Q6'}])
def test_context_name_collision_is_ambiguous_even_when_history_is_hidden(allowed):
    with pytest.raises(ValueError, match='Ambiguous current/historical reference'):
        check_historical_prose('P6/Q6', allowed, current=CURRENT, historical_contexts={'P6'})


def test_allowed_history_and_ordinary_prose_still_work():
    check_historical_prose('See R1/Q6:1 and R1/diff; compare and/or retain.',
                           {'R1/Q6:1', 'R1/diff'}, current=CURRENT)
    # No current P6: this is unambiguously an explicitly permitted historical ID.
    check_historical_prose('P6/Q6', {'P6/Q6'}, current={'Q6'}, historical_contexts={'P6'})


def proposal(text, evidence=None):
    return {'entries': [{'revises': [], 'knowledge': [{
        'text': text, 'evidence': ['diff', 'P1:1', 'Q1:1'] if evidence is None else evidence}]}]}


def test_replay_keeps_pair_text_and_evidence_unchanged_on_generation_and_reload(bundle, tmp_path):
    raw = proposal('Compare P1/Q1 and steps P1:1/Q1:1.')
    original = deepcopy((raw, bundle))
    fake = Fake(raw)
    dest = tmp_path/'replay'
    value = replay.run_replay(bundle, dest, generate=fake, input_view=replay.KNOWLEDGE_INPUT_VIEW)
    assert value['replay'] == raw == read(dest/'replay.json')
    assert replay.load_replay(dest) == value
    assert fake.calls == 1 and (raw, bundle) == original
    # Reload must recheck actual endpoint existence, not just the saved result.
    raw['entries'][0]['knowledge'][0]['text'] = 'Compare P1/Q999.'
    response = read(dest/'response.json'); response['content'] = json.dumps(raw)
    (dest/'response.json').write_text(json.dumps(response))
    (dest/'raw_output.txt').write_text(response['content'])
    for name in ('parsed.json', 'replay.json'):
        (dest/name).write_text(json.dumps(raw))
    with pytest.raises(ValueError, match=r'entries\[0\].knowledge\[0\].text.*P1/Q999'):
        replay.load_replay(dest)


def test_evidence_arrays_never_accept_pair_shorthand(bundle):
    with pytest.raises(ValueError):
        replay.validate_result(proposal('Compare P1/Q1.', ['diff', 'P1/Q1']),
                               bundle['payload'], input_view=replay.KNOWLEDGE_INPUT_VIEW)


def test_replay_checks_hidden_archive_context_names_for_ambiguity(bundle):
    payload = deepcopy(bundle['payload'])
    payload['memory']['sources']['P1/diff'] = {
        'parent': payload['parent'], 'diff': payload['diff'],
        'execution_context': bundle['execution_context']}
    with pytest.raises(ValueError, match='Ambiguous current/historical reference'):
        replay.validate_result(proposal('Compare P1/Q1.'), payload,
                               input_view=replay.KNOWLEDGE_INPUT_VIEW)

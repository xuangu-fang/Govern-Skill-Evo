#!/usr/bin/env python3
"""Validate static semantic evidence; no tasks, evaluator or agent are imported."""
import hashlib
import json
import os
import socket
import sys
import types
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TAU = REPO / 'external/tau2-bench'
sys.dont_write_bytecode = True
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['TAU2_DATA_DIR'] = str(TAU / 'data')
package = types.ModuleType('tau2')
package.__path__ = [str(TAU / 'src/tau2')]
sys.modules['tau2'] = package

def no_network(*args, **kwargs):
    raise RuntimeError('Static audit: network disabled')

socket.socket.connect = no_network
socket.create_connection = no_network
from tau2.domains.airline.data_model import FlightDB
from tau2.domains.airline.tools import AirlineTools
from tau2.domains.retail.data_model import RetailDB
from tau2.domains.retail.tools import RetailTools
from loguru import logger
logger.remove()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(domain, calls):
    cls, toolkit = (FlightDB, AirlineTools) if domain == 'airline' else (RetailDB, RetailTools)
    db = cls.load(TAU / f'data/tau2/domains/{domain}/db.json')
    obj = toolkit(db)
    output = []
    for call in calls:
        before = db.get_hash()
        try:
            result = getattr(obj, call['name'])(**call['arguments'])
            row = {'accepted': True, 'result': result.model_dump(mode='json') if hasattr(result, 'model_dump') else result}
        except ValueError as exc:
            row = {'accepted': False, 'error': str(exc)}
        row['mutated'] = before != db.get_hash()
        output.append(row)
        if not row['accepted']:
            break
    return output


def main():
    audit = json.loads((HERE / 'latent_governance_candidate_audit.json').read_text())
    candidates = json.loads((HERE / 'latent_governance_candidates.json').read_text())
    for path, digest in audit['frozen_file_sha256'].items():
        assert sha(REPO / path) == digest, path
    for path, digest in audit['artifact_sha256'].items():
        assert sha(HERE / path) == digest, path
    dbs = {d: json.loads((TAU / f'data/tau2/domains/{d}/db.json').read_text()) for d in ['airline', 'retail']}
    policy = {d: (TAU / f'data/tau2/domains/{d}/policy.md').read_text() for d in dbs}
    admitted = []
    witness_count = 0
    for c in candidates:
        for q in c['canonical_evidence_quotes']:
            assert q in policy[c['domain']], (c['candidate_id'], q)
        assert set(c['criteria']) == {f'C{i}' for i in range(1, 9)}
        supports = c['native_state_support']['states']
        for state in supports:
            coll = 'reservations' if c['domain'] == 'airline' else 'orders'
            entity = dbs[c['domain']][coll][state['entity_id']]
            assert entity == state['native_entity_snapshot']
            assert entity['user_id'] == state['user_id']
        assert c['native_state_support']['number_of_independent_states'] == len({s['user_id'] for s in supports})
        for w in c['backend_witnesses']:
            assert probe(c['domain'], w['calls']) == w['result'], c['candidate_id']
            witness_count += 1
        if c['static_verdict'].startswith('ADMISSIBLE'):
            admitted.append(c['candidate_id'])
            for q in c['VISIBLE_AFTER_HIDING']:
                assert q in policy[c['domain']], (c['candidate_id'], q)
            for q in c['HIDDEN']['canonical_spans']:
                assert q in policy[c['domain']], (c['candidate_id'], q)
            assert len({s['user_id'] for s in supports}) >= 2
            assert c['governance_outcome_critical'] and c['criteria']['C1']['value']
            assert c['criteria']['C5']['value'] and c['criteria']['C6']['value']
            assert c['backend_enforcement'] != 'FULL'
            assert c['VISIBLE_AFTER_HIDING'] and c['HIDDEN']
            assert len(c['backend_witnesses']) == 2
            assert all(w['result'][-1]['accepted'] and w['result'][-1]['mutated'] for w in c['backend_witnesses'])
    assert admitted == audit['admissible_candidate_ids']
    assert len(candidates) == audit['candidate_count']
    assert len({c['candidate_id'] for c in candidates}) == len(candidates)
    for field, counts in audit['counts'].items():
        assert dict(Counter(c[field] for c in candidates)) == counts
    for c in candidates:
        if not c['static_verdict'].startswith('ADMISSIBLE'):
            continue
        for state, witness in zip(c['native_state_support']['states'], c['backend_witnesses']):
            e = state['native_entity_snapshot']
            result = witness['result'][-1]['result']
            if c['domain'] == 'airline':
                statuses = [dbs['airline']['flights'][f['flight_number']]['dates'][f['date']]['status'] for f in e['flights']]
                if c['candidate_id'] == 'LGA01':
                    assert e['cabin'] == 'business' and 'landed' in statuses
                    assert result['status'] == 'cancelled'
                elif c['candidate_id'] == 'LGA02':
                    assert e['cabin'] == 'business' and 'delayed' in statuses
                    assert not set(statuses) & {'landed', 'flying'}
                elif c['candidate_id'] == 'LGA03':
                    assert e['insurance'] == 'yes' and e['cabin'] == 'economy'
                    assert e['created_at'] < '2024-05-14T15:00:00' and set(statuses) == {'available'}
                elif c['candidate_id'] == 'LGA04':
                    assert result['flights'][0]['origin'] == e['origin']
                    assert result['flights'][-1]['destination'] != e['destination']
            else:
                assert e['status'] == 'pending' and len(e['items']) >= 2
                assert result['status'] == 'pending (item modified)'
    forbidden_modules = ['tau2.agent', 'tau2.user', 'tau2.evaluator', 'tau2.runner', 'tau2.orchestrator']
    assert not any(n == p or n.startswith(p + '.') for n in sys.modules for p in forbidden_modules)
    assert audit['contract']['outcome_based_selection'] is False
    assert audit['contract']['tasks_constructed'] == 0
    print(json.dumps({'static_validation': 'PASS', 'candidate_count': len(candidates),
                      'native_backend_witnesses_reproduced': witness_count,
                      'admissible_candidate_ids': admitted,
                      'frozen_files_verified': len(audit['frozen_file_sha256']),
                      'calls': audit['contract']['calls'], 'tasks_constructed': 0,
                      'policy_files_modified': False,
                      'verdict': audit['verdict']}, indent=2))

if __name__ == '__main__':
    main()

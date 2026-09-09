#!/usr/bin/env python3
"""Offline native-tool replay; never imports the simulation entry point."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import types
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TAU2 = REPO / 'external/tau2-bench'
sys.dont_write_bytecode = True
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['TAU2_DATA_DIR'] = str(TAU2 / 'data')

# Avoid tau2.__init__, which eagerly imports runner, agents and evaluators.
# All domain models, toolkit decorators, and mutation implementations stay native.
package = types.ModuleType('tau2')
package.__path__ = [str(TAU2 / 'src/tau2')]
sys.modules['tau2'] = package

def no_network(*args, **kwargs):
    raise RuntimeError('Network disabled during static validation')

socket.socket.connect = no_network
socket.create_connection = no_network

from tau2.data_model.tasks import Task
from tau2.domains.airline.data_model import FlightDB
from tau2.domains.airline.tools import AirlineTools
from tau2.domains.retail.data_model import RetailDB
from tau2.domains.retail.tools import RetailTools
from loguru import logger
logger.remove()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_db(domain):
    cls = FlightDB if domain == 'airline' else RetailDB
    return cls.load(TAU2 / f'data/tau2/domains/{domain}/db.json')


def snapshot(db, candidate):
    collection = db.reservations if candidate['domain'] == 'airline' else db.orders
    return {'entity': collection[candidate['entity_id']].model_dump(mode='json'),
            'user': db.users[candidate['user_id']].model_dump(mode='json')}


def replay(candidate, base):
    db = deepcopy(base)
    toolkit = AirlineTools(db) if candidate['domain'] == 'airline' else RetailTools(db)
    result = {'initial_state': snapshot(db, candidate), 'steps': []}
    for call in candidate['probe_calls']:
        before = db.get_hash()
        try:
            value = getattr(toolkit, call['name'])(**call['arguments'])
            step = {'call': call, 'accepted': True,
                    'result': value.model_dump(mode='json') if hasattr(value, 'model_dump') else value}
        except ValueError as exc:
            step = {'call': call, 'accepted': False, 'error': str(exc)}
        step['mutated'] = before != db.get_hash()
        step['post_state'] = snapshot(db, candidate)
        result['steps'].append(step)
        if not step['accepted']:
            break
    return result


def main():
    manifest = json.loads((HERE / 'conditional_governance_manifest.json').read_text())
    audit = json.loads((HERE / 'conditional_candidate_audit.json').read_text())
    tasks = json.loads((HERE / 'conditional_governance_tasks.json').read_text())
    exemptions = manifest.get('user_authorized_freeze_exemptions', {})
    drift = []
    for path, digest in manifest['frozen_file_sha256'].items():
        if sha(REPO / path) != digest:
            assert path in exemptions, path
            drift.append(path)
    for path, digest in manifest['artifact_sha256'].items():
        assert sha(HERE / path) == digest, path
    bases = {d: load_db(d) for d in ('airline', 'retail')}
    accepted = [c for c in audit['candidates'] if c['verdict'].startswith('ACCEPT_')]
    assert len(tasks) == len(accepted) == manifest['counts']['accepted_tasks']
    assert {t['id'] for t in tasks} == {c['task_id'] for c in accepted}
    for task in tasks:
        Task.model_validate(task)
        assert task['initial_state'] is None
    for c in audit['candidates']:
        actual = replay(c, bases[c['domain']])
        assert actual == c['backend_probe'], c['candidate_id']
        for clause in c['policy_clauses']:
            assert clause in (TAU2 / f'data/tau2/domains/{c["domain"]}/policy.md').read_text()
        if c['verdict'].startswith('ACCEPT_'):
            assert actual['steps'][-1]['accepted'] and actual['steps'][-1]['mutated']
            assert c['family'] == 'B' and c['independence_group'] == 'flown_override_business_cancel'
            state = actual['initial_state']['entity']
            assert state['cabin'] == 'business'
            statuses = [bases['airline'].flights[f['flight_number']].dates[f['date']].status for f in state['flights']]
            assert 'landed' in statuses and 'available' in statuses
    forbidden = ('tau2.agent', 'tau2.user', 'tau2.evaluator', 'tau2.runner', 'tau2.orchestrator')
    assert not any(m == p or m.startswith(p + '.') for m in sys.modules for p in forbidden)
    assert manifest['counts']['independent_accepted_states'] == len({c['independence_group'] for c in accepted}) == 1
    assert manifest['construction_verdict'] == 'INSUFFICIENT_NATIVE_CONDITIONAL_STATES'
    assert manifest['calls'] == dict.fromkeys(['Agent', 'UserSimulator', 'Evaluator', 'Judge'], 0)
    print(json.dumps({'static_validation': 'PASS', 'candidate_probes_reproduced': len(audit['candidates']),
                      'accepted_tasks': len(tasks), 'independent_accepted_states': 1,
                      'frozen_files_verified': len(manifest['frozen_file_sha256']) - len(drift),
                      'user_authorized_freeze_exemptions': drift,
                      'preservation_status': 'PASS_WITH_USER_AUTHORIZED_EXEMPTIONS' if drift else 'PASS',
                      'network_disabled': True, 'calls': manifest['calls'],
                      'construction_verdict': manifest['construction_verdict']}, indent=2))

if __name__ == '__main__':
    main()

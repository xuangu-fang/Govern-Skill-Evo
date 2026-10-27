from src.skill_evolution.v24.benchmark import current as benchmark_current
"""Exact citation extraction, lossless shared menus and targeted Repair inputs."""
from copy import deepcopy
import json
from src.skill_evolution.v24.facts import require

def select_targets(candidate, memory):
    """Only exact items in explicitly revised entries qualify as carried over."""
    old = {entry['id']: entry for entry in memory['entries']}
    revised = {mid for entry in candidate['entries'] for mid in entry['revises']}
    targets, inventory = [], []
    for ei, entry in enumerate(candidate['entries']):
        remaining = [(mid, ki, item) for mid in entry['revises']
                     for ki, item in enumerate(old[mid]['knowledge'])]
        for ki, item in enumerate(entry['knowledge']):
            target = {'entry_index': ei, 'knowledge_index': ki}
            match = next((i for i, (_, _, previous) in enumerate(remaining) if item == previous), None)
            row = {'target': target, 'revises': entry['revises']}
            if match is not None:
                mid, old_index, _ = remaining.pop(match)
                row.update(classification='unchanged', previous={'memory_id': mid, 'knowledge_index': old_index})
            else:
                row['classification'] = 'new' if not entry['revises'] else 'changed_or_added_in_revision'
                targets.append({'target': target, 'knowledge': deepcopy(item)})
            inventory.append(row)
    implicit = [{'memory_id': mid, 'knowledge_count': len(entry['knowledge'])}
                for mid, entry in old.items() if mid not in revised]
    return targets, {'candidate_items': inventory, 'untouched_memory_entries': implicit}


def extract(*args, **kwargs):
    return benchmark_current().evidence("knowledge_evidence.extract", *args, **kwargs)


def build_input(*args, **kwargs):
    return benchmark_current().evidence("knowledge_evidence.build_input", *args, **kwargs)

def menu_references(*args, **kwargs):
    return benchmark_current().evidence("knowledge_evidence.menu_references", *args, **kwargs)


def check_sources(*args, **kwargs):
    return benchmark_current().evidence("knowledge_evidence.check_sources", *args, **kwargs)


def menu_key(menu):
    require(isinstance(menu, list) and all(isinstance(action, str) for action in menu),
               'Action menu must be a list of strings')
    # Ordered tuple preserves duplicates and exact text; no identifier-only equality.
    return tuple(menu)


def compact(*args, **kwargs):
    return benchmark_current().evidence("knowledge_evidence.compact", *args, **kwargs)


def restore(*args, **kwargs):
    return benchmark_current().evidence("knowledge_evidence.restore", *args, **kwargs)


def verify_equivalence(original, value):
    restored = restore(value)
    # Python equality alone considers False == 0 and 1 == 1.0. Preserve JSON types too.
    exact = lambda obj: json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    require(exact(restored) == exact(original), 'Restored input differs from original')
    return {'valid': True, 'entire_input_equal': True, 'evidence_ids_equal': True,
            'local_menu_references_equal': True, 'raw_records_equal': True}

def build_repair_input(*args, **kwargs):
    return benchmark_current().evidence("knowledge_evidence.build_repair_input", *args, **kwargs)

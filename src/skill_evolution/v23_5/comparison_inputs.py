"""Freeze historical V23.4 inputs for a V23.5 single-round view comparison.

This is an evaluation boundary, not a conversion into a V23.5 production lineage.
No Diagnosis, Editor, Actor, Gate, or Memory publication is performed here.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

from src.skill_evolution.v23 import grouping, memory
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23.prompts import execution_context
from src.skill_evolution.v23_4 import preconditioner as source_pc, replay as source_replay
from . import evolution, preconditioner, replay
from .config import method_config
from .output_feedback import LEGACY
from .memory_view import MEMORY_V3, KNOWLEDGE_ONLY

FORMAT = 'v23_5_knowledge_only_single_round_v1'
ROUNDS = ('R03', 'R04', 'R05', 'R06')
STAGES = ('preconditioner', 'replay')
ARMS = {'memory_v3': MEMORY_V3, 'knowledge_only': KNOWLEDGE_ONLY}
CONTRACT = memory.MULTI_KNOWLEDGE_CONTRACT
read, save = evolution.read, evolution.save


def validate_spec(spec):
    require(set(spec) == {'question', 'hypothesis', 'rounds', 'call_config', 'max_attempts',
                         'max_input_chars', 'max_input_bytes', 'repetitions', 'retry_delay_seconds'},
            'Unexpected comparison configuration fields')
    require(spec['rounds'] == list(ROUNDS) and spec['repetitions'] == 1,
            'This protocol freezes R03-R06 once per arm')
    require(spec['max_attempts'] == 3, 'Use three total attempts per cell, including resumed attempts')
    require(all(type(spec[k]) is int and spec[k] > 0 for k in ('max_input_chars', 'max_input_bytes')),
            'Invalid input limits')
    require(isinstance(spec['retry_delay_seconds'], (int, float)) and 0 <= spec['retry_delay_seconds'] <= 60,
            'Invalid retry delay')
    require(all(isinstance(spec[k], str) and spec[k].strip() for k in ('question', 'hypothesis')),
            'Record the research question and hypothesis before running')
    cfg = spec['call_config']
    require(cfg == grouping.call_configuration(base_url=cfg['endpoint'].removesuffix('/chat/completions'),
            model=cfg['model'], max_tokens=cfg['max_tokens'], timeout=cfg['timeout_seconds']),
            'Call configuration must match the existing generator exactly')
    require(type(cfg['max_tokens']) is int and cfg['max_tokens'] > 0 and cfg['timeout_seconds'] > 0,
            'Invalid request budget')
    return spec


def selected(round_dir, stage):
    folder = round_dir/stage
    path = (folder/read(folder/'result.json')['path']).resolve()
    require(path.is_relative_to(folder.resolve()) and path.is_dir(), 'Selected attempt escapes its stage')
    return path


def collect_round(source, label):
    """Recheck the original loaders, raw pair records, and exact pre-round archive."""
    source = Path(source).resolve()
    rd = source/'rounds'/label
    number = int(label[1:])
    frozen = read(rd/'round_input.json')
    result = read(rd/'result.json')
    require(frozen['round_id'] == f'{source.name}_{label}' and frozen['state']['next_round'] == number,
            'Wrong historical round identity')
    require(result['status'] == 'completed' and result['before'] == frozen['state'],
            'Historical round not committed from this frozen input')
    prior = (source/frozen['state']['active_memory']).resolve()
    require(prior.is_relative_to(source), 'Prior Memory outside source campaign')
    state = read(prior/'active.json')
    permitted = [f'{source.name}_R{i:02}' for i in range(1, number)]
    require(state['commits'] == [cid for cid in permitted if cid in state['commits']],
            'Future, unknown, duplicate, or unordered Memory commits')
    current_memory = memory.load_memory(prior, memory_contract=CONTRACT)
    require(current_memory == frozen['memory'], 'Pre-round Memory differs from immutable archive')
    paths = {name: selected(rd, name) for name in ('grouping', 'diagnosis', 'preconditioner', 'editor', 'replay')}
    pc = source_pc.load_preconditioner(paths['preconditioner'], expected_memory_contract=CONTRACT)
    rp = source_replay.load_replay(paths['replay'], expected_memory_contract=CONTRACT)
    require(pc['memory'] == rp['payload']['memory'] == current_memory, 'Module inputs use different Memory')
    require(pc['facts']['parent'] == rp['payload']['parent'] == frozen['parent'], 'Historical Parent differs')
    pc_meta = read(paths['preconditioner']/'run.json')
    require(Path(pc_meta['diagnosis_directory']).resolve() == paths['diagnosis'] and
            Path(pc_meta['grouping_directory']).resolve() == paths['grouping'], 'Original Plan lineage differs')
    require(Path(rp['editor_directory']).resolve() == paths['editor'], 'Selected Editor differs')
    raw_pc = read(paths['preconditioner']/'input.json')
    raw_rp = read(paths['replay']/'input.json')
    records = {side: [read(p) for p in raw_rp['record_paths'][side]] for side in ('parent', 'candidate')}
    require([r['task']['id'] for r in records['parent']] == frozen['tasks'], 'Current task batch differs')
    review = raw_rp['pair_audit'][0].get('implementation_review')
    rebuilt = source_replay.build_replay(paths['editor'], records['parent'], records['candidate'],
                memory=current_memory, implementation_review=review, memory_contract=CONTRACT)
    require(raw_rp == {**rebuilt, 'record_paths': raw_rp['record_paths']}, 'Raw executions do not reproduce Replay input')
    require(raw_rp == read(rd/'pairs/input.json'), 'Paired evidence snapshot differs')
    replay_meta = read(paths['replay']/'run.json')
    require(replay_meta['input_view'] == source_replay.INPUT_VIEW and
            replay_meta['prompt_version'] == replay.LEARNING_PROMPT_VERSION,
            'Comparison baseline requires the validated P4 / Memory v3 input')
    return {'preconditioner': raw_pc, 'replay': raw_rp, 'prior': prior, 'state': state,
            'replay_memory_v3': read(paths['replay']/'model_input.json')['memory'],
            'selected': {k: str(v) for k, v in paths.items()}, 'round_input': frozen}


def messages(root, label, stage, arm):
    root = Path(root)
    method = method_config(ARMS[arm], retry_policy=LEGACY)
    material = read(root/'cases'/label/stage/'material.json')
    if stage == 'preconditioner':
        return preconditioner.messages_for(material, memory_view=ARMS[arm], memory_contract=CONTRACT)
    require(stage == 'replay', 'Unknown comparison stage')
    if arm == 'memory_v3':
        # Reuse the history view already validated by the original Replay loader.
        # Only the current facts and system prompt are composed here; no new source
        # inventory or archive fingerprint is needed for this fixed-input experiment.
        payload = replay.knowledge_model_input(material, memory_contract=CONTRACT)
        payload['memory'] = read(root/'cases'/label/'replay_memory_v3.json')
        system = replay.LEARNING_PROMPT_PATH.read_text().rstrip() + '\n\n' + execution_context(material['background'])
        system += '\n\n' + replay.MEMORY_FORMAT_PATH.read_text() + '\n\n' + replay.MULTI_VIEW_PATH.read_text()
        system += '\n\n' + replay.MULTI_FORMAT_PATH.read_text()
        return [{'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]
    return replay.messages_for(material, input_view=method['replay_input_view'], memory_contract=CONTRACT,
                               prompt_version=method['replay_prompt_version'])


def case_path(root, label, stage, arm):
    return Path(root)/'cases'/label/stage/arm


def prepare(source, root, spec):
    """Create a new immutable input set; never reuse or overwrite a partial freeze."""
    spec = deepcopy(validate_spec(spec))
    source, root = Path(source).resolve(), Path(root).resolve()
    require(not root.is_relative_to(source) and not source.is_relative_to(root), 'Comparison must be isolated from source')
    require(not root.exists(), 'Use a new comparison directory')
    collected = {label: collect_round(source, label) for label in ROUNDS}
    root.mkdir(parents=True)
    save(root/'config.json', spec)
    checks, cells = {}, []
    for label, row in collected.items():
        prior = root/'cases'/label/'memory_before'
        (prior/'archive').mkdir(parents=True)
        shutil.copyfile(row['prior']/'active.json', prior/'active.json')
        for cid in row['state']['commits']:
            shutil.copyfile(row['prior']/'archive'/f'{cid}.json', prior/'archive'/f'{cid}.json')
        require(memory.load_memory(prior, memory_contract=CONTRACT) == row['preconditioner']['memory'],
                'Copied archive does not reproduce pre-round Memory')
        save(root/'cases'/label/'replay_memory_v3.json', row['replay_memory_v3'])
        save(root/'cases'/label/'round_input.json', row['round_input'])
        checks[label] = {'selected_original_attempts': row['selected'], 'prior_memory_source': str(row['prior']),
                         'commits_before_round': row['state']['commits'], 'no_future_memory': True,
                         'original_lineage_verified': True, 'raw_pairs_rebuilt': True,
                         'task_ids': row['round_input']['tasks'], 'stages': {}}
        for stage in STAGES:
            material = row[stage]
            save(root/'cases'/label/stage/'material.json', material)
            views = {}
            # Counterbalance arm order over rounds; no additional sampling or calls.
            order = list(ARMS) if int(label[1:]) % 2 else list(reversed(ARMS))
            for arm in order:
                rendered = messages(root, label, stage, arm)
                encoded = json.dumps(rendered, ensure_ascii=False)
                require(len(encoded) <= spec['max_input_chars'] and len(encoded.encode()) <= spec['max_input_bytes'],
                        'Frozen input exceeds shared capacity; no truncation or fallback')
                dest = case_path(root, label, stage, arm)
                save(dest/'messages.json', rendered)
                views[arm] = json.loads(rendered[1]['content'])
                save(dest/'model_input.json', views[arm])
                (dest/'prompt.md').write_text(rendered[0]['content'])
                method = method_config(ARMS[arm], retry_policy=LEGACY)
                save(dest/'versions.json', method)
                cells.append({'round': label, 'stage': stage, 'arm': arm})
            current = [{k: v for k, v in views[a].items() if k != 'memory'} for a in ARMS]
            require(current[0] == current[1], 'Arms differ in current facts')
            full = material['memory'] if stage == 'preconditioner' else material['payload']['memory']
            require(all(v['memory']['entries'] == full['entries'] for v in views.values()), 'Knowledge content changed')
            checks[label]['stages'][stage] = {'current_facts_equal': True, 'knowledge_equal': True}
    save(root/'input_checks.json', checks)
    manifest = {'format': FORMAT, 'created_at': evolution.now(),
                'source_campaign': str(source), 'spec': spec,
                'arms': {a: method_config(v, retry_policy=LEGACY) for a, v in ARMS.items()}, 'cells': cells}
    save(root/'freeze.json', manifest)
    verify(root)
    return manifest


def verify(root):
    root = Path(root).resolve()
    manifest = read(root/'freeze.json')
    require(manifest['format'] == FORMAT, 'Unknown comparison input contract')
    validate_spec(manifest['spec'])
    require(read(root/'config.json') == manifest['spec'], 'Frozen configuration differs')
    require(manifest['arms'] == {a: method_config(v, retry_policy=LEGACY) for a, v in ARMS.items()}, 'Frozen method versions differ')
    expected_cells = [{'round': r, 'stage': s, 'arm': a} for r in ROUNDS for s in STAGES
                      for a in (list(ARMS) if int(r[1:]) % 2 else list(reversed(ARMS)))]
    require(manifest['cells'] == expected_cells, 'Missing, duplicated, or reordered cells')
    for cell in manifest['cells']:
        args = cell['round'], cell['stage'], cell['arm']
        rendered = messages(root, *args)
        folder = case_path(root, *args)
        require(read(folder/'messages.json') == rendered and
                read(folder/'model_input.json') == json.loads(rendered[1]['content']),
                'Saved model input differs from projection')
    return manifest

"""Import the immutable Step 4 state and the first, truncated Step 5 generation."""
from contextlib import contextmanager
from math import ceil
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from unittest.mock import patch

from skillopt.engine.trainer import _format_step_buffer
from src.adapters.officeqa.skillopt_budget import ATTEMPTS, TrainingPaused, digest
from src.skill_evolution.v28.benchmarks.searchqa.protocol import file_digest, require
from src.skill_evolution.v28.storage import freeze, read, save

STEP5 = Path('steps/step_0005')
ARCHIVED_ANALYST = '0bf939df92e44c71ae96b16dfa63f679'
PATCH_ORDER = ('succ_002', 'succ_001', 'fail_001', 'succ_003', 'succ_000', 'fail_000')
OLD_ENTRY_SHA256 = '57888dd5885e1c5bacf6c5acb2bf6745aa4c62172dfa72510fc590b34a273830'


def check_archived_run(project, recorded, identity):
    for key in ('actor', 'optimizer', 'data', 'test_workers', 'protocol'):
        require(recorded[key] == identity[key], f'Archived {key} differs')
    require(dict(identity['native'], out_root=recorded['native']['out_root']) == recorded['native'],
            'Archived native training settings differ')
    for name, expected in recorded['source_sha256'].items():
        # The historical receipt identifies the pre-retry launcher.
        actual = OLD_ENTRY_SHA256 if name == 'scripts/runs/skillopt/searchqa/run.py' else file_digest(project / name)
        require(expected == actual, f'Archived source differs: {name}')


def seed_attempt(staged, archive, identity):
    source = archive / 'model_calls' / ARCHIVED_ANALYST
    request = read(source / 'http_001_request.json')
    body = request['body']
    messages = body['messages']
    ids = re.findall(r'^### Trajectory [0-9]+ \(id=([0-9a-f]+)\)$', messages[-1]['content'], re.M)
    settings = identity['optimizer']
    require(len(ids) == len(set(ids)) == 8 and body == dict(messages=messages,
            max_tokens=settings['max_tokens'], **{k: settings[k] for k in
            ('model', 'temperature', 'stream', 'thinking', 'reasoning_effort')}) and
            request['url'] == identity['actor']['endpoint'], 'Unexpected archived analyst request')
    require(read(source / 'http_001_response_body.bin')['choices'][0]['finish_reason'] == 'length' and
            read(source / 'status.json')['http_attempts'] == 1, 'Expected the original truncated attempt')
    scope = [4, [(STEP5 / 'rollout/predictions').as_posix(), 'error', ids]]
    call = digest(['analyst', scope])
    directory = staged / 'model_calls' / call
    save(directory / 'input.json', dict(identity=scope, stage='analyst', messages=messages,
                                        max_completion_tokens=body['max_tokens'], max_attempts=ATTEMPTS))
    for name in ('http_001_request.json', 'http_001_response.json', 'http_001_response_body.bin'):
        shutil.copy2(source / name, directory / name)
    save(staged / 'step5_origin.json', dict(archived_call=ARCHIVED_ANALYST, imported_call=call,
                                            source=str(archive), last_completed_step=4))


def prepare_fork(root, source, identity):
    campaign = root / 'campaign'
    if campaign.exists():
        require((campaign / 'step5_origin.json').is_file(), 'Existing campaign did not start from Step 5')
        return
    archive = source / 'campaign'
    with TemporaryDirectory(dir=root, prefix='.prefix-') as tmp:
        staged = Path(tmp) / 'campaign'
        (staged / 'skills').mkdir(parents=True)
        history = read(archive / 'history.json')[:4]
        require([r['step'] for r in history] == [1, 2, 3, 4], 'Incomplete training prefix')
        save(staged / 'history.json', history)
        for i in range(5):
            skill = Path('skills') / f'skill_v{i:04d}.md'
            shutil.copy2(archive / skill, staged / skill)
            if i:
                part = Path('steps') / f'step_{i:04d}'
                (staged / part).mkdir(parents=True)
                for name in ('step_record.json', 'trajectory_digest.json'):
                    shutil.copy2(archive / part / name, staged / part / name)
        last = history[-1]
        require(last['current_origin'] == last['best_origin'] == 'step_0002' and
                    last['action'] == 'reject', 'Unexpected fork predecessor')
        shutil.copy2(staged / 'skills/skill_v0002.md', staged / 'best_skill.md')
        state = {k: last[k] for k in ('best_step', 'current_score', 'best_score', 'current_origin', 'best_origin')}
        save(staged / 'runtime_state.json', dict(state, last_completed_step=4,
             best_skill_path=str(campaign / 'best_skill.md'), current_skill_path=str(campaign / 'skills/skill_v0004.md')))
        for subdir in ('rollout', 'patches'):
            shutil.copytree(archive / STEP5 / subdir, staged / STEP5 / subdir)
        names = {f.stem for f in (staged / STEP5 / 'patches').glob('*.json')}
        require(names == {'minibatch_' + s for s in PATCH_ORDER[:-1]}, 'Unexpected Step 5 sibling patches')
        seed_attempt(staged, archive, identity)
        staged.rename(campaign)



def reflection_context(adapter, step_dir):
    step = int(step_dir.name.removeprefix('step_'))
    cfg = adapter._cfg
    per_epoch = ceil(cfg['train_size'] / (cfg['batch_size'] * cfg['accumulation']))
    epoch_start = step - (step - 1) % per_epoch
    buffer = []
    for i in range(epoch_start, step):
        prior = step_dir.parent / f'step_{i:04d}'
        digest = prior / 'trajectory_digest.json'
        if digest.exists():
            buffer.append(read(digest))
        else:
            require(read(prior / 'step_record.json')['action'].startswith('skip'),
                        f'Missing reflection history for step {i}')
    return _format_step_buffer(buffer)


@contextmanager
def verify_seeded_call(campaign, budget):
    """A changed reconstructed prompt must not silently replay an old journal."""
    origin = read(campaign / 'step5_origin.json')
    directory = campaign / 'model_calls' / origin['imported_call']
    seeded = read(directory / 'input.json')
    generate = budget.generate

    def checked(identity, stage, messages, cap):
        if identity[0] == 4 and stage == 'analyst':
            if identity != seeded['identity'] or messages != seeded['messages'] or cap != seeded['max_completion_tokens']:
                raise TrainingPaused('Step 5 analyst differs from its archived first attempt')
        return generate(identity, stage, messages, cap)

    with patch.object(budget, 'generate', checked):
        yield

"""Official DocVQA splits, native SkillOpt trainer, and a separate frozen Best Test."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
UPSTREAM = ROOT / 'external/SkillOpt'
sys.path[:0] = [str(ROOT), str(UPSTREAM), str(ROOT / 'external/SkillAdam')]

from skillopt.config import flatten_config, load_config
from skillopt.engine.trainer import ReflACTTrainer
from skillopt.envs.docvqa.adapter import DocVQAAdapter
from skillopt.utils.scoring import compute_score

from src.skill_evolution.v29.benchmarks.docvqa import actor, protocol, scoring
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
from src.skill_evolution.v29.stages import freeze_text
from src.skill_evolution.v29.storage import freeze, read, save
from src.skillopt_alfworld_native.project import sha
from src.skillopt_alfworld_native.transport import provider

CONFIG = ROOT / 'experiments/configs/docvqa_skillopt_deepseek_flash.yaml'
DEFAULT = ROOT / 'experiments/baselines/docvqa_skillopt_deepseek_flash'
require = protocol.require


class SharedDocVQA(DocVQAAdapter):
    _env_name = 'docvqa'  # Preserve benchmark-specific native analyst prompts.

    def __init__(self, cfg, dataset):
        super().__init__(**{k: cfg[k] for k in (
            'split_dir', 'split_mode', 'workers', 'max_turns', 'seed', 'max_completion_tokens',
            'exec_timeout', 'analyst_workers', 'minibatch_size', 'failure_only', 'edit_budget',
            'image_detail')})
        self.shared = DocVQAActorAdapter(dataset)
        self.shared.workers = self.workers
        self.setup(cfg)

    def setup(self, cfg):
        super().setup(cfg)
        dataset = self.shared.dataset
        for split in ('train', 'val', 'test'):
            items = self.dataloader.get_split_items(split)
            require([r['id'] for r in items] == dataset.source_ids[split], f'{split} IDs differ')
            for item in items:
                case = dataset.case(item['id'])
                require(case.metadata['source_split'] == split and item['answers'] == case.reference and
                        item['question'] == case.payload['question'] and
                        Path(item['image_path']).resolve() == dataset.root / case.payload['image_path'],
                        f"Source payload differs for {item['id']}")

    def rollout(self, env_manager, skill_content, out_dir, **kwargs):
        ids = [item['id'] for item in env_manager]
        splits = {self.shared.dataset.case(uid).metadata['source_split'] for uid in ids}
        require(splits in ({'train'}, {'val'}), 'Training rollout requires one Train or Val split')
        directory = Path(out_dir)
        if splits == {'val'}:
            require(ids == self.shared.dataset.source_ids['val'], 'Selection requires the full fixed Val set')
            directory = directory / hashlib.sha256(skill_content.encode()).hexdigest()
        skill_path = directory / 'skill.md'
        freeze_text(skill_path, skill_content)
        role = 'candidate' if splits == {'val'} else 'parent'
        records = self.shared.actor_batch(ids, skill_path, directory / 'batch', {'split': 'train', 'role': role})
        rows = []
        for item, record in zip(env_manager, records):
            execution = record['execution']
            predicted = execution['answer']['extracted_answer']
            hard, anls = execution['metrics']['hard'], execution['metrics']['anls']
            system, user = execution['initial_messages']
            user_text = user['content'][0]['text']
            question, answers = item['question'], item['answers']
            feedback = (f'[EVALUATION RESULT]\nQuestion: {question}\nPredicted answer: {predicted!r}\n'
                        f'Gold answers: {answers!r}\nANLS: {anls:.4f}')
            # Match the native direct-chat DocVQA transcript. Only the Actor sees image bytes.
            pred = directory / 'predictions' / item['id']
            freeze_text(pred / 'target_system_prompt.txt', system['content'])
            freeze_text(pred / 'target_user_prompt.txt', user_text)
            freeze(pred / 'conversation.json', [
                {'role': 'user', 'content': user_text + '\n\n[image] ' + Path(item['image_path']).name},
                {'type': 'message', 'turn': 1, 'content': execution['content']},
                {'role': 'system', 'content': feedback}])
            rows.append(dict(id=item['id'], question=question, task_type=item['task_type'],
                             task_description=question, hard=hard, soft=anls, predicted_answer=predicted,
                             response=execution['content'], agent_ok=True, n_turns=1,
                             image_paths=item['image_paths'], gold_answer=answers,
                             fail_reason=f"predicted '{predicted}' but expected one of {answers}" if anls <= 0 else ''))
        freeze_text(directory / 'results.jsonl', ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
        return rows


def prepare(root):
    cfg = flatten_config(load_config(str(CONFIG)))
    cfg.update(split_dir=str(ROOT / cfg['split_dir']), skill_init=str(UPSTREAM / cfg['skill_init']),
               out_root=str(root / 'campaign'))
    dataset = DocVQADataset(Path(cfg['split_dir']).parent)
    adapter = SharedDocVQA(cfg, dataset)
    for split, ids in dataset.source_ids.items():
        official = read(UPSTREAM / 'data/docvqa_id_split' / split / 'items.json')
        require(ids == [str(r['questionId']) for r in official], f'{split} differs from SkillOpt release')
    model = protocol.actor_config()
    require(cfg['target_model'] == cfg['optimizer_model'] == model['model'] and
            cfg['reasoning_effort'] == model['reasoning_effort'] and
            cfg['max_completion_tokens'] == model['max_tokens'] and cfg['exec_timeout'] == model['timeout_seconds'],
            'DeepSeek settings differ from the shared Actor')
    require(Path(cfg['skill_init']).read_text() == protocol.initial_skill(), 'Initial Skill differs')
    optimizer = dict(model=cfg['optimizer_model'], base_url=model['endpoint'].removesuffix('/chat/completions'),
                     reasoning_effort=model['reasoning_effort'], temperature=model['temperature'],
                     thinking=model['thinking'], stream=False, timeout_seconds=300, max_tokens=16384)
    files = [CONFIG, Path(__file__).resolve(), Path(cfg['skill_init']),
             ROOT / 'src/skillopt_alfworld_native/transport.py',
             ROOT / 'external/SkillAdam/skilladam/benchmarks/docvqa/evaluation.py']
    shared = Path(protocol.__file__).parent
    files.extend(shared / name for name in ('actor.py', 'adapter.py', 'dataset.py', 'protocol.py', 'scoring.py',
                                            'context/actor_system.md', 'context/actor_user.md'))
    files.extend(Path(cfg['split_dir']).glob('*/*.csv'))
    native = UPSTREAM / 'skillopt'
    files.extend(p for p in native.rglob('*') if p.suffix in {'.md', '.py'} and
                 ('envs' not in p.parts or p.parent == native / 'envs' or p.is_relative_to(native / 'envs/docvqa')))
    images = {row['image_path'] for row in dataset.rows.values()}
    identity = dict(native=cfg, revision=protocol.REVISION, split_ids=dataset.source_ids,
                    image_sha256={name: sha(dataset.root / name) for name in sorted(images)},
                    actor=model, optimizer=optimizer, test_workers=adapter.shared.test_workers,
                    source_sha256={str(p.relative_to(ROOT)): sha(p) for p in files})
    return cfg, adapter, identity


@contextmanager
def optimizer_provider(root, key, *, http_transport=None):
    # Other local experiments can configure overrides on the shared backend.
    overrides = {prefix + field: '' for prefix in ('OPENAI_COMPATIBLE_', 'OPTIMIZER_OPENAI_COMPATIBLE_')
                 for field in ('EXTRA_BODY', 'MAX_ATTEMPTS', 'CONNECT_TIMEOUT_SECONDS')}
    with patch.dict(os.environ, overrides), provider(root, api_key=key, http_transport=http_transport):
        yield


def selected_skill(root):
    receipt = read(root / 'selection.json')
    path = root / 'best_skill.md'
    require(sha(path) == receipt['sha256'], 'Best Skill differs from completed Selection')
    return path


def train(root, cfg, adapter):
    if (root / 'selection.json').exists():
        selected_skill(root)
        return read(root / 'selection.json')
    campaign = Path(cfg['out_root'])
    if not (campaign / 'summary.json').exists():
        ReflACTTrainer(dict(cfg), adapter).train()
    summary, state = read(campaign / 'summary.json'), read(campaign / 'runtime_state.json')
    steps = cfg['num_epochs'] * math.ceil(len(adapter.dataloader.train_items) / (cfg['batch_size'] * cfg['accumulation']))
    require(summary['total_steps'] == state['last_completed_step'] == steps and
            [r['step'] for r in read(campaign / 'history.json')] == list(range(1, steps + 1)),
            'Final Selection requires completed training')
    best = (campaign / 'best_skill.md').read_text()
    score, step = state['best_score'], state['best_step']
    current = Path(state['current_skill_path']).read_text()
    # The upstream combined train/test path checks the final candidate once more on Val.
    if current != best:
        items = adapter.build_eval_env(cfg['sel_env_num'], 'valid_seen', cfg['seed'])
        current_score, _ = compute_score(adapter.rollout(items, current, campaign / 'final_selection_eval'))
        if current_score > score:
            best, score, step = current, current_score, steps
    path = root / 'best_skill.md'
    freeze_text(path, best)
    receipt = dict(steps=steps, best_step=step, selection_hard=score,
                   selection_cases=cfg['sel_env_num'], sha256=sha(path))
    freeze(root / 'selection.json', receipt)
    return receipt


def test_best(root, adapter, repeat=1):
    require(type(repeat) is int and repeat >= 1, 'Test repeat must be a positive integer')
    best = selected_skill(root)
    directory = root / ('test' if repeat == 1 else f'test_repeat_{repeat}')
    ids = adapter.shared.dataset.source_ids['test']
    freeze(directory / 'evaluation.json', dict(tasks=ids, skill_sha256=sha(best), actor=protocol.actor_config(),
                                               workers=adapter.shared.test_workers, repeat=repeat))
    records = adapter.shared.actor_batch(ids, best, directory / 'runs', {'split': 'test', 'role': 'evaluation'},
                                         final=True)
    metrics = scoring.summarize_scores([dict(task_id=r['task_id'], metrics=r['execution']['metrics'])
                                        for r in records], ids)
    result = dict(status='complete', **metrics, api_requests=sum(r['execution']['api_requests'] for r in records))
    freeze(directory / 'summary.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='verify', choices=('verify', 'train', 'test'))
    parser.add_argument('--output', type=Path, default=DEFAULT, help='Training and frozen Test run directory')
    parser.add_argument('--repeat', type=int, help='Independent Test replicate, starting at 1')
    parser.add_argument('--report', type=Path, help='Offline verification report')
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    args = parser.parse_args()
    if args.repeat is not None and (args.action != 'test' or args.repeat < 1):
        parser.error('--repeat requires test and a positive integer')
    if args.report and args.action != 'verify':
        parser.error('--report applies to verify')
    root = args.output.resolve()
    if args.action == 'verify':
        from scripts.runs.skillopt.docvqa.verify import verify
        result = verify(root)
        if args.report:
            save(args.report, result)
    else:
        cfg, adapter, identity = prepare(root)
        if args.action == 'test':
            selected_skill(root)
        from scripts.runs.run_v29_pilot import read_credentials
        key = read_credentials(args.env_file, {'actor': identity['actor'], 'module_calls': {}})['OPENAI_API_KEY']
        with actor.locked(root):
            if not (root / 'run.json').exists():
                require(not any(p.name != '.execution.lock' for p in root.iterdir()), 'Run directory is not empty')
            freeze(root / 'run.json', identity, read_only=args.action == 'test')
            adapter.shared.transport = actor.ChatTransport(key)
            if args.action == 'train':
                freeze(root / 'optimizer.json', identity['optimizer'])
                with optimizer_provider(root, key):
                    result = train(root, cfg, adapter)
            else:
                result = test_best(root, adapter, args.repeat or 1)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

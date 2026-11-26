"""Native SkillOpt training with the shared SearchQA Actor and an independent Best Test."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
UPSTREAM = ROOT / 'external/SkillOpt'
sys.path[:0] = [str(ROOT), str(UPSTREAM), str(ROOT / 'external/SkillAdam')]

from skillopt.config import flatten_config, load_config
from skillopt.engine.trainer import ReflACTTrainer
from skillopt.envs.searchqa.adapter import SearchQAAdapter
from skillopt.utils.scoring import compute_score

from src.adapters.searchqa.skilladam import Batch60ActorAdapter
from src.skill_evolution.v28.benchmarks.searchqa import actor, protocol
from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
from src.skill_evolution.v28.evaluation import run_evaluation
from src.skill_evolution.v28.validation import operation
from src.skill_evolution.v28.stages import freeze, freeze_text, read
from scripts.runs.skillopt.searchqa.optimizer_retry import optimizer_provider, retry_config
from scripts.runs.skillopt.searchqa import step5

CONFIG = ROOT / 'experiments/configs/searchqa_skillopt_deepseek_flash.yaml'
ARCHIVE = ROOT / 'experiments/baselines/searchqa_skillopt_deepseek_flash'
DEFAULT = ROOT / 'experiments/baselines/searchqa_skillopt_deepseek_flash_shared_retry'
require = protocol.require


class SharedSearchQA(SearchQAAdapter):
    @property
    def _env_name(self):
        return 'searchqa'

    def __init__(self, cfg, dataset):
        super().__init__(**{k: cfg[k] for k in (
            'split_dir', 'split_mode', 'workers', 'max_turns', 'seed', 'max_completion_tokens',
            'exec_timeout', 'analyst_workers', 'minibatch_size', 'failure_only', 'edit_budget')})
        self.shared = Batch60ActorAdapter(dataset)
        self.setup(cfg)

    def setup(self, cfg):
        super().setup(cfg)
        # v28 merges Train and Val in its optimization view. Bind the original
        # split and payload before allowing the native loader to schedule either.
        dataset = self.shared.dataset
        for split in ('train', 'val', 'test'):
            items = self.dataloader.get_split_items(split)
            for item in items:
                case = dataset.case(item['id'])
                require(case.metadata['source_split'] == split and
                        item == {'id': case.case_id, **case.payload, 'answers': case.reference},
                        f'SkillOpt and shared Actor disagree on {case.case_id}')
        train = [r['id'] for r in self.dataloader.train_items + self.dataloader.val_items]
        test = [r['id'] for r in self.dataloader.test_items]
        require(train == dataset.splits['train'] and test == dataset.splits['test'],
                'SkillOpt split membership or order differs from the shared Actor')

    def reflect(self, results, skill_content, out_dir, **kwargs):
        step_dir = Path(out_dir)
        kwargs['step_buffer_context'] = step5.reflection_context(self, step_dir)
        patches = super().reflect(results, skill_content, out_dir, **kwargs)
        # The imported siblings originally finished asynchronously. Keep their
        # observed merge order when the missing analyst completes on the new run.
        if step_dir.name == 'step_0005' and (step_dir.parents[1] / 'step5_origin.json').exists():
            return [read(step_dir / 'patches' / f'minibatch_{name}.json') for name in step5.PATCH_ORDER]
        return patches

    def rollout(self, env_manager, skill_content, out_dir, **kwargs):
        directory = Path(out_dir)
        ids = [item['id'] for item in env_manager]
        splits = {self.shared.dataset.case(uid).metadata['source_split'] for uid in ids}
        require(splits in ({'train'}, {'val'}), 'Training rollout requires one non-Test split')
        if splits == {'val'}:
            # A restarted native step can propose a different candidate. Keep its
            # selection rollouts separate from an interrupted earlier proposal.
            directory = directory / protocol.digest(skill_content)
        skill = directory / 'skill.md'
        freeze_text(skill, skill_content)
        records = self.shared.actor_batch(ids, skill, directory / 'batch',
                                          {'split': 'train', 'role': 'candidate' if splits == {'val'} else 'parent'})
        rows = []
        for record in records:
            uid = record['task_id']
            case = self.shared.dataset.case(uid)
            execution = record['execution']
            predicted = execution['answer']['extracted_answer']
            em, f1 = execution['metrics']['em'], execution['metrics']['f1']
            question = case.payload['question']
            # The native analysts read these three files. Gold and scoring
            # feedback enter the transcript only after the Actor has finished.
            pred = directory / 'predictions' / uid
            system, user = execution['initial_messages']
            freeze_text(pred / 'target_system_prompt.txt', system['content'])
            freeze_text(pred / 'target_user_prompt.txt', user['content'])
            feedback = (f'[EVALUATION RESULT]\nQuestion: {question}\nPredicted answer: {predicted!r}\n'
                        f'Gold answers: {case.reference!r}\nExact Match: {em}\nF1: {f1:.4f}')
            freeze(pred / 'conversation.json', [
                {'type': 'message', 'turn': 1, 'content': execution['content']},
                {'role': 'system', 'content': feedback}])
            rows.append({'id': uid, 'question': question, 'hard': int(em), 'soft': f1,
                         'em': em, 'f1': f1, 'n_turns': 1, 'agent_ok': True,
                         'response': execution['content'], 'predicted_answer': predicted,
                         'gold_answers': case.reference, 'fail_reason': '' if em else
                         f"EM=0: predicted '{predicted}' but expected {case.reference}"})
        freeze_text(directory / 'results.jsonl', ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
        return rows


def prepare(root):
    cfg = flatten_config(load_config(str(CONFIG)))
    cfg.update(out_root=str(root / 'campaign'), split_dir=str(ROOT / cfg['split_dir']),
               skill_init=str(UPSTREAM / cfg['skill_init']))
    dataset = SearchQADataset(batch_size=60)
    adapter = SharedSearchQA(cfg, dataset)
    model = protocol.actor_config(60)
    require((cfg['target_model'], cfg['optimizer_model'], cfg['reasoning_effort']) ==
            (model['model'], model['model'], model['reasoning_effort']), 'Model alignment differs')
    require((cfg['workers'], cfg['exec_timeout'], cfg['max_completion_tokens']) ==
            (adapter.shared.workers, model['timeout_seconds'], model['max_tokens']), 'Actor settings differ')
    require(Path(cfg['skill_init']).read_bytes() ==
            (ROOT / 'experiments/configs/v28_searchqa_initial_skill.md').read_bytes(), 'Initial Skill differs')
    optimizer = dict(model=cfg['optimizer_model'], base_url=model['endpoint'].removesuffix('/chat/completions'),
                     reasoning_effort=model['reasoning_effort'], temperature=model['temperature'],
                     thinking=model['thinking'], stream=False, timeout_seconds=600, max_tokens=16384)
    native = UPSTREAM / 'skillopt'
    sources = [p for p in native.rglob('*') if p.suffix in {'.py', '.md'}
               and ('envs' not in p.parts or p.parent == native / 'envs'
                    or p.is_relative_to(native / 'envs/searchqa'))]
    sources.extend([Path(__file__), Path(step5.__file__),
                    Path(__file__).with_name('optimizer_retry.py'),
                    ROOT / 'src/adapters/officeqa/skillopt_optimizer.py', ROOT / 'src/adapters/officeqa/skillopt_budget.py',
                    ROOT / 'src/adapters/officeqa/execution.py', ROOT / 'src/skill_evolution/v27/json_response.py',
                    ROOT / 'src/adapters/searchqa/skilladam.py', Path(actor.__file__),
                    Path(protocol.__file__), Path(CONFIG)])
    shared = Path(actor.__file__).parent
    sources.extend(shared / name for name in ('adapter.py', 'scoring.py', 'dataset.py',
                                               'context/actor_user.md', 'context/actor_system.md'))
    sources.extend((ROOT / 'external/SkillAdam/skilladam/benchmarks/searchqa') / name
                   for name in ('rollout.py', 'evaluation.py'))
    identity = dict(native=cfg, actor=model, optimizer=optimizer, optimizer_retry=retry_config(),
                    test_workers=adapter.shared.test_workers,
                    data=dataset.snapshot(), protocol=protocol.implementation_identity(),
                    source_sha256={str(p.relative_to(ROOT)): protocol.file_digest(p) for p in sources})
    return cfg, adapter, identity


def selected_skill(root):
    receipt = read(root / 'selection.json')
    path = root / 'best_skill.md'
    require(protocol.file_digest(path) == receipt['sha256'], 'Best Skill differs from completed Selection')
    return path


def train(root, cfg, adapter):
    if (root / 'selection.json').exists():
        selected_skill(root)
        return read(root / 'selection.json')
    campaign = Path(cfg['out_root'])
    if not (campaign / 'summary.json').exists():
        ReflACTTrainer(dict(cfg), adapter).train()
    summary = read(campaign / 'summary.json')
    state = read(campaign / 'runtime_state.json')
    steps = cfg['num_epochs'] * ((cfg['train_size'] + cfg['batch_size'] - 1) // cfg['batch_size'])
    require(state['last_completed_step'] == summary['total_steps'] == steps and
            [r['step'] for r in read(campaign / 'history.json')] == list(range(1, steps + 1)),
            'Selection requires completed training')
    best = (campaign / 'best_skill.md').read_text()
    current = Path(state['current_skill_path']).read_text()
    score, step = state['best_score'], state['best_step']
    # Preserve upstream final Selection promotion while keeping Test separate.
    if current != best:
        items = adapter.build_eval_env(cfg['sel_env_num'], 'valid_seen', cfg['seed'])
        final_score, _ = compute_score(adapter.rollout(items, current, campaign / 'final_selection_eval'))
        if final_score > score:
            best, score, step = current, final_score, steps
    path = root / 'best_skill.md'
    freeze_text(path, best)
    receipt = dict(steps=steps, best_step=step, selection_em=score, selection_cases=cfg['sel_env_num'],
                   sha256=protocol.file_digest(path))
    freeze(root / 'selection.json', receipt)
    return receipt


def test_best(root, adapter):
    best = selected_skill(root)
    directory = root / 'test'
    with operation(adapter.shared):
        return run_evaluation(directory, adapter=adapter.shared, skill_file=best,
                              resume=(directory / 'plan.json').exists())


def train_formal(root, cfg, adapter, identity, key, *, from_step5=False, http_transport=None):
    require(not root.is_relative_to(ARCHIVE) and not ARCHIVE.is_relative_to(root),
            'The original formal archive is read-only; use a new run directory')
    with actor.locked(root):
        start = root / 'start.json'
        if not start.exists():
            require(not any(p.name != '.execution.lock' for p in root.iterdir()), 'New run needs an empty directory')
            freeze(start, {'from_step5': from_step5})
        archived_start = read(start)['from_step5']
        require(not from_step5 or archived_start, 'Cannot import Step 5 into an existing fresh run')
        freeze(root / 'run.json', identity)
        freeze(root / 'optimizer.json', identity['optimizer'])
        if archived_start:
            step5.check_archived_run(ROOT, read(ARCHIVE / 'run.json'), identity)
            step5.prepare_fork(root, ARCHIVE, identity)
        with optimizer_provider(root, key, http_transport=http_transport) as budget:
            with step5.verify_seeded_call(root / 'campaign', budget) if archived_start else nullcontext():
                return train(root, cfg, adapter)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='verify', choices=('verify', 'train', 'test'))
    parser.add_argument('--report', type=Path, help='Save the offline verification result as JSON')
    parser.add_argument('--output', type=Path, default=DEFAULT, help='Run directory for train and test')
    parser.add_argument('--from-step5', action='store_true', help='Import the archived Step 5 analyst attempt')
    args = parser.parse_args()
    if args.from_step5 and args.action != 'train':
        parser.error('--from-step5 applies to train')
    if args.report and args.action != 'verify':
        parser.error('--report applies to offline verification')
    root = args.output.resolve()
    cfg, adapter, identity = prepare(root)
    if args.action == 'verify':
        from scripts.runs.skillopt.searchqa.verify import verify
        result = verify(cfg, adapter, identity)
        if args.report:
            from src.skill_evolution.v28.storage import save
            save(args.report, result)
    else:
        if args.action == 'test':
            selected_skill(root)
        key = os.environ['OPENAI_API_KEY']
        adapter.shared.transport = actor.ChatTransport(key, metadata=identity['actor'])
        if args.action == 'train':
            result = train_formal(root, cfg, adapter, identity, key, from_step5=args.from_step5)
        else:
            with actor.locked(root):
                recorded = read(root / 'run.json')
                if 'optimizer_retry' in recorded:
                    freeze(root / 'run.json', identity, read_only=True)
                else:
                    step5.check_archived_run(ROOT, recorded, identity)
                result = {k: v for k, v in test_best(root, adapter).items() if k != 'cases'}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()

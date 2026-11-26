"""Native SkillOpt on the locally aligned LMB 35/18/124 split. Default action is offline."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
import skillopt
from skillopt.config import flatten_config, load_config
from skillopt.engine import trainer
from skillopt.envs.livemathematicianbench.adapter import LiveMathematicianBenchAdapter
from skillopt.envs.livemathematicianbench.evaluator import evaluate, extract_answer
from skillopt.utils.scoring import compute_score, skill_hash

from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.stages import freeze, freeze_text, read, save
from src.skill_evolution.v27.training import Case
from src.skill_evolution.v27_1.lmb import actor
from src.skillopt_alfworld_native.transport import provider, usage_summary

UPSTREAM = ROOT / 'external/SkillOpt'
PIN = '7da46ae693ee0329b80225c0128a37d65db10e9e'
CONFIG = ROOT / 'experiments/configs/lmb_skillopt_deepseek_flash.yaml'
REFERENCE = ROOT / 'experiments/launches/v27_12_lmb53_20261118/config.json'
ADAM = ROOT / 'experiments/launches/lmb53_skilladam_v27_5_official_flash_20261120_0020/config.json'
DEFAULT = ROOT / 'experiments/baselines/lmb_skillopt_deepseek_flash'
COMMON_IDS = ROOT / 'src/skill_evolution/v27/resources/lmb_ids.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_sources():
    # The LMB environment has the clean upstream wheel. The working checkout
    # also contains transport/Trainer changes for other benchmarks.
    installed = Path(skillopt.__file__).resolve().parent.parent
    entries = subprocess.check_output(['git', '-C', str(UPSTREAM), 'ls-tree', '-r', PIN, '--',
        'skillopt', 'configs/_base_/default.yaml', 'configs/livemathematicianbench/default.yaml'], text=True)
    for entry in entries.splitlines():
        meta, name = entry.split('\t')
        if name.startswith('skillopt/') and Path(name).suffix not in {'.py', '.md'}:
            continue
        path = (UPSTREAM if name.startswith('configs/') else installed) / name
        data = path.read_bytes()
        oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        require(oid == meta.split()[-1], f'SkillOpt differs from {PIN}: {name}')


def actor_cost(directory):
    requests = retries = unknown = input_tokens = output_tokens = 0
    for slot in directory.glob('**/actor/*/attempts/*/request_started.json'):
        requests += 1
        retries += int(slot.parent.name != '001')
        response = slot.with_name('response.json')
        usage = actor.usage_view(read(response) if response.exists() else {})
        unknown += int(usage['input_tokens'] is None or usage['output_tokens'] is None)
        input_tokens += usage['input_tokens'] or 0
        output_tokens += usage['output_tokens'] or 0
    scored = sum(1 for _ in directory.glob('**/actor/*/result.json'))
    return dict(scored=scored, request_slots=requests, retry_slots=retries,
                known_input_tokens=input_tokens, known_output_tokens=output_tokens, unknown_usage_slots=unknown)


def score(content, choices, label):
    correct = next(choice for choice in choices if choice['label'] == label)
    result = evaluate(content, correct, choices)
    answer = {k: result[k] for k in ('predicted_label', 'predicted_text', 'correct_label', 'correct_text')}
    return answer, {'em': result['em'], 'f1': result['f1']}


class LMBAdapter(LiveMathematicianBenchAdapter):
    @property
    def _env_name(self):
        return 'livemathematicianbench'

    def __init__(self, cfg, test_workers):
        super().__init__(**{key: cfg[key] for key in (
            'split_dir', 'split_mode', 'seed', 'shuffle_choices', 'max_turns', 'workers',
            'max_completion_tokens', 'exec_timeout', 'use_theorem', 'use_sketch',
            'analyst_workers', 'failure_only', 'edit_budget', 'minibatch_size')})
        self.setup(cfg)
        self.test_workers = test_workers
        self.transport = None

    def setup(self, cfg):
        super().setup(cfg)
        # The trainer reloads prepared_v1 at startup. Apply the local ID lists
        # after every load so rollout, validation gates and Best Test see the same split.
        loader = self.dataloader
        groups = {'train': loader.train_items, 'val': loader.val_items, 'test': loader.test_items}
        by_id = {row['id']: row for rows in groups.values() for row in rows}
        ids = read(COMMON_IDS)
        self.split = {uid: split for split, members in ids.items() for uid in members}
        require(len(by_id) == sum(map(len, groups.values())) == len(self.split) == 177
                and by_id.keys() == self.split.keys(), 'LMB split IDs differ from the source data')
        require([len(ids[k]) for k in ('train', 'val', 'test')] == [35, 18, 124]
                and self.split['202512:46'] == 'val', 'Unexpected local LMB split')
        for split, rows in groups.items():
            rows[:] = [by_id[uid] for uid in ids[split]]
        print('  [SkillOpt local LMB split] train=35 val=18 test=124')

    def _case(self, item, skill, directory):
        case = Case(item['id'], {k: item[k] for k in ('question', 'choices')},
                    {'label': item['correct_choice']['label']}, {'split': self.split[item['id']]})
        journal = directory / 'actor' / case.case_id
        record = actor.execute(case, skill, journal, self.transport)
        answer = record['answer']
        em = record['metrics']['em']
        outcome = {'termination': record['termination'], **answer, 'em': em}
        system, user = record['initial_messages']
        pred = directory / 'predictions' / case.case_id
        freeze_text(pred / 'target_system_prompt.txt', system['content'])
        freeze_text(pred / 'target_user_prompt.txt', user['content'])
        row = {'id': case.case_id, 'hard': int(em), 'soft': em, 'task_type': 'math_mcq',
               'n_turns': 1, 'agent_ok': True, 'predicted_answer': answer['predicted_label'],
               **outcome, 'api_requests': record['api_requests'], 'usage': record['usage_records']}
        if directory.name in ('rollout_prev', 'rollout_curr') or directory.parent.name == 'topup':
            # Match the pinned LMB process_one transcript consumed by native cross-epoch comparisons.
            prediction = answer['predicted_label'] or extract_answer(record['content'])
            row['predicted_answer'] = prediction
            row['fail_reason'] = '' if em else f"MCQ=0: predicted '{prediction}' but expected '{answer['correct_label']}'"
            verification = (
                f"[EVALUATION RESULT]\nQuestion: {item['question']}\n"
                f"Predicted label: {answer['predicted_label']!r}\nPredicted text: {answer['predicted_text']!r}\n"
                f"Correct label: {answer['correct_label']!r}\nCorrect text: {answer['correct_text']!r}\n"
                f"Exact Match: {em}"
            )
            conversation = [{'type': 'message', 'turn': 1, 'content': record['content']},
                            {'role': 'system', 'content': verification}]
        else:
            conversation = [{'role': 'assistant', 'content': record['content']},
                            {'role': 'system', 'content': json.dumps(outcome, ensure_ascii=False)}]
        freeze(pred / 'conversation.json', conversation)
        return row

    def _batch(self, items, skill, directory, workers):
        require(self.transport is not None, 'Missing Actor transport')
        ids = [i['id'] for i in items]
        require(ids and len(ids) == len(set(ids)), 'Empty or duplicate rollout')
        directory = Path(directory)
        freeze(directory / 'binding.json', {'ids': ids, 'skill': skill,
               'presentations': actor.p.digest([(i['question'], i['choices'], i['correct_choice']) for i in items])})
        # Use the shared Actor prompt and the native SkillOpt scorer.
        with patch.object(actor, 'score', score):
            with ThreadPoolExecutor(max_workers=workers) as pool:
                rows = list(pool.map(lambda item: self._case(item, skill, directory), items))
        freeze_text(directory / 'results.jsonl', ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
        return rows

    def rollout(self, env_manager, skill_content, out_dir, **kwargs):
        require({self.split[i['id']] for i in env_manager} in ({'train'}, {'val'}),
                'Training requires a single non-Test split')
        return self._batch(env_manager, skill_content, out_dir, self.workers)

    def test_best(self, root, cfg):
        selection = read(root / 'selection.json')
        best = root / 'best_skill.md'
        require(digest(best) == selection['sha256'], 'Best Skill differs from final Selection')
        items = self.build_eval_env(cfg['test_env_num'], 'valid_unseen', cfg['seed'])
        ids = [i['id'] for i in items]
        require(ids == read(COMMON_IDS)['test'], 'Unexpected Test membership or order')
        directory = root / 'test'
        try:
            rows = self._batch(items, best.read_text(), directory, self.test_workers)
        finally:
            completed = [r['id'] for r in items if (directory / 'actor' / r['id'] / 'result.json').is_file()]
            pending = set(ids).difference(completed)
            save(directory / 'coverage.json', {'total': len(items), 'scored_ids': completed,
                 'pending_ids': [r['id'] for r in items if r['id'] in pending]})
        wins = sum(r['hard'] for r in rows)
        summary = {'skill_sha256': selection['sha256'],
                   'common_124': {'completed': len(rows), 'correct': wins, 'em': wins / len(rows)},
                   'actor_requests': sum(r['api_requests'] for r in rows), 'actor_cost': actor_cost(directory)}
        freeze(root / 'test/summary.json', summary)
        return summary


def prepare(root):
    check_sources()
    cfg = flatten_config(load_config(str(CONFIG)))
    cfg.update(split_dir=str(ROOT / cfg['split_dir']), skill_init=str(UPSTREAM / cfg['skill_init']),
               out_root=str(root / 'campaign'))
    manifest = read(Path(cfg['split_dir']) / 'split_manifest.json')
    require(manifest == read(ROOT / 'src/skill_evolution/v27/resources/lmb_content_manifest.json')
            and manifest['content_revision'] == '6f53c5ff7227633ea954b2847cd590314d582047', 'Unexpected LMB release')
    for name, sha in manifest['output_sha256'].items():
        require(digest(Path(cfg['split_dir']) / name) == sha, 'Local split changed: ' + name)
    reference = read(REFERENCE)
    adam = read(resolve_experiment_path(ADAM))
    profile = reference['actor']
    require(profile == adam['actor'] == actor.p.ACTOR and
            (cfg['target_model'], cfg['optimizer_model']) == (profile['model'], profile['model']) and
            (cfg['max_completion_tokens'], cfg['exec_timeout'], cfg['reasoning_effort']) ==
            (profile['max_tokens'], profile['timeout_seconds'], profile['reasoning_effort']),
            'Actor/model settings differ from LMB reference')
    require(Path(cfg['skill_init']).read_bytes() == reference['initial_skill']['text'].encode(),
            'Unexpected initial Skill')
    adapter = LMBAdapter(cfg, adam['test_workers'])
    require((cfg['sel_env_num'], cfg['test_env_num']) ==
            (len(adapter.dataloader.val_items), len(adapter.dataloader.test_items)), 'Incomplete LMB evaluation')
    optimizer = dict(model=cfg['optimizer_model'], base_url=adam['optimizer']['base_url'],
                     temperature=profile['temperature'], reasoning_effort=profile['reasoning_effort'],
                     thinking=profile['thinking'], stream=False, timeout_seconds=profile['timeout_seconds'],
                     max_tokens=64000)  # Native stages select their own limit below this backend ceiling.
    identity = {'upstream': PIN, 'native': cfg, 'actor': profile, 'optimizer': optimizer,
                'test_workers': adapter.test_workers, 'data': manifest['output_sha256'],
                'content_revision': manifest['content_revision'], 'initial_skill_sha256': digest(Path(cfg['skill_init'])),
                'common_ids_sha256': digest(COMMON_IDS), 'launcher_sha256': digest(Path(__file__))}
    return cfg, adapter, identity


def train(root, cfg, adapter):
    campaign = Path(cfg['out_root'])
    if not (campaign / 'summary.json').exists():
        trainer.ReflACTTrainer(dict(cfg), adapter).train()
    state = read(campaign / 'runtime_state.json')
    require(state['last_completed_step'] == read(campaign / 'summary.json')['total_steps'] == 4 and
            [r['step'] for r in read(campaign / 'history.json')] == [1, 2, 3, 4], 'Training incomplete')
    current = Path(state['current_skill_path']).read_text()
    best = Path(state['best_skill_path']).read_text()
    best_score = state['best_score']
    final_score = best_score
    origin, step = state['best_origin'], state['best_step']
    if skill_hash(current) != skill_hash(best):
        val = adapter.build_eval_env(cfg['sel_env_num'], 'valid_seen', cfg['seed'])
        final_score, _ = compute_score(adapter.rollout(val, current, campaign / 'final_selection_eval'))
        if final_score > best_score:
            best, best_score, origin, step = current, final_score, state['current_origin'], 4
    freeze_text(root / 'best_skill.md', best)
    result = {'sha256': digest(root / 'best_skill.md'), 'best_step': step, 'best_origin': origin,
              'best_selection_em': best_score, 'final_selection_em': final_score, 'selection_cases': cfg['sel_env_num']}
    freeze(root / 'selection.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', nargs='?', default='verify', choices=('verify', 'train', 'test'))
    parser.add_argument('--output', type=Path, default=DEFAULT, help='Formal run directory for train/test')
    parser.add_argument('--report', type=Path, help='Write offline acceptance results as JSON')
    args = parser.parse_args()
    if args.report and args.stage != 'verify':
        parser.error('--report belongs to offline verify')
    root = args.output.resolve()
    cfg, adapter, identity = prepare(root)
    if args.stage == 'verify':
        from scripts.runs.skillopt.lmb.verify import verify
        result = verify(cfg, adapter, identity)
        if args.report:
            save(args.report, result)
    else:
        if args.stage == 'test':
            require((root / 'selection.json').is_file(), 'Test requires completed final Selection')
        from scripts.runs.run_v27_2_campaign import read_credentials
        key = read_credentials(ROOT / '.env.v27_12', read(REFERENCE))['OPENAI_API_KEY']
        adapter.transport = actor.ChatTransport(key, metadata=identity['actor'])
        with actor.locked(root):
            freeze(root / 'run.json', identity, read_only=args.stage == 'test')
            if args.stage == 'train':
                freeze(root / 'optimizer.json', identity['optimizer'])
                try:
                    with provider(root, api_key=key):
                        result = train(root, cfg, adapter)
                finally:
                    save(root / 'training_cost.json', {'actor': actor_cost(root / 'campaign'),
                         'optimizer': usage_summary(root)['optimizer']})
            else:
                result = adapter.test_best(root, cfg)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

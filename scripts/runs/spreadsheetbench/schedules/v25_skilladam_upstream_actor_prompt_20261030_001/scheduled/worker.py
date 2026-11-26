"""Frozen SheetBench training/test worker. Real execution requires the scheduled deadline."""
import argparse
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[6]
HOME = ROOT / 'experiments/comparisons/v25_skilladam_upstream_actor_prompt_20261030_001/scheduled_run'
PUBLISHED = ROOT / 'experiments/methods/v25/v25_skilladam_upstream_actor_prompt_20261030_001_v25/config'
V25_RECORD = ROOT / 'artifacts/methods/v25/v25_skilladam_upstream_actor_prompt_20261030_001_v25'


def folder_for(side):
    return V25_RECORD if side == 'v25' else ROOT / 'artifacts/methods/skilladam/spreadsheetbench/upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam'


def module_for(side, name):
    from importlib import import_module
    package = 'src.skill_evolution.v25'
    if side == 'v25':
        package += '.revisions.upstream_actor_scheduled'
    else:
        package = 'src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.scheduled.actor_runtime'
    return import_module(package + '.' + name)


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def verify_files():
    for path, expected in read(HOME / 'manifest.json')['files'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen scheduled execution file changed: ' + path)


def credentials(schedule, side, config):
    from dotenv import dotenv_values
    official = dotenv_values(schedule['official_env'])
    if official.get('OPENAI_BASE_URL', '').rstrip('/') != 'https://api.deepseek.com' or not official.get('OPENAI_API_KEY'):
        raise ValueError('Official DeepSeek credentials are unavailable or routed incorrectly')
    if config['actor_base_url'].rstrip('/') == 'https://api.deepseek.com':
        key = official['OPENAI_API_KEY']
    else:
        proxy = dotenv_values(schedule['actor_proxy_env'])
        if proxy.get('OPENAI_COMPATIBLE_BASE_URL', '').rstrip('/') not in (
                'http://llm-proxy.intra.didiglobal.com', 'http://llm-proxy.intra.xiaojukeji.com'):
            raise ValueError('Expected the existing intranet proxy credential source')
        key = proxy.get('OPENAI_COMPATIBLE_API_KEY')
        if not key or key.lower().startswith(('your-', 'your_', 'sk-your')):
            raise ValueError('Intranet Actor credential is missing or a placeholder')
    os.environ['OPENAI_API_KEY'] = key
    os.environ['OPENAI_BASE_URL'] = config['actor_base_url']
    return official['OPENAI_API_KEY']


def native_backend(native, bridge, shared, cfg, output, official_key):
    """Persist successful calls for exact replay; only granted Momentum failures get extra HTTP calls."""
    from skilladam.methods.skilladam import _generation_payload, _generation_from_payload
    class Backend(native.backend_type(bridge)):
        def __init__(self):
            super().__init__(shared, cfg, output, optimizer=native.native_transport(
                bridge, shared, cfg, output, api_key=official_key))
            self.call_indices = defaultdict(int)

        def generate(self, request):
            pair = (self.iteration, request.stage)
            number = self.call_indices[pair]; self.call_indices[pair] += 1
            directory = output / 'logical_calls' / f'{self.iteration:03}_{request.stage}_{number:03}'
            signature = {'stage': request.stage, 'messages': [dict(m) for m in request.messages],
                'context': asdict(request.context), 'metadata': dict(request.metadata)}
            signature = json.loads(json.dumps(signature, default=dict))
            signature_path = directory / 'request.json'
            if signature_path.exists():
                if read(signature_path) != signature:
                    raise ValueError('Resume logical request changed')
            else:
                save(signature_path, signature)
            cached = directory / 'success.json'
            if cached.exists():
                return _generation_from_payload(read(cached))
            started = directory / 'initial_started.json'
            if not started.exists():
                save(started, {'at': now()})
                try:
                    result = self.optimizer.generate(request)
                    if request.stage == 'momentum_update':
                        # Validate on a copy before native apply; no output rewriting or extra feedback.
                        self.validate_output(request, result)
                    save(cached, _generation_payload(result))
                    return result
                except Exception as exc:
                    save(directory / 'failure.json', {'kind': request.stage, 'error_type': type(exc).__name__, 'at': now()})
                    raise
            if request.stage != 'momentum_update' or not (directory / 'grant.json').exists():
                raise ValueError('Interrupted optimizer call requires an authorized Momentum grant')
            if read(directory / 'grant.json') != {'schema': 'momentum_extra3_v1', 'request_sha256': digest(signature), 'extra': 3}:
                raise ValueError('Momentum grant signature differs')
            attempt_cfg = deepcopy(cfg)
            attempt_cfg['optimizer_transport']['sdk_max_retries'] = 0
            single = native.native_transport(bridge, shared, attempt_cfg, output, api_key=official_key)
            while len(list(directory.glob('extra_*.json'))) < 3:
                number = len(list(directory.glob('extra_*.json'))) + 1
                # Reserve BEFORE sending: a crash cannot reset an allowance.
                save(directory / f'extra_{number:02}.json', {'at': now(), 'sdk_max_retries': 0})
                try:
                    result = single.generate(request)
                    self.validate_output(request, result)
                    save(cached, _generation_payload(result))
                    return result
                except Exception as exc:
                    save(directory / f'error_extra_{number:02}.json', {'error_type': type(exc).__name__, 'at': now()})
            raise ValueError('Momentum extra-three request budget exhausted')
    return Backend()


def train(side, folder, config, official_key, resume):
    ev = module_for(side, 'evolution')
    output = folder / 'campaign'
    if side == 'v25':
        if not resume and output.exists():
            raise ValueError('Existing campaign requires explicit resume')
        result = ev.run_campaign(output, config=None if resume else config, resume=resume)
        if result.get('status') != 'complete':
            raise ValueError('V25 returned before the entire campaign completed')
        final = ev.final_parent(output)
        if final is None:
            raise ValueError('V25 final Skill is missing')
        (folder / 'final_skill.md').write_bytes(final.read_bytes())
        save(folder / 'training_complete.json', {'status': 'complete', 'rounds': len(config['batches']),
            'skill_sha256': hashlib.sha256(final.read_bytes()).hexdigest(), 'at': now()})
    else:
        from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.scheduled.bridge import spreadsheetbench_native_optimizer as native
        bridge = native.load_bridge(folder)
        from src.skill_evolution.skilladam.spreadsheetbench.layout import UPSTREAM_CONFIG
        cfg = read(UPSTREAM_CONFIG / 'skilladam.json')
        if not resume and output.exists():
            raise ValueError('Existing campaign requires explicit resume')
        backend = native_backend(native, bridge, config, cfg, output, official_key)
        runner = bridge.AlignedRunner(config=bridge.native_config(cfg), adapter=bridge.AlignedAdapter(folder),
            backend=backend, context=bridge.context_for(config, cfg), output_dir=output)
        # Before the first Gate there is no checkpoint. Exact successful generations and Actors are replayed.
        checkpoint_resume = resume and (output / 'checkpoint.json').exists()
        result = runner.run(cases=bridge.cases_for(config, cfg),
            initial_skill=(UPSTREAM_CONFIG / 'initial_skill.md').read_text(), resume=checkpoint_resume)
        save(output / 'completion.json', {'status': 'complete',
            'iterations': [r.to_dict() for r in result.feedback_loop.iterations], 'at': now()})
        checkpoint = read(output / 'checkpoint.json')
        if checkpoint['next_iteration'] != 8 or len(checkpoint['iterations']) != 8 or checkpoint['pending_post_decision'] is not None:
            raise ValueError('SkillAdam did not finish all eight batches and Momentum updates')
        if (output / 'final_skill.md').read_text() != checkpoint['current_skill']:
            raise ValueError('Final Skill differs from checkpoint')
        (folder / 'final_skill.md').write_bytes((output / 'final_skill.md').read_bytes())
        save(folder / 'training_complete.json', {'status': 'complete', 'rounds': 8,
            'skill_sha256': hashlib.sha256((folder / 'final_skill.md').read_bytes()).hexdigest(), 'at': now()})


def completed_training():
    for name in ('v25', 'skilladam'):
        folder = folder_for(name)
        receipt = read(folder / 'training_complete.json')
        if receipt['status'] != 'complete' or receipt['rounds'] != 8:
            raise ValueError('Both complete training runs are required before Test')
        if hashlib.sha256((folder / 'final_skill.md').read_bytes()).hexdigest() != receipt['skill_sha256']:
            raise ValueError('Final Skill changed after training')
        if name == 'v25':
            state = read(folder / 'campaign/state.json')
            if state['next_round'] != 9:
                raise ValueError('V25 round publication is incomplete')
            for number in range(1, 9):
                if read(folder / f'campaign/rounds/R{number:02}/result.json')['status'] != 'completed':
                    raise ValueError('V25 round is incomplete')
            if (folder / 'campaign' / state['parent']).read_bytes() != (folder / 'final_skill.md').read_bytes():
                raise ValueError('V25 selected Skill differs')
        else:
            checkpoint = read(folder / 'campaign/checkpoint.json')
            if (checkpoint['next_iteration'] != 8 or len(checkpoint['iterations']) != 8
                    or checkpoint['pending_post_decision'] is not None or checkpoint['terminal_stop_reason']):
                raise ValueError('SkillAdam checkpoint is incomplete')
            if checkpoint['current_skill'] != (folder / 'final_skill.md').read_text():
                raise ValueError('SkillAdam selected Skill differs')


def test(side, folder, config, resume):
    evaluation = module_for(side, 'evaluation')
    actor = module_for(side, 'benchmarks.spreadsheetbench.actor')
    ev = module_for(side, 'evolution')
    completed_training()
    compatibility = load('scheduled_test_scoring', folder / 'test_scoring.py')
    reference = read(read(HOME / 'schedule.json')['test_reference'])
    test_config = deepcopy(config)
    # Reuse the already audited full-280 metadata interpretation; no training or Actor input changes.
    for key in config['test_tasks']:
        before, after = config['task_items'][key], reference['task_items'][key]
        if {k:v for k,v in before.items() if k != 'answer_region'} != {k:v for k,v in after.items() if k != 'answer_region'}:
            raise ValueError('Test input differs from audited source')
        if key != 'test:60-7' and before != after:
            raise ValueError('Unexpected metadata correction')
        test_config['task_items'][key] = deepcopy(after)
    test_config['dataset']['metadata_issues'] = []
    test_config['dataset']['scoring_compatibility'] = reference['dataset']['scoring_compatibility']
    skill = (folder / 'final_skill.md').read_text()
    if len(config['test_tasks']) != 280:
        raise ValueError('Full Test split required')
    bundle = {'campaign': str(folder / 'campaign'), 'skill_text': skill,
        'actor_config': test_config, 'tasks': [test_config['task_items'][key] for key in config['test_tasks']],
        'initial_reference': None, 'evaluation_policy': 'Frozen final Skill, 280 Test tasks; no optimization; audited scoring compatibility'}
    def invoke(key, skill_path, directory, cfg):
        return actor.run(cfg['task_items'][key], Path(skill_path).read_text(), directory, cfg, score=compatibility.score)
    result = evaluation.run(folder / 'test', resume=resume, bundle=bundle, runner=invoke)
    if result['completed'] != 280:
        raise ValueError('Incomplete Test')
    save(folder / 'test_complete.json', {'status': 'complete', 'completed': 280,
        'hard': result['hard'], 'success': result['success'], 'at': now()})


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['check', 'train', 'test'])
    p.add_argument('--side', required=True, choices=['v25', 'skilladam'])
    p.add_argument('--resume', action='store_true')
    args = p.parse_args()
    verify_files()
    schedule = read(HOME / 'schedule.json'); folder = folder_for(args.side)
    sys.path.insert(0, str(ROOT))
    from src.skill_evolution.skilladam.spreadsheetbench.layout import UPSTREAM, UPSTREAM_CONFIG, read_actor_config
    sys.path.insert(0, str(UPSTREAM))
    os.environ['PYTHONPATH'] = os.pathsep.join((str(ROOT), str(UPSTREAM)))
    os.chdir(ROOT)
    ev = module_for(args.side, 'evolution')
    using_benchmark = module_for(args.side, 'benchmark').using_benchmark
    SpreadsheetBenchAdapter = module_for(args.side, 'benchmarks.spreadsheetbench.adapter').SpreadsheetBenchAdapter
    config = read(PUBLISHED / 'config.json') if args.side == 'v25' else read_actor_config(UPSTREAM_CONFIG / 'shared_config.json')
    official_key = credentials(schedule, args.side, config)
    with using_benchmark(SpreadsheetBenchAdapter()):
        ev.validate_config(config); ev.check_live_environment(config)
        expected_runtime = read(PUBLISHED / 'prepared/runtime.json')
        if ev.runtime_snapshot(config) != expected_runtime:
            raise ValueError('Docker runtime differs from the prepared experiment')
        if args.action == 'check':
            print(json.dumps({'side': args.side, 'status': 'passed', 'model_requests': 0,
                'credential_sources_present': True, 'runtime_matches': True})); return
        if datetime.now(timezone.utc) < datetime.fromisoformat(schedule['not_before']):
            raise ValueError('Scheduled start time has not arrived')
        with (folder / '.worker.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            process = folder / f'{args.action}_process.json'
            save(process, {'status': 'running', 'pid': os.getpid(), 'at': now(), 'resume': args.resume})
            try:
                if args.action == 'train': train(args.side, folder, config, official_key, args.resume)
                else: test(args.side, folder, config, args.resume)
                save(process, {'status': 'complete', 'pid': os.getpid(), 'at': now()})
            except BaseException as exc:
                # Detailed traceback stays in local process log; never dump environment or credentials.
                save(process, {'status': 'stopped', 'pid': os.getpid(), 'at': now(), 'error_type': type(exc).__name__})
                traceback.print_exc(); raise SystemExit(1)


if __name__ == '__main__':
    main()

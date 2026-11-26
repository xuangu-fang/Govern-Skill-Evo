"""SpreadsheetBench v25.1 Actor with v25.5 training evidence and native SkillAdam summaries."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.skilladam.spreadsheetbench.layout import ALIGNED_CONFIG as BASELINE, UPSTREAM, read_actor_config
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.bridge import spreadsheetbench_native_optimizer as native
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.native_cache import cached_native
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime.benchmarks.spreadsheetbench import timeline

bridge = native.load_bridge(BASELINE)


def summary_input(record, native_user):
    # This is the same formal execution view: temporary format repair and
    # unexecuted generations have already been excluded by build_facts.
    facts = bridge.facts.build_facts([record])['facts']
    run, = timeline.project(facts)['runs']
    outcome = run.pop('outcome')
    # Keep SkillAdam's own label and judgment metrics alongside the scored submission.
    _, marker, judgment = native_user.rpartition('\n\n## Outcome\n')
    bridge.require(bool(marker), 'Missing native summary outcome')
    return ('## Execution Trace (execution_only_v1)\n\n'
            'initial.messages contains the original Actor context. attempts are in execution order. '
            'Only feedback_to_actor was returned to the Actor.\n\n'
            + json.dumps(run, ensure_ascii=False, separators=(',', ':'))
            + '\n\n## Post-submission outcome (not visible to the Actor)\n\n'
            + json.dumps(outcome, ensure_ascii=False, separators=(',', ':')) + marker + judgment)


class FeedbackRunner(bridge.AlignedRunner):
    def _generate(self, *, stage, messages, metadata):
        if stage == 'trajectory_compression':
            task_id = metadata['case_id']
            backend = self.backend
            ctx = backend.patch_context
            bridge.require(backend.iteration == ctx.iteration and task_id in ctx.training_case_ids,
                           'Summary must use the current training batch')
            slot = backend.rollout_counts[ctx.iteration, 'training_rollout'] - 1
            batch = backend.output / 'shared_actor' / f'iter_{ctx.iteration:03d}' / f'training_rollout_{slot}'
            record = bridge.read(batch / task_id.replace(':', '_') / 'trajectory.json')
            bridge.require(record['task'] == backend.shared['task_items'][task_id] and
                           record['skill'] == ctx.current_skill and
                           bridge.protocol.execution_history(record['protocol']),
                           'Summary source differs from the current training execution')
            system, user = messages
            bridge.require((system['role'], user['role']) == ('system', 'user'), 'Unexpected summary roles')
            messages = (system, {**user, 'content': summary_input(record, user['content'])})
        return super()._generate(stage=stage, messages=messages, metadata=metadata)


def prepare():
    shared = read_actor_config(BASELINE / 'shared_config.json')
    shared['actor_max_workers'] = 15
    cfg = bridge.read(BASELINE / 'skilladam.json')
    native.validate(bridge, shared, cfg)
    bridge.require(cfg['native']['trajectory_compression'] == 'llm', 'Expected native LLM compression')
    return shared, cfg


def test_bundle(campaign):
    cfg = read_actor_config(BASELINE / 'evaluation/config.json')
    cfg['actor_max_workers'] = 40
    state = bridge.read(campaign / 'checkpoint.json')
    skill = (campaign / 'final_skill.md').read_text()
    bridge.require([r['training_case_ids'] for r in state['iterations']] == cfg['batches']
                   and state['next_iteration'] == len(cfg['batches']) and state['pending_post_decision'] is None
                   and skill.strip() and skill == state['current_skill'], 'Final campaign Skill is not ready')
    return {'campaign': str(campaign), 'skill_text': skill, 'actor_config': cfg,
            'tasks': [cfg['task_items'][uid] for uid in cfg['test_tasks']], 'initial_reference': None,
            'evaluation_policy': 'Frozen final Skill, 280 tasks, no optimization or Skill update'}


def run_test(campaign, output):
    from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime import evaluation
    bundle = test_bundle(campaign)
    def invoke(task, skill_file, directory, config):
        return bridge.actor.run(config['task_items'][task], Path(skill_file).read_text(), directory, config)
    result = evaluation.run(output, bundle=bundle, runner=invoke, resume=(output / 'input.json').exists())
    bridge.require(result['status'] == 'complete' and len(result['tasks']) == 280
                   and [r['task_id'] for r in result['tasks']] == bundle['actor_config']['test_tasks'],
                   'Incomplete fixed-Skill test')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'train', 'test', 'train-test'), nargs='?', default='preflight')
    parser.add_argument('--output', type=Path, help='Training campaign directory')
    parser.add_argument('--test-output', type=Path, help='Separate directory for the fixed-Skill test')
    args = parser.parse_args()
    shared, cfg = prepare()
    if args.command == 'preflight':
        print(json.dumps({'training_cases': len(cfg['native']['optimization_case_ids']),
                          'batch_sizes': list(map(len, shared['batches'])), 'test_cases': len(shared['test_tasks']),
                          'model_requests': 0}))
        return
    if args.output is None:
        parser.error('A training campaign directory is required (--output)')
    output = args.output.resolve()
    testing = args.command in ('test', 'train-test')
    if testing and args.test_output is None:
        parser.error('Testing requires --test-output')
    if testing:
        test_output = args.test_output.resolve()
        if test_output.is_relative_to(output) or output.is_relative_to(test_output):
            parser.error('Training and test require separate directories')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Actor request workers invoke python -m; use the same frozen Actor in those children.
    os.chdir(ROOT)
    os.environ['PYTHONPATH'] = os.pathsep.join([str(ROOT), str(UPSTREAM)])
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=False)
    from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime.benchmark import using_benchmark
    with using_benchmark(bridge.SharedAdapter()):
        if args.command in ('train', 'train-test'):
            backend = cached_native(native, bridge, shared, cfg, output, os.environ['OPENAI_API_KEY'])
            runner = FeedbackRunner(config=bridge.native_config(cfg), adapter=bridge.AlignedAdapter(BASELINE),
                                    backend=backend, context=bridge.context_for(shared, cfg), output_dir=output)
            runner.run(cases=bridge.cases_for(shared, cfg), initial_skill=(BASELINE / 'initial_skill.md').read_text())
        if testing:
            result = run_test(output, test_output)
            print(json.dumps({k: result[k] for k in ('completed', 'success', 'hard', 'per_cell_pass_rate')}))


if __name__ == '__main__':
    main()

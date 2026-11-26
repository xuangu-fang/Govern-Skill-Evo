"""LMB design-to-runtime agreement, native parsing and immutable data boundary."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from unittest.mock import patch

from scripts.runs import run_v27_1_campaign as cli
from src.skill_evolution.v27.training import load_dataset
from src.skill_evolution.v27.benchmarks.lmb import protocol as old_protocol, scoring as old_scoring
from src.skill_evolution.v27_1.lmb import protocol as p, scoring
from src.skill_evolution.v27_1 import config as settings, evolution as ev, replay, memory
from .runtime_support import Base
from .support import bind, fresh, Generator
from .test_editor import offline


class AcceptanceTests(Base):
    def setUp(self):
        super().setUp(); offline(self)

    def test_frozen_design_data_schedule_and_exact_prompts(self):
        data = load_dataset(p.ROOT / 'data/livemathematicianbench/prepared_v1')
        config = ev.read(settings.DEFAULT_CONFIG)
        design = ev.read(p.ROOT / 'docs/methods/v27_1/experiment_plan.json')
        spec = ev.read(p.ROOT / 'docs/methods/v27_1/source_map.json')
        with fresh(data).using(): settings.validate_config(config, executable=True)
        self.assertEqual(config['batches'], design['schedule']['batches'])
        self.assertEqual(data.splits['test'], design['schedule']['test_ids'])
        self.assertEqual([len(b) for b in config['batches']], [10]*5+[3])
        self.assertEqual([len(data.source_splits[s]) for s in ('train','validation','test')], [35,18,124])
        self.assertEqual(config['method']['contracts'], spec['contracts'])
        self.assertEqual(config['method']['prompts'], {k:v['planned_prompt_version'] for k,v in spec['prompts'].items()})
        self.assertEqual(p.IDENTITY['execution_profile'], spec['identities']['actor_execution_profile'])
        self.assertEqual(config['actor']['max_tokens'], 65536)
        self.assertEqual(config['actor'], p.ACTOR)
        self.assertEqual(config['initial_skill']['text'],
                         (p.ROOT / 'docs/methods/v27_1/baseline/lmb/initial_skill.md').read_text())
        self.assertEqual({k:v['max_tokens'] for k,v in config['module_calls'].items()}, dict.fromkeys(settings.MODEL_MODULES,32768))
        self.assertTrue(all(v['timeout_seconds']==300 for v in config['module_calls'].values()))
        self.assertNotIn('context_window_tokens', config)
        for name, prompt in settings.render_prompts().items():
            self.assertEqual(prompt, (p.ROOT / f'docs/methods/v27_1/prompts/{name}.md').read_bytes().decode())
        output = self.root / 'never_started'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials')), redirect_stdout(io.StringIO()) as log:
            cli.main(['train',str(output),'--config',str(settings.DEFAULT_CONFIG),'--env-file','/missing','--validate-only'])
        self.assertEqual(json.loads(log.getvalue())['status'], 'valid')
        self.assertFalse(output.exists())

    def test_native_parser_equivalence_and_format_diagnostic_not_em(self):
        choices = [{'label':c,'text':f'Proposition {c}'} for c in 'ABCDE']
        cases = ['<answer>A</answer>','<ANSWER>\na\n</ANSWER>', 'explanation\nA):.',
                 '<answer>Proposition A</answer>', 'A because of a condition',
                 '<answer>B</answer>\n<answer>A</answer>', 'outside<answer>A</answer>',
                 '<answer>proposition a</answer>', 'unknown', '', '<answer>A', '<answer>B</answer>']
        for content in cases:
            with self.subTest(content=content):
                answer, metrics = scoring.score(content, choices, 'A')
                self.assertEqual((answer,metrics), old_scoring.score(content,choices,'A'))
                self.assertEqual(metrics['em'],metrics['f1'])
        answer, metrics = scoring.score('A',choices,'A')
        self.assertEqual(metrics['em'],1); self.assertFalse(answer['format_compliant'])
        for metrics in ({'em':0,'f1':.5}, {'em':True,'f1':True}):
            self.reject(p.score_view,metrics)
        self.reject(scoring.summarize_scores, [], ['task'])

    def test_old_actor_config_unchanged_and_no_global_binding(self):
        old = deepcopy(old_protocol.ACTOR)
        data, _, adapter, _ = bind(self.root)
        with adapter.using(): self.assertEqual(adapter.actor_adapter._actor['max_tokens'],65536)
        self.assertEqual(old_protocol.ACTOR,old)
        self.assertEqual(old_protocol.ACTOR['max_tokens'],49152)
        self.assertNotEqual(p.IDENTITY['execution_profile'],old_protocol.IDENTITY['execution_profile'])

    def test_em_unchanged_pairs_skip_replay_but_all_sources_still_validate(self):
        _, transport, adapter, config = bind(self.root,rounds=1,mode='none')
        root = self.root / 'unchanged'; generator=Generator(count=1)
        with adapter.using():
            ev.run_campaign(root,config=config,generate=generator)
            self.assertNotIn('replay',generator.calls)
            self.assertEqual(memory.load_memory(root/'memory')['memory']['rounds'][0]['entries'],[])
            bundle=ev.read(root/'rounds/R01/pairs/input.json')
            folder=root/'rounds/R01/parent_runs/actor'/adapter.actor_adapter.task_key(config['batches'][0][1])
            (folder/'trajectory.json').unlink()
            self.reject(replay.replay_call,bundle)
        self.assertEqual(transport.calls,4)

    def test_test_data_and_worker_mutations_fail_before_requests(self):
        data, transport, adapter, config=bind(self.root,rounds=1)
        for field, value, original in (('workers',1,20),('test_workers',15,16),('workers',True,20)):
            setattr(adapter.actor_adapter,field,value)
            self.reject(adapter._bound)
            setattr(adapter.actor_adapter,field,original)
        with adapter.using():
            cli.run_training(self.root/'campaign',config,generate=Generator(no_change='diagnosis'))
            cli.run_test(self.root/'campaign',self.root/'evaluation')
            self.reject(adapter.register_archive,self.root/'evaluation/runs')
            before=transport.calls
            data.rows[data.splits['test'][0]]['choices'][0]['text'] += ' changed'
            self.reject(cli.run_test,self.root/'campaign',self.root/'evaluation',resume=True)
            self.assertEqual(transport.calls,before)

"""Inherited input guards and real dotenv import, with synthetic credentials only."""
import importlib.metadata
import json
from unittest.mock import patch
from dotenv import dotenv_values

from . import test_offline as original
from src.skill_evolution.v27 import cli
from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter
from src.skill_evolution.v27.benchmarks.lmb import protocol as p
from src.skill_evolution.v27.config import campaign_config,validate_config
from src.skill_evolution.v27.evaluation import ArchiveTransport
from src.skill_evolution.v27.training import load_dataset


class RuntimeConfigTests(original.Base):
    def test_inherited_defaults_and_saved_configuration(self):
        data=load_dataset(original.ROOT/'data/livemathematicianbench/prepared_v1')
        adapter=LMBAdapter(data,ArchiveTransport(),gate_metric=p.EM_GATE)
        with using_benchmark(adapter):
            cfg=campaign_config(adapter);validate_config(cfg)
            self.assertEqual(cfg['max_input_chars'],4000000)
            self.assertEqual(cfg['max_message_utf8_bytes'],6000000)
            self.assertEqual(cfg['actor']['max_tokens'],49152)
            self.assertEqual(cfg['actor']['request_attempts_total'],6)
            self.assertEqual(cfg['max_attempts'],6)
            self.assertEqual({name:c['max_tokens'] for name,c in cfg['module_calls'].items()},
                {'grouping':16384,'diagnosis':32768,'preconditioner':32768,'editor':16384,'replay':32768})
            self.assertTrue(all('context_window_tokens' not in c for c in cfg['module_calls'].values()))
            saved=json.loads((original.ROOT/'experiments/configs/v27_lmb53_epoch1_deepseek_flash.json').read_text())
            validate_config(saved);self.assertEqual(saved,cfg)
            self.assertEqual([len(b) for b in cfg['batches']],[10]*5+[3])
            explicit=campaign_config(adapter,context_window_tokens=1048576)
            validate_config(explicit)
            self.assertTrue(all(c['context_window_tokens']==1048576 for c in explicit['module_calls'].values()))

    def test_credentials_entry_uses_installed_dotenv_with_synthetic_file(self):
        lock=(original.ROOT/'benchmarks/livemathematicianbench/requirements.lock.txt').read_text().splitlines()
        self.assertIn('python-dotenv=='+importlib.metadata.version('python-dotenv'),lock)
        fixture=self.root/'synthetic.env'
        fixture.write_text('OPENAI_API_KEY="SYNTHETIC_TEST_KEY"\nOPENAI_BASE_URL=https://api.deepseek.com\n')
        with patch('dotenv.dotenv_values',side_effect=lambda path:dotenv_values(fixture)) as loader:
            self.assertEqual(cli.credentials(),'SYNTHETIC_TEST_KEY')
            loader.assert_called_once_with(original.ROOT/'.env')
            fixture.write_text('OPENAI_BASE_URL=https://api.deepseek.com\n')
            self.reject(cli.credentials)
            fixture.write_text('OPENAI_API_KEY=SYNTHETIC_TEST_KEY\nOPENAI_BASE_URL=https://invalid.example\n')
            self.reject(cli.credentials)

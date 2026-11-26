"""Independent identities, reviewed prompts, and lightweight published history."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v28_2 import grouping as old_grouping
from src.skill_evolution.v28_3 import evolution as old_ev
from src.skill_evolution.v28_5 import config, diagnosis, preconditioner, editor, replay, gate, memory
from src.skill_evolution.v28_5 import evolution as ev, evaluation, output_feedback
from src.skill_evolution.v28_5.campaign import RUNTIME_VERSION
from src.skill_evolution.v28.benchmarks.searchqa import protocol
from tests.skill_evolution.v28.runtime_support import Base, snapshot
from tests.skill_evolution.v28_3.support import bind as old_bind
from .support import bind, fresh, Generator, no_hashes
from .test_editor import offline

ROOT = protocol.ROOT


class BindingTests(Base):
    def setUp(self):
        super().setUp(); offline(self); self.enterContext(no_hashes())
        self.data, self.actor, self.adapter, self.config = bind(self.root / 'fixture', rounds=1, size=1, mode='gain')
        self.enterContext(self.adapter.using())

    def complete(self):
        root = self.root / 'campaign'; gen = Generator(count=1)
        with patch.object(old_grouping, 'grouping_call', side_effect=AssertionError('No Grouping')):
            ev.run_campaign(root, config=self.config, generate=gen)
        self.assertEqual(gen.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'])
        self.assertFalse((root / 'rounds/R01/grouping').exists())
        self.assertEqual(ev.read(root / 'implementation.json')['runtime_version'], RUNTIME_VERSION)
        return root

    def test_runtime_prompt_texts_exactly_match_reviewed_artifacts(self):
        self.assertEqual(config.MODEL_MODULES, ('diagnosis', 'preconditioner', 'editor', 'replay'))
        for name, text in config.render_prompts().items():
            self.assertEqual(text, (ROOT / f'docs/methods/v28_5/prompts/{name}.md').read_text())
        for name in config.MODEL_MODULES:
            self.assertNotEqual(config.render_prompts()[name], (ROOT / f'docs/methods/v28_3/prompts/{name}.md').read_text())
        self.assertEqual({k: v['max_tokens'] for k, v in config.module_calls().items()},
                         {'diagnosis': 65536, 'preconditioner': 65536, 'editor': 65536, 'replay': 65536})

    def test_downstream_algorithms_and_new_source_bindings(self):
        for name in ('diagnosis', 'preconditioner', 'editor', 'replay', 'gate', 'memory', 'evolution', 'stages'):
            definitions = []
            for version in ('v28_3', 'v28_5'):
                source = (ROOT / f'src/skill_evolution/{version}/{name}.py').read_text()
                # Version labels in validation messages change with the binding;
                # compare executable definitions after that sole normalization.
                tree = ast.parse(source.replace('v28_3', 'VERSION').replace('v28_5', 'VERSION')
                                 .replace('v28.3', 'VERSION').replace('v28.5', 'VERSION'))
                definitions.append({n.name: ast.dump(n) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))})
            self.assertEqual(*definitions, name)
        self.assertIs(editor.preconditioner, preconditioner)
        self.assertIs(replay.editor, editor); self.assertIs(gate.replay, replay)
        self.assertIs(memory.gate, gate); self.assertIs(output_feedback.diagnosis, diagnosis)
        self.assertIs(evaluation.ev, ev)

    def test_grouping_and_old_identities_rejected_before_execution(self):
        for section in ('prompts', 'contracts', 'execution_input_views'):
            bad = deepcopy(self.config); bad['method'][section]['grouping'] = 'old'
            self.reject(config.validate_config, bad)
        for key in ('version', 'stage_contract'):
            bad = deepcopy(self.config); bad['method'][key] = 'v28_3_old'
            self.reject(config.validate_config, bad)
        bad = deepcopy(self.config); bad['module_calls']['grouping'] = deepcopy(bad['module_calls']['diagnosis'])
        self.reject(config.validate_config, bad)
        self.assertEqual(self.actor.seen, [])

    def test_cross_version_resume_rejected_without_relabeling(self):
        _, _, adapter, cfg = old_bind(self.root / 'old_data', rounds=1, size=1)
        old = self.root / 'old'; new = self.root / 'new'
        with adapter.using(): old_ev.initialize(old, cfg)
        before = snapshot(old); self.reject(ev.run_campaign, old, resume=True)
        self.assertEqual(snapshot(old), before)
        ev.initialize(new, self.config)
        before = snapshot(new)
        with adapter.using(): self.reject(old_ev.run_campaign, new, resume=True)
        self.assertEqual(snapshot(new), before)

    def test_completed_export_and_test_readiness_do_not_open_old_actor_sources(self):
        root = self.complete(); before = snapshot(root); adapter = fresh(self.data)
        with adapter.using(), patch.object(adapter.actor_adapter, 'read_batch', side_effect=AssertionError('Old Actor batch')), \
             patch.object(adapter, 'source_record', side_effect=AssertionError('Old Actor source')), \
             patch.object(memory, '_prepare', side_effect=AssertionError('Historical recomputation')):
            state = memory.load_memory(root / 'memory')
            selected = ev.final_parent(root)
            identity = evaluation.prepare_test(root, self.root / 'not_started_test')
        self.assertEqual(state['selection']['selected_text'], selected.read_text())
        self.assertEqual(identity['skill'], selected.read_text())
        self.assertEqual(snapshot(root), before)
        self.assertFalse((self.root / 'not_started_test').exists())

    def test_next_round_only_registers_current_evidence(self):
        data, actor, adapter, cfg = bind(self.root / 'two_data', rounds=2, size=2, mode='gain')
        root = self.root / 'two'; gen = Generator(count=1)
        with adapter.using():
            ev.run_round(root, config=cfg, generate=gen)
            original = adapter.register_archive
            def only_current(folder):
                self.assertIn('R02', Path(folder).parts)
                return original(folder)
            with patch.object(adapter, 'register_archive', side_effect=only_current):
                ev.run_campaign(root, generate=gen)
            self.assertTrue(all('R02' in p.parts for p in adapter._directories.values()))
        self.assertEqual(len(actor.seen), 8)

    def test_checkpoint_and_runtime_drift_rejected(self):
        root = self.complete()
        selected = ev.read(root / 'state.json')['parent']
        for name in (selected, 'state.json', 'implementation.json'):
            path = root / name; original = path.read_bytes()
            path.write_text('{}')
            self.reject(ev.final_parent, root)
            path.write_bytes(original)
        before = snapshot(root)
        self.assertTrue(ev.final_parent(root).is_file())
        self.assertEqual(snapshot(root), before)

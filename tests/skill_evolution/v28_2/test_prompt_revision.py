"""Prompt v2 binding and recovery boundaries; authored outputs do not test model judgment."""
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
import json
from unittest.mock import patch

from src.skill_evolution.v28.benchmarks.searchqa import protocol
from src.skill_evolution.v28_2 import config, diagnosis, preconditioner, grouping, editor, stages, evolution
from tests.skill_evolution.v28.runtime_support import Base, snapshot
from .support import bind, fresh, Generator, no_hashes
from .test_editor import offline

BASELINE = protocol.ROOT / 'docs/methods/v28_2/revisions/prompt_v2/baseline'


class PromptRevisionTests(Base):
    def setUp(self):
        super().setUp(); offline(self); self.enterContext(no_hashes())
        self.data, self.transport, self.adapter, self.config = bind(self.root, rounds=1)
        self.enterContext(self.adapter.using())

    def grouped(self):
        root = self.root / 'parents'
        records = self.adapter.actor_batch(self.data.batches[0], self.skill, root, {'split': 'train', 'role': 'parent'})
        self.adapter.register_archive(root)
        call = grouping.grouping_call(records, 'R01')
        raw = Generator()('grouping', call.messages, self.root, self.config['module_calls']['grouping'])
        return call.complete_text(raw['content'])

    def proposal(self):
        return {'decision': 'revise', 'reason': 'P1:1 and P2:1 support a scoped relation correction.',
                'plan': {'goal': 'Match the requested entity role while preserving required name components.',
                         'updates': [{'id': 'u1', 'text': self.correction,
                                      'basis': ['P1:1', 'P2:1']}]}}

    correction = ('Use the question and context to distinguish the requested entity role from an associated entity.\n'
                  'Select the entity satisfying that relation and preserve components needed to distinguish it.\n'
                  'Respect a requested abbreviation; otherwise do not impose abbreviation on complete names.\n')

    def test_config_and_prompt_changes_are_limited_to_two_versioned_resources(self):
        old = stages.read(BASELINE / 'campaign_config.json')
        expected = deepcopy(old)
        for name in ('diagnosis', 'preconditioner'):
            expected['method']['prompts'][name] = f'v28_2_searchqa_{name}_v2'
        actual = stages.read(config.DEFAULT_CONFIG)
        self.assertEqual(actual, expected)
        rendered = config.render_prompts()
        changed = []
        for name, text in rendered.items():
            baseline = (BASELINE / 'prompts' / f'{name}.md').read_text()
            if text != baseline: changed.append(name)
            self.assertEqual(text, self.adapter.resource(f'{name}.md').read_text())
            # SearchQA evidence, scorer, shared inputs and Actor protocol precede
            # the edited guidance; these must remain byte-for-byte identical.
            boundary = {'diagnosis': '## Identify a justified decision change',
                        'preconditioner': '## Frozen proposal and available input'}.get(name)
            if boundary: self.assertEqual(text.split(boundary)[0], baseline.split(boundary)[0])
            for suffix in ('## Evidence', '## Exact output contract', '## Execution reference lists'):
                if suffix in baseline:
                    self.assertEqual(text.split(suffix, 1)[1], baseline.split(suffix, 1)[1])
        self.assertEqual(changed, ['diagnosis', 'preconditioner'])
        self.assertEqual(config.contracts(), old['method']['contracts'])
        self.assertEqual(config.prompt_versions(), actual['method']['prompts'])

    def test_old_config_and_campaign_cannot_resume_as_prompt_v2(self):
        old_config = deepcopy(self.config)
        for name in ('diagnosis', 'preconditioner'):
            old_config['method']['prompts'][name] = f'v28_2_searchqa_{name}_v1'
        self.reject(config.validate_config, old_config, executable=True)
        root = self.root / 'old_campaign'
        # Initialize an authentic v1 identity without any Actor/model execution.
        with ExitStack() as stack:
            for name, module in (('diagnosis', diagnosis), ('preconditioner', preconditioner)):
                stack.enter_context(patch.object(module, 'PROMPT_VERSION', f'v28_2_searchqa_{name}_v1'))
                stack.enter_context(patch.object(module, 'render_prompt', return_value=(BASELINE / 'prompts' / f'{name}.md').read_text()))
            with fresh(self.data).using(): evolution.initialize(root, old_config)
        before = snapshot(root); generate = Generator()
        self.reject(evolution.run_campaign, root, generate=generate, resume=True)
        self.assertEqual(snapshot(root), before)
        self.assertEqual(self.transport.calls, 0); self.assertEqual(generate.calls, [])

    def test_stale_prompt_text_or_version_rejected_before_method_request(self):
        grouped = self.grouped(); dc = diagnosis.diagnosis_call(grouped)
        saved = dc.complete(self.proposal())
        for call in (dc, preconditioner.preconditioner_call(saved, {'rounds': []})):
            self.assertEqual(call.prompt_version, f'v28_2_searchqa_{call.name}_v2')
            options = {'call_config': self.config['module_calls'][call.name], 'max_attempts': 6,
                       'max_input_chars': 4000000, 'max_message_utf8_bytes': 6000000, 'retry_delay_seconds': 2.0}
            messages = deepcopy(call.messages)
            messages[0]['content'] = (BASELINE / 'prompts' / f'{call.name}.md').read_text()
            variants = [replace(call, prompt_version=f'v28_2_searchqa_{call.name}_v1'), replace(call, messages=messages)]
            generate = Generator()
            for i, stale in enumerate(variants):
                self.reject(stages.run_stage, self.root / f'{call.name}_{i}', stale, generate=generate, **options)
            self.assertEqual(generate.calls, [])

    def test_complete_shared_correction_and_partial_revision_reach_editor_without_reason(self):
        grouped = self.grouped(); dc = diagnosis.diagnosis_call(grouped)
        original = self.proposal()
        original['plan']['updates'][0]['text'] += 'Always abbreviate every place name.\n'
        saved = dc.complete(original); pc = preconditioner.preconditioner_call(saved, {'rounds': []})
        self.assertEqual([r['ref'] for r in json.loads(pc.messages[1]['content'])['runs']], ['P1', 'P2'])
        self.assertNotIn('reason', json.loads(pc.messages[1]['content']))
        adjusted = pc.complete({'adjustments': [{'target': 'u1', 'action': 'REPLACE', 'text': self.correction,
                                               'reason': 'Preserve the supported relation correction; the naming addition lacks grounds.'}]})
        effective = adjusted['effective_plan']
        self.assertEqual(effective, {'goal': original['plan']['goal'], 'updates': [
            {**original['plan']['updates'][0], 'text': self.correction}]})
        self.assertEqual(saved['diagnosis'], original)
        visible = json.loads(editor.editor_call(adjusted).messages[1]['content'])
        self.assertEqual(visible['plan']['updates'], [{'id': 'u1', 'text': self.correction}])
        self.assertEqual(set(visible), {'parent', 'plan'})

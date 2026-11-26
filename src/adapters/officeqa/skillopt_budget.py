"""Persistent retry budget and JSON contracts for the OfficeQA SkillOpt profile."""
import hashlib
import json
from pathlib import Path
import re
from threading import Lock

from src.skill_evolution.v27.json_response import parse_json_response
from .execution import atomic_json as save

ATTEMPTS = 6
LENGTHS_BEFORE_INCREASE = 3
CAP_MULTIPLIER = 2


def read(path):
    return json.loads(Path(path).read_bytes())


class TrainingPaused(SystemExit):
    """Cross SkillOpt's catch-Exception fallbacks without committing a failed update."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def validate(text, stage, original):
    try:
        obj = parse_json_response(text)
    except ValueError as exc:
        raise ValueError(str(exc.__cause__ or exc)) from exc

    if stage in ('analyst', 'merge'):
        patch = obj.get('patch') if stage == 'analyst' else obj
        if not isinstance(patch, dict) or not isinstance(patch.get('edits'), list):
            raise ValueError('Expected patch.edits array' if stage == 'analyst' else 'Expected edits array')
        for i, edit in enumerate(patch['edits']):
            if not isinstance(edit, dict) or edit.get('op') not in ('append', 'replace', 'insert_after', 'delete'):
                raise ValueError(f'edits[{i}].op must be append, replace, insert_after or delete')
            for field in ('target', 'content'):
                required = (field == 'target' and edit['op'] != 'append' or
                            field == 'content' and edit['op'] != 'delete')
                if (field in edit and not isinstance(edit[field], str) or
                        required and not edit.get(field, '').strip()):
                    raise ValueError(f'edits[{i}].{field} must be text' + (' and nonempty' if required else ''))
        if 'reasoning' in patch and not isinstance(patch['reasoning'], str):
            raise ValueError('Patch reasoning must be text')
    elif stage == 'ranking':
        match = re.search(r'Pool \((\d+) [^\n]+?, budget=(\d+)\)', original[-1]['content'])
        indices = obj.get('selected_indices')
        if not isinstance(indices, list) or not indices or any(type(i) != int or i < 0 for i in indices):
            raise ValueError('selected_indices must be a nonempty array of zero-based integer indices')
        if len(set(indices)) != len(indices) or (match and (max(indices) >= int(match[1]) or
                                                            len(indices) != int(match[2]))):
            raise ValueError('selected_indices must select the requested number of distinct in-range indices')
    else:
        field = {'slow_update': 'slow_update_content', 'meta_skill': 'meta_skill_content'}[stage]
        if not isinstance(obj.get(field), str) or not obj[field].strip():
            raise ValueError(f'{field} must be nonempty text')
    return obj


def repair(original, text, error):
    return [*original, {'role': 'assistant', 'content': text},
            {'role': 'user', 'content': f'Previous output validation error: {error}\n'
             'Return the complete corrected JSON object. Preserve all unaffected content and fields.'}]


class OptimizerBudget:
    def __init__(self, campaign, send, record):
        self.calls = Path(campaign) / 'model_calls'
        self.paused = Path(campaign) / 'optimizer_paused.json'
        self.send = send
        self.record = record
        self.guard = Lock()
        self.locks = {}

    def check(self):
        if self.paused.exists():
            raise TrainingPaused(f'Optimizer paused: {read(self.paused)}')

    def halt(self, folder, stage):
        with self.guard:
            if not self.paused.exists():
                save(self.paused, {'stage': stage, 'call': folder.name, 'attempts': ATTEMPTS,
                                   'reason': 'optimizer_attempts_exhausted'})
        self.check()

    def recover(self):
        self.check()
        # The process can exit after reserving slot six and before writing the
        # pause marker. Reconcile it before the trainer or Actor resumes.
        for last in self.calls.glob(f'*/http_{ATTEMPTS:03}_request.json'):
            folder = last.parent
            status = folder / 'status.json'
            if status.exists() and read(status)['status'] == 'complete':
                continue
            if not all((folder / f'http_{n:03}_request.json').exists() for n in range(1, ATTEMPTS)):
                raise TrainingPaused(f'Incomplete optimizer journal: {folder}')
            initial = read(folder / 'input.json')
            self.generate(initial['identity'], initial['stage'], initial['messages'], initial['max_completion_tokens'])

    def generate(self, identity, stage, base, cap):
        folder = self.calls / digest([stage, identity])
        with self.guard:
            lock = self.locks.setdefault(folder, Lock())
        with lock:
            self.check()
            path = folder / 'input.json'
            if not path.exists():
                save(path, {'identity': identity, 'stage': stage, 'messages': base,
                            'max_completion_tokens': cap, 'max_attempts': ATTEMPTS})
            initial = read(path)
            original, cap = initial['messages'], initial['max_completion_tokens']
            messages, lengths = original, 0
            for number in range(1, ATTEMPTS + 1):
                self.check()
                stem = f'http_{number:03}'
                request = folder / (stem + '_request.json')
                raw = folder / (stem + '_response_body.bin')
                meta = folder / (stem + '_response.json')
                outcome = folder / (stem + '_outcome.json')
                if not request.exists():
                    limit = cap * CAP_MULTIPLIER if lengths >= LENGTHS_BEFORE_INCREASE else cap
                    self.send(folder, stem, messages, limit)
                # A reserved request without a recorded reply may already have reached
                # the provider. Charge it once even across a process crash.
                if not raw.exists():
                    if not outcome.exists():
                        save(outcome, {'action': 'unknown_delivery'})
                    continue
                if meta.exists() and read(meta)['status'] != 200:
                    save(outcome, {'action': 'http_error', 'status': read(meta)['status']})
                    continue
                try:
                    response = json.loads(raw.read_bytes())
                    choice = response['choices'][0]
                    finish = choice['finish_reason']
                    text = choice['message'].get('content')
                    text = '' if text is None else text
                    usage = response.get('usage') or {}
                    if not isinstance(text, str) or not isinstance(usage, dict):
                        raise ValueError('Expected text message content and object usage')
                except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
                    save(outcome, {'action': 'invalid_envelope', 'error': str(exc)})
                    continue
                if not outcome.exists():
                    self.record(stage, usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0))
                if finish == 'length':
                    lengths += 1
                    decision = {'action': 'length', 'length_count': lengths}
                elif finish == 'stop':
                    try:
                        obj = validate(text, stage, original)
                    except ValueError as exc:
                        messages = repair(original, text, str(exc))
                        decision = {'action': 'repair', 'error': str(exc)}
                    else:
                        save(outcome, {'action': 'valid'})
                        save(folder / 'status.json', {'status': 'complete', 'http_attempts': number})
                        return json.dumps(obj, ensure_ascii=False), usage
                else:
                    decision = {'action': 'unexpected_finish', 'finish_reason': finish}
                save(outcome, decision)
            save(folder / 'status.json', {'status': 'paused', 'http_attempts': ATTEMPTS})
            self.halt(folder, stage)

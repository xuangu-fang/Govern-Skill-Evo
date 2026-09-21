"""Opt-in v18 text simulator: prompt-only repair, unchanged stopping semantics."""
import hashlib

from tau2.user.user_simulator import UserSimulator

USER_SIMULATOR_NAME = 'user_simulator_v18'
PROMPT_VERSION = 'v18-user-confirmation-1'
CONFIRMATION_GUIDELINES = '''## Confirmation and task completion
Confirmation of a pending action is not completion of that action. When your
reply authorizes or confirms an action that the assistant still needs to carry
out, do not include an end-of-conversation signal (###STOP###, ###TRANSFER###,
or ###OUT-OF-SCOPE###) in that same reply. Allow the assistant another turn to
perform the confirmed action and report the result.
After receiving the assistant's response about the action's outcome, decide
whether to continue or end the conversation under the normal stopping rules.
This does not require you to approve an action, relax your requirements, invent
missing information, or continue after you withdraw the request or genuinely
choose to end the interaction. Normal completion, withdrawal, transfer, and
out-of-scope stopping rules still apply when you are not confirming a pending
action that requires another assistant turn.
'''


def sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


PROMPT_SHA256 = sha256(CONFIRMATION_GUIDELINES)


class V18UserSimulator(UserSimulator):
    """Snapshot the original prompt plus one shared constraint per instance.

    No global monkeypatch, response rewriting, retry, or is_stop override.
    The original scenario/persona/tools and generation behavior are inherited.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._base_system_prompt = super().system_prompt
        self._v18_system_prompt = self._base_system_prompt + '\n\n' + CONFIRMATION_GUIDELINES

    @property
    def system_prompt(self):
        return self._v18_system_prompt

    def prompt_record(self):
        """Exact model-visible system text; private simulator audit, not learner input."""
        return {
            'schema_version': 'user_simulator_prompt_v18.1',
            'implementation': USER_SIMULATOR_NAME,
            'prompt_version': PROMPT_VERSION,
            'shared_guidelines_sha256': PROMPT_SHA256,
            'base_system_prompt_sha256': sha256(self._base_system_prompt),
            'system_prompt_sha256': sha256(self.system_prompt),
            'system_prompt': self.system_prompt,
        }


def register_user_simulator():
    """Register only the v18 name, without replacing the default constructor."""
    from tau2.registry import registry
    try:
        existing = registry.get_user_constructor(USER_SIMULATOR_NAME)
    except KeyError:
        registry.register_user(V18UserSimulator, USER_SIMULATOR_NAME)
    else:
        if existing is not V18UserSimulator:
            raise ValueError('v18 user simulator name already bound to another constructor')

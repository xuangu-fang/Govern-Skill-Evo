"""User simulator variant that fixes only the first user message."""

from __future__ import annotations

from tau2.data_model.message import AssistantMessage, UserMessage
from tau2.registry import registry
from tau2.user.user_simulator import UserSimulator


USER_NAME = "insurance_reason_fixed_opening_user"


def _opening_from_instructions(instructions: str) -> str:
    marker = "\tReason for call:\n\t\t"
    terminator = "\n\tKnown info:"
    if marker not in instructions or terminator not in instructions:
        raise ValueError("Structured user instructions do not contain a reason-for-call block")
    return instructions.split(marker, 1)[1].split(terminator, 1)[0].strip()


class FixedOpeningUserSimulator(UserSimulator):
    """Emit the supplied reason-for-call verbatim once, then behave normally."""

    def generate_next_message(self, message, state):
        if not any(isinstance(item, UserMessage) for item in state.messages):
            if not isinstance(message, AssistantMessage):
                raise TypeError("The fixed opening expects the agent greeting first")
            state.messages.append(message)
            user_message = UserMessage(
                role="user",
                content=_opening_from_instructions(self.instructions or ""),
            )
            state.messages.append(user_message)
            return user_message, state
        return super().generate_next_message(message, state)


def register_fixed_opening_user() -> None:
    if USER_NAME not in registry.get_info().users:
        registry.register_user(FixedOpeningUserSimulator, USER_NAME)

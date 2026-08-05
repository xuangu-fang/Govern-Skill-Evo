"""Registration point for Process Verifier's built-in rule handlers."""

from __future__ import annotations

from src.verifiers.handlers.deterministic.payment_method_ownership import (
    check_payment_method_ownership,
)
from src.verifiers.handlers.deterministic.tool_response_exclusivity import (
    check_tool_response_exclusivity,
)
from src.verifiers.handlers.deterministic.transfer_protocol import (
    check_transfer_protocol,
)
from src.verifiers.registry import CheckerRegistry
from src.verifiers.handlers.semantic.transfer_scope import (
    TransferScopeJudgmentDataset,
    make_transfer_scope_checker,
)
from src.verifiers.handlers.semantic.write_confirmation import (
    WriteConfirmationJudgmentDataset,
    make_write_confirmation_checker,
)


def build_builtin_registry() -> CheckerRegistry:
    """Register every handler shipped with the current project."""
    registry = CheckerRegistry()
    registry.register(
        "deterministic",
        "transfer_protocol",
        check_transfer_protocol,
    )
    registry.register(
        "deterministic",
        "tool_response_exclusivity",
        check_tool_response_exclusivity,
    )
    registry.register(
        "deterministic",
        "payment_method_ownership",
        check_payment_method_ownership,
    )
    registry.register_semantic(
        "transfer_scope",
        TransferScopeJudgmentDataset,
        make_transfer_scope_checker,
    )
    registry.register_semantic(
        "write_confirmation",
        WriteConfirmationJudgmentDataset,
        make_write_confirmation_checker,
    )
    return registry

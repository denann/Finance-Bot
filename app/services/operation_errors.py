"""Typed failures for logical finance operations spanning multiple mutations."""

from __future__ import annotations

from typing import Any


class AtomicOperationError(RuntimeError):
    """Base error for a logical operation that cannot report normal success."""

    def __init__(self, message: str, *, operation: str, reconciliation_required: bool = False):
        self.operation = operation
        self.reconciliation_required = reconciliation_required
        super().__init__(message)


class PartialMutationError(AtomicOperationError):
    """Raise after a mutation when a later required step reports failure."""


class CommitOutcomeUnknownError(AtomicOperationError):
    """Raise when remote commit or rollback cannot be proven."""

    def __init__(self, message: str, *, operation: str):
        super().__init__(message, operation=operation, reconciliation_required=True)


class ReconciliationRequiredError(AtomicOperationError):
    """Raise when known partial state requires a manual consistency check."""

    def __init__(self, message: str, *, operation: str):
        super().__init__(message, operation=operation, reconciliation_required=True)


def require_success_after_write(result: Any, *, operation: str, default_message: str) -> Any:
    """Promote a result-style failure after mutation into a typed exception.

    Pre-write validation may still return ``success=False`` normally. Callers
    use this helper only after their first mutation has succeeded, ensuring the
    outer Sheets transaction receives an exception and performs rollback.
    """

    if isinstance(result, dict) and result.get("success"):
        return result
    message = default_message
    if isinstance(result, dict) and result.get("message"):
        message = str(result["message"])
    raise PartialMutationError(message, operation=operation)

"""Small typed result contract for extracted application use cases."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, is_dataclass
from types import MappingProxyType
from typing import Any, Mapping


def _freeze(value: Any) -> Any:
    """Detach and recursively freeze mutable payload containers."""

    if is_dataclass(value):
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return deepcopy(value)


def immutable_payload(value: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    """Return a detached, read-only payload snapshot."""

    return _freeze(dict(value or {}))


def mutable_payload(value: Any) -> Any:
    """Recursively thaw an application payload at a compatibility boundary."""

    if isinstance(value, Mapping):
        return {key: mutable_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [mutable_payload(item) for item in value]
    if isinstance(value, frozenset):
        return {mutable_payload(item) for item in value}
    return deepcopy(value)


@dataclass(frozen=True, slots=True)
class UseCaseResult:
    """Base result returned by an extracted application use case."""

    message: str = ""
    payload: Mapping[str, Any] = field(default_factory=immutable_payload)


@dataclass(frozen=True, slots=True)
class ValidationFailure(UseCaseResult):
    """Normal validation failure that happened before any mutation."""

    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ClarificationRequired(UseCaseResult):
    """A user decision or missing field is required before preview."""

    reason: str = ""
    missing_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PreviewReady(UseCaseResult):
    """An immutable payload is ready for owner-visible confirmation."""


@dataclass(frozen=True, slots=True)
class MutationCommitted(UseCaseResult):
    """The requested mutation completed successfully."""


@dataclass(frozen=True, slots=True)
class OperationFailed(UseCaseResult):
    """The operation failed with a known non-reconciliation outcome."""

    operation: str = ""


@dataclass(frozen=True, slots=True)
class ReconciliationRequired(OperationFailed):
    """The final persistence outcome is unknown and needs reconciliation."""

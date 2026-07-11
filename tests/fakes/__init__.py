"""Reusable fake adapters for tests that must not call external services."""

from .clock import FrozenClock
from .sheets import FailurePlan, InMemoryWorksheet
from .telegram import FakeCallbackQuery, FakeContext, FakeMessage, FakeUpdate

__all__ = [
    "FailurePlan",
    "FakeCallbackQuery",
    "FakeContext",
    "FakeMessage",
    "FakeUpdate",
    "FrozenClock",
    "InMemoryWorksheet",
]

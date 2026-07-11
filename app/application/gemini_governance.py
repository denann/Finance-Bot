"""Typed request-scoped Gemini budgets and prompt metadata."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator

from app.config import GEMINI_CALLS_PER_UPDATE
from app.observability import increment_metric


PROMPT_VERSIONS = {
    "transaction_parser": "transaction-parser-v1",
    "intent_router": "intent-router-v1",
    "finance_ask": "finance-ask-v1",
    "finance_insight": "finance-insight-v1",
    "finance_audit": "finance-audit-v1",
    "finance_coach": "finance-coach-v1",
    "image_receipt_parser": "image-receipt-v1",
    "category_alias": "category-alias-v1",
    "generic_text": "generic-text-v1",
}


class GeminiGovernanceError(RuntimeError):
    """Base error for governed Gemini invocation."""


class GeminiBudgetExceeded(GeminiGovernanceError):
    """The Telegram update already consumed its allowed model calls."""


class GeminiInputTooLarge(GeminiGovernanceError):
    """The governed prompt exceeds the configured character limit."""


@dataclass
class GeminiCallBudget:
    """One primary call per update plus one image-schema compatibility call."""

    max_primary_calls: int = GEMINI_CALLS_PER_UPDATE
    primary_calls: int = 0
    compatibility_calls: int = 0

    def consume(self, feature: str, *, compatibility: bool = False) -> int:
        if compatibility:
            if feature != "image_receipt_parser" or self.compatibility_calls >= 1 or self.primary_calls < 1:
                increment_metric("gemini.budget_exhausted")
                raise GeminiBudgetExceeded("Fallback kompatibilitas Gemini tidak tersedia.")
            self.compatibility_calls += 1
            return self.primary_calls + self.compatibility_calls
        if self.primary_calls >= self.max_primary_calls:
            increment_metric("gemini.budget_exhausted")
            raise GeminiBudgetExceeded("Batas panggilan Gemini untuk update ini sudah habis.")
        self.primary_calls += 1
        return self.primary_calls

    @property
    def total_calls(self) -> int:
        return self.primary_calls + self.compatibility_calls


_current_budget: ContextVar[GeminiCallBudget | None] = ContextVar("gemini_call_budget", default=None)


@contextmanager
def gemini_request_scope(max_primary_calls: int | None = None) -> Iterator[GeminiCallBudget]:
    """Bind one shared AI budget to a logical Telegram request."""

    existing = _current_budget.get()
    if existing is not None:
        yield existing
        return
    budget = GeminiCallBudget(max_primary_calls=int(max_primary_calls or GEMINI_CALLS_PER_UPDATE))
    token = _current_budget.set(budget)
    try:
        yield budget
    finally:
        _current_budget.reset(token)


def current_or_local_budget() -> GeminiCallBudget:
    """Return the request budget or a local budget for direct CLI use."""

    return _current_budget.get() or GeminiCallBudget()


def prompt_version(feature: str) -> str:
    return PROMPT_VERSIONS.get(feature, PROMPT_VERSIONS["generic_text"])

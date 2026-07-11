"""Bounded asynchronous boundary for synchronous external work."""

from __future__ import annotations

import asyncio
import weakref
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, TypeVar

from app.config import (
    GEMINI_CONCURRENCY,
    GEMINI_TIMEOUT_SECONDS,
    SCHEDULED_WORK_CONCURRENCY,
    SHEETS_INTERACTIVE_CONCURRENCY,
    SHEETS_TIMEOUT_SECONDS,
)
from app.observability import emit_event, increment_metric, monotonic_ms, observe_duration


T = TypeVar("T")


class ExternalWorkClass(str, Enum):
    INTERACTIVE_SHEETS = "interactive_sheets"
    GEMINI = "gemini"
    SCHEDULED = "scheduled"


class ExternalIOError(RuntimeError):
    """Base error for governed external worker execution."""


class ExternalIOSaturated(ExternalIOError):
    """No worker slot became available within the bounded wait."""


class ExternalIOTimeout(ExternalIOError):
    """A read-only or safely repeatable operation exceeded its timeout."""


class ExternalMutationOutcomeUnknown(ExternalIOTimeout):
    """A mutation timed out while its worker may still complete remotely."""

    reconciliation_required = True


@dataclass(frozen=True)
class ExternalWorkPolicy:
    limit: int
    timeout_seconds: float


_POLICIES = {
    ExternalWorkClass.INTERACTIVE_SHEETS: ExternalWorkPolicy(SHEETS_INTERACTIVE_CONCURRENCY, SHEETS_TIMEOUT_SECONDS),
    ExternalWorkClass.GEMINI: ExternalWorkPolicy(GEMINI_CONCURRENCY, GEMINI_TIMEOUT_SECONDS),
    ExternalWorkClass.SCHEDULED: ExternalWorkPolicy(SCHEDULED_WORK_CONCURRENCY, SHEETS_TIMEOUT_SECONDS),
}
_loop_semaphores: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[ExternalWorkClass, asyncio.Semaphore]]" = weakref.WeakKeyDictionary()


def _semaphore(work_class: ExternalWorkClass, limit: int) -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    by_class = _loop_semaphores.setdefault(loop, {})
    semaphore = by_class.get(work_class)
    if semaphore is None:
        semaphore = asyncio.Semaphore(limit)
        by_class[work_class] = semaphore
    return semaphore


async def run_external_work(
    work_class: ExternalWorkClass,
    operation: str,
    function: Callable[..., T],
    *args: Any,
    timeout_seconds: float | None = None,
    mutation: bool = False,
    policy: ExternalWorkPolicy | None = None,
    **kwargs: Any,
) -> T:
    """Run synchronous external work without blocking the event loop."""

    selected_policy = policy or _POLICIES[work_class]
    timeout = float(timeout_seconds or selected_policy.timeout_seconds)
    semaphore = _semaphore(work_class, selected_policy.limit)
    started = monotonic_ms()
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
    except TimeoutError as exc:
        increment_metric(f"external_io.{work_class.value}.saturated")
        raise ExternalIOSaturated(f"Worker {work_class.value} sedang penuh.") from exc

    try:
        increment_metric(f"external_io.{work_class.value}.started")
        result = await asyncio.wait_for(
            asyncio.to_thread(function, *args, **kwargs),
            timeout=timeout,
        )
    except TimeoutError as exc:
        increment_metric(f"external_io.{work_class.value}.timeout")
        emit_event(
            "external_io_timeout",
            work_class=work_class.value,
            operation=operation,
            mutation=mutation,
        )
        error_type = ExternalMutationOutcomeUnknown if mutation else ExternalIOTimeout
        raise error_type(f"Operasi {operation} melewati batas waktu.") from exc
    except Exception:
        increment_metric(f"external_io.{work_class.value}.failed")
        raise
    finally:
        semaphore.release()
        observe_duration(f"external_io.{work_class.value}.duration_ms", monotonic_ms() - started)

    increment_metric(f"external_io.{work_class.value}.completed")
    return result


async def run_sheets_read(operation: str, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return await run_external_work(ExternalWorkClass.INTERACTIVE_SHEETS, operation, function, *args, **kwargs)


async def run_gemini(operation: str, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return await run_external_work(ExternalWorkClass.GEMINI, operation, function, *args, **kwargs)


async def run_scheduled(operation: str, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return await run_external_work(ExternalWorkClass.SCHEDULED, operation, function, *args, **kwargs)

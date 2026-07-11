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
    """Run synchronous external work without blocking the event loop.

    The concurrency slot belongs to the underlying worker, not only to the
    awaiting coroutine.  ``asyncio.to_thread`` cannot stop a running thread
    when the caller times out, so the slot is released by the worker task's
    completion callback.  This prevents timed-out calls from silently
    exceeding the configured concurrency limit.
    """

    selected_policy = policy or _POLICIES[work_class]
    timeout = float(selected_policy.timeout_seconds if timeout_seconds is None else timeout_seconds)
    semaphore = _semaphore(work_class, selected_policy.limit)
    started = monotonic_ms()
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
    except TimeoutError as exc:
        increment_metric(f"external_io.{work_class.value}.saturated")
        raise ExternalIOSaturated(f"Worker {work_class.value} sedang penuh.") from exc

    worker_task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    caller_timed_out = False

    def release_worker_slot(completed: asyncio.Task) -> None:
        """Release capacity only after the real thread-backed task finishes."""

        semaphore.release()
        observe_duration(f"external_io.{work_class.value}.worker_duration_ms", monotonic_ms() - started)
        # Always retrieve the task exception.  Awaiters still receive the same
        # exception, while this also closes the small race where the worker can
        # finish between wait_for timing out and the timeout flag being set.
        try:
            completed.exception()
        except (asyncio.CancelledError, Exception):
            pass

    worker_task.add_done_callback(release_worker_slot)

    try:
        increment_metric(f"external_io.{work_class.value}.started")
        # Shield keeps the worker task alive when wait_for times out.  The
        # remote operation may still complete, especially for mutations.
        result = await asyncio.wait_for(asyncio.shield(worker_task), timeout=timeout)
    except TimeoutError as exc:
        caller_timed_out = True
        increment_metric(f"external_io.{work_class.value}.timeout")
        emit_event(
            "external_io_timeout",
            work_class=work_class.value,
            operation=operation,
            mutation=mutation,
            worker_still_running=not worker_task.done(),
        )
        error_type = ExternalMutationOutcomeUnknown if mutation else ExternalIOTimeout
        raise error_type(f"Operasi {operation} melewati batas waktu.") from exc
    except asyncio.CancelledError:
        caller_timed_out = True
        increment_metric(f"external_io.{work_class.value}.cancelled")
        raise
    except Exception:
        increment_metric(f"external_io.{work_class.value}.failed")
        raise
    finally:
        # This duration measures how long the caller waited.  Worker duration
        # is recorded separately by ``release_worker_slot``.
        observe_duration(f"external_io.{work_class.value}.duration_ms", monotonic_ms() - started)

    increment_metric(f"external_io.{work_class.value}.completed")
    return result


async def run_sheets_read(operation: str, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return await run_external_work(ExternalWorkClass.INTERACTIVE_SHEETS, operation, function, *args, **kwargs)


async def run_gemini(operation: str, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return await run_external_work(ExternalWorkClass.GEMINI, operation, function, *args, **kwargs)


async def run_scheduled(operation: str, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return await run_external_work(ExternalWorkClass.SCHEDULED, operation, function, *args, **kwargs)

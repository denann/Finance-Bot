"""Deterministic concurrency and timeout tests for external work."""

from __future__ import annotations

import asyncio
import threading

import pytest

from app.application.external_io import (
    ExternalIOTimeout,
    ExternalMutationOutcomeUnknown,
    ExternalWorkClass,
    ExternalWorkPolicy,
    run_external_work,
)
from app.observability import correlation_scope, current_correlation_id


def test_slow_worker_does_not_block_lightweight_coroutine() -> None:
    started = threading.Event()
    release = threading.Event()

    def slow_read() -> str:
        started.set()
        release.wait(2)
        return "done"

    async def scenario() -> None:
        task = asyncio.create_task(run_external_work(ExternalWorkClass.INTERACTIVE_SHEETS, "slow_read", slow_read))
        while not started.is_set():
            await asyncio.sleep(0)
        lightweight_ran = False

        async def lightweight() -> None:
            nonlocal lightweight_ran
            lightweight_ran = True

        await lightweight()
        assert lightweight_ran
        release.set()
        assert await task == "done"

    asyncio.run(scenario())


def test_concurrency_limit_is_never_exceeded() -> None:
    lock = threading.Lock()
    active = 0
    maximum = 0
    release = threading.Event()

    def worker() -> None:
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        release.wait(2)
        with lock:
            active -= 1

    async def scenario() -> None:
        policy = ExternalWorkPolicy(limit=2, timeout_seconds=2)
        tasks = [asyncio.create_task(run_external_work(ExternalWorkClass.GEMINI, "bounded", worker, policy=policy)) for _ in range(4)]
        while maximum < 2:
            await asyncio.sleep(0)
        assert maximum == 2
        release.set()
        await asyncio.gather(*tasks)

    asyncio.run(scenario())
    assert maximum == 2


def test_scheduled_capacity_is_separate_from_interactive_capacity() -> None:
    release = threading.Event()

    def blocked() -> None:
        release.wait(2)

    async def scenario() -> None:
        one = ExternalWorkPolicy(limit=1, timeout_seconds=2)
        scheduled = asyncio.create_task(run_external_work(ExternalWorkClass.SCHEDULED, "scheduled", blocked, policy=one))
        await asyncio.sleep(0)
        interactive = asyncio.create_task(run_external_work(ExternalWorkClass.INTERACTIVE_SHEETS, "interactive", lambda: "ok", policy=one))
        assert await interactive == "ok"
        release.set()
        await scheduled

    asyncio.run(scenario())


def test_timeout_types_distinguish_read_from_ambiguous_mutation() -> None:
    release = threading.Event()

    def blocked() -> None:
        release.wait(1)

    async def scenario() -> None:
        policy = ExternalWorkPolicy(limit=1, timeout_seconds=0.01)
        with pytest.raises(ExternalIOTimeout) as read_error:
            await run_external_work(ExternalWorkClass.INTERACTIVE_SHEETS, "read", blocked, policy=policy)
        assert not isinstance(read_error.value, ExternalMutationOutcomeUnknown)
        with pytest.raises(ExternalMutationOutcomeUnknown) as write_error:
            await run_external_work(ExternalWorkClass.INTERACTIVE_SHEETS, "write", blocked, mutation=True, policy=policy)
        assert write_error.value.reconciliation_required is True
        release.set()

    asyncio.run(scenario())


def test_correlation_context_survives_worker_boundary() -> None:
    async def scenario() -> str:
        with correlation_scope("phase3-correlation"):
            return await run_external_work(ExternalWorkClass.GEMINI, "context", current_correlation_id)

    assert asyncio.run(scenario()) == "phase3-correlation"

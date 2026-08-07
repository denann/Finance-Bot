"""Scheduler reads must run in a bounded worker with one request snapshot."""

from __future__ import annotations

import asyncio
import threading

from tests.fakes.external_modules import install_external_stubs
from tests.fakes.sheets import InMemoryWorksheet

install_external_stubs()

from app.scheduler import jobs
from app.sheets import client


def test_daily_scheduler_offloads_reads_and_deduplicates_same_sheet(monkeypatch) -> None:
    event_loop_thread = threading.get_ident()
    worker_threads: list[int] = []
    sent: list[str] = []
    sheet = InMemoryWorksheet("transactions", [["id", "date"], ["txn_1", "2026-07-11"]])

    monkeypatch.setattr(client, "get_sheet", lambda name: sheet)

    def fake_daily_report():
        worker_threads.append(threading.get_ident())
        client.get_all_records("transactions")
        return {
            "date": "2026-07-11",
            "count": 1,
            "total_income": 0,
            "total_expense": 10_000,
            "total_gross_expense": 10_000,
            "net": -10_000,
            "by_category": {"Food & Beverage": 10_000},
            "transactions": [],
        }

    def fake_budget_summary():
        worker_threads.append(threading.get_ident())
        client.get_all_records("transactions")
        return []

    async def fake_send_message(text, **_kwargs):
        sent.append(text)

    monkeypatch.setattr(jobs, "get_daily_report", fake_daily_report)
    monkeypatch.setattr(jobs, "get_budget_summary", fake_budget_summary)
    monkeypatch.setattr(jobs, "send_message", fake_send_message)

    asyncio.run(jobs.job_daily_summary())

    assert sent
    assert worker_threads and all(thread_id != event_loop_thread for thread_id in worker_threads)
    assert sheet.failure_plan.calls.get("get_all_records", 0) == 1

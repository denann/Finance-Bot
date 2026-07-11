"""Offline synthetic benchmark backed by real application service calls.

``optimized`` mode executes the current application services against an
instrumented in-memory Google Sheets adapter.  ``baseline`` mode preserves the
historical pre-Phase-3 operation profile solely for before/after reporting; it
is explicitly labelled as modelled rather than measured.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
import json
import statistics
import time
from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:  # Keep the benchmark credential-free in minimal developer environments.
    import gspread  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - exercised by direct CLI use here.
    from tests.fakes.external_modules import install_external_stubs

    install_external_stubs()


@dataclass(frozen=True)
class BenchmarkResult:
    dataset_size: int
    scenario: str
    iterations: int
    measurement: str
    p50_ms: float
    p95_ms: float
    p99_ms: float
    sheets_calls: int
    rows_read: int
    rows_written: int
    full_range_rewrites: int
    duplicate_reads: int
    gemini_calls: int
    context_characters: int
    selected_records: int


TRANSACTION_HEADERS = [
    "id", "date", "type", "amount", "category", "account", "to_account",
    "subject", "description", "catatan", "tipe_pengeluaran", "raw_input",
    "parsed_by", "hutang_id", "tipe_hutang",
]


class InstrumentedWorksheet:
    """Minimal worksheet implementation that measures actual adapter usage."""

    def __init__(self, title: str, headers: list[str], records: list[dict] | None = None):
        self.title = title
        self.headers = list(headers)
        self.rows = [self.headers] + [self._row(record) for record in (records or [])]
        self.calls: Counter[str] = Counter()
        self.rows_read = 0
        self.rows_written = 0
        self.full_range_rewrites = 0

    def _row(self, record: dict) -> list[Any]:
        return [record.get(header, "") for header in self.headers]

    def append_row(self, row: list[Any], **_kwargs: Any) -> dict:
        self.calls["append_row"] += 1
        self.rows_written += 1
        self.rows.append(list(row))
        index = len(self.rows)
        return {"updates": {"updatedRange": f"{self.title}!A{index}:Z{index}"}}

    def append_rows(self, rows: list[list[Any]], **_kwargs: Any) -> dict:
        self.calls["append_rows"] += 1
        start = len(self.rows) + 1
        materialized = [list(row) for row in rows]
        self.rows.extend(materialized)
        self.rows_written += len(materialized)
        return {"updates": {"updatedRange": f"{self.title}!A{start}:Z{len(self.rows)}"}}

    def get_all_records(self, **_kwargs: Any) -> list[dict]:
        self.calls["get_all_records"] += 1
        body = self.rows[1:]
        self.rows_read += len(body)
        return [dict(zip(self.headers, row)) for row in body]

    def get_all_values(self) -> list[list[Any]]:
        self.calls["get_all_values"] += 1
        self.rows_read += len(self.rows)
        return [list(row) for row in self.rows]

    def col_values(self, column: int) -> list[Any]:
        self.calls["col_values"] += 1
        self.rows_read += len(self.rows)
        index = column - 1
        return [row[index] if index < len(row) else "" for row in self.rows]

    def delete_rows(self, start: int, end: int | None = None) -> None:
        self.calls["delete_rows"] += 1
        last = end or start
        del self.rows[start - 1:last]

    def sort(self, *sort_specs: tuple[int, str], range: str) -> dict:
        self.calls["sort"] += 1
        header, body = self.rows[:1], self.rows[1:]
        for column, direction in reversed(sort_specs):
            index = int(column) - 1
            body.sort(
                key=lambda row: str(row[index] if index < len(row) else ""),
                reverse=str(direction).lower().startswith("des"),
            )
        self.rows = header + body
        return {"sortedRange": range, "sortSpecs": list(sort_specs)}

    def update(self, values: list[list[Any]], range_name: str | None = None, **_kwargs: Any) -> dict:
        self.calls["update"] += 1
        self.rows_written += len(values)
        if len(values) > 1:
            self.full_range_rewrites += 1
        return {"updatedRange": range_name or "A1"}


class InstrumentedWorkbook:
    """Collection of in-memory worksheets plus aggregate operation counters."""

    def __init__(self, transactions: list[dict]):
        account_records = [
            {"account_name": name, "type": "cash", "balance": 1_000_000, "currency": "IDR", "last_updated": "2026-07-11"}
            for name in ("Cash", "BCA", "DANA", "BRI")
        ]
        self.sheets = {
            "transactions": InstrumentedWorksheet("transactions", TRANSACTION_HEADERS, transactions),
            "accounts": InstrumentedWorksheet("accounts", ["account_name", "type", "balance", "currency", "last_updated"], account_records),
            "budgets": InstrumentedWorksheet("budgets", ["id", "month", "category", "budget_amount", "created_at", "updated_at"], [
                {"id": "budget_1", "month": "2026-06", "category": "Food & Beverage", "budget_amount": 2_000_000}
            ]),
            "debts": InstrumentedWorksheet("debts", ["id", "type", "person_name", "original_amount", "remaining_amount", "description", "due_date", "is_settled", "created_at", "settled_at", "source_transaction_id"], []),
            "debt_payments": InstrumentedWorksheet("debt_payments", ["id", "debt_id", "amount", "date", "account", "description", "created_at"], []),
            "assets": InstrumentedWorksheet("assets", ["id", "name", "category", "current_value", "description", "is_active", "created_at", "updated_at", "asset_type", "quantity", "unit", "price_source", "price_per_unit", "last_price_update", "purchase_price_per_unit", "purchase_date"], []),
            "categories": InstrumentedWorksheet("categories", ["category", "type", "is_active", "emoji", "aliases"], [
                {"category": "Food & Beverage", "type": "expense", "is_active": "TRUE", "emoji": "🍽️", "aliases": "makan,jajan"}
            ]),
            "net_worth_snapshots": InstrumentedWorksheet("net_worth_snapshots", ["id", "snapshot_date", "total_accounts", "total_assets", "total_liabilities", "net_worth", "created_at"], []),
        }

    def get_sheet(self, name: str) -> InstrumentedWorksheet:
        if name not in self.sheets:
            self.sheets[name] = InstrumentedWorksheet(name, ["id"], [])
        return self.sheets[name]

    def metrics(self) -> dict[str, int]:
        sheets_calls = sum(sum(sheet.calls.values()) for sheet in self.sheets.values())
        rows_read = sum(sheet.rows_read for sheet in self.sheets.values())
        rows_written = sum(sheet.rows_written for sheet in self.sheets.values())
        rewrites = sum(sheet.full_range_rewrites for sheet in self.sheets.values())
        duplicate_reads = 0
        for sheet in self.sheets.values():
            reads = sheet.calls["get_all_records"] + sheet.calls["get_all_values"]
            duplicate_reads += max(0, reads - 1)
        return {
            "sheets_calls": sheets_calls,
            "rows_read": rows_read,
            "rows_written": rows_written,
            "full_range_rewrites": rewrites,
            "duplicate_reads": duplicate_reads,
        }


def build_synthetic_transactions(size: int) -> list[dict]:
    """Create deterministic synthetic finance rows without real user data."""

    accounts = ("Cash", "BCA", "DANA", "BRI")
    categories = ("Food & Beverage", "Transport", "Bills & Utilities", "Shopping")
    start = date(2025, 1, 1)
    rows = []
    for index in range(size):
        transaction_date = start + timedelta(days=index % 540)
        is_transfer = index % 23 == 0
        is_debt = not is_transfer and index % 19 == 0
        transaction_type = "transfer" if is_transfer else ("income" if index % 11 == 0 else "expense")
        account = accounts[index % len(accounts)]
        rows.append({
            "id": f"synthetic_{index:06d}",
            "date": transaction_date.isoformat(),
            "type": transaction_type,
            "amount": (index % 97 + 1) * 1_000,
            "category": "Transfer" if is_transfer else ("Debt Payment" if is_debt else categories[index % len(categories)]),
            "account": account,
            "to_account": accounts[(index + 1) % len(accounts)] if is_transfer else "",
            "subject": f"Synthetic person {index % 5}" if is_debt else "",
            "description": "Repeated synthetic description" if index % 9 == 0 else f"Synthetic item {index % 37}",
            "catatan": "" if index % 13 else None,
            "tipe_pengeluaran": "Harian" if transaction_type == "expense" else "",
            "raw_input": "synthetic benchmark",
            "parsed_by": "debt" if is_debt else "regex",
            "hutang_id": "",
            "tipe_hutang": "",
        })
    return rows


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return ordered[position]


def _historical_baseline_profile(size: int, scenario: str, selected_limit: int) -> dict[str, int]:
    """Return the documented pre-Phase-3 profile; this is not measured code."""

    if scenario in {"single_save", "five_item_save"}:
        return {
            "sheets_calls": 3,
            "rows_read": size + 1,
            "rows_written": size,
            "full_range_rewrites": 1,
            "duplicate_reads": 0,
            "gemini_calls": 0,
            "selected_records": 0,
            "context_characters": 0,
        }
    if scenario in {"last", "monthly_report", "search", "export"}:
        return {"sheets_calls": 1, "rows_read": size, "rows_written": 0, "full_range_rewrites": 0, "duplicate_reads": 0, "gemini_calls": 0, "selected_records": 0, "context_characters": 0}
    if scenario in {"ask", "insight", "audit", "coach"}:
        duplicates = 1 if scenario in {"insight", "coach"} else 2
        return {"sheets_calls": 5 + duplicates, "rows_read": size * (1 + duplicates), "rows_written": 0, "full_range_rewrites": 0, "duplicate_reads": duplicates, "gemini_calls": 1, "selected_records": min(size, 15), "context_characters": 0}
    if scenario == "multi_unresolved":
        return {"sheets_calls": 0, "rows_read": 0, "rows_written": 0, "full_range_rewrites": 0, "duplicate_reads": 0, "gemini_calls": 5, "selected_records": 0, "context_characters": 0}
    return {"sheets_calls": 0, "rows_read": 0, "rows_written": 0, "full_range_rewrites": 0, "duplicate_reads": 0, "gemini_calls": 1 if scenario == "image_success" else 2, "selected_records": 0, "context_characters": 0}


def _run_optimized_once(rows: list[dict], scenario: str, selected_limit: int) -> dict[str, int]:
    """Execute one real application scenario against instrumented adapters."""

    from app.application.gemini_governance import gemini_request_scope
    from app.config import SHEET_TRANSACTIONS
    from app.services import finance_insight_service, report_service, transaction_service
    from app.sheets import client as sheets_client

    workbook = InstrumentedWorkbook(rows)
    context_characters = 0
    selected_records = 0
    gemini_calls = 0

    with ExitStack() as stack:
        stack.enter_context(patch.object(sheets_client, "get_sheet", workbook.get_sheet))
        stack.enter_context(patch.object(transaction_service, "TRANSACTION_SORT_MODE", "server"))

        if scenario in {"single_save", "five_item_save"}:
            stack.enter_context(patch.object(transaction_service, "validate_transaction", return_value=(True, "ok")))
            stack.enter_context(patch.object(transaction_service, "ensure_category_for_transaction", side_effect=lambda category, _type: category))
            stack.enter_context(patch.object(transaction_service, "calculate_account_deltas", return_value={"Cash": -10_000}))
            stack.enter_context(patch.object(transaction_service, "validate_accounts_exist", return_value=(True, [])))
            stack.enter_context(patch.object(transaction_service, "apply_account_deltas", return_value={"success": True, "new_balances": {"Cash": 990_000}, "failed_accounts": []}))
            ids = iter(range(1, 20))

            def build_row(parsed: dict, raw: str):
                index = next(ids)
                txn_id = f"bench_new_{index}"
                return txn_id, [txn_id, "2026-07-11", parsed["type"], parsed["amount"], parsed.get("category", ""), parsed.get("account", "Cash"), "", "", raw, "", "Harian", raw, "regex", "", ""]

            stack.enter_context(patch.object(transaction_service, "build_transaction_row", side_effect=build_row))
            parsed = {"type": "expense", "amount": 10_000, "category": "Food & Beverage", "account": "Cash"}
            with sheets_client.sheets_transaction(f"benchmark:{scenario}"):
                if scenario == "single_save":
                    transaction_service.save_transaction(parsed.copy(), "synthetic")
                else:
                    transaction_service.save_transactions_batch([{"parsed": parsed.copy(), "raw": f"synthetic-{i}"} for i in range(5)])

        else:
            with sheets_client.sheets_request_snapshot():
                if scenario == "last":
                    transaction_service.get_recent_transactions(limit=10)
                elif scenario == "monthly_report":
                    report_service.get_monthly_report(2026, 6)
                elif scenario == "search":
                    report_service.search_transactions("synthetic", limit=10)
                elif scenario == "export":
                    transaction_service.get_transactions_for_export("2026-06")
                elif scenario in {"ask", "insight", "audit", "coach"}:
                    with patch.object(finance_insight_service, "AI_CONTEXT_RECORD_LIMIT", selected_limit):
                        if scenario == "ask":
                            context = finance_insight_service.build_ask_finance_context("cari transaksi synthetic")
                            feature = "finance_ask"
                        elif scenario == "insight":
                            context = finance_insight_service.build_monthly_finance_context("2026-06")
                            feature = "finance_insight"
                        elif scenario == "audit":
                            context = finance_insight_service.build_audit_context("2026-06")
                            feature = "finance_audit"
                        else:
                            context = finance_insight_service.build_coach_context("2026-06", "cara hemat bulan ini")
                            feature = "finance_coach"
                        context_characters = len(json.dumps(context, default=str, separators=(",", ":"), sort_keys=True))
                        metadata = context.get("context_metadata") or (context.get("monthly_context") or {}).get("context_metadata") or {}
                        selected_records = int(metadata.get("records_selected", 0) or 0)
                        with gemini_request_scope() as budget:
                            budget.consume(feature)
                            gemini_calls = budget.total_calls
                elif scenario == "multi_unresolved":
                    # Exercise the real shared call budget used by the batch parser.
                    with gemini_request_scope() as budget:
                        budget.consume("transaction_batch_parser")
                        gemini_calls = budget.total_calls
                elif scenario == "image_success":
                    with gemini_request_scope() as budget:
                        budget.consume("image_receipt_parser")
                        gemini_calls = budget.total_calls
                elif scenario == "image_compatibility":
                    with gemini_request_scope() as budget:
                        budget.consume("image_receipt_parser")
                        budget.consume("image_receipt_parser", compatibility=True)
                        gemini_calls = budget.total_calls
                else:  # pragma: no cover - guarded by SCENARIOS.
                    raise ValueError(f"Unknown scenario: {scenario}")

    metrics = workbook.metrics()
    return {
        **metrics,
        "gemini_calls": gemini_calls,
        "context_characters": context_characters,
        "selected_records": selected_records,
    }


def run_benchmark(size: int, scenario: str, *, iterations: int = 5, mode: str = "baseline", selected_limit: int = 40) -> BenchmarkResult:
    """Run one synthetic scenario and return observed or historical counts."""

    rows = build_synthetic_transactions(size)
    durations: list[float] = []
    profile: dict[str, int] | None = None
    for _ in range(iterations):
        started = time.perf_counter()
        if mode == "optimized":
            profile = _run_optimized_once(rows, scenario, selected_limit)
        else:
            # Preserve a cheap historical comparator without pretending it is
            # current application execution.
            profile = _historical_baseline_profile(size, scenario, selected_limit)
            sorted(rows, key=lambda row: (row["date"], row["id"]), reverse=True)
        durations.append((time.perf_counter() - started) * 1_000)

    assert profile is not None
    return BenchmarkResult(
        dataset_size=size,
        scenario=scenario,
        iterations=iterations,
        measurement="observed_application" if mode == "optimized" else "historical_modelled",
        p50_ms=round(statistics.median(durations), 3),
        p95_ms=round(_percentile(durations, 0.95), 3),
        p99_ms=round(_percentile(durations, 0.99), 3),
        **profile,
    )


SCENARIOS = (
    "single_save", "five_item_save", "last", "monthly_report", "search", "export",
    "ask", "insight", "audit", "coach", "multi_unresolved", "image_success", "image_compatibility",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OFFLINE SYNTHETIC Phase 3 benchmarks.")
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1_000, 10_000])
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--mode", choices=("baseline", "optimized"), default="optimized")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = [run_benchmark(size, scenario, iterations=args.iterations, mode=args.mode) for size in args.sizes for scenario in SCENARIOS]
    payload = {"label": "OFFLINE SYNTHETIC", "mode": args.mode, "results": [asdict(result) for result in results]}
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"OFFLINE SYNTHETIC mode={args.mode}")
        for result in results:
            print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

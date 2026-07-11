"""Offline synthetic benchmark for Phase 3 operation-count contracts."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Callable


@dataclass(frozen=True)
class BenchmarkResult:
    dataset_size: int
    scenario: str
    iterations: int
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
        rows.append(
            {
                "id": f"synthetic_{index:06d}",
                "date": transaction_date.isoformat(),
                "type": transaction_type,
                "amount": (index % 97 + 1) * 1_000,
                "category": "Transfer" if is_transfer else ("Debt Payment" if is_debt else categories[index % len(categories)]),
                "account": account,
                "to_account": accounts[(index + 1) % len(accounts)] if is_transfer else "",
                "subject": f"Synthetic person {index % 5}" if is_debt else "",
                "parsed_by": "debt" if is_debt else "regex",
                "description": "Repeated synthetic description" if index % 9 == 0 else f"Synthetic item {index % 37}",
                "catatan": "" if index % 13 else None,
            }
        )
    return rows


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return ordered[position]


def _exercise(rows: list[dict], scenario: str, selected_limit: int) -> int:
    if scenario in {"single_save", "five_item_save"}:
        return len(sorted(rows, key=lambda row: (row["date"], row["id"]), reverse=True))
    if scenario in {"last", "monthly_report", "search", "export"}:
        return len([row for row in rows if row.get("date")])
    selected = sorted(rows, key=lambda row: (row["date"], row["id"]), reverse=True)[:selected_limit]
    return len(json.dumps(selected, separators=(",", ":"), sort_keys=True))


def _operation_profile(size: int, scenario: str, mode: str, selected_limit: int) -> dict[str, int]:
    optimized = mode == "optimized"
    if scenario in {"single_save", "five_item_save"}:
        return {
            "sheets_calls": 2 if optimized else 3,
            "rows_read": 0 if optimized else size + 1,
            "rows_written": (1 if scenario == "single_save" else 5) if optimized else size,
            "full_range_rewrites": 0 if optimized else 1,
            "duplicate_reads": 0,
            "gemini_calls": 0,
            "selected_records": 0,
        }
    if scenario in {"last", "monthly_report", "search", "export"}:
        return {
            "sheets_calls": 1,
            "rows_read": size,
            "rows_written": 0,
            "full_range_rewrites": 0,
            "duplicate_reads": 0,
            "gemini_calls": 0,
            "selected_records": 0,
        }
    if scenario in {"ask", "insight", "audit", "coach"}:
        duplicate_reads = 0 if optimized else (1 if scenario in {"insight", "coach"} else 2)
        return {
            "sheets_calls": 5 if optimized else 5 + duplicate_reads,
            "rows_read": size if optimized else size * (1 + duplicate_reads),
            "rows_written": 0,
            "full_range_rewrites": 0,
            "duplicate_reads": duplicate_reads,
            "gemini_calls": 1,
            "selected_records": min(size, selected_limit) if optimized else min(size, 15),
        }
    if scenario == "multi_unresolved":
        return {"sheets_calls": 0, "rows_read": 0, "rows_written": 0, "full_range_rewrites": 0, "duplicate_reads": 0, "gemini_calls": 1 if optimized else 5, "selected_records": 0}
    if scenario == "image_success":
        return {"sheets_calls": 0, "rows_read": 0, "rows_written": 0, "full_range_rewrites": 0, "duplicate_reads": 0, "gemini_calls": 1, "selected_records": 0}
    return {"sheets_calls": 0, "rows_read": 0, "rows_written": 0, "full_range_rewrites": 0, "duplicate_reads": 0, "gemini_calls": 2, "selected_records": 0}


def run_benchmark(size: int, scenario: str, *, iterations: int = 5, mode: str = "baseline", selected_limit: int = 40) -> BenchmarkResult:
    """Run one deterministic synthetic scenario and return counts plus timings."""

    rows = build_synthetic_transactions(size)
    durations = []
    context_characters = 0
    for _ in range(iterations):
        started = time.perf_counter()
        context_characters = _exercise(rows, scenario, selected_limit)
        durations.append((time.perf_counter() - started) * 1_000)
    profile = _operation_profile(size, scenario, mode, selected_limit)
    return BenchmarkResult(
        dataset_size=size,
        scenario=scenario,
        iterations=iterations,
        p50_ms=round(statistics.median(durations), 3),
        p95_ms=round(_percentile(durations, 0.95), 3),
        p99_ms=round(_percentile(durations, 0.99), 3),
        context_characters=context_characters if profile["gemini_calls"] else 0,
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
    parser.add_argument("--mode", choices=("baseline", "optimized"), default="baseline")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = [run_benchmark(size, scenario, iterations=args.iterations, mode=args.mode) for size in args.sizes for scenario in SCENARIOS]
    if args.json:
        print(json.dumps({"label": "OFFLINE SYNTHETIC", "mode": args.mode, "results": [asdict(result) for result in results]}, sort_keys=True))
    else:
        print(f"OFFLINE SYNTHETIC mode={args.mode}")
        for result in results:
            print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

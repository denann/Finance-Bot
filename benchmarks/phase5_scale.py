"""Offline Phase 5 scale evidence using current services and fake adapters."""

from __future__ import annotations

import argparse
import json
import tracemalloc
from dataclasses import asdict, dataclass

from benchmarks.phase3_synthetic import run_benchmark
from app.config import SHEETS_REQUEST_ROW_BUDGET


DEFAULT_SIZES = (100, 1_000, 10_000, 25_000, 50_000, 100_000)
DEFAULT_SCENARIOS = ("single_save", "last", "monthly_report", "search", "export", "ask")


@dataclass(frozen=True)
class ScaleObservation:
    dataset_size: int
    scenario: str
    measurement: str
    measurement_row_budget: int
    default_row_budget: int
    default_budget_exceeded: bool
    growth_class: str
    sheets_calls: int
    rows_read: int
    rows_written: int
    duplicate_reads: int
    full_range_rewrites: int
    selected_records: int
    context_characters: int
    peak_memory_bytes: int
    local_p50_ms: float


def classify_growth(rows_read: int, rows_written: int, dataset_size: int) -> str:
    """Classify observed adapter transfer growth without using local latency."""

    if rows_read >= dataset_size and dataset_size > 0:
        return "O(N) row transfer"
    if rows_written <= 5 and rows_read == 0:
        return "O(1) application row transfer"
    return "bounded by selected records"


def observe(size: int, scenario: str) -> ScaleObservation:
    """Run one current application scenario against instrumented fake Sheets."""

    tracemalloc.start()
    try:
        measurement_budget = max(SHEETS_REQUEST_ROW_BUDGET, size + 10_000)
        result = run_benchmark(
            size,
            scenario,
            iterations=1,
            mode="optimized",
            row_budget=measurement_budget,
        )
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return ScaleObservation(
        dataset_size=size,
        scenario=scenario,
        measurement="OFFLINE SYNTHETIC OBSERVED APPLICATION",
        measurement_row_budget=measurement_budget,
        default_row_budget=SHEETS_REQUEST_ROW_BUDGET,
        default_budget_exceeded=result.rows_read > SHEETS_REQUEST_ROW_BUDGET,
        growth_class=classify_growth(result.rows_read, result.rows_written, size),
        sheets_calls=result.sheets_calls,
        rows_read=result.rows_read,
        rows_written=result.rows_written,
        duplicate_reads=result.duplicate_reads,
        full_range_rewrites=result.full_range_rewrites,
        selected_records=result.selected_records,
        context_characters=result.context_characters,
        peak_memory_bytes=peak,
        local_p50_ms=result.p50_ms,
    )


def workload_projection(monthly_transactions: int, years: int) -> dict[str, int | str]:
    """Return a labelled planning projection, never an observed capacity claim."""

    return {
        "measurement": "MODELLED WORKLOAD PROJECTION",
        "monthly_transactions": monthly_transactions,
        "years": years,
        "projected_transaction_rows": monthly_transactions * 12 * years,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline Phase 5 scale evidence.")
    parser.add_argument("--sizes", nargs="+", type=int, default=list(DEFAULT_SIZES))
    parser.add_argument("--scenarios", nargs="+", choices=DEFAULT_SCENARIOS, default=list(DEFAULT_SCENARIOS))
    parser.add_argument("--monthly-rates", nargs="+", type=int, default=[100, 500, 2_000])
    parser.add_argument("--years", nargs="+", type=int, default=[1, 3, 5])
    args = parser.parse_args()

    observations = [observe(size, scenario) for size in args.sizes for scenario in args.scenarios]
    projections = [workload_projection(rate, years) for rate in args.monthly_rates for years in args.years]
    print(json.dumps({
        "label": "OFFLINE PHASE 5 EVIDENCE",
        "observations": [asdict(item) for item in observations],
        "projections": projections,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

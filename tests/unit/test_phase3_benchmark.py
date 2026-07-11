"""Deterministic contracts for the Phase 3 synthetic benchmark."""

from benchmarks.phase3_synthetic import build_synthetic_transactions, run_benchmark


def test_synthetic_dataset_is_deterministic_and_contains_required_variation() -> None:
    rows = build_synthetic_transactions(10_000)
    assert len(rows) == 10_000
    assert rows[0]["id"] == "synthetic_000000"
    assert rows[-1]["id"] == "synthetic_009999"
    assert {row["type"] for row in rows} == {"expense", "income", "transfer"}
    assert len({row["account"] for row in rows}) >= 4
    assert any(row["to_account"] for row in rows)
    assert any(row["parsed_by"] == "debt" and row["subject"] for row in rows)
    assert any(row["catatan"] is None for row in rows)


def test_baseline_save_profile_records_full_rewrite_amplification() -> None:
    result = run_benchmark(1_000, "single_save", iterations=1, mode="baseline")
    assert result.sheets_calls == 3
    assert result.rows_read == 1_001
    assert result.rows_written == 1_000
    assert result.full_range_rewrites == 1


def test_optimized_profiles_have_bounded_counts() -> None:
    save = run_benchmark(10_000, "single_save", iterations=1, mode="optimized")
    ai = run_benchmark(10_000, "ask", iterations=1, mode="optimized")
    multi = run_benchmark(10_000, "multi_unresolved", iterations=1, mode="optimized")
    assert (save.rows_read, save.rows_written, save.full_range_rewrites) == (0, 1, 0)
    assert ai.selected_records == 40
    assert ai.duplicate_reads == 0
    assert multi.gemini_calls == 1

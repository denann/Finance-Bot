"""Contracts for Phase 5 scale evidence labels and measured operations."""

from benchmarks.phase5_scale import observe, workload_projection


def test_phase5_observation_executes_current_application_path() -> None:
    save = observe(100, "single_save")
    report = observe(100, "monthly_report")

    assert save.measurement == "OFFLINE SYNTHETIC OBSERVED APPLICATION"
    assert (save.rows_read, save.rows_written, save.full_range_rewrites) == (0, 1, 0)
    assert save.growth_class == "O(1) application row transfer"
    assert report.rows_read >= 100
    assert report.growth_class == "O(N) row transfer"
    assert report.peak_memory_bytes > 0
    assert report.default_budget_exceeded is False


def test_workload_projection_cannot_be_mistaken_for_observation() -> None:
    projection = workload_projection(500, 3)
    assert projection == {
        "measurement": "MODELLED WORKLOAD PROJECTION",
        "monthly_transactions": 500,
        "years": 3,
        "projected_transaction_rows": 18_000,
    }

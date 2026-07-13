"""Offline behavior tests for the owner-facing structured-log reader."""

from __future__ import annotations

import csv

from scripts import view_logs


def test_log_reader_filters_renders_and_exports_csv(tmp_path) -> None:
    """Owner output stays readable while CSV keeps every structured field."""

    source = tmp_path / "finance_bot.log"
    source.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-07-13T03:00:00+00:00","event":"handler_done","correlation_id":"tg-1","duration_ms":12}',
                '{"timestamp":"2026-07-13T03:01:00+00:00","event":"handler_failed","correlation_id":"tg-2","error_type":"TimeoutError","safe_note":"retry later"}',
                "not-json",
            ]
        ),
        encoding="utf-8",
    )

    records, malformed = view_logs.load_records(source)
    errors = view_logs.filtered_records(records, event=None, errors_only=True)

    assert malformed == 1
    assert len(errors) == 1
    table = view_logs.render_table(view_logs.DISPLAY_COLUMNS, view_logs.table_rows(errors, columns=view_logs.DISPLAY_COLUMNS))
    assert "handler_failed" in table
    assert "2026-07-13 10:01:00 WIB" in table

    output = tmp_path / "readable.csv"
    view_logs.write_csv(output, errors)
    with output.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"timestamp": "2026-07-13T03:01:00+00:00", "event": "handler_failed", "correlation_id": "tg-2", "error_type": "TimeoutError", "safe_note": "retry later"}]


def test_table_renderer_clips_wide_metadata() -> None:
    """Long metadata cannot make the default terminal table unreadable."""

    table = view_logs.render_table(["event"], [["x" * 80]], max_width=12)

    assert "x" * 80 not in table
    assert "..." in table

"""Collision-resistant temporary export path tests."""

from __future__ import annotations

import os

from app.bot.handler_parts.health_recurring_export import create_unique_export_temp_path


def test_concurrent_exports_receive_different_temp_paths() -> None:
    """Two exports for the same period cannot overwrite one another."""

    first = create_unique_export_temp_path()
    second = create_unique_export_temp_path()
    try:
        assert first != second
        assert os.path.exists(first)
        assert os.path.exists(second)
        assert os.path.basename(first).startswith("finance_export_")
        assert first.endswith(".csv")
    finally:
        for path in (first, second):
            if os.path.exists(path):
                os.remove(path)

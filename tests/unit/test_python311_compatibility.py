"""Import-level compatibility checks for the Python version used by hosting."""

from __future__ import annotations

from app.application.bulk_input import BulkItem, BulkItemStatus


def test_bulk_item_uses_an_independent_immutable_payload_default() -> None:
    """Dataclass defaults must work on Python 3.11 and not share mutable state."""

    first = BulkItem("one", 0, "input one", BulkItemStatus.READY)
    second = BulkItem("two", 1, "input two", BulkItemStatus.READY)

    assert dict(first.parsed_payload) == {}
    assert first.parsed_payload is not second.parsed_payload
